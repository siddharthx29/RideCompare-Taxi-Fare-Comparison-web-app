from backend.app.services.serviceability import resolve_service_region, resolve_trip_serviceability


def test_goa_coverage_only_allows_configured_regional_provider():
    region, adapters, quote_names = resolve_trip_serviceability(
        "Panaji, Goa, India", 15.4989, 73.8278,
        "Baga Beach, North Goa, India", 15.5553, 73.7517,
        {"city": "Panaji", "state": "Goa", "country_code": "in"},
        {"city": "Baga", "state": "Goa", "country_code": "in"},
    )

    assert region == "Goa"
    assert adapters == ("GoaMiles",)
    assert "Uber Go" not in quote_names
    assert "Ola Mini" not in quote_names
    assert "Rapido Bike" not in quote_names


def test_coverage_rejects_out_of_area_and_unsupported_city():
    assert resolve_service_region("Bangalore", 14.0, 77.0) is None
    assert resolve_service_region("Unsupported City", 18.0, 79.0) is None
    assert resolve_service_region(
        "Village, Kerala, India", 10.1, 76.5,
        {"village": "Village", "state": "Kerala", "country_code": "in"},
    ) is None


def test_trip_requires_pickup_and_drop_in_same_supported_region():
    region, adapters, quote_names = resolve_trip_serviceability(
        "MG Road, Kochi", 9.9723, 76.2784,
        "Bangalore Airport", 13.1986, 77.7066,
    )

    assert region is None
    assert adapters == ()
    assert quote_names == ()