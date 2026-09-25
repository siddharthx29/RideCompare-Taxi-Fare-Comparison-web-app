import urllib.request
import json

def test_city(name, p_name, d_name, p_lat, p_lng, d_lat, d_lng, dist, dur):
    payload = {
        "pickup": p_name,
        "drop": d_name,
        "pickup_lat": p_lat,
        "pickup_lng": p_lng,
        "drop_lat": d_lat,
        "drop_lng": d_lng,
        "distance_km": dist,
        "duration_min": dur
    }
    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/fare/compare",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        comp = data["comparison"]
        print(f"=== {name} ({comp['detectedCity']}, {comp.get('state')}) ===")
        print("Notice:", comp.get("regionalNotice"))
        print("Providers:")
        for p in comp["providers"]:
            print(f"  - {p['provider']}: Rs.{p['actualFare']} | Govt: {p.get('isGovernmentBacked')} | Tag: {p.get('categoryTag')} | ZeroSurge: {p.get('zeroSurge')} | Body: {p.get('regulatoryBody')}")
        print()

if __name__ == "__main__":
    test_city("GOA", "Panaji, Goa", "Baga Beach, Goa", 15.4989, 73.8278, 15.5553, 73.7517, 15.2, 32.0)
    test_city("KOCHI", "MG Road, Kochi", "CIAL Airport, Kochi", 9.9723, 76.2784, 10.1518, 76.3930, 28.5, 52.0)
    test_city("KOLKATA", "Park Street, Kolkata", "Howrah Station, Kolkata", 22.5505, 88.3527, 22.5857, 88.3426, 6.2, 22.0)
    test_city("MUMBAI", "BKC, Mumbai", "Marine Drive, Mumbai", 19.0688, 72.8704, 18.9432, 72.8230, 18.0, 45.0)
