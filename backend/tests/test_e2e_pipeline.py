import urllib.request
import urllib.parse
import json

def test_full_pipeline():
    # 1. Geocode Lulu Mall
    with urllib.request.urlopen("http://127.0.0.1:5000/api/geocode?q=Lulu+Mall") as r:
        lulu_list = json.loads(r.read().decode())
    assert len(lulu_list) > 0, "No results for Lulu Mall"
    lulu = lulu_list[0]

    # 2. Geocode Cochin Airport
    with urllib.request.urlopen("http://127.0.0.1:5000/api/geocode?q=Cochin+Airport") as r:
        airport_list = json.loads(r.read().decode())
    assert len(airport_list) > 0, "No results for Cochin Airport"
    airport = airport_list[0]

    print("Pickup:", lulu["displayName"], f"({lulu['lat']}, {lulu['lng']})")
    print("Destination:", airport["displayName"], f"({airport['lat']}, {airport['lng']})")

    # 3. Query route
    params = urllib.parse.urlencode({
        "start": f"{lulu['lng']},{lulu['lat']}",
        "end": f"{airport['lng']},{airport['lat']}",
        "sourceName": lulu["displayName"],
        "destName": airport["displayName"],
        "sourceAddress": json.dumps(lulu["address"]),
        "destAddress": json.dumps(airport["address"])
    })

    with urllib.request.urlopen(f"http://127.0.0.1:5000/api/route?{params}") as r:
        route_res = json.loads(r.read().decode())

    print("Is Serviceable:", route_res.get("isServiceable"))
    print("Detected City:", route_res.get("comparison", {}).get("detectedCity"))
    print("Distance:", route_res.get("comparison", {}).get("distanceKm"), "km")
    print("Duration:", route_res.get("comparison", {}).get("durationMins"), "mins")
    providers = route_res.get("comparison", {}).get("providers", [])
    print(f"Total Provider Quotes: {len(providers)}")
    for p in providers:
        print(f"  - {p['provider']}: {p.get('currencySymbol', '₹')}{p.get('actualFare')} (ETA: {p.get('etaMinutes')}m)")

if __name__ == "__main__":
    test_full_pipeline()
