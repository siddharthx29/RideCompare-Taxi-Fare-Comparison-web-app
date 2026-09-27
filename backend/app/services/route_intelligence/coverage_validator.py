import re
from typing import Tuple, Optional, Dict, Any, List
from backend.app.services.route_intelligence.models import (
    RouteType,
    RecommendationCategory,
    ConfidenceLevel,
    RouteContext,
    ProviderCoverageRecord,
    MultimodalLeg,
    MultimodalOption,
)


def _normalize(val: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(val or "").lower()).strip()


class CoverageValidator:
    """
    Intelligent Complete-Route Validation & Area Matching Engine.
    Validates whether a provider can realistically complete the entire origin-to-destination
    journey, detects partial coverage, and constructs multimodal route options.
    """

    def validate_complete_route(
        self,
        provider_name: str,
        vehicle_type: str,
        route_context: RouteContext,
        provider_record: Optional[ProviderCoverageRecord] = None
    ) -> Tuple[bool, RecommendationCategory, ConfidenceLevel, str, Optional[str]]:
        """
        Returns:
            eligible: bool (True only for DIRECT full coverage)
            category: RecommendationCategory (DIRECT, PARTIAL, UNSUPPORTED)
            confidence: ConfidenceLevel
            reason: str
            partial_boundary: Optional[str]
        """
        orig_norm = _normalize(route_context.origin_label)
        dest_norm = _normalize(route_context.destination_label)
        dist_km = route_context.distance_km
        r_type = route_context.route_type

        # If no specific provider record, apply conservative heuristics
        if not provider_record:
            if r_type in [RouteType.OUTSTATION, RouteType.INTERCITY]:
                # If name implies outstation/intercity
                if any(k in provider_name.lower() for k in ["outstation", "intercity", "tourist"]):
                    return (
                        True,
                        RecommendationCategory.DIRECT,
                        ConfidenceLevel.MEDIUM,
                        f"Provider supports intercity route for {round(dist_km, 1)} km.",
                        None
                    )
                # If bike or auto
                if any(k in vehicle_type.lower() for k in ["bike", "moto", "auto", "tuk"]):
                    return (
                        False,
                        RecommendationCategory.UNSUPPORTED,
                        ConfidenceLevel.HIGH,
                        f"Destination is outside provider's local operating boundaries. {vehicle_type} does not serve {r_type.value.lower()} routes.",
                        None
                    )

            # Local route default
            return (
                True,
                RecommendationCategory.DIRECT,
                ConfidenceLevel.MEDIUM,
                "Service area covers current local transit corridor.",
                None
            )

        # ==========================================
        # 1. DISTANCE LIMIT CHECK
        # ==========================================
        if dist_km > provider_record.maximum_distance:
            # Check if this represents partial coverage
            covered_limit = provider_record.maximum_distance
            # Identify closest major hub within boundary
            hub = "Local Municipal Boundary"
            if "kochi" in orig_norm:
                hub = "Aluva / Perumbavoor Corridor"
            elif "bangalore" in orig_norm:
                hub = "Bangalore Peripheral Ring Road"
            elif "mumbai" in orig_norm:
                hub = "Thane / Navi Mumbai Exit"

            if provider_record.vehicle_type == "Bike":
                return (
                    False,
                    RecommendationCategory.UNSUPPORTED,
                    ConfidenceLevel.HIGH,
                    f"Destination ({round(dist_km, 1)} km) exceeds Rapido Bike's maximum operating limit ({provider_record.maximum_distance} km). Excluded from direct rides.",
                    hub
                )

            return (
                False,
                RecommendationCategory.PARTIAL,
                ConfidenceLevel.HIGH,
                f"Partial coverage only. {provider_record.name} operates up to {hub} (~{covered_limit} km), but does not provide direct service to {route_context.destination_city or 'destination'}.",
                hub
            )

        # ==========================================
        # 2. OUTSTATION / INTERCITY ROUTE CHECK
        # ==========================================
        if r_type in [RouteType.OUTSTATION, RouteType.INTERCITY]:
            # Provider MUST have intercity or outstation explicitly enabled
            if r_type == RouteType.OUTSTATION and not provider_record.outstation_supported:
                # Local cab or auto trying to go outstation
                hub = provider_record.areas[0] if provider_record.areas else "City Limits"
                return (
                    False,
                    RecommendationCategory.PARTIAL if provider_record.vehicle_type == "Cab" else RecommendationCategory.UNSUPPORTED,
                    ConfidenceLevel.HIGH,
                    f"Destination is outside this provider's operating area. {provider_record.name} is licensed for local {provider_record.coverage_regions[0] if provider_record.coverage_regions else 'city'} transit only.",
                    hub
                )

            if r_type == RouteType.INTERCITY and not (provider_record.intercity_supported or provider_record.outstation_supported):
                return (
                    False,
                    RecommendationCategory.UNSUPPORTED,
                    ConfidenceLevel.HIGH,
                    f"Intercity travel to {route_context.destination_city or 'destination'} is not supported by {provider_record.name}.",
                    None
                )

            # Check supported destinations if defined
            if provider_record.destinations:
                dest_clean = dest_norm
                matched_dest = any(
                    _normalize(d) in dest_clean or dest_clean in _normalize(d)
                    for d in provider_record.destinations
                )
                if matched_dest:
                    return (
                        True,
                        RecommendationCategory.DIRECT,
                        ConfidenceLevel.HIGH,
                        f"Verified direct route. Provider operates regular outstation/intercity service to {route_context.destination_city or 'this destination'}.",
                        None
                    )

            # If general outstation is supported and within distance
            if provider_record.outstation_supported and dist_km >= provider_record.minimum_distance:
                return (
                    True,
                    RecommendationCategory.DIRECT,
                    ConfidenceLevel.HIGH,
                    f"Provider supports complete outstation route from {route_context.origin_city or 'origin'} to {route_context.destination_city or 'destination'}.",
                    None
                )

        # ==========================================
        # 3. AIRPORT TRANSFER CHECK
        # ==========================================
        if r_type == RouteType.AIRPORT_TRANSFER:
            if provider_record.service_type == "airport" or provider_record.intercity_supported:
                return (
                    True,
                    RecommendationCategory.DIRECT,
                    ConfidenceLevel.HIGH,
                    "Provider is authorized for airport pickup, drop-off, and toll access.",
                    None
                )

        # ==========================================
        # 4. LOCAL / URBAN ROUTE CHECK
        # ==========================================
        return (
            True,
            RecommendationCategory.DIRECT,
            ConfidenceLevel.HIGH,
            "Provider actively serves both pickup and drop-off localities.",
            None
        )

    def generate_multimodal_option(
        self,
        route_context: RouteContext,
        currency_symbol: str = "₹"
    ) -> Optional[MultimodalOption]:
        """
        Generate a realistic multimodal itinerary when complete direct transit is
        prohibitive, long-distance, or when users benefit from combining local and intercity transit.
        Conforming to Section 8 & 12.
        """
        r_type = route_context.route_type
        dist_km = route_context.distance_km
        orig = route_context.origin_label.split(",")[0].strip()
        dest = route_context.destination_label.split(",")[0].strip()

        # Generate multimodal for long distance (>45 km) or outstation routes
        if r_type not in [RouteType.OUTSTATION, RouteType.INTERCITY, RouteType.LONG_DISTANCE] and dist_km < 40.0:
            return None

        # Build location-specific transit hub
        norm_orig = _normalize(route_context.origin_label)
        if "kochi" in norm_orig or "ernakulam" in norm_orig:
            hub = "Aluva KSRTC & Metro Transit Terminal"
            hub_dist = min(22.0, max(8.0, dist_km * 0.18))
            leg2_dist = max(10.0, dist_km - hub_dist)
            leg1_fare = round(45 + hub_dist * 13)
            leg2_fare = round(leg2_dist * 2.5)  # Express bus / shared mountain cab
            leg2_provider = "KSRTC Fast Passenger / Hill Highway Bus"
            leg2_type = "Express Transit Bus"
        elif "bangalore" in norm_orig:
            hub = "Majestic Central Bus & Railway Station"
            hub_dist = min(20.0, max(6.0, dist_km * 0.15))
            leg2_dist = max(15.0, dist_km - hub_dist)
            leg1_fare = round(50 + hub_dist * 14)
            leg2_fare = round(leg2_dist * 2.8)
            leg2_provider = "KSRTC Airavat Club Class / Express Intercity"
            leg2_type = "Intercity AC Coach"
        elif "mumbai" in norm_orig:
            hub = "Dadar Asiad / Shivneri Intercity Terminal"
            hub_dist = min(18.0, max(5.0, dist_km * 0.16))
            leg2_dist = max(20.0, dist_km - hub_dist)
            leg1_fare = round(60 + hub_dist * 16)
            leg2_fare = round(leg2_dist * 3.0)
            leg2_provider = "MSRTC Shivneri AC / Intercity Shared Cab"
            leg2_type = "Express Intercity"
        else:
            hub = f"{orig} Central Intercity Terminal"
            hub_dist = min(15.0, max(5.0, dist_km * 0.15))
            leg2_dist = max(10.0, dist_km - hub_dist)
            leg1_fare = round(50 + hub_dist * 14)
            leg2_fare = round(leg2_dist * 2.5)
            leg2_provider = "Regional Intercity Express Service"
            leg2_type = "Intercity Coach / Train"

        leg1_dur = round((hub_dist / 22.0) * 60)
        leg2_dur = round((leg2_dist / 40.0) * 60 + 15)  # includes buffer

        total_fare = leg1_fare + leg2_fare
        total_dur = leg1_dur + leg2_dur

        return MultimodalOption(
            type="MULTIMODAL",
            title=f"Multimodal Route: Local Cab + Express Transit",
            summary=f"Combine a local cab to {hub} with a high-frequency express service directly to {dest}.",
            total_distance_km=round(dist_km, 1),
            total_duration_mins=total_dur,
            total_estimated_fare=total_fare,
            currency_symbol=currency_symbol,
            transfer_count=1,
            recommendation_note="Never hide transfers: this option saves up to 50% compared to a dedicated one-way outstation cab.",
            legs=[
                MultimodalLeg(
                    leg_number=1,
                    mode="Cab / Auto",
                    provider="Local Taxi / Uber Go",
                    vehicle_type="Cab",
                    from_location=orig,
                    to_location=hub,
                    distance_km=round(hub_dist, 1),
                    duration_mins=leg1_dur,
                    estimated_fare=leg1_fare,
                    currency_symbol=currency_symbol,
                    instructions=f"Take a local cab or auto from {orig} to {hub} (approx {leg1_dur} mins)."
                ),
                MultimodalLeg(
                    leg_number=2,
                    mode="Intercity Express",
                    provider=leg2_provider,
                    vehicle_type=leg2_type,
                    from_location=hub,
                    to_location=dest,
                    distance_km=round(leg2_dist, 1),
                    duration_mins=leg2_dur,
                    estimated_fare=leg2_fare,
                    currency_symbol=currency_symbol,
                    instructions=f"Board the express intercity coach from {hub} to {dest} (approx {leg2_dur} mins)."
                )
            ]
        )


# Global singleton validator
coverage_validator = CoverageValidator()
