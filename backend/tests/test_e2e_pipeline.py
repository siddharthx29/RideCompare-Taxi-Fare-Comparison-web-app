import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_full_pipeline():
    # 1. Geocode Lulu Mall
    r = client.get("/api/geocode?q=Lulu+Mall")
    assert r.status_code == 200
    lulu_list = r.json()
    assert len(lulu_list) > 0, "No results for Lulu Mall"
    lulu = lulu_list[0]

    # 2. Geocode Cochin Airport
    r2 = client.get("/api/geocode?q=Cochin+Airport")
    assert r2.status_code == 200
    airport_list = r2.json()
    assert len(airport_list) > 0, "No results for Cochin Airport"
    airport = airport_list[0]

    print("Pickup:", lulu["displayName"], f"({lulu['lat']}, {lulu['lng']})")
    print("Destination:", airport["displayName"], f"({airport['lat']}, {airport['lng']})")

    # 3. Query route
    params = {
        "start": f"{lulu['lng']},{lulu['lat']}",
        "end": f"{airport['lng']},{airport['lat']}",
        "sourceName": lulu["displayName"],
        "destName": airport["displayName"],
        "sourceAddress": json.dumps(lulu["address"]),
        "destAddress": json.dumps(airport["address"])
    }

    r3 = client.get("/api/route", params=params)
    assert r3.status_code == 200
    route_res = r3.json()

    print("Is Serviceable:", route_res.get("isServiceable"))
    print("Detected City:", route_res.get("comparison", {}).get("detectedCity"))
    print("Distance:", route_res.get("comparison", {}).get("distanceKm"), "km")
    print("Duration:", route_res.get("comparison", {}).get("durationMins"), "mins")
    providers = route_res.get("comparison", {}).get("providers", [])
    print(f"Total Provider Quotes: {len(providers)}")
    for p in providers:
        print(f"  - {p['provider']}: {p.get('currencySymbol', '₹')}{p.get('actualFare')} (ETA: {p.get('etaMinutes')}m)")

    assert route_res.get("success") is True
    assert route_res.get("isServiceable") is True
    assert len(providers) >= 3

if __name__ == "__main__":
    test_full_pipeline()
