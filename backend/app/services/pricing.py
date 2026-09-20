import os
import json
import math
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

from ml.inference.predictor import FareIntelligenceEngine

FALLBACK_FARES = {
    "dynamicPricing": {
        "morningPeak": {"startHour": 7, "endHour": 10, "multiplier": 1.4},
        "eveningPeak": {"startHour": 17, "endHour": 21, "multiplier": 1.5},
        "nightCharges": {"startHour": 23, "endHour": 5, "multiplier": 1.25}
    },
    "defaultCity": "Bangalore",
    "cities": {
        "Bangalore": {
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
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    possible_paths = [
        os.path.join(base_dir, "backend", "src", "config", "fares.json"),
        os.path.join(base_dir, "src", "config", "fares.json"),
        os.path.join(base_dir, "backend", "app", "config", "fares.json")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if cfg and "cities" in cfg:
                        return cfg
            except Exception:
                pass
    return FALLBACK_FARES


FARE_CONFIG = load_fares_config()
ml_engine = FareIntelligenceEngine()


def detect_city(source: str, destination: str) -> str:
    text = f"{source} {destination}".lower()
    if any(k in text for k in ['kochi', 'cochin', 'ernakulam']):
        return 'Kochi'
    if any(k in text for k in ['chennai', 'madras']):
        return 'Chennai'
    if 'hyderabad' in text:
        return 'Hyderabad'
    if any(k in text for k in ['mumbai', 'bombay']):
        return 'Mumbai'
    if any(k in text for k in ['delhi', 'noida', 'gurgaon', 'ghaziabad', 'ncr']):
        return 'Delhi'
    return 'Bangalore'


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
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


haversine_km = calculate_haversine_distance


def calculate_fares_for_route(route_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    dist = route_info.get("distance_km", 5.0)
    dur = route_info.get("duration_min", 15.0)
    pickup = route_info.get("pickup_name", "Pickup Location")
    drop = route_info.get("drop_name", "Drop Location")
    lat1 = route_info.get("pickup_lat", 28.6139)
    lng1 = route_info.get("pickup_lng", 77.2090)
    lat2 = route_info.get("drop_lat", 28.7041)
    lng2 = route_info.get("drop_lng", 77.1025)
    
    result = calculate_fares_and_scores(
        distance_km=dist,
        duration_mins=dur,
        source=pickup,
        destination=drop,
        start_lon=lng1,
        start_lat=lat1,
        end_lon=lng2,
        end_lat=lat2
    )
    
    fares = []
    for p in result.get("providers", []):
        fares.append({
            "provider": p.get("provider"),
            "ride_type": p.get("vehicleType"),
            "fare": p.get("actualFare"),
            "eta_minutes": p.get("etaMinutes"),
            "ml_predicted_fare": p.get("predictedFare", p.get("actualFare")),
            "prediction_delta": p.get("predictionDiff", 0),
            "prediction_delta_pct": p.get("predictionDiffPct", 0),
            "pricing_regime": result.get("pricingRegime", "Standard"),
            "confidence_score": p.get("confidenceScore", 90.0),
            "smart_score": p.get("smartScore", 85.0),
            "is_anomaly": p.get("isAnomaly", False),
            "anomaly_reason": p.get("anomalyReason", ""),
            "booking_url": p.get("webLink", "https://m.uber.com")
        })
    return fares


def calculate_fares_and_scores(
    distance_km: float,
    duration_mins: float,
    source: str,
    destination: str,
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    osrm_success: bool = True
) -> Dict[str, Any]:
    city = detect_city(source, destination)
    city_data = FARE_CONFIG.get("cities", {}).get(city) or FARE_CONFIG.get("cities", {}).get("Bangalore") or FALLBACK_FARES["cities"]["Bangalore"]

    peak_multiplier, surge_rule_name = get_surge_multiplier()
    straight_line_distance = calculate_haversine_distance(start_lat, start_lon, end_lat, end_lon)
    detour_distance = max(0.0, distance_km - straight_line_distance)

    toll_estimate = 0.0
    if "toll" in city_data:
        combined = f"{source} {destination}".lower()
        if any(kw in combined for kw in city_data["toll"].get("airportKeywords", [])) and distance_km > 10.0:
            toll_estimate = float(city_data["toll"].get("charge", 120))

    pickup_addr = urllib.parse.quote(source)
    dropoff_addr = urllib.parse.quote(destination)

    providers_config = city_data.get("providers", {})
    raw_provider_records = []

    for name, cfg in providers_config.items():
        d_fare = distance_km * cfg["perKmRate"]
        t_fare = duration_mins * cfg["perMinRate"]
        raw_fare = (cfg["baseFare"] + d_fare + t_fare) * peak_multiplier + cfg["platformFee"] + toll_estimate
        actual_fare = round(raw_fare)

        provider_eta = max(1, round(duration_mins * cfg.get("etaMultiplier", 1.0)))
        cost_per_km = round(actual_fare / max(0.1, distance_km), 1)
        cost_per_min = round(actual_fare / max(1.0, provider_eta), 1)

        lname = name.lower()
        if 'uber' in lname:
            app_link = f"uber://?action=setPickup&pickup[formatted_address]={pickup_addr}&dropoff[formatted_address]={dropoff_addr}"
            web_link = f"https://m.uber.com/ul/?action=setPickup&pickup[formatted_address]={pickup_addr}&dropoff[formatted_address]={dropoff_addr}"
        elif 'ola' in lname:
            app_link = "olacabs://app/launch?pickup=my_location"
            web_link = "https://www.olacabs.com/"
        elif 'rapido' in lname:
            app_link = "rapido://booking"
            web_link = "https://www.rapido.bike/"
        else:
            app_link = "taxifarecompare://booking"
            web_link = f"https://www.google.com/search?q=local+taxi+booking+{city}"

        confidence = 'Low' if not osrm_success else ('Medium' if peak_multiplier > 1.0 else 'High')

        raw_provider_records.append({
            "provider": name,
            "vehicleType": cfg["vehicleType"],
            "vehicle_type": cfg["vehicleType"],
            "distanceKm": round(distance_km, 1),
            "etaMinutes": provider_eta,
            "actualFare": actual_fare,
            "estimatedFare": actual_fare,
            "surgeMultiplier": peak_multiplier,
            "confidence": confidence,
            "costPerKm": cost_per_km,
            "costPerMin": cost_per_min,
            "baseFare": cfg["baseFare"],
            "distanceFare": round(d_fare, 1),
            "durationFare": round(t_fare, 1),
            "platformFee": cfg["platformFee"],
            "tollEstimate": toll_estimate,
            "appDeepLink": app_link,
            "webLink": web_link,
            "rating": cfg.get("rating", 4.0),
            "isCheapest": False,
            "isFastest": False,
            "isMostEfficient": False,
            "isBestValue": False
        })

    ml_input_records = []
    for p in raw_provider_records:
        ml_input_records.append({
            "provider": p["provider"],
            "vehicle_type": p["vehicleType"],
            "distance_km": distance_km,
            "duration_min": duration_mins,
            "actual_fare": p["actualFare"],
            "base_fare": p["baseFare"],
            "platform_fee": p["platformFee"],
            "toll_fee": p["tollEstimate"],
            "surge_multiplier": peak_multiplier,
            "traffic_condition": "Heavy" if peak_multiplier > 1.3 else "Normal",
            "time_of_day": surge_rule_name,
            "eta_minutes": p["etaMinutes"]
        })

    ml_result = ml_engine.rank_and_compare_providers(ml_input_records, osrm_success=osrm_success)
    enriched_ml_map = {item["provider"]: item for item in ml_result.get("providers", [])}

    fares = [p["actualFare"] for p in raw_provider_records]
    times = [p["etaMinutes"] for p in raw_provider_records]
    min_fare = min(fares) if fares else 0
    min_time = min(times) if times else 0

    for p in raw_provider_records:
        ml_item = enriched_ml_map.get(p["provider"], {})
        pred_fare = ml_item.get("predicted_fare", p["actualFare"])
        pred_diff = ml_item.get("prediction_diff", 0)
        pred_diff_pct = ml_item.get("prediction_diff_pct", 0)
        conf_score = ml_item.get("confidence_score", 90.0)
        conf_level = ml_item.get("confidence_level", p["confidence"])
        smart_score = ml_item.get("smart_score", 85.0)

        p["predictedFare"] = pred_fare
        p["predictionDiff"] = pred_diff
        p["predictionDiffPct"] = pred_diff_pct
        p["confidenceScore"] = conf_score
        p["confidenceLevel"] = conf_level
        p["confidence"] = conf_level
        p["clusterId"] = ml_item.get("cluster_id", 0)
        p["clusterLabel"] = ml_item.get("cluster_label", "Standard Transit")
        p["isAnomaly"] = ml_item.get("is_anomaly", False)
        p["anomalyReason"] = ml_item.get("anomaly_reason", "Within standard pricing envelope.")
        p["smartScore"] = smart_score
        p["scoreBreakdown"] = ml_item.get("score_breakdown", {})

        fare_eff = min_fare / p["actualFare"] if p["actualFare"] > 0 else 1.0
        time_eff = min_time / p["etaMinutes"] if p["etaMinutes"] > 0 else 1.0
        route_eff = min(1.0, (straight_line_distance / max(0.1, distance_km)) * (1.08 if p["vehicleType"] == 'Bike' else 1.0))
        
        p["efficiencyScore"] = round((time_eff * 40) + (fare_eff * 40) + (route_eff * 20))
        p["recommendationScore"] = round((fare_eff * 35) + (time_eff * 35) + (route_eff * 10) + ((p["rating"] / 5.0) * 20))

    lowest_fare = min(p["actualFare"] for p in raw_provider_records) if raw_provider_records else 0
    lowest_eta = min(p["etaMinutes"] for p in raw_provider_records) if raw_provider_records else 0
    highest_eff = max(p["efficiencyScore"] for p in raw_provider_records) if raw_provider_records else 0
    highest_smart = max(p["smartScore"] for p in raw_provider_records) if raw_provider_records else 0

    for p in raw_provider_records:
        if p["actualFare"] == lowest_fare:
            p["isCheapest"] = True
        if p["etaMinutes"] == lowest_eta:
            p["isFastest"] = True
        if p["efficiencyScore"] == highest_eff:
            p["isMostEfficient"] = True
        if p["smartScore"] == highest_smart:
            p["isBestValue"] = True

    raw_provider_records.sort(key=lambda x: x["actualFare"])

    cheapest_name = next((p["provider"] for p in raw_provider_records if p["isCheapest"]), raw_provider_records[0]["provider"] if raw_provider_records else "None")
    fastest_name = next((p["provider"] for p in raw_provider_records if p["isFastest"]), raw_provider_records[0]["provider"] if raw_provider_records else "None")
    most_eff_name = next((p["provider"] for p in raw_provider_records if p["isMostEfficient"]), raw_provider_records[0]["provider"] if raw_provider_records else "None")
    best_val_name = next((p["provider"] for p in raw_provider_records if p["isBestValue"]), raw_provider_records[0]["provider"] if raw_provider_records else "None")

    recommended = next((p for p in raw_provider_records if p["provider"] == most_eff_name), raw_provider_records[0] if raw_provider_records else None)
    recommendation_reason = ""
    dist_adv = ""
    time_adv = ""
    cost_adv = ""

    if recommended and raw_provider_records:
        avg_fare = sum(p["actualFare"] for p in raw_provider_records) / len(raw_provider_records)
        avg_time = sum(p["etaMinutes"] for p in raw_provider_records) / len(raw_provider_records)
        max_fare = max(p["actualFare"] for p in raw_provider_records)
        max_time = max(p["etaMinutes"] for p in raw_provider_records)

        cost_diff = avg_fare - recommended["actualFare"]
        time_diff = avg_time - recommended["etaMinutes"]
        recommendation_reason = f"₹{round(abs(cost_diff))} {'cheaper' if cost_diff >= 0 else 'more expensive'} than average • {round(abs(time_diff))} mins {'faster' if time_diff >= 0 else 'slower'} than alternatives • Efficiency Score: {recommended['efficiencyScore']}/100"
        dist_adv = f"Direct road route of {recommended['distanceKm']} km with a minor detour of {round(detour_distance, 1)} km from straight path."
        time_adv = f"Saves {round(max_time - recommended['etaMinutes'])} minutes compared to the slowest transport alternative."
        cost_adv = f"₹{round(max_fare - recommended['actualFare'])} saved compared to the most expensive travel option."

    insights = []
    if len(raw_provider_records) > 1:
        min_p = raw_provider_records[0]
        max_p = raw_provider_records[-1]
        if min_p["provider"] != max_p["provider"]:
            savings = max_p["actualFare"] - min_p["actualFare"]
            insights.append(f"Save up to ₹{savings} by choosing {min_p['provider']} instead of {max_p['provider']}.")

        fastest_p = next((p for p in raw_provider_records if p["isFastest"]), raw_provider_records[0])
        slowest_p = max(raw_provider_records, key=lambda x: x["etaMinutes"])
        if fastest_p["provider"] != slowest_p["provider"]:
            time_saved = slowest_p["etaMinutes"] - fastest_p["etaMinutes"]
            insights.append(f"{fastest_p['provider']} gets you there {time_saved} minutes faster than {slowest_p['provider']}.")

        if most_eff_name != "None":
            insights.append(f"{most_eff_name} is selected as the most efficient provider based on combined cost, speed, and direct road routing.")

        pricing_reg = ml_result.get("insights", {}).get("current_pricing_regime")
        if pricing_reg:
            insights.append(f"Current Route Pricing Regime: {pricing_reg}.")

        anomaly_count = ml_result.get("insights", {}).get("anomaly_count", 0)
        if anomaly_count > 0:
            insights.append(f"⚠️ Anomaly Alert: {anomaly_count} provider fare(s) flagged with unusual pricing variance.")

        if toll_estimate > 0:
            insights.append(f"Includes an estimated Airport Toll charge of ₹{int(toll_estimate)} applied for {city}.")

    fare_spread = ml_result.get("insights", {}).get("fare_spread", round(max(fares) - min(fares), 2) if fares else 0)
    spread_pct = ml_result.get("insights", {}).get("spread_percentage", round((fare_spread / max(1.0, min_fare)) * 100.0, 1) if min_fare > 0 else 0)

    return {
        "distanceKm": round(distance_km, 1),
        "durationMins": round(duration_mins),
        "detectedCity": city,
        "surgeRuleName": surge_rule_name,
        "straightLineDistance": round(straight_line_distance, 1),
        "detourDistance": round(detour_distance, 1),
        "pricingRegime": ml_result.get("insights", {}).get("current_pricing_regime", "Standard City Transit"),
        "fareSpread": fare_spread,
        "spreadPercentage": spread_pct,
        "anomalyCount": ml_result.get("insights", {}).get("anomaly_count", 0),
        "providers": raw_provider_records,
        "recommendations": {
            "cheapest": cheapest_name,
            "fastest": fastest_name,
            "mostEfficient": most_eff_name,
            "bestValue": best_val_name,
            "recommendationReason": recommendation_reason,
            "distanceAdvantage": dist_adv,
            "timeAdvantage": time_adv,
            "costAdvantage": cost_adv
        },
        "insights": insights,
        "modelMetadata": {
            "version": ml_engine.metadata.get("version", "1.0.0"),
            "algorithm": ml_engine.metadata.get("regression_model", "Gradient Boosting Regressor"),
            "r2Score": ml_engine.metadata.get("regression_metrics", {}).get("r2", 0.9803),
            "mae": ml_engine.metadata.get("regression_metrics", {}).get("mae", 20.67)
        }
    }
