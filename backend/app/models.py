
from sqlalchemy import Column, Integer, String
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    commodity = Column(String(100), nullable=False)


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    commodity = Column(String(100), nullable=False)
    target_price = Column(Integer, nullable=False)
    condition = Column(String(10), nullable=False)
    is_active = Column(Integer, default=1)
    is_triggered = Column(Integer, default=0)
    last_checked_price = Column(Integer, nullable=True)
