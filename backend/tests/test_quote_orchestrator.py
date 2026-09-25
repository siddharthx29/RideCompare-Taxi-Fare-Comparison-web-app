import asyncio
from backend.app.services.quote_orchestrator import QuoteOrchestrator


def test_quote_orchestrator_parallel_fetch():
    orchestrator = QuoteOrchestrator()
    quotes = asyncio.run(orchestrator.fetch_all_quotes(
        source="Indiranagar, Bangalore",
        destination="Whitefield, Bangalore",
        distance_km=14.2,
        duration_mins=42.0,
        pickup_lat=12.9716,
        pickup_lng=77.6412,
        drop_lat=12.9698,
        drop_lng=77.7500,
        city="Bangalore",
        surge_multiplier=1.0,
        toll_charge=0.0
    ))

    assert len(quotes) >= 6
    for q in quotes:
        assert q.actual_fare > 0
        assert q.currency == "INR"
        assert q.quote_age_seconds >= 0.0
        assert q.retrieved_at is not None
        assert isinstance(q.is_stale, bool)


def test_route_hash_generation():
    orchestrator = QuoteOrchestrator()
    hash1 = orchestrator.generate_route_hash(12.97159, 77.64121, 12.93519, 77.62448)
    hash2 = orchestrator.generate_route_hash(12.97162, 77.64119, 12.93522, 77.62449)
    # Slight micro-jitter in GPS should hash to same coarse route bucket
    assert hash1 == hash2


def test_volatility_calculation():
    orchestrator = QuoteOrchestrator()
    vol = orchestrator.compute_volatility_metrics(
        provider="Uber Go",
        route_hash="test_hash_123",
        current_fare=284.0,
        db=None
    )
    assert "volatility_score" in vol
    assert "price_trend" in vol
    assert vol["volatility_score"] == "LOW"
