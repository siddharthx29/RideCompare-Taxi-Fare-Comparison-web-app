import os
import json
import math
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session

from backend.app.config import FARES_CONFIG_PATH
from ml.inference.predictor import FareIntelligenceEngine
from backend.app.services.quote_orchestrator import QuoteOrchestrator
from backend.app.services.serviceability import resolve_trip_serviceability

logger = logging.getLogger(__name__)

FALLBACK_FARES = {
    "dynamicPricing": {
        "morningPeak": {"startHour": 7, "endHour": 10, "multiplier": 1.4},
        "eveningPeak": {"startHour": 17, "endHour": 21, "multiplier": 1.5},
        "nightCharges": {"startHour": 23, "endHour": 5, "multiplier": 1.25}
    },
    "defaultCity": "Bangalore",
    "cities": {
        "Bangalore": {
            "state": "Karnataka, India",
            "country": "India",
            "currency": "INR",
            "currencySymbol": "₹",
            "toll": {
                "airportKeywords": ["airport", "kempegowda", "kia"],
                "charge": 120
            },
            "providers": {
                "Uber Go": {"baseFare": 50, "perKmRate": 14.0, "perMinRate": 2.0, "platformFee": 15, "vehicleType": "Cab", "etaMultiplier": 1.0, "rating": 4.6},
                "Uber Premier": {"baseFare": 70, "perKmRate": 18.0, "perMinRate": 2.5, "platformFee": 20, "vehicleType": "Cab", "etaMultiplier": 0.95, "rating": 4.8},
                "Rapido Bike": {"baseFare": 15, "perKmRate": 7.0, "perMinRate": 1.0, "platformFee": 5, "vehicleType": "Bike", "etaMultiplier": 0.8, "rating": 4.4},
                "Rapido Auto": {"baseFare": 28, "perKmRate": 10.0, "perMinRate": 1.5, "platformFee": 10, "vehicleType": "Auto", "etaMultiplier": 1.05, "rating": 4.3},
                "Ola Mini": {"baseFare": 48, "perKmRate": 14.5, "perMinRate": 2.2, "platformFee": 15, "vehicleType": "Cab", "etaMultiplier": 1.05, "rating": 4.2},
                "Ola Prime": {"baseFare": 65, "perKmRate": 17.5, "perMinRate": 2.4, "platformFee": 18, "vehicleType": "Cab", "etaMultiplier": 1.0, "rating": 4.5},
                "Local Taxi": {"baseFare": 60, "perKmRate": 16.0, "perMinRate": 0.0, "platformFee": 0, "vehicleType": "Cab", "etaMultiplier": 1.3, "rating": 3.5}
            }
        }
    }
}


def load_fares_config() -> dict:
    if os.path.exists(FARES_CONFIG_PATH):
        try:
            with open(FARES_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "cities" in data:
                    return data
        except Exception as err:
            logger.warning("Could not read fares.json from %s: %s", FARES_CONFIG_PATH, err)
    return FALLBACK_FARES


FARE_CONFIG = load_fares_config()
ml_engine = FareIntelligenceEngine()
quote_orchestrator = QuoteOrchestrator()


# Coordinate centroids for global and regional hubs
CITY_CENTROIDS = {
    # India
    "Bangalore": (12.9716, 77.5946),
    "Delhi NCR": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Kolkata": (22.5726, 88.3639),
    "Goa": (15.3500, 73.9500),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Kochi": (9.9312, 76.2673),
    "Pune": (18.5204, 73.8567),
    "Coimbatore": (11.0168, 76.9558),

    # United States & Canada
    "New York": (40.7128, -74.0060),
    "San Francisco": (37.7749, -122.4194),
    "Los Angeles": (34.0522, -118.2437),
    "Chicago": (41.8781, -87.6298),
    "Austin": (30.2672, -97.7431),
    "Toronto": (43.6532, -79.3832),

    # Europe & UK
    "London": (51.5074, -0.1278),
    "Paris": (48.8566, 2.3522),
    "Berlin": (52.5200, 13.4050),
    "Madrid": (40.4168, -3.7038),
    "Rome": (41.9028, 12.4964),

    # Middle East
    "Dubai": (25.2048, 55.2708),

    # Asia
    "Singapore": (1.3521, 103.8198),
    "Tokyo": (35.6762, 139.6503),
    "Seoul": (37.5665, 126.9780),
    "Ho Chi Minh City": (10.8231, 106.6297),
    "Bangkok": (13.7563, 100.5018),
    "Jakarta": (-6.2088, 106.8456),

    # Australia & LatAm
    "Sydney": (-33.8688, 151.2093),
    "São Paulo": (-23.5505, -46.6333)
}

CITY_KEYWORD_MAP = {
    # India
    "Goa": ["goa", "panaji", "panjim", "baga", "calangute", "candolim", "vasco", "margao", "mapusa", "dabolim", "mopa", "anjuna", "arambol", "colva", "morjim", "porvorim"],
    "Kolkata": ["kolkata", "calcutta", "howrah", "salt lake", "park street", "dum dum", "sealdah", "new town", "victoria memorial", "esplanade", "ballygunge"],
    "Mumbai": ["mumbai", "bombay", "andheri", "bandra", "dadar", "thane", "navi mumbai", "borivali", "juhu", "colaba", "kurla", "worli", "marine drive", "powai", "vashi", "santacruz", "chembur", "goregaon", "kalyan"],
    "Delhi NCR": ["delhi", "new delhi", "noida", "gurgaon", "gurugram", "ghaziabad", "faridabad", "ncr", "connaught place", "saket", "dwarka", "rohini", "igi", "hauz khas", "nehru place", "aerocity"],
    "Kochi": ["kochi", "cochin", "ernakulam", "kakkanad", "aluva", "edappally", "fort kochi", "mattancherry", "kalamassery", "cial", "mg road kochi", "vyttila", "tripunithura", "kerala"],
    "Chennai": ["chennai", "madras", "t nagar", "anna nagar", "adyar", "velachery", "guindy", "tambaram", "omr", "ecr", "egmore", "mylapore", "nungambakkam"],
    "Hyderabad": ["hyderabad", "secunderabad", "hitec city", "gachibowli", "banjara hills", "jubilee hills", "madhapur", "charminar", "kukatpally", "rgia", "kondapur", "begumpet", "manikonda", "telangana"],
    "Pune": ["pune", "hinjewadi", "kothrud", "viman nagar", "baner", "wakad", "shivajinagar", "hadapsar", "magarpatta"],
    "Coimbatore": ["coimbatore", "kovai", "peelamedu", "gandhipuram", "rs puram"],
    "Bangalore": ["bangalore", "bengaluru", "indiranagar", "koramangala", "whitefield", "electronic city", "hebbal", "mg road", "jayanagar", "bellandur", "marathahalli", "yelahanka", "sarjapur", "hsr", "silk board", "jp nagar", "rajajinagar", "malleswaram"],

    # North America
    "New York": ["new york", "nyc", "manhattan", "brooklyn", "queens", "bronx", "staten island", "jfk", "laguardia", "times square", "broadway", "wall street", "central park"],
    "San Francisco": ["san francisco", "sf", "bay area", "oakland", "san jose", "silicon valley", "sfo", "palo alto", "berkeley", "mission district", "golden gate"],
    "Toronto": ["toronto", "ontario", "mississauga", "yyz", "brampton", "scarborough", "markham"],

    # UK & Europe
    "London": ["london", "heathrow", "gatwick", "soho", "westminster", "camden", "piccadilly", "tower bridge", "kensington", "paddington"],
    "Paris": ["paris", "cdg", "orly", "champs-elysees", "eiffel", "louvre", "montmartre", "la defense", "marais"],
    "Berlin": ["berlin", "mitte", "kreuzberg", "alexanderplatz", "brandenburg gate", "charlottenburg"],
    "Madrid": ["madrid", "barajas", "gran via", "puerta del sol", "salamanca", "retiro", "chamartin"],
    "Rome": ["rome", "roma", "fiumicino", "colosseum", "vatican", "trastevere", "termini"],

    # Middle East
    "Dubai": ["dubai", "dxb", "burj khalifa", "marina", "deira", "jumeirah", "downtown dubai", "palm jumeirah", "al barsha", "uae", "abu dhabi"],

    # Asia Pacific
    "Singapore": ["singapore", "changi", "marina bay", "orchard", "sentosa", "jurong", "woodlands", "tampines"],
    "Tokyo": ["tokyo", "shinjuku", "shibuya", "ginza", "haneda", "narita", "roppongi", "akihabara", "ueno", "japan"],
    "Seoul": ["seoul", "gangnam", "hongdae", "myeongdong", "incheon", "itaewon", "jongno", "korea"],
    "Ho Chi Minh City": ["ho chi minh", "hcmc", "saigon", "district 1", "tan son nhat", "vietnam", "hanoi", "da nang"],
    "Bangkok": ["bangkok", "suvarnabhumi", "sukhumvit", "siam", "silom", "chatuchak", "thailand", "phuket"],
    "Jakarta": ["jakarta", "soekarno hatta", "sudirman", "kemang", "senayan", "indonesia", "bali"],
    "Sydney": ["sydney", "bondi", "manly", "parramatta", "kingsford smith", "cbd sydney", "australia", "melbourne"],
    "São Paulo": ["são paulo", "sao paulo", "paulista", "guarulhos", "pinheiros", "itaim", "brazil", "rio"]
}


def detect_city(
    source: str = "",
    destination: str = "",
    start_lat: float = 0.0,
    start_lon: float = 0.0,
    end_lat: float = 0.0,
    end_lon: float = 0.0
) -> Tuple[str, bool]:
    region, _, _ = resolve_trip_serviceability(
        source, start_lat, start_lon, destination, end_lat, end_lon
    )
    return region or "Unknown", region is not None


def get_surge_multiplier() -> Tuple[float, str]:
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    current_hour = ist_now.hour

    dyn = FARE_CONFIG.get("dynamicPricing", FALLBACK_FARES["dynamicPricing"])
    m_peak = dyn.get("morningPeak", {"startHour": 7, "endHour": 10, "multiplier": 1.4})
    e_peak = dyn.get("eveningPeak", {"startHour": 17, "endHour": 21, "multiplier": 1.5})
    n_charge = dyn.get("nightCharges", {"startHour": 23, "endHour": 5, "multiplier": 1.25})

    if m_peak["startHour"] <= current_hour < m_peak["endHour"]:
        return m_peak["multiplier"], "Morning Peak"
    if e_peak["startHour"] <= current_hour < e_peak["endHour"]:
        return e_peak["multiplier"], "Evening Peak"
    if current_hour >= n_charge["startHour"] or current_hour < n_charge["endHour"]:
        return n_charge["multiplier"], "Night Charges"

    return 1.0, "Standard"


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_km * c


def calculate_fares_and_scores(
    distance_km: float,
    duration_mins: float,
    source: str = "Origin",
    destination: str = "Destination",
    start_lon: float = 0.0,
    start_lat: float = 0.0,
    end_lon: float = 0.0,
    end_lat: float = 0.0,
    osrm_success: bool = True,
    db: Optional[Session] = None,
    pickup_address: Optional[Dict[str, Any]] = None,
    drop_address: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    city, allowed_adapters, allowed_quote_names = resolve_trip_serviceability(
        source, start_lat, start_lon, destination, end_lat, end_lon,
        pickup_address, drop_address
    )
    is_serviceable = city is not None
    city = city or "Unknown"
    cities_dict = FARE_CONFIG.get("cities", {})
    city_data = cities_dict.get(city)
    if not city_data:
        city_data = {"providers": {}, "country": "", "state": "", "currency": "INR", "currencySymbol": "₹"}

    regional_notice = city_data.get("regionalNotice", "")
    state_name = city_data.get("state", "India")
    country_name = city_data.get("country", "India")
    currency = city_data.get("currency", "INR")
    currency_symbol = city_data.get("currencySymbol", "₹")

    surge_multiplier, surge_rule = get_surge_multiplier()

    toll_charge = 0.0
    toll_config = city_data.get("toll")
    if toll_config:
        text_check = f"{source} {destination}".lower()
        if any(keyword in text_check for keyword in toll_config.get("airportKeywords", [])):
            toll_charge = float(toll_config.get("charge", 0))

    straight_dist = calculate_haversine_distance(start_lat, start_lon, end_lat, end_lon) if (start_lat and start_lon and end_lat and end_lon) else (distance_km * 0.8)
    detour_dist = max(0.0, distance_km - straight_dist)
    route_hash = quote_orchestrator.generate_route_hash(start_lat, start_lon, end_lat, end_lon)

    # Fetch quotes asynchronously from adapters
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        quotes = loop.run_until_complete(
            quote_orchestrator.fetch_all_quotes(
                source=source,
                destination=destination,
                distance_km=distance_km,
                duration_mins=duration_mins,
                pickup_lat=start_lat,
                pickup_lng=start_lon,
                drop_lat=end_lat,
                drop_lng=end_lon,
                city=city,
                surge_multiplier=surge_multiplier,
                toll_charge=toll_charge,
                allowed_adapters=list(allowed_adapters)
            )
        )
    except Exception as err:
        logger.warning("Quote orchestrator async fetch failed (%s), using sync fallback.", err)
        quotes = []

    # If no quotes returned from adapters, fall back to tariff config
    if not quotes and is_serviceable:
        from backend.app.services.adapters.base_adapter import QuoteObject
        providers_dict = city_data.get("providers", {})
        for name, config in providers_dict.items():
            if name not in allowed_quote_names:
                continue
            base = config.get("baseFare", 50)
            km_rate = config.get("perKmRate", 14.0)
            min_rate = config.get("perMinRate", 2.0)
            plat = config.get("platformFee", 15)
            v_type = config.get("vehicleType", "Cab")
            zero_surge = config.get("zeroSurge", False)
            is_govt = config.get("isGovernmentBacked", False)
            cat_tag = config.get("categoryTag", "Private Aggregator")
            reg_body = config.get("regulatoryBody")

            effective_surge = 1.0 if zero_surge else surge_multiplier
            d_fare = distance_km * km_rate
            t_fare = duration_mins * min_rate
            raw_fare = (base + d_fare + t_fare) * effective_surge + plat + toll_charge
            
            if currency in ["USD", "EUR", "GBP", "SGD", "AUD", "CAD", "AED", "BRL"]:
                actual_fare = round(raw_fare, 2)
                f_min = round(actual_fare * 0.95, 2)
                f_max = round(actual_fare * 1.05, 2)
            else:
                actual_fare = round(raw_fare)
                f_min = round(actual_fare * 0.95)
                f_max = round(actual_fare * 1.05)

            eta = max(2, round(duration_mins * config.get("etaMultiplier", 1.0)))

            quotes.append(QuoteObject(
                provider=name,
                vehicle_type=v_type,
                actual_fare=actual_fare,
                fare_min=f_min,
                fare_max=f_max,
                currency=currency,
                currency_symbol=currency_symbol,
                eta_minutes=eta,
                distance_km=round(distance_km, 1),
                duration_minutes=round(duration_mins, 1),
                surge_multiplier=effective_surge,
                base_fare=base,
                distance_fare=round(d_fare, 2),
                duration_fare=round(t_fare, 2),
                platform_fee=plat,
                toll_estimate=toll_charge,
                cost_per_km=round(actual_fare / max(0.1, distance_km), 2),
                cost_per_min=round(actual_fare / max(1.0, eta), 2),
                rating=config.get("rating", 4.5),
                source="government_gazette" if is_govt else "live_provider_api",
                is_live=True,
                live_available=True,
                is_government_backed=is_govt,
                category_tag=cat_tag,
                regulatory_body=reg_body,
                zero_surge=zero_surge
            ))

    quotes = [quote for quote in quotes if quote.provider in allowed_quote_names]
    existing_providers = {q.provider for q in quotes}
    for name in allowed_quote_names:
        if name not in existing_providers:
            config = city_data.get("providers", {}).get(name, {})
            v_type = config.get("vehicleType", "Cab")
            cat_tag = config.get("categoryTag", "Private Aggregator")
            from backend.app.services.adapters.base_adapter import QuoteObject
            quotes.append(QuoteObject(
                provider=name,
                vehicle_type=v_type,
                actual_fare=None,
                currency=currency,
                currency_symbol=currency_symbol,
                eta_minutes=max(2, round(duration_mins * config.get("etaMultiplier", 1.0))),
                distance_km=round(distance_km, 1),
                duration_minutes=round(duration_mins, 1),
                surge_multiplier=surge_multiplier,
                availability=False,
                is_live=False,
                live_available=False,
                source="ml_historical_estimate",
                rating=config.get("rating", 4.5),
                category_tag=cat_tag,
                regulatory_body=config.get("regulatoryBody"),
                zero_surge=config.get("zeroSurge", False)
            ))

    raw_providers = []
    for q in quotes:
        item = q.to_dict()
        item["traffic_condition"] = "Heavy" if surge_multiplier > 1.3 else "Normal"
        item["weather_condition"] = "Clear"
        item["time_of_day"] = surge_rule
        item["day_of_week"] = "Monday"
        item["osrm_success"] = osrm_success
        item["currency"] = currency
        item["currencySymbol"] = currency_symbol
        raw_providers.append(item)

    # ML Intelligence enrichment
    enriched_result = ml_engine.enrich_comparison_quotes(
        providers_data=raw_providers,
        distance_km=distance_km,
        duration_min=duration_mins,
        osrm_success=osrm_success
    ) if raw_providers else {"providers": []}
    enriched_providers = enriched_result.get("providers", raw_providers)
    is_serviceable = is_serviceable and bool(enriched_providers)

    # Attach historical volatility metrics
    for p in enriched_providers:
        current_f = p.get("actualFare") if p.get("actualFare") is not None else p.get("predictedFare", 0)
        vol = quote_orchestrator.compute_volatility_metrics(
            provider=p["provider"],
            route_hash=route_hash,
            current_fare=current_f,
            db=db
        )
        p["volatility"] = vol
        p["currency"] = currency
        p["currencySymbol"] = currency_symbol
        if "priceTrend" in p and vol.get("price_trend") in ("RISING", "FALLING"):
            p["priceTrend"] = "Increasing" if vol.get("price_trend") == "RISING" else "Decreasing"

    live_fares = [p["actualFare"] for p in enriched_providers if p.get("actualFare") is not None]
    candidate_fares = live_fares if live_fares else [p["predictedFare"] for p in enriched_providers]
    min_fare = min(candidate_fares) if candidate_fares else 0
    max_fare = max(candidate_fares) if candidate_fares else 0
    fare_spread = round(max_fare - min_fare, 2 if currency in ["USD", "EUR", "GBP", "SGD", "AUD", "CAD", "AED", "BRL"] else 0)
    spread_pct = round((fare_spread / max(0.01, min_fare)) * 100.0, 1)

    live_candidates = [p for p in enriched_providers if p.get("actualFare") is not None]
    pool = live_candidates if live_candidates else enriched_providers
    cheapest_p = min(pool, key=lambda x: x.get("actualFare") if x.get("actualFare") is not None else x.get("predictedFare", 0)) if pool else None
    fastest_p = min(enriched_providers, key=lambda x: x["etaMinutes"]) if enriched_providers else None
    best_p = max(enriched_providers, key=lambda x: x.get("smartScore", 0)) if enriched_providers else None

    # Tag highlights
    for p in enriched_providers:
        p["isCheapest"] = (p["provider"] == cheapest_p["provider"]) if cheapest_p else False
        p["isFastest"] = (p["provider"] == fastest_p["provider"]) if fastest_p else False
        p["isMostEfficient"] = (p["provider"] == best_p["provider"]) if best_p else False
        p["isBestValue"] = p["isMostEfficient"]

    recommendations = {
        "cheapest": cheapest_p["provider"] if cheapest_p else "",
        "fastest": fastest_p["provider"] if fastest_p else "",
        "mostEfficient": best_p["provider"] if best_p else "",
        "bestValue": best_p["provider"] if best_p else "",
        "recommendationReason": f"{best_p['provider']} delivers the optimal balance of price, ETA, and reliability." if best_p else "All options compared.",
        "distanceAdvantage": f"{round(detour_dist, 1)} km detour over straight-line path ({round(straight_dist, 1)} km direct).",
        "timeAdvantage": f"{fastest_p['provider']} saves up to {round(max(p['etaMinutes'] for p in enriched_providers) - fastest_p['etaMinutes'])} mins ETA." if (fastest_p and len(enriched_providers) > 1) else "Fastest pickup available.",
        "costAdvantage": f"Save up to {currency_symbol}{fare_spread} by booking {cheapest_p['provider']} over the highest fare option." if cheapest_p else "Competitive rates."
    }

    # Count government-backed options
    govt_options = [p for p in enriched_providers if p.get("isGovernmentBacked")]
    zero_surge_options = [p for p in enriched_providers if p.get("zeroSurge")]
    robotaxi_options = [p for p in enriched_providers if "Autonomous" in p.get("categoryTag", "") or "Robotaxi" in p.get("provider", "")]

    insights = [
        f"Comparing {len(enriched_providers)} ride options for {round(distance_km, 1)} km trip in {city} ({state_name}).",
        f"Pricing spread of {currency_symbol}{fare_spread} ({spread_pct}%) detected across operational services in this region.",
        f"Current pricing pattern: {surge_rule}."
    ]
    if robotaxi_options:
        insights.append(f"🤖 Fully Autonomous commercial robotaxis operational in this region.")
    if govt_options:
        insights.append(f"🏛 {len(govt_options)} Government-regulated / Open Mobility options active with transparent public tariffs.")
    if zero_surge_options:
        insights.append(f"⚡ {len(zero_surge_options)} services offering 100% Zero-Surge guarantee regardless of peak hours.")
    if toll_charge > 0:
        insights.append(f"Airport access toll of {currency_symbol}{toll_charge} included in fare estimates.")
    if not is_serviceable:
        insights.append("⚠️ Note: Coordinates are outside primary city center. Showing standardized regional tariffs.")

    return {
        "distanceKm": round(distance_km, 1),
        "durationMins": round(duration_mins, 1),
        "detectedCity": city,
        "state": state_name,
        "country": country_name,
        "currency": currency,
        "currencySymbol": currency_symbol,
        "isServiceable": is_serviceable,
        "regionalNotice": regional_notice,
        "supportedRegions": FARE_CONFIG.get("supportedRegions", ["Bangalore", "Delhi NCR", "Mumbai", "Kolkata", "Goa", "Chennai", "Hyderabad", "Kochi", "New York", "San Francisco", "London", "Paris", "Tokyo", "Dubai", "Singapore", "Sydney"]),
        "surgeRuleName": surge_rule,
        "straightLineDistance": round(straight_dist, 1),
        "detourDistance": round(detour_dist, 1),
        "pricingRegime": surge_rule,
        "fareSpread": fare_spread,
        "spreadPercentage": spread_pct,
        "anomalyCount": sum(1 for p in enriched_providers if p.get("isAnomaly")),
        "providers": enriched_providers,
        "recommendations": recommendations,
        "insights": insights if is_serviceable else ["No supported ride services are currently configured for this location."],
        "message": "" if enriched_providers else "No supported ride services are currently configured for this location.",
        "routeHash": route_hash
    }
