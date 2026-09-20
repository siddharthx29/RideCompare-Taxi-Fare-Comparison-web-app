from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Search(Base):
    __tablename__ = 'searches'

    id = Column(Integer, primary_key=True, index=True)
    source = Column(Text, nullable=False)
    destination = Column(Text, nullable=False)
    source_lat = Column(Float, nullable=True)
    source_lng = Column(Float, nullable=True)
    dest_lat = Column(Float, nullable=True)
    dest_lng = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    duration_min = Column(Float, nullable=True)
    cheapest_provider = Column(String(50), nullable=True)
    fastest_provider = Column(String(50), nullable=True)
    best_provider = Column(String(50), nullable=True)
    selected_provider = Column(String(50), nullable=True)
    savings = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Analytics(Base):
    __tablename__ = 'analytics'

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    clicks = Column(Integer, default=0)
    redirects = Column(Integer, default=0)
    fare = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class HistoricalFare(Base):
    __tablename__ = 'historical_fares'

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    vehicle_type = Column(String(30), nullable=False)
    source = Column(Text, nullable=False)
    destination = Column(Text, nullable=False)
    source_lat = Column(Float, nullable=True)
    source_lng = Column(Float, nullable=True)
    dest_lat = Column(Float, nullable=True)
    dest_lng = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=False)
    duration_min = Column(Float, nullable=False)
    actual_fare = Column(Float, nullable=False)
    base_fare = Column(Float, default=0.0)
    surge_multiplier = Column(Float, default=1.0)
    platform_fee = Column(Float, default=0.0)
    toll_fee = Column(Float, default=0.0)
    traffic_condition = Column(String(30), default='Normal')
    weather_condition = Column(String(30), default='Clear')
    time_of_day = Column(String(30), default='Regular')
    day_of_week = Column(String(20), default='Monday')
    fare_per_km = Column(Float, nullable=True)
    fare_per_min = Column(Float, nullable=True)
    cluster_id = Column(Integer, nullable=True)
    cluster_label = Column(String(50), nullable=True)
    is_anomaly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
