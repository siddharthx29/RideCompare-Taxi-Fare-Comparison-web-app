import re
from typing import Dict, Any, Optional, Tuple, List
from backend.app.services.route_intelligence.models import (
    RouteType,
    RouteContext,
)

AIRPORT_KEYWORDS = [
    "airport", "cial", "kia", "kempegowda", "dabolim", "mopa", "manohar",
    "heathrow", "gatwick", "jfk", "sfo", "dxb", "changi", "haneda", "narita",
    "tan son nhat", "dum dum", "nsb", "nedumbassery", "devenahalli"
]

OUTSTATION_DESTINATIONS = {
    "kochi": ["munnar", "thekkady", "vagamon", "alappuzha", "alleppey", "kumarakom", "athirappilly", "idukki", "wayanad", "kovalam", "varkala", "marari"],
    "bangalore": ["mysore", "mysuru", "coorg", "madikeri", "ooty", "nandi hills", "chikmagalur", "bandipur", "kabini", "hampi", "shravanabelagola"],
    "mumbai": ["pune", "lonavala", "khandala", "alibaug", "nashik", "shirdi", "mahabaleshwar", "panchgani", "matheran", "lavasa"],
    "goa": ["dudhsagar", "gokarna", "karwar", "dandeli", "sawantwadi", "amboli", "tarkarli"],
    "delhi": ["agra", "jaipur", "shimla", "rishikesh", "haridwar", "neemrana", "manali"],
    "kolkata": ["digha", "mandarmani", "shantiniketan", "sundarbans", "darjeeling", "siliguri"]
}

INTERCITY_PAIRS = [
    ("kochi", "thrissur"), ("kochi", "kottayam"), ("kochi", "alappuzha"), ("kochi", "palakkad"), ("kochi", "kozhikode"),
    ("bangalore", "mysore"), ("bangalore", "hosur"), ("bangalore", "tumkur"), ("bangalore", "kolar"), ("bangalore", "hassan"),
    ("mumbai", "pune"), ("mumbai", "thane"), ("mumbai", "navi mumbai"), ("mumbai", "nashik"),
    ("chennai", "pondicherry"), ("chennai", "vellore"), ("chennai", "kanchipuram")
]


def _normalize_text(val: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(val or "").lower()).strip()


class RouteClassifier:
    """
    Intelligent Route Classification Engine.
    Categorizes journeys into LOCAL, SHORT_DISTANCE, MEDIUM_DISTANCE,
    LONG_DISTANCE, INTERCITY, OUTSTATION, and AIRPORT_TRANSFER.
    """

    def classify_route(
        self,
        origin_label: str,
        destination_label: str,
        distance_km: float,
        duration_mins: float,
        origin_lat: float = 0.0,
        origin_lng: float = 0.0,
        dest_lat: float = 0.0,
        dest_lng: float = 0.0,
        pickup_address: Optional[Dict[str, Any]] = None,
        drop_address: Optional[Dict[str, Any]] = None,
        detected_city: Optional[str] = None
    ) -> RouteContext:
        norm_orig = _normalize_text(origin_label)
        norm_dest = _normalize_text(destination_label)
        full_text = f"{norm_orig} {norm_dest}"

        # 1. Airport Transfer Detection
        is_airport = any(kw in full_text for kw in AIRPORT_KEYWORDS)
        if is_airport:
            return RouteContext(
                origin_label=origin_label,
                destination_label=destination_label,
                distance_km=distance_km,
                duration_mins=duration_mins,
                route_type=RouteType.AIRPORT_TRANSFER,
                origin_city=detected_city,
                destination_city="Airport",
                is_airport_transfer=True,
                pickup_coords=[origin_lat, origin_lng],
                drop_coords=[dest_lat, dest_lng],
                pickup_address=pickup_address,
                drop_address=drop_address,
                classification_reason="Airport hub corridor detected. Requires luggage-capable and highway-certified transit."
            )

        # 2. Known Outstation Tourist / Hill Station Detection
        # Check if destination matches recognized outstation getaways from the origin
        orig_city_key = (detected_city or "").lower()
        if not orig_city_key:
            for city_key in OUTSTATION_DESTINATIONS:
                if city_key in norm_orig:
                    orig_city_key = city_key
                    break

        known_outstations = OUTSTATION_DESTINATIONS.get(orig_city_key, [])
        is_known_outstation = any(dest in norm_dest for dest in known_outstations)
        
        # General outstation heuristics:
        # Distance > 60 km to a different city/district/hill region, or known outstation pair
        is_hill_or_resort = any(term in norm_dest for term in ["munnar", "ooty", "coorg", "hills", "resort", "thekkady", "wayanad", "idukki", "lonavala"])

        if is_known_outstation or is_hill_or_resort or (distance_km >= 80.0 and ("kerala" in full_text or "karnataka" in full_text or "maharashtra" in full_text)):
            route_type = RouteType.OUTSTATION
            return RouteContext(
                origin_label=origin_label,
                destination_label=destination_label,
                distance_km=distance_km,
                duration_mins=duration_mins,
                route_type=route_type,
                origin_city=detected_city or "Origin",
                destination_city=destination_label.split(",")[0].strip(),
                is_outstation=True,
                is_intercity=True,
                pickup_coords=[origin_lat, origin_lng],
                drop_coords=[dest_lat, dest_lng],
                pickup_address=pickup_address,
                drop_address=drop_address,
                classification_reason=f"Long-distance outstation tourist / hill route detected ({round(distance_km, 1)} km). Local short-range transit and bike taxis are prohibited."
            )

        # 3. Intercity Detection
        # Check known intercity pairs or distance between 45 and 180 km
        is_intercity_pair = any(
            (c1 in norm_orig and c2 in norm_dest) or (c2 in norm_orig and c1 in norm_dest)
            for c1, c2 in INTERCITY_PAIRS
        )

        if is_intercity_pair or distance_km > 55.0:
            return RouteContext(
                origin_label=origin_label,
                destination_label=destination_label,
                distance_km=distance_km,
                duration_mins=duration_mins,
                route_type=RouteType.INTERCITY,
                origin_city=detected_city or "Origin",
                destination_city=destination_label.split(",")[0].strip(),
                is_intercity=True,
                pickup_coords=[origin_lat, origin_lng],
                drop_coords=[dest_lat, dest_lng],
                pickup_address=pickup_address,
                drop_address=drop_address,
                classification_reason=f"Intercity travel across municipal districts ({round(distance_km, 1)} km). Requires highway-cleared cabs or intercity fleet."
            )

        # 4. Long Distance Intra-Region / Peri-Urban (35 - 55 km)
        if distance_km > 35.0:
            return RouteContext(
                origin_label=origin_label,
                destination_label=destination_label,
                distance_km=distance_km,
                duration_mins=duration_mins,
                route_type=RouteType.LONG_DISTANCE,
                origin_city=detected_city or "Metro",
                destination_city=destination_label.split(",")[0].strip(),
                pickup_coords=[origin_lat, origin_lng],
                drop_coords=[dest_lat, dest_lng],
                pickup_address=pickup_address,
                drop_address=drop_address,
                classification_reason=f"Extended peri-urban journey ({round(distance_km, 1)} km). Cabs recommended; bikes and autos suboptimal."
            )

        # 5. Medium Distance (18 - 35 km)
        if distance_km > 18.0:
            return RouteContext(
                origin_label=origin_label,
                destination_label=destination_label,
                distance_km=distance_km,
                duration_mins=duration_mins,
                route_type=RouteType.MEDIUM_DISTANCE,
                origin_city=detected_city or "Metro",
                destination_city=destination_label.split(",")[0].strip(),
                pickup_coords=[origin_lat, origin_lng],
                drop_coords=[dest_lat, dest_lng],
                pickup_address=pickup_address,
                drop_address=drop_address,
                classification_reason=f"Suburban corridor travel ({round(distance_km, 1)} km). Cabs and autos suitable; bike taxis limited."
            )

        # 6. Short Distance (10 - 18 km)
        if distance_km > 10.0:
            return RouteContext(
                origin_label=origin_label,
                destination_label=destination_label,
                distance_km=distance_km,
                duration_mins=duration_mins,
                route_type=RouteType.SHORT_DISTANCE,
                origin_city=detected_city or "Metro",
                destination_city=destination_label.split(",")[0].strip(),
                pickup_coords=[origin_lat, origin_lng],
                drop_coords=[dest_lat, dest_lng],
                pickup_address=pickup_address,
                drop_address=drop_address,
                classification_reason=f"Short-to-medium intra-city trip ({round(distance_km, 1)} km). All standard vehicle types eligible."
            )

        # 7. Local (< 10 km)
        return RouteContext(
            origin_label=origin_label,
            destination_label=destination_label,
            distance_km=distance_km,
            duration_mins=duration_mins,
            route_type=RouteType.LOCAL,
            origin_city=detected_city or "Metro",
            destination_city=destination_label.split(",")[0].strip(),
            pickup_coords=[origin_lat, origin_lng],
            drop_coords=[dest_lat, dest_lng],
            pickup_address=pickup_address,
            drop_address=drop_address,
            classification_reason=f"Short local intra-city transit ({round(distance_km, 1)} km). Urban bikes, autos, and cabs fully operational."
        )


# Global singleton classifier
route_classifier = RouteClassifier()
