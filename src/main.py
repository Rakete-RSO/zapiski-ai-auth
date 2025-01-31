import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from operator import or_
from typing import List

from pydantic import BaseModel
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from strawberry.fastapi import GraphQLRouter
import pybreaker

from src.billing_listener import BillingListener
from src.config import DEVELOPMENT_MODE

# from models import User
from .auth import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)
from .database import create_tables, get_db
from .graphql_schema import schema
from .models import Billing, SubscriptionTier, UpdateSubscription, User
from .schemas import UserLogin

circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=3,  # Max failures before opening the circuit
    reset_timeout=10,  # Wait time before trying again (in seconds)
)

billing_listener = BillingListener()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup code
    create_tables()
    billing_listener.start()
    scheduler.start()  # Start the scheduler
    try:
        yield  # Run the app
    finally:
        scheduler.shutdown()  # Shutdown: Stop the scheduler
        billing_listener.stop()  # Stop the billing listener


app = FastAPI(lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
graphql_app = GraphQLRouter(schema, context_getter=lambda: {"db": next(get_db())})
app.include_router(graphql_app, prefix="/graphql")


@app.post("/update-subscription")
def update_subscription(
    update_request: UpdateSubscription,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Update the subscription tier of the logged-in user.
    """
    try:
        # Verify the token and get the user payload
        payload = verify_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Get the logged-in user
        user = db.query(User).filter(User.username == payload["username"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate the new subscription tier
        if update_request.subscription_tier not in SubscriptionTier:
            raise HTTPException(status_code=400, detail="Invalid subscription tier")

        # Update the user's subscription tier
        user.subscription_tier = update_request.subscription_tier
        db.commit()
        db.refresh(user)

        return {
            "msg": f"Subscription tier updated to {user.subscription_tier.value}",
            "user_id": str(user.id),
            "subscription_tier": user.subscription_tier.value,
        }
    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503, detail="Service unavailable (Circuit Open)"
        )


@app.get("/verify-token")
def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Endpoint to verify the validity of a token.
    It returns information about the token if it is valid.
    """
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    return {"msg": "Token is valid", "token_info": payload}


def validate_password(password: str) -> bool:
    """
    Validate that the password meets the minimum requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Check for uppercase
        return False
    if not re.search(r"[a-z]", password):  # Check for lowercase
        return False
    return True


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        # Check if username or email exists
        db_user = (
            db.query(User)
            .filter(or_(User.username == user.username, User.email == user.email))
            .first()
        )

        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid username")
        if not verify_password(user.password, db_user.password):  # type: ignore
            raise HTTPException(status_code=401, detail="Invalid password")

        # Generate the JWT token
        access_token = create_access_token(
            user_id=db_user.id, username=db_user.username
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503, detail="Service unavailable (Circuit Open)"
        )


@app.post("/register")
def register(user: UserLogin, db: Session = Depends(get_db)):
    try:
        # Check if username or email exists
        db_user = (
            db.query(User)
            .filter(or_(User.username == user.username, User.email == user.email))
            .first()
        )

        if db_user:
            raise HTTPException(status_code=409, detail="Username already exists!")

        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", user.email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        if not validate_password(user.password) and not DEVELOPMENT_MODE:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters long, and include uppercase, lowercase, number, and special character",
            )

        # Hash the password before saving
        hashed_password = hash_password(user.password)

        # Create the new user
        new_user = User(
            username=user.username,
            email=user.email,
            password=hashed_password,
            subscription_tier=SubscriptionTier.Basic,
        )

        # Add to the database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"msg": "User created successfully"}

    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503, detail="Service unavailable (Circuit Open)"
        )


class BillingResponse(BaseModel):
    id: str
    customer_email: str
    amount: float
    currency: str
    payment_intent_id: str
    status: str
    created_at: datetime


@app.get("/billings", response_model=List[BillingResponse])
def get_billings(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Get all billing records for the authenticated user
    """
    try:
        # Verify the token and get the user payload
        payload = verify_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Get the logged-in user
        user = db.query(User).filter(User.username == "Vanja").first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Query billings for the user's email
        billings = db.query(Billing).filter(Billing.customer_email == user.email).all()

        return [
            {
                "id": str(b.id),
                "customer_email": b.customer_email,
                "amount": b.amount,
                "currency": b.currency,
                "payment_intent_id": b.payment_intent_id,
                "status": b.status,
                "created_at": b.created_at,
            }
            for b in billings
        ]
    except pybreaker.CircuitBreakerError:
        raise HTTPException(
            status_code=503, detail="Service unavailable (Circuit Open)"
        )


@app.get("/health-check")
def health_check():
    global grpc_server
    # return status 200
    return {
        "status": "healthy",
        "grpc_server": "running" if grpc_server else "not running",
    }


# Monthly billing service
scheduler = BackgroundScheduler()


def monthly_task():
    """
    Task to check user subscription dates and trigger GET requests.
    """
    with next(get_db()) as db:
        users = db.query(User).all()
        today = datetime.now(timezone.utc).date()

        for user in users:
            if user.subscribed_date and user.subscribed_date == today.day:
                response = requests.get("https://jsonplaceholder.typicode.com/posts/1")
                print(
                    f"Sent request for {user.username}, Status: {response.status_code}"
                )


# Add the monthly job to the scheduler
scheduler.add_job(
    monthly_task, "cron", day="*", hour=0, minute=0
)  # Executes daily at midnight UTC

grpc_server = None

import grpc
from concurrent import futures
from sqlalchemy.orm import Session
from typing import Optional
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from src import user_verification_pb2
from src import user_verification_pb2_grpc

from .database import get_db
from .models import User


class UserVerificationService(user_verification_pb2_grpc.UserVerificationServicer):
    def VerifyUser(self, request, context):
        # Get database session
        db: Session = next(get_db())
        try:
            # Check if user exists
            user: Optional[User] = (
                db.query(User).filter(User.username == request.username).first()
            )
            return user_verification_pb2.UserExistsResponse(exists=user is not None)
        finally:
            db.close()


def serve_grpc():
    logger.debug("gRPC Server starting...")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_verification_pb2_grpc.add_UserVerificationServicer_to_server(
        UserVerificationService(), server
    )
    server.add_insecure_port("0.0.0.0:50051")
    server.start()
    print("gRPC Server: ", server)
    return server


@app.on_event("startup")
async def startup_event():
    """
    Start the scheduler when the application starts.
    """
    scheduler.start()
    global grpc_server
    grpc_server = serve_grpc()


@app.on_event("shutdown")
async def shutdown_event():
    """
    Shut down the scheduler gracefully when the application shuts down.
    """
    scheduler.shutdown()
    global grpc_server
    if grpc_server:
        grpc_server.stop(0)
