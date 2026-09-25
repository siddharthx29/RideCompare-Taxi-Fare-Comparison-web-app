import pytest
from backend.app.services.pricing import calculate_fares_and_scores, detect_city


def test_global_city_detection_and_currencies():
    # Tokyo
    city_tokyo, serviceable_tokyo = detect_city(source="Shinjuku Station", destination="Tokyo Tower", start_lat=35.69, start_lon=139.70, end_lat=35.65, end_lon=139.74)
    assert city_tokyo == "Tokyo"
    assert serviceable_tokyo is True

    comp_tokyo = calculate_fares_and_scores(distance_km=8.0, duration_mins=22.0, source="Shinjuku Station", destination="Tokyo Tower", start_lat=35.69, start_lon=139.70, end_lat=35.65, end_lon=139.74)
    assert comp_tokyo["currency"] == "JPY"
    assert comp_tokyo["currencySymbol"] == "¥"
    provider_names_tokyo = [p["provider"] for p in comp_tokyo["providers"]]
    assert any("GO App" in name for name in provider_names_tokyo)

    # San Francisco (Waymo One Autonomous Robotaxi)
    city_sf, _ = detect_city(source="Mission District", destination="Golden Gate Bridge", start_lat=37.76, start_lon=-122.42, end_lat=37.81, end_lon=-122.47)
    assert city_sf == "San Francisco"
    comp_sf = calculate_fares_and_scores(distance_km=12.0, duration_mins=25.0, source="Mission District", destination="Golden Gate Bridge", start_lat=37.76, start_lon=-122.42, end_lat=37.81, end_lon=-122.47)
    assert comp_sf["currency"] == "USD"
    assert comp_sf["currencySymbol"] == "$"
    provider_names_sf = [p["provider"] for p in comp_sf["providers"]]
    assert any("Waymo" in name for name in provider_names_sf)

    # London (TfL Black Cab)
    city_lon, _ = detect_city(source="Piccadilly Circus", destination="Tower Bridge", start_lat=51.51, start_lon=-0.13, end_lat=51.50, end_lon=-0.07)
    assert city_lon == "London"
    comp_lon = calculate_fares_and_scores(distance_km=6.0, duration_mins=18.0, source="Piccadilly Circus", destination="Tower Bridge", start_lat=51.51, start_lon=-0.13, end_lat=51.50, end_lon=-0.07)
    assert comp_lon["currency"] == "GBP"
    assert comp_lon["currencySymbol"] == "£"
    provider_names_lon = [p["provider"] for p in comp_lon["providers"]]
    assert any("Black Cab" in name for name in provider_names_lon)

    # Dubai (Dubai Taxi DTC / Hala)
    city_dxb, _ = detect_city(source="Burj Khalifa", destination="Dubai Marina", start_lat=25.19, start_lon=55.27, end_lat=25.08, end_lon=55.14)
    assert city_dxb == "Dubai"
    comp_dxb = calculate_fares_and_scores(distance_km=20.0, duration_mins=24.0, source="Burj Khalifa", destination="Dubai Marina", start_lat=25.19, start_lon=55.27, end_lat=25.08, end_lon=55.14)
    assert comp_dxb["currency"] == "AED"
    provider_names_dxb = [p["provider"] for p in comp_dxb["providers"]]
    assert any("Dubai Taxi" in name for name in provider_names_dxb)

    # Singapore (CDG Zig / Grab)
    city_sin, _ = detect_city(source="Marina Bay Sands", destination="Changi Airport", start_lat=1.28, start_lon=103.85, end_lat=1.36, end_lon=103.99)
    assert city_sin == "Singapore"
    comp_sin = calculate_fares_and_scores(distance_km=18.0, duration_mins=20.0, source="Marina Bay Sands", destination="Changi Airport", start_lat=1.28, start_lon=103.85, end_lat=1.36, end_lon=103.99)
    assert comp_sin["currency"] == "SGD"
    assert comp_sin["currencySymbol"] == "S$"
    provider_names_sin = [p["provider"] for p in comp_sin["providers"]]
    assert any("ComfortDelGro" in name or "CDG Zig" in name for name in provider_names_sin)

    # Vietnam (Xanh SM VinFast EV / Grab)
    city_hcm, _ = detect_city(source="District 1, Ho Chi Minh City", destination="Tan Son Nhat Airport", start_lat=10.77, start_lon=106.70, end_lat=10.81, end_lon=106.65)
    assert city_hcm == "Ho Chi Minh City"
    comp_hcm = calculate_fares_and_scores(distance_km=7.5, duration_mins=22.0, source="District 1, Ho Chi Minh City", destination="Tan Son Nhat Airport", start_lat=10.77, start_lon=106.70, end_lat=10.81, end_lon=106.65)
    assert comp_hcm["currency"] == "VND"
    assert comp_hcm["currencySymbol"] == "₫"
    provider_names_hcm = [p["provider"] for p in comp_hcm["providers"]]
    assert any("Xanh SM" in name for name in provider_names_hcm)
