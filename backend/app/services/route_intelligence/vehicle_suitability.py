from typing import Tuple, Optional
from backend.app.services.route_intelligence.models import (
    RouteType,
    SuitabilityLevel,
    RouteContext,
    ProviderCoverageRecord,
)


class VehicleSuitabilityEngine:
    """
    Intelligent Vehicle Suitability Engine.
    Evaluates whether a vehicle category (Bike, Auto, Cab, Intercity Cab, Airport Taxi)
    is realistically suitable and legally compliant for the specific route type and distance.
    """

    def evaluate_suitability(
        self,
        vehicle_type: str,
        route_context: RouteContext,
        provider_record: Optional[ProviderCoverageRecord] = None
    ) -> Tuple[bool, SuitabilityLevel, float, str]:
        """
        Returns:
            is_suitable: bool
            level: SuitabilityLevel ('HIGH', 'MEDIUM', 'LOW', 'UNSUITABLE')
            score: float (0.0 to 1.0)
            reason: str
        """
        v_type_lower = vehicle_type.strip().lower()
        dist_km = route_context.distance_km
        r_type = route_context.route_type

        # ==========================================
        # 1. BIKE / MOTORCYCLE TAXI SUITABILITY
        # ==========================================
        if "bike" in v_type_lower or "moto" in v_type_lower or "two_wheeler" in v_type_lower:
            # Hard exclude on long-distance, outstation, intercity, and airport transfers
            if r_type in [RouteType.LONG_DISTANCE, RouteType.INTERCITY, RouteType.OUTSTATION]:
                return (
                    False,
                    SuitabilityLevel.UNSUITABLE,
                    0.0,
                    f"Rapido Bike / 2-wheeler taxi is not considered for this journey because the service/vehicle type does not support {round(dist_km, 1)} km {r_type.value.lower()} highway routes. Two-wheeler passenger transport is restricted to short urban trips."
                )

            if r_type == RouteType.AIRPORT_TRANSFER:
                return (
                    False,
                    SuitabilityLevel.UNSUITABLE,
                    0.0,
                    f"Bike taxi is unsuitable for airport transfers due to passenger luggage constraints and highway expressway limitations."
                )

            if dist_km > 18.0:
                return (
                    False,
                    SuitabilityLevel.UNSUITABLE,
                    0.0,
                    f"Rapido Bike is excluded for this {round(dist_km, 1)} km trip. Safe urban bike-taxi operating distance is capped at 18 km."
                )

            if dist_km > 12.0:
                return (
                    True,
                    SuitabilityLevel.MEDIUM,
                    0.60,
                    f"Bike taxi is feasible for solo travelers, but rider fatigue increases beyond 12 km ({round(dist_km, 1)} km)."
                )

            return (
                True,
                SuitabilityLevel.HIGH,
                0.92,
                f"Bike taxi is highly suitable for quick, cost-effective short intra-city travel ({round(dist_km, 1)} km)."
            )

        # ==========================================
        # 2. AUTO RICKSHAW / TUKTUK SUITABILITY
        # ==========================================
        if "auto" in v_type_lower or "tuk" in v_type_lower or "three_wheeler" in v_type_lower:
            # Autos cannot do outstation or long-distance intercity highway travel
            if r_type in [RouteType.OUTSTATION, RouteType.INTERCITY] or dist_km > 35.0:
                return (
                    False,
                    SuitabilityLevel.UNSUITABLE,
                    0.0,
                    f"Auto rickshaws are restricted to local municipal zones (max 30-35 km) and cannot operate on {round(dist_km, 1)} km {r_type.value.lower()} routes."
                )

            if r_type == RouteType.AIRPORT_TRANSFER and dist_km > 25.0:
                return (
                    False,
                    SuitabilityLevel.UNSUITABLE,
                    0.0,
                    f"Auto rickshaws are unsuitable for long-distance airport transit ({round(dist_km, 1)} km) due to highway safety and luggage limitations."
                )

            if dist_km > 22.0:
                return (
                    True,
                    SuitabilityLevel.MEDIUM,
                    0.55,
                    f"Auto is feasible but nearing maximum comfortable operating distance for 3-wheelers ({round(dist_km, 1)} km)."
                )

            return (
                True,
                SuitabilityLevel.HIGH,
                0.88,
                f"Auto rickshaw is economical and well-suited for intra-city urban transit ({round(dist_km, 1)} km)."
            )

        # ==========================================
        # 3. INTERCITY & OUTSTATION CABS
        # ==========================================
        is_dedicated_outstation = (
            (provider_record and (provider_record.outstation_supported or provider_record.service_type in ["outstation", "intercity"]))
            or any(term in v_type_lower for term in ["outstation", "intercity", "tourist taxi", "express"])
        )

        if r_type in [RouteType.OUTSTATION, RouteType.INTERCITY]:
            if is_dedicated_outstation:
                return (
                    True,
                    SuitabilityLevel.HIGH,
                    0.98,
                    f"Dedicated {provider_record.category_tag if provider_record else 'Outstation Fleet'} with verified intercity coverage, experienced highway drivers, and luggage capacity."
                )

            # Standard urban cabs on outstation
            if dist_km > 90.0:
                return (
                    False,
                    SuitabilityLevel.UNSUITABLE,
                    0.0,
                    f"Standard intra-city cab is not authorized or equipped for {round(dist_km, 1)} km mountain/outstation travel without an outstation fleet package."
                )

            return (
                True,
                SuitabilityLevel.MEDIUM,
                0.65,
                f"Standard cab can cover medium intercity distance ({round(dist_km, 1)} km), though an Outstation tier is preferred."
            )

        # ==========================================
        # 4. AIRPORT TRANSFER CABS
        # ==========================================
        if r_type == RouteType.AIRPORT_TRANSFER:
            is_airport_fleet = (
                (provider_record and provider_record.service_type == "airport")
                or "airport" in v_type_lower
            )
            if is_airport_fleet:
                return (
                    True,
                    SuitabilityLevel.HIGH,
                    0.96,
                    f"Official airport taxi service with dedicated airport pickup bays and regulated toll handling."
                )
            return (
                True,
                SuitabilityLevel.HIGH,
                0.90,
                f"Comfortable climate-controlled cab with ample luggage trunk capacity for airport transit."
            )

        # ==========================================
        # 5. GENERAL CAB (Local, Short, Medium)
        # ==========================================
        return (
            True,
            SuitabilityLevel.HIGH,
            0.90,
            f"Four-wheeler cab provides optimal comfort, passenger safety, and reliability for this {round(dist_km, 1)} km route."
        )


# Global singleton engine
vehicle_suitability_engine = VehicleSuitabilityEngine()
