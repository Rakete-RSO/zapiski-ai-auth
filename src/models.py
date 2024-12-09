from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
import enum

from .database import Base


class SubscriptionTier(enum.Enum):
    Basic = "Basic"
    Pro = "Pro"
    Premium = "Premium"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    subscribed_date = Column(DateTime, default=func.now())
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.Basic)
