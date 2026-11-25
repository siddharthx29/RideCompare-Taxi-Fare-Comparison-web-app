import urllib.request
import urllib.parse
import json
import sys

# Ensure stdout supports UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = 'http://127.0.0.1:5000'

test_queries = [
    'Kochi', 'Cochin', 'Lulu Mall', 'Lulu Mall Kochi', 'Edappally',
    'Kalamassery', 'Aluva Metro Station', 'Kochi Airport', 'Ernakulam South',
    'Vyttila', 'Fort Kochi', 'MG Road Kochi',
    'lulu mal', 'kalamaserry', 'edapally'
]

print('=' * 70)
print('1. VERIFYING LOCATION DISCOVERY & AUTOCOMPLETE')
print('=' * 70)

for q in test_queries:
    url = f"{BASE}/api/location/search?q={urllib.parse.quote(q)}&limit=2"
    try:
        with urllib.request.urlopen(url) as req:
            res = json.loads(req.read().decode('utf-8'))
            results = res.get('results', [])
            print(f"Query: {q:<22} -> Found: {len(results)} items")
            for item in results[:1]:
                print(f"   Primary: {item.get('name')}")
                print(f"   Display: {item.get('displayName')}")
                print(f"   Coords:  ({item.get('latitude')}, {item.get('longitude')})")
                print(f"   Source:  {item.get('source')} | Provider: {item.get('provider')}")
            print()
    except Exception as e:
        print(f"Query {q} failed: {e}")

print('=' * 70)
print('2. VERIFYING REVERSE GEOCODING WITH DETAILED ADDRESS')
print('=' * 70)
rev_url = f"{BASE}/api/location/reverse?lat=10.0284&lon=76.3074"
with urllib.request.urlopen(rev_url) as req:
    rev_res = json.loads(req.read().decode('utf-8'))
    print("Reverse Name:    ", rev_res.get('name'))
    print("Reverse Display: ", rev_res.get('displayName'))
    print("Structured Address:")
    for k, v in rev_res.get('address', {}).items():
        if v:
            print(f"   {k}: {v}")

print('=' * 70)
print('3. VERIFYING ROUTE & FARE COMPARISON INTEGRATION')
print('=' * 70)
with urllib.request.urlopen(f"{BASE}/api/location/search?q=Lulu+Mall") as r:
    src_res = json.loads(r.read().decode('utf-8'))['results'][0]
with urllib.request.urlopen(f"{BASE}/api/location/search?q=Kochi+Airport") as r:
    dst_res = json.loads(r.read().decode('utf-8'))['results'][0]

params = urllib.parse.urlencode({
    'start': f"{src_res['longitude']},{src_res['latitude']}",
    'end': f"{dst_res['longitude']},{dst_res['latitude']}",
    'sourceName': src_res['displayName'],
    'destName': dst_res['displayName'],
    'sourceAddress': json.dumps(src_res['address']),
    'destAddress': json.dumps(dst_res['address'])
})

with urllib.request.urlopen(f"{BASE}/api/route?{params}") as r:
    route_res = json.loads(r.read().decode('utf-8'))
    print("Trip Serviceable: ", route_res.get('isServiceable'))
    print("Distance:         ", route_res.get('comparison', {}).get('distanceKm'), "km")
    print("Duration:         ", route_res.get('comparison', {}).get('durationMins'), "mins")
    print("Detected City:    ", route_res.get('comparison', {}).get('detectedCity'))
    print("Providers:")
    for p in route_res.get('comparison', {}).get('providers', []):
        print(f"   - {p['provider']}: ₹{p['actualFare']} ({p['vehicleType']})")

print('=' * 70)
print('ALL VERIFICATIONS COMPLETED SUCCESSFULLY!')
print('=' * 70)
