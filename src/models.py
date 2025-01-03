import enum
import uuid

from sqlalchemy import DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class SubscriptionTier(enum.Enum):
    Basic = "Basic"
    Pro = "Pro"
    Premium = "Premium"


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
