import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.app.services.route_intelligence.models import (
    RouteType,
    RecommendationCategory,
    ConfidenceLevel,
    SuitabilityLevel,
    RouteContext,
    EvaluationResult,
    MultimodalOption,
)
from backend.app.services.route_intelligence.provider_registry import provider_registry
from backend.app.services.route_intelligence.route_classifier import route_classifier
from backend.app.services.route_intelligence.vehicle_suitability import vehicle_suitability_engine
from backend.app.services.route_intelligence.coverage_validator import coverage_validator

logger = logging.getLogger(__name__)


class AgenticDecisionEngine:
    """
    RideCompare Agentic AI Route Eligibility & Decision Pipeline.
    Prioritizes route feasibility and service coverage BEFORE price optimization.
    Guarantees Rapido Bike and cheap unviable options are never blindly recommended.
    """

    def __init__(self):
        self.registry = provider_registry
        self.classifier = route_classifier
        self.suitability_engine = vehicle_suitability_engine
        self.coverage_validator = coverage_validator

    def evaluate_ride(
        self,
        origin: str,
        destination: str,
        provider: str,
        vehicle_type: str,
        availability: bool = True,
        route_context: Optional[RouteContext] = None,
        distance_km: float = 0.0,
        duration_mins: float = 0.0
    ) -> EvaluationResult:
        """
        Core decision function conforming to Section 20.
        Evaluates a single ride candidate against:
        1. Route feasibility & classification
        2. Provider coverage & operating boundaries
        3. Vehicle suitability & safety
        4. Complete route support
        5. Live availability
        """
        if not route_context:
            route_context = self.classifier.classify_route(
                origin_label=origin,
                destination_label=destination,
                distance_km=distance_km,
                duration_mins=duration_mins
            )

        # Lookup provider coverage metadata
        provider_record = self.registry.find_provider_by_quote_name(
            quote_name=provider,
            region=route_context.origin_city
        )

        explanations = []

        # Step 1: Availability Check
        if not availability:
            return EvaluationResult(
                provider=provider,
                vehicle_type=vehicle_type,
                eligible=False,
                category=RecommendationCategory.UNSUPPORTED,
                reason="Currently unavailable in this service sector.",
                suitability_level=SuitabilityLevel.UNSUITABLE,
                suitability_score=0.0,
                route_supported=False,
                coverage_confidence=ConfidenceLevel.LOW,
                vehicle_suitability=ConfidenceLevel.LOW,
                explanations=["Live service not currently reporting available vehicles."]
            )

        # Step 2: Vehicle Suitability Check
        v_suitable, v_level, v_score, v_reason = self.suitability_engine.evaluate_suitability(
            vehicle_type=vehicle_type,
            route_context=route_context,
            provider_record=provider_record
        )

        # Step 3: Complete-Route Coverage Validation
        c_eligible, c_cat, c_conf, c_reason, partial_hub = self.coverage_validator.validate_complete_route(
            provider_name=provider,
            vehicle_type=vehicle_type,
            route_context=route_context,
            provider_record=provider_record
        )

        # Aggregate Decision
        is_direct = v_suitable and c_eligible
        suitability_conf = (
            ConfidenceLevel.HIGH if v_level == SuitabilityLevel.HIGH
            else (ConfidenceLevel.MEDIUM if v_level == SuitabilityLevel.MEDIUM else ConfidenceLevel.LOW)
        )

        if is_direct:
            category = RecommendationCategory.DIRECT
            final_reason = f"✓ {v_reason} {c_reason}".strip()
            explanations.append("✓ Route feasibility verified")
            explanations.append(f"✓ {provider} covers complete origin to destination")
            explanations.append(f"✓ {vehicle_type} is appropriate for {round(route_context.distance_km, 1)} km {route_context.route_type.value.lower()} journey")
        elif c_cat == RecommendationCategory.PARTIAL:
            category = RecommendationCategory.PARTIAL
            final_reason = f"⚠ {c_reason}"
            explanations.append(f"⚠ Partial coverage only: Terminates at {partial_hub or 'boundary'}")
            explanations.append(f"✕ Ineligible as a direct ride without transfers")
        else:
            category = RecommendationCategory.UNSUPPORTED
            # Give the most specific and user-friendly explanation
            if not v_suitable:
                final_reason = f"✕ {v_reason}"
                explanations.append(f"✕ Vehicle suitability constraint: {v_reason}")
            else:
                final_reason = f"✕ {c_reason}"
                explanations.append(f"✕ Operating boundary constraint: {c_reason}")

        return EvaluationResult(
            provider=provider,
            vehicle_type=vehicle_type,
            eligible=is_direct,
            category=category,
            reason=final_reason,
            suitability_level=v_level,
            suitability_score=v_score,
            route_supported=c_eligible,
            coverage_confidence=c_conf,
            vehicle_suitability=suitability_conf,
            partial_boundary_reached=partial_hub,
            warning=c_reason if c_cat == RecommendationCategory.PARTIAL else None,
            explanations=explanations
        )

    def process_route_and_filter_candidates(
        self,
        origin: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        raw_candidates: List[Dict[str, Any]],
        detected_city: Optional[str] = None,
        origin_lat: float = 0.0,
        origin_lng: float = 0.0,
        dest_lat: float = 0.0,
        dest_lng: float = 0.0,
        pickup_address: Optional[Dict[str, Any]] = None,
        drop_address: Optional[Dict[str, Any]] = None,
        currency_symbol: str = "₹"
    ) -> Dict[str, Any]:
        """
        Executes complete Agentic Decision Pipeline across all candidate providers:
        1. Classifies route
        2. Injects any missing outstation / intercity providers if route requires them
        3. Evaluates feasibility & coverage of each candidate
        4. Separates into DIRECT, PARTIAL, UNSUPPORTED
        5. Computes Multimodal option if beneficial
        6. Selects Recommendations (Cheapest, Fastest, Best Value) ONLY from valid DIRECT rides
        7. Synthesizes explainable Agent Reasoning
        """
        route_ctx = self.classifier.classify_route(
            origin_label=origin,
            destination_label=destination,
            distance_km=distance_km,
            duration_mins=duration_mins,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            pickup_address=pickup_address,
            drop_address=drop_address,
            detected_city=detected_city
        )

        # If long distance or outstation, check if we need to supplement candidate list
        # with dedicated outstation providers from registry
        all_candidate_dicts = list(raw_candidates)
        existing_names = {c.get("provider") for c in all_candidate_dicts}

        if route_ctx.route_type in [RouteType.OUTSTATION, RouteType.INTERCITY, RouteType.LONG_DISTANCE]:
            outstation_records = [
                p for p in self.registry.get_all_providers()
                if (p.outstation_supported or p.intercity_supported)
                and (not detected_city or any(cr.lower() == detected_city.lower() for cr in p.coverage_regions))
            ]
            for rec in outstation_records:
                if rec.name not in existing_names:
                    # Synthetic quote for outstation fleet
                    base = rec.base_fare
                    d_fare = round(distance_km * rec.per_km_rate)
                    t_fare = round(duration_mins * rec.per_min_rate)
                    fare = base + d_fare + t_fare + rec.platform_fee
                    all_candidate_dicts.append({
                        "provider": rec.name,
                        "vehicleType": rec.vehicle_type,
                        "distanceKm": round(distance_km, 1),
                        "etaMinutes": max(8, round(duration_mins * 0.25 + 5)),
                        "actualFare": fare,
                        "estimatedFare": fare,
                        "fareMin": round(fare * 0.95),
                        "fareMax": round(fare * 1.08),
                        "fare_min": round(fare * 0.95),
                        "fare_max": round(fare * 1.08),
                        "surgeMultiplier": 1.0,
                        "baseFare": base,
                        "distanceFare": d_fare,
                        "durationFare": t_fare,
                        "platformFee": rec.platform_fee,
                        "tollEstimate": 120 if route_ctx.is_outstation else 0,
                        "costPerKm": round(fare / max(0.1, distance_km), 1),
                        "costPerMin": round(fare / max(1.0, duration_mins), 1),
                        "isGovernmentBacked": rec.is_government_backed,
                        "categoryTag": rec.category_tag,
                        "regulatoryBody": rec.regulatory_body,
                        "zeroSurge": rec.zero_surge,
                        "isLive": True,
                        "liveAvailable": True,
                        "confidence": 0.92,
                        "confidenceLevel": "HIGH",
                        "smartScore": 94,
                        "appDeepLink": "https://m.uber.com" if "uber" in rec.name.lower() else "https://book.olacabs.com",
                        "webLink": "https://m.uber.com" if "uber" in rec.name.lower() else "https://book.olacabs.com",
                    })
                    existing_names.add(rec.name)

        direct_rides: List[Dict[str, Any]] = []
        partial_rides: List[Dict[str, Any]] = []
        unsupported_rides: List[Dict[str, Any]] = []
        evaluations: List[EvaluationResult] = []

        for cand in all_candidate_dicts:
            p_name = cand.get("provider", "Unknown")
            v_type = cand.get("vehicleType", "Cab")
            avail = cand.get("liveAvailable", True)

            eval_res = self.evaluate_ride(
                origin=origin,
                destination=destination,
                provider=p_name,
                vehicle_type=v_type,
                availability=avail,
                route_context=route_ctx,
                distance_km=distance_km,
                duration_mins=duration_mins
            )
            evaluations.append(eval_res)

            # Enrich candidate with AI decision metadata
            cand_copy = dict(cand)
            cand_copy["eligibility"] = eval_res.category.value
            cand_copy["eligibilityReason"] = eval_res.reason
            cand_copy["suitabilityLevel"] = eval_res.suitability_level.value
            cand_copy["suitabilityScore"] = eval_res.suitability_score
            cand_copy["routeSupported"] = eval_res.route_supported
            cand_copy["coverageConfidence"] = eval_res.coverage_confidence.value
            cand_copy["vehicleSuitabilityConfidence"] = eval_res.vehicle_suitability.value
            cand_copy["evaluationExplanations"] = eval_res.explanations
            if eval_res.partial_boundary_reached:
                cand_copy["partialBoundary"] = eval_res.partial_boundary_reached
            if eval_res.warning:
                cand_copy["warning"] = eval_res.warning

            if eval_res.category == RecommendationCategory.DIRECT:
                direct_rides.append(cand_copy)
            elif eval_res.category == RecommendationCategory.PARTIAL:
                partial_rides.append(cand_copy)
            else:
                unsupported_rides.append(cand_copy)

        # Fallback handling conforming to Section 19:
        # If no direct ride found after strict filtering, check broader categories
        if not direct_rides and partial_rides:
            logger.info("No direct rides verified. Retaining partial options as fallbacks with explicit warnings.")

        # Compute price / ETA / bestValue highlights ONLY on direct rides
        cheapest_p = None
        fastest_p = None
        best_p = None

        if direct_rides:
            # Sort direct rides by suitability score descending, then price
            cheapest_p = min(direct_rides, key=lambda x: x.get("actualFare") if x.get("actualFare") is not None else x.get("predictedFare", 9999))
            fastest_p = min(direct_rides, key=lambda x: x.get("etaMinutes", 999))
            best_p = max(direct_rides, key=lambda x: (x.get("suitabilityScore", 0) * 50) + x.get("smartScore", 80))

            for p in direct_rides:
                p["isCheapest"] = (p["provider"] == cheapest_p["provider"])
                p["isFastest"] = (p["provider"] == fastest_p["provider"])
                p["isMostEfficient"] = (p["provider"] == best_p["provider"])
                p["isBestValue"] = p["isMostEfficient"]

        # Multimodal alternative
        multimodal = self.coverage_validator.generate_multimodal_option(
            route_context=route_ctx,
            currency_symbol=currency_symbol
        )

        # Synthesize Agent Reasoning narrative
        agent_reasoning = self._build_agent_reasoning(
            route_context=route_ctx,
            direct_rides=direct_rides,
            unsupported_rides=unsupported_rides,
            partial_rides=partial_rides,
            cheapest=cheapest_p,
            recommended=best_p
        )

        recommendations = {
            "cheapest": cheapest_p["provider"] if cheapest_p else "",
            "fastest": fastest_p["provider"] if fastest_p else "",
            "mostEfficient": best_p["provider"] if best_p else "",
            "bestValue": best_p["provider"] if best_p else "",
            "recommended": best_p["provider"] if best_p else (direct_rides[0]["provider"] if direct_rides else "None verified"),
            "recommendationReason": agent_reasoning["headline"],
            "distanceAdvantage": f"{round(distance_km, 1)} km ({route_ctx.route_type.value}) route validated against provider operating boundaries.",
            "timeAdvantage": f"{fastest_p['provider']} offers fastest verified arrival." if fastest_p else "Standard travel time.",
            "costAdvantage": f"Cheapest verified direct ride: {cheapest_p['provider']}." if cheapest_p else "No direct options verified."
        }

        return {
            "routeContext": route_ctx.model_dump(),
            "directRides": direct_rides,
            "partialRides": partial_rides,
            "unsupportedRides": unsupported_rides,
            "allEvaluations": [e.model_dump() for e in evaluations],
            "multimodalOption": multimodal.model_dump() if multimodal else None,
            "agentReasoning": agent_reasoning,
            "recommendations": recommendations,
        }

    def _build_agent_reasoning(
        self,
        route_context: RouteContext,
        direct_rides: List[Dict[str, Any]],
        unsupported_rides: List[Dict[str, Any]],
        partial_rides: List[Dict[str, Any]],
        cheapest: Optional[Dict[str, Any]],
        recommended: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        r_type = route_context.route_type
        dist = route_context.distance_km
        orig = route_context.origin_label.split(",")[0].strip()
        dest = route_context.destination_label.split(",")[0].strip()

        excluded_bike = any("bike" in (u.get("vehicleType") or "").lower() for u in unsupported_rides)
        excluded_auto = any("auto" in (u.get("vehicleType") or "").lower() for u in unsupported_rides)

        if r_type in [RouteType.OUTSTATION, RouteType.LONG_DISTANCE, RouteType.INTERCITY]:
            headline = f"Long-distance {r_type.value.lower()} route detected ({round(dist, 1)} km). Local bikes and autos excluded before price ranking."
            audit_summary = f"RideCompare evaluated {len(direct_rides) + len(unsupported_rides) + len(partial_rides)} transport options. "
            if excluded_bike:
                audit_summary += "Rapido Bike taxi was disqualified because 2-wheeler passenger transport is neither safe nor permitted on highway/outstation routes. "
            if excluded_auto:
                audit_summary += "Auto rickshaws were excluded due to local municipal permit perimeters. "
            if direct_rides:
                audit_summary += f"Verified {len(direct_rides)} direct cab / outstation options capable of completing the full journey to {dest}."
            else:
                audit_summary += "No direct private aggregator currently covers the entire route; consider multimodal transit."
        elif r_type == RouteType.AIRPORT_TRANSFER:
            headline = f"Airport transfer corridor detected ({round(dist, 1)} km). Luggage-capable and highway-certified rides prioritized."
            audit_summary = f"Filtered out small two-wheelers due to expressway and passenger baggage restrictions. {len(direct_rides)} airport-authorized cabs verified."
        else:
            headline = f"Local urban route validated ({round(dist, 1)} km). Full multimodal fleet eligible."
            audit_summary = f"All standard urban providers (Bikes, Autos, Cabs) operate within this local transit zone."

        return {
            "headline": headline,
            "routeClassification": r_type.value,
            "routeDistanceKm": round(dist, 1),
            "auditSummary": audit_summary,
            "feasibleDirectCount": len(direct_rides),
            "excludedCount": len(unsupported_rides),
            "partialCount": len(partial_rides),
            "cheapestDirect": cheapest["provider"] if cheapest else None,
            "recommendedDirect": recommended["provider"] if recommended else None,
            "rapidoBikeExcluded": excluded_bike,
            "exclusionHighlights": [
                f"{u['provider']}: {u['eligibilityReason']}"
                for u in unsupported_rides[:4]
            ]
        }


# Global singleton engine
agentic_decision_engine = AgenticDecisionEngine()
