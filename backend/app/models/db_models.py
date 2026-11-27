from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, Index, UniqueConstraint
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


class FareSnapshot(Base):
    __tablename__ = 'fare_snapshots'

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    route_hash = Column(String(64), nullable=False, index=True)
    vehicle_type = Column(String(30), nullable=False, index=True)
    fare = Column(Float, nullable=False)
    fare_min = Column(Float, nullable=True)
    fare_max = Column(Float, nullable=True)
    eta_minutes = Column(Integer, nullable=False)
    distance_km = Column(Float, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    surge_multiplier = Column(Float, default=1.0)
    traffic_condition = Column(String(30), default='Normal')
    quote_age_seconds = Column(Float, default=0.0)
    is_anomaly = Column(Boolean, default=False)
    cluster_id = Column(Integer, nullable=True)
    cluster_label = Column(String(50), nullable=True)
    predicted_fare = Column(Float, nullable=True)
    confidence_score = Column(Float, default=90.0)
    smart_score = Column(Float, default=85.0)
    source = Column(String(50), default='permitted_tariff')
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True, index=True)
    normalized_query = Column(String(255), index=True, nullable=False)
    place_name = Column(String(255), nullable=False)
    display_name = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    house_number = Column(String(100), nullable=True)
    road = Column(String(255), nullable=True)
    neighbourhood = Column(String(255), nullable=True)
    suburb = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    postcode = Column(String(50), nullable=True)
    country = Column(String(100), default='India')
    provider = Column(String(50), default='mapbox')
    provider_place_id = Column(String(100), index=True, nullable=True)
    search_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.utcnow)


class DemandObservation(Base):
    __tablename__ = 'demand_observations'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    provider = Column(String(50), nullable=False, index=True)
    pickup_zone = Column(String(64), nullable=False, index=True)
    destination_zone = Column(String(64), nullable=True)
    ride_category = Column(String(30), default='Cab')
    observed_fare_if_available = Column(Float, nullable=True)
    observed_demand_signal = Column(Float, nullable=True)
    observed_supply_signal = Column(Float, nullable=True)
    traffic_level = Column(Float, default=1.0)
    distance_km = Column(Float, default=0.0)
    duration_min = Column(Float, default=0.0)
    pricing_pressure_score = Column(Float, default=1.0)
    demand_level = Column(String(20), default='NORMAL')
    confidence = Column(Float, default=0.8)
    source_type = Column(String(50), default='ml_estimate')
    reason = Column(Text, nullable=True)
    actual_observation_when_available = Column(Float, nullable=True)


class FareSubmission(Base):
    __tablename__ = 'fare_submissions'
    __table_args__ = (
        Index('ix_fare_submissions_route_provider_time', 'route_fingerprint', 'provider', 'quotation_timestamp'),
        Index('ix_fare_submissions_status_created', 'submission_status', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    device_fingerprint = Column(String(128), nullable=False, index=True)
    provider = Column(String(30), nullable=False, index=True)
    pickup_location = Column(Text, nullable=False)
    destination_location = Column(Text, nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    vehicle_category = Column(String(50), nullable=False, index=True)
    submitted_fare = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default='INR')
    quotation_timestamp = Column(DateTime, nullable=False, index=True)
    estimated_distance_km = Column(Float, nullable=False)
    estimated_duration_min = Column(Float, nullable=False)
    surge_multiplier = Column(Float, nullable=True)
    additional_fees = Column(Float, nullable=False, default=0.0)
    screenshot_reference = Column(Text, nullable=True)
    route_fingerprint = Column(String(64), nullable=False, index=True)
    submission_status = Column(String(30), nullable=False, default='COMMUNITY_REPORTED', index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class FareVerification(Base):
    __tablename__ = 'fare_verification'

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, nullable=False, index=True)
    verification_method = Column(String(80), nullable=False)
    reference_fare = Column(Float, nullable=True)
    predicted_fare = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=False, default=0.0)
    anomaly_score = Column(Float, nullable=True)
    verification_status = Column(String(30), nullable=False, index=True)
    verification_explanation = Column(Text, nullable=False)
    evidence_count = Column(Integer, nullable=False, default=0)
    verified_at = Column(DateTime, default=datetime.utcnow)


class FareObservation(Base):
    __tablename__ = 'fare_observations'
    __table_args__ = (
        Index('ix_fare_observations_route_provider_vehicle_time', 'route_fingerprint', 'provider', 'vehicle_category', 'observation_timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, nullable=True, index=True)
    provider = Column(String(30), nullable=False, index=True)
    route_fingerprint = Column(String(64), nullable=False, index=True)
    vehicle_category = Column(String(50), nullable=False, index=True)
    observed_fare = Column(Float, nullable=False)
    observation_timestamp = Column(DateTime, nullable=False, index=True)
    evidence_type = Column(String(40), nullable=False)
    verification_status = Column(String(30), nullable=False, index=True)


class CommunityVote(Base):
    __tablename__ = 'community_votes'
    __table_args__ = (
        UniqueConstraint('submission_id', 'device_fingerprint', name='uq_community_vote_submission_device'),
    )

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, nullable=False, index=True)
    device_fingerprint = Column(String(128), nullable=False, index=True)
    vote_type = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = 'model_versions'

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(80), nullable=False, index=True)
    version = Column(String(40), nullable=False)
    training_dataset_version = Column(String(80), nullable=False)
    evaluation_metrics = Column(Text, nullable=False, default='{}')
    deployed_at = Column(DateTime, nullable=True)


class CoverageRegion(Base):
    __tablename__ = 'coverage_regions'

    region_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(10), nullable=False)
    legal_surge_cap = Column(Float, default=2.0)
    auto_rickshaw_metered_available = Column(Boolean, default=True)
    metered_auto_fare = Column(Text, default='{}')
    intercity_enabled = Column(Boolean, default=True)
    geofence_geojson = Column(Text, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ServiceStatus(Base):
    __tablename__ = 'service_statuses'
    __table_args__ = (
        UniqueConstraint('region_id', 'service_name', name='uq_service_status_region_service'),
    )

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(String(50), nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    status = Column(String(30), default='active', index=True)  # 'active', 'suspended', 'unavailable'
    status_reason = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RateCard(Base):
    __tablename__ = 'rate_cards'
    __table_args__ = (
        Index('ix_rate_cards_city_service_ride', 'city', 'service', 'ride_type'),
    )

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    country = Column(String(10), nullable=False)
    service = Column(String(50), nullable=False, index=True)
    ride_type = Column(String(50), nullable=False)
    vehicle_category = Column(String(30), nullable=False)
    base_fare = Column(Float, nullable=False)
    per_km = Column(Float, nullable=False)
    per_min = Column(Float, default=0.0)
    booking_fee = Column(Float, default=0.0)
    min_fare = Column(Float, default=0.0)
    free_km = Column(Float, default=0.0)
    long_distance_threshold = Column(Float, nullable=True)
    long_distance_rate = Column(Float, nullable=True)
    night_multiplier = Column(Float, default=1.0)
    currency = Column(String(10), default='INR')
    currency_symbol = Column(String(5), default='₹')
    tax_pct = Column(Float, default=0.05)
    source_url = Column(Text, nullable=True)
    last_verified_date = Column(String(30), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SeoKeyword(Base):
    __tablename__ = 'seo_keywords'

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(200), unique=True, nullable=False, index=True)
    normalized_keyword = Column(String(200), nullable=False, index=True)
    category = Column(String(40), nullable=False, index=True)  # general, competitor, local, route
    intent = Column(String(40), nullable=False, default='commercial')
    location = Column(String(100), nullable=True, index=True)
    search_volume = Column(Integer, nullable=True)  # Only populated from verified CSV/API data
    keyword_difficulty = Column(Float, nullable=True)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    ctr = Column(Float, nullable=False, default=0.0)
    avg_position = Column(Float, nullable=True)
    mapped_page_slug = Column(String(255), nullable=True, index=True)
    duplicate_of_id = Column(Integer, nullable=True)
    opportunity_score = Column(Float, nullable=False, default=0.0, index=True)
    data_source = Column(String(40), nullable=False, default='seed')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SeoPage(Base):
    __tablename__ = 'seo_pages'

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String(120), unique=True, nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    page_type = Column(String(40), nullable=False, index=True)  # pillar, comparison, city, airport, route, editorial
    target_keyword = Column(String(200), nullable=False)
    secondary_keywords = Column(Text, nullable=False, default='[]')
    location = Column(String(100), nullable=True, index=True)
    search_intent = Column(String(40), nullable=False, default='commercial')
    seo_title = Column(String(255), nullable=False)
    meta_description = Column(Text, nullable=False)
    h1 = Column(String(255), nullable=False)
    content_json = Column(Text, nullable=False, default='{}')
    status = Column(String(30), nullable=False, default='published', index=True)  # draft, published, rejected, archived
    quality_score = Column(Float, nullable=False, default=100.0)
    quality_issues = Column(Text, nullable=False, default='[]')
    canonical_url = Column(String(500), nullable=False)
    is_indexable = Column(Boolean, nullable=False, default=True, index=True)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    ctr = Column(Float, nullable=False, default=0.0)
    avg_position = Column(Float, nullable=True)
    last_audited_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class SeoSearchMetric(Base):
    __tablename__ = 'seo_search_metrics'
    __table_args__ = (
        Index('ix_seo_metrics_date_source', 'date', 'source'),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(20), nullable=False, index=True)
    source = Column(String(30), nullable=False, index=True)  # gsc, bing, ga4
    page_url = Column(String(500), nullable=True, index=True)
    query = Column(String(255), nullable=True, index=True)
    clicks = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    ctr = Column(Float, nullable=False, default=0.0)
    position = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SeoAuditLog(Base):
    __tablename__ = 'seo_audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    run_type = Column(String(30), nullable=False, index=True)  # daily, weekly, monthly, manual
    status = Column(String(20), nullable=False, default='ok')
    summary = Column(Text, nullable=False)
    recommendations_json = Column(Text, nullable=False, default='[]')
    created_at = Column(DateTime, default=datetime.utcnow, index=True)



