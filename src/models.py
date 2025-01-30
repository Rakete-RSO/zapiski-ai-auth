import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pydantic import BaseModel
from .database import Base


class SubscriptionTier(enum.Enum):
    Basic = "Basic"
    Pro = "Pro"
    Premium = "Premium"


class UpdateSubscription(BaseModel):
    subscription_tier: SubscriptionTier


class User(Base):
    __tablename__ = "users"
    __allow_unmapped__ = True

    id: Mapped = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str] = mapped_column()
    subscription_tier: Mapped[str] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.Basic
    )
    subscribed_date: Mapped[DateTime] = mapped_column(DateTime, default=func.now())


class Billing(Base):
    __tablename__ = "billings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    customer_email: Mapped[str] = mapped_column(ForeignKey("users.email"))
    amount: Mapped[float] = mapped_column()
    currency: Mapped[str] = mapped_column()
    payment_intent_id: Mapped[str] = mapped_column()
    client_secret: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
