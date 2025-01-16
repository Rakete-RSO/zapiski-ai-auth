import strawberry
from typing import Optional
from datetime import datetime
from strawberry.types import Info
from sqlalchemy.orm import Session
from .models import User, SubscriptionTier
from .database import get_db
from .auth import verify_access_token

@strawberry.type
class UserType:
    id: str
    username: str
    email: str
    subscription_tier: SubscriptionTier
    subscribed_date: datetime

# Define the Query class
@strawberry.type
class Query:
    @strawberry.field
    def get_user(self, info: Info, access_token: str) -> Optional[UserType]:
        # Verify the access token and get the payload
        payload = verify_access_token(access_token)
        print(payload)
        if not payload:
            return None  # Return None if the token is invalid or expired

        db: Session = info.context["db"]
        user = db.query(User).filter(User.username == payload["username"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")


        # Return the user data
        return UserType(
            id=str(user.id),
            username=user.username,
            email=user.email,
            subscription_tier=user.subscription_tier,
            subscribed_date=user.subscribed_date,
        )

# Define the Mutation class
@strawberry.type
class Mutation:
    @strawberry.mutation
    def register_user(
        self, info: Info, username: str, email: str, password: str
    ) -> str:
        db: Session = info.context["db"]

        # Check if the user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return "User already exists!"

        # Create the new user
        new_user = User(
            username=username,
            email=email,
            password=password,  # Ensure hashing is applied here
            subscription_tier=SubscriptionTier.Basic,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return f"User {username} registered successfully!"

schema = strawberry.Schema(query=Query, mutation=Mutation)
