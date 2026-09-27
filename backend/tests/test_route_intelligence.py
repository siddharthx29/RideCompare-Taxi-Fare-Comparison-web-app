import pytest
from backend.app.services.route_intelligence.models import (
    RouteType,
    RecommendationCategory,
    SuitabilityLevel,
)
from backend.app.services.route_intelligence.route_classifier import route_classifier
from backend.app.services.route_intelligence.vehicle_suitability import vehicle_suitability_engine
from backend.app.services.route_intelligence.coverage_validator import coverage_validator
from backend.app.services.route_intelligence.agentic_decision_engine import agentic_decision_engine
from backend.app.services.pricing import calculate_fares_and_scores


def test_route_classifier_kochi_to_munnar():
    ctx = route_classifier.classify_route(
        origin_label="MG Road, Kochi, Kerala",
        destination_label="Munnar, Idukki, Kerala",
        distance_km=128.5,
        duration_mins=210.0,
        detected_city="Kochi"
    )
    assert ctx.route_type in [RouteType.OUTSTATION, RouteType.LONG_DISTANCE]
    assert ctx.is_outstation is True


def test_route_classifier_local():
    ctx = route_classifier.classify_route(
        origin_label="Kochi, Kerala",
        destination_label="Kakkanad, Kochi, Kerala",
        distance_km=11.2,
        duration_mins=28.0,
        detected_city="Kochi"
    )
    assert ctx.route_type == RouteType.SHORT_DISTANCE or ctx.route_type == RouteType.LOCAL


def test_vehicle_suitability_rapido_bike_excluded_for_outstation():
    ctx = route_classifier.classify_route(
        origin_label="Kochi, Kerala",
        destination_label="Munnar, Kerala",
        distance_km=128.5,
        duration_mins=210.0,
        detected_city="Kochi"
    )
    is_suitable, level, score, reason = vehicle_suitability_engine.evaluate_suitability(
        vehicle_type="Bike",
        route_context=ctx
    )
    assert is_suitable is False
    assert level == SuitabilityLevel.UNSUITABLE
    assert "not considered for this journey" in reason or "unsuitable" in reason.lower()


def test_vehicle_suitability_rapido_bike_accepted_for_short_local():
    ctx = route_classifier.classify_route(
        origin_label="Indiranagar, Bangalore",
        destination_label="Koramangala, Bangalore",
        distance_km=6.5,
        duration_mins=18.0,
        detected_city="Bangalore"
    )
    is_suitable, level, score, reason = vehicle_suitability_engine.evaluate_suitability(
        vehicle_type="Bike",
        route_context=ctx
    )
    assert is_suitable is True
    assert level == SuitabilityLevel.HIGH


def test_auto_rickshaw_excluded_for_long_outstation():
    ctx = route_classifier.classify_route(
        origin_label="Kochi",
        destination_label="Munnar",
        distance_km=128.0,
        duration_mins=200.0,
        detected_city="Kochi"
    )
    is_suitable, level, score, reason = vehicle_suitability_engine.evaluate_suitability(
        vehicle_type="Auto",
        route_context=ctx
    )
    assert is_suitable is False
    assert level == SuitabilityLevel.UNSUITABLE


def test_agentic_decision_never_recommends_rapido_bike_for_kochi_to_munnar():
    raw_candidates = [
        {"provider": "Rapido Bike", "vehicleType": "Bike", "actualFare": 900, "etaMinutes": 200, "distanceKm": 128.0},
        {"provider": "Rapido Auto", "vehicleType": "Auto", "actualFare": 1300, "etaMinutes": 220, "distanceKm": 128.0},
        {"provider": "Uber Go", "vehicleType": "Cab", "actualFare": 2200, "etaMinutes": 210, "distanceKm": 128.0},
        {"provider": "Uber Intercity", "vehicleType": "Cab", "actualFare": 2600, "etaMinutes": 200, "distanceKm": 128.0},
        {"provider": "Kerala Tourism Tourist Taxi", "vehicleType": "Cab", "actualFare": 2900, "etaMinutes": 200, "distanceKm": 128.0},
    ]
    res = agentic_decision_engine.process_route_and_filter_candidates(
        origin="Kochi, Kerala",
        destination="Munnar, Kerala",
        distance_km=128.0,
        duration_mins=210.0,
        raw_candidates=raw_candidates,
        detected_city="Kochi"
    )

    # Rapido Bike MUST be in unsupportedRides, NEVER in directRides
    direct_names = [p["provider"] for p in res["directRides"]]
    unsupported_names = [p["provider"] for p in res["unsupportedRides"]]

    assert "Rapido Bike" not in direct_names
    assert "Rapido Bike" in unsupported_names
    assert "Rapido Auto" not in direct_names

    # Recommended and cheapest must NOT be Rapido Bike
    recs = res["recommendations"]
    assert recs["cheapest"] != "Rapido Bike"
    assert recs["recommended"] != "Rapido Bike"
    assert res["agentReasoning"]["rapidoBikeExcluded"] is True
    assert res["multimodalOption"] is not None


def test_full_pricing_calculation_kochi_munnar_excludes_bike_from_cheapest():
    res = calculate_fares_and_scores(
        distance_km=128.0,
        duration_mins=210.0,
        source="Kochi, Kerala",
        destination="Munnar, Kerala",
        start_lat=9.9312,
        start_lon=76.2673,
        end_lat=10.0889,
        end_lon=77.0595
    )

    assert res["isServiceable"] is True
    assert "directProviders" in res
    assert "excludedProviders" in res
    assert "multimodalOption" in res
    assert "agentReasoning" in res

    # Verify recommendations
    recs = res["recommendations"]
    assert recs["cheapest"] != "Rapido Bike"
    assert "Rapido Bike" not in [p["provider"] for p in res["directProviders"]]

    # Verify Rapido Bike is listed in excludedProviders with clear reason
    excluded_names = [p["provider"] for p in res["excludedProviders"]]
    assert "Rapido Bike" in excluded_names
    rapido_bike_rec = next(p for p in res["excludedProviders"] if p["provider"] == "Rapido Bike")
    assert "not considered for this journey" in rapido_bike_rec["eligibilityReason"] or "unsuitable" in rapido_bike_rec["eligibilityReason"].lower()
