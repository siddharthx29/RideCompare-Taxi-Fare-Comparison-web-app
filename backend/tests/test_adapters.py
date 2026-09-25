import asyncio
from backend.app.services.adapters.provider_adapters import (
    UberAdapter,
    OlaAdapter,
    RapidoAdapter,
    KeralaSavariAdapter,
    GoaMilesAdapter,
    YatriSathiAdapter,
    NammaYatriAdapter,
    LocalTaxiAdapter
)
from backend.app.services.pricing import detect_city, calculate_fares_and_scores


def test_uber_adapter_get_quotes():
    adapter = UberAdapter(enabled=True)
    quotes = asyncio.run(adapter.get_quotes(
        source="Indiranagar, Bangalore",
        destination="Koramangala, Bangalore",
        distance_km=6.5,
        duration_mins=20.0,
        pickup_lat=12.9716,
        pickup_lng=77.6412,
        drop_lat=12.9352,
        drop_lng=77.6245,
        city="Bangalore",
        surge_multiplier=1.0,
        toll_charge=0.0
    ))

    assert len(quotes) == 2
    providers = [q.provider for q in quotes]
    assert "Uber Go" in providers
    assert "Uber Premier" in providers

    uber_go = next(q for q in quotes if q.provider == "Uber Go")
    assert uber_go.actual_fare > 0
    assert uber_go.vehicle_type == "Cab"
    assert uber_go.currency == "INR"
    assert uber_go.retrieved_at is not None
    assert uber_go.expires_at is not None


def test_goa_mobility_restrictions():
    """In Goa, Uber, Ola, and Rapido are prohibited; GoaMiles and GTDC operate."""
    uber = UberAdapter(enabled=True)
    ola = OlaAdapter(enabled=True)
    rapido = RapidoAdapter(enabled=True)
    goa_miles = GoaMilesAdapter(enabled=True)

    # Private commercial apps must return empty in Goa
    assert asyncio.run(uber.get_quotes("Panaji", "Baga Beach", 15.0, 30.0, 15.49, 73.82, 15.55, 73.75, "Goa")) == []
    assert asyncio.run(ola.get_quotes("Panaji", "Baga Beach", 15.0, 30.0, 15.49, 73.82, 15.55, 73.75, "Goa")) == []
    assert asyncio.run(rapido.get_quotes("Panaji", "Baga Beach", 15.0, 30.0, 15.49, 73.82, 15.55, 73.75, "Goa")) == []

    # GoaMiles and GTDC must provide authorized quotes
    quotes = asyncio.run(goa_miles.get_quotes("Panaji", "Baga Beach", 15.0, 30.0, 15.49, 73.82, 15.55, 73.75, "Goa"))
    assert len(quotes) == 3
    names = [q.provider for q in quotes]
    assert "GoaMiles Hatchback" in names
    assert "GTDC Tourist Taxi" in names
    gtdc = next(q for q in quotes if q.provider == "GTDC Tourist Taxi")
    assert gtdc.is_government_backed is True
    assert gtdc.zero_surge is True


def test_mumbai_transport_regulations():
    """In Mumbai, Rapido Bike is restricted by Maharashtra RTO, but Kaali Peeli and Cool Cabs operate."""
    rapido = RapidoAdapter(enabled=True)
    local_taxi = LocalTaxiAdapter(enabled=True)

    rapido_quotes = asyncio.run(rapido.get_quotes("BKC", "Marine Drive", 18.0, 45.0, 19.06, 72.87, 18.94, 72.82, "Mumbai"))
    # Rapido Bike should NOT be offered in Mumbai
    assert all(q.provider != "Rapido Bike" for q in rapido_quotes)
    assert any(q.provider == "Rapido Auto" for q in rapido_quotes)

    mumbai_taxis = asyncio.run(local_taxi.get_quotes("BKC", "Marine Drive", 18.0, 45.0, 19.06, 72.87, 18.94, 72.82, "Mumbai"))
    assert len(mumbai_taxis) >= 2
    names = [q.provider for q in mumbai_taxis]
    assert "Mumbai Kaali Peeli" in names
    assert "Mumbai Cool Cab" in names
    kaali_peeli = next(q for q in mumbai_taxis if q.provider == "Mumbai Kaali Peeli")
    assert kaali_peeli.is_government_backed is True
    assert kaali_peeli.zero_surge is True


def test_kerala_savari_adapter():
    """Kerala Savari operates in Kerala under Labour Dept with zero surge guarantee."""
    adapter = KeralaSavariAdapter(enabled=True)
    quotes = asyncio.run(adapter.get_quotes("MG Road Kochi", "CIAL Airport", 30.0, 50.0, 9.97, 76.27, 10.15, 76.39, "Kochi"))
    assert len(quotes) == 2
    names = [q.provider for q in quotes]
    assert "Kerala Savari Auto" in names
    assert "Kerala Savari Cab" in names
    cab = next(q for q in quotes if q.provider == "Kerala Savari Cab")
    assert cab.is_government_backed is True
    assert cab.zero_surge is True
    assert "Kerala Labour" in cab.regulatory_body


def test_yatri_sathi_kolkata_adapter():
    """Yatri Sathi operates in Kolkata under West Bengal Govt with zero surge."""
    adapter = YatriSathiAdapter(enabled=True)
    quotes = asyncio.run(adapter.get_quotes("Park Street", "Howrah Station", 6.0, 20.0, 22.55, 88.35, 22.58, 88.34, "Kolkata"))
    assert len(quotes) == 2
    names = [q.provider for q in quotes]
    assert "Yatri Sathi Meter Taxi" in names
    assert "Kolkata Yellow Taxi" in names
    ys = next(q for q in quotes if q.provider == "Yatri Sathi Meter Taxi")
    assert ys.is_government_backed is True
    assert ys.zero_surge is True


def test_detect_city_coordinates_and_keywords():
    # Coords matching Goa centroid
    city, serviceable = detect_city(start_lat=15.4989, start_lon=73.8278, end_lat=15.5553, end_lon=73.7517)
    assert city == "Goa"
    assert serviceable is True

    # Coords matching Kolkata
    city, serviceable = detect_city(start_lat=22.5726, start_lon=88.3639, end_lat=22.5505, end_lon=88.3527)
    assert city == "Kolkata"
    assert serviceable is True

    # Keywords matching Mumbai
    city, serviceable = detect_city(source="Bandra Kurla Complex", destination="Marine Drive")
    assert city == "Mumbai"
    assert serviceable is True


def test_disabled_adapter_returns_empty():
    adapter = UberAdapter(enabled=False)
    quotes = asyncio.run(adapter.get_quotes(
        source="A",
        destination="B",
        distance_km=5.0,
        duration_mins=15.0,
        pickup_lat=12.9,
        pickup_lng=77.6,
        drop_lat=12.95,
        drop_lng=77.65,
        city="Bangalore"
    ))
    assert quotes == []

