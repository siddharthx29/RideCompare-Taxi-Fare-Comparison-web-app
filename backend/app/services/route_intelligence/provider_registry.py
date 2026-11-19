import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.app.services.route_intelligence.models import (
    ProviderCoverageRecord,
    ConfidenceLevel,
)

logger = logging.getLogger(__name__)

DEFAULT_COVERAGE_PATH = Path(__file__).resolve().parents[2] / "config" / "provider_coverage_registry.json"


class ProviderRegistry:
    """
    Dynamic Provider Knowledge Repository.
    Maintains a configurable catalog of transportation providers, operating ranges,
    service types, covered regions, intercity/outstation routes, and distance limits.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_COVERAGE_PATH
        self._providers: Dict[str, ProviderCoverageRecord] = {}
        self._load_defaults()
        if self.config_path.exists():
            self._load_from_file(self.config_path)

    def _load_defaults(self):
        """Populate initial comprehensive provider catalog."""
        default_records = [
            # ==========================================
            # KOCHI / KERALA FLEET
            # ==========================================
            ProviderCoverageRecord(
                id="rapido_bike_kochi",
                name="Rapido Bike",
                vehicle_type="Bike",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Edappally", "Fort Kochi", "Aluva", "Vyttila", "Tripunithura", "Kalamassery"],
                supported_routes=["Kochi Local", "Ernakulam - Kakkanad", "Vyttila - Edappally"],
                destinations=["Kakkanad", "Edappally", "Aluva", "Fort Kochi", "Mattancherry", "Vyttila"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=18.0,
                base_fare=15.0,
                per_km_rate=7.0,
                per_min_rate=1.0,
                platform_fee=5.0,
                rating=4.3,
                restrictions=["Intra-city short trips only", "Max 18 km", "No highway/intercity/outstation routes", "Single passenger only"]
            ),
            ProviderCoverageRecord(
                id="rapido_auto_kochi",
                name="Rapido Auto",
                vehicle_type="Auto",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Edappally", "Fort Kochi", "Aluva", "Vyttila", "Tripunithura"],
                supported_routes=["Kochi Municipal Zone"],
                destinations=["Kakkanad", "Edappally", "Aluva", "Fort Kochi", "Vyttila"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=30.0,
                base_fare=25.0,
                per_km_rate=9.5,
                per_min_rate=1.2,
                platform_fee=8.0,
                rating=4.2,
                restrictions=["City municipal bounds only", "Max 30 km", "No outstation routes"]
            ),
            ProviderCoverageRecord(
                id="kerala_savari_auto_kochi",
                name="Kerala Savari Auto",
                vehicle_type="Auto",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Edappally", "Fort Kochi", "Aluva", "Vyttila", "Tripunithura"],
                supported_routes=["Kochi Corporation Limits"],
                destinations=["Kakkanad", "Edappally", "Aluva", "Vyttila"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=25.0,
                base_fare=25.0,
                per_km_rate=12.0,
                per_min_rate=0.0,
                platform_fee=2.0,
                rating=4.7,
                is_government_backed=True,
                category_tag="Govt-Backed",
                regulatory_body="Govt of Kerala Labour Department",
                zero_surge=True,
                restrictions=["Municipal zone only", "Zero surge regulated"]
            ),
            ProviderCoverageRecord(
                id="kerala_savari_cab_kochi",
                name="Kerala Savari Cab",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Aluva", "Angamaly", "Perumbavoor", "CIAL Airport", "Vyttila", "Cherthala"],
                supported_routes=["Ernakulam District", "Kochi - CIAL Airport", "Kochi - Cherthala"],
                destinations=["CIAL Airport", "Aluva", "Angamaly", "Perumbavoor", "Kakkanad", "Cherthala"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=1.0,
                maximum_distance=65.0,
                base_fare=40.0,
                per_km_rate=14.0,
                per_min_rate=0.0,
                platform_fee=5.0,
                rating=4.8,
                is_government_backed=True,
                category_tag="Govt-Backed",
                regulatory_body="Govt of Kerala Labour Department",
                zero_surge=True,
                restrictions=["District level coverage only", "Zero surge regulated"]
            ),
            ProviderCoverageRecord(
                id="uber_go_kochi",
                name="Uber Go",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Aluva", "Fort Kochi", "Angamaly", "CIAL Airport"],
                supported_routes=["Kochi Greater Metro", "Kochi - CIAL Airport", "Kochi - Aluva"],
                destinations=["Kakkanad", "Aluva", "Angamaly", "CIAL Airport", "Vyttila", "Edappally"],
                intercity_supported=True,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=80.0,
                base_fare=45.0,
                per_km_rate=13.0,
                per_min_rate=1.8,
                platform_fee=10.0,
                rating=4.5,
                restrictions=["Local urban & airport corridors (under 80 km)"]
            ),
            ProviderCoverageRecord(
                id="uber_premier_kochi",
                name="Uber Premier",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Aluva", "Fort Kochi", "CIAL Airport"],
                supported_routes=["Kochi Metro", "Kochi - CIAL Airport"],
                destinations=["Kakkanad", "Aluva", "CIAL Airport"],
                intercity_supported=True,
                outstation_supported=False,
                minimum_distance=1.0,
                maximum_distance=100.0,
                base_fare=65.0,
                per_km_rate=16.5,
                per_min_rate=2.2,
                platform_fee=15.0,
                rating=4.7,
                restrictions=["Local urban & airport corridors"]
            ),
            ProviderCoverageRecord(
                id="ola_mini_kochi",
                name="Ola Mini",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kakkanad", "Aluva", "Fort Kochi", "CIAL Airport"],
                supported_routes=["Kochi Metro"],
                destinations=["Kakkanad", "Aluva", "CIAL Airport"],
                intercity_supported=True,
                outstation_supported=False,
                minimum_distance=1.0,
                maximum_distance=80.0,
                base_fare=42.0,
                per_km_rate=13.5,
                per_min_rate=2.0,
                platform_fee=10.0,
                rating=4.1,
                restrictions=["Urban & suburban routes (under 80 km)"]
            ),
            ProviderCoverageRecord(
                id="uber_intercity_kochi",
                name="Uber Intercity",
                vehicle_type="Cab",
                service_type="intercity",
                coverage_type="intercity_corridor",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kochi", "Aluva", "CIAL Airport"],
                supported_routes=["Kochi - Munnar", "Kochi - Thrissur", "Kochi - Alappuzha", "Kochi - Kottayam", "Kochi - Kozhikode"],
                destinations=["Munnar", "Thrissur", "Alappuzha", "Kottayam", "Vagamon", "Thekkady", "Kozhikode", "Palakkad", "Idukki", "Kumarakom", "Marari"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=25.0,
                maximum_distance=300.0,
                base_fare=450.0,
                per_km_rate=17.0,
                per_min_rate=1.5,
                platform_fee=40.0,
                rating=4.7,
                category_tag="Intercity Fleet",
                restrictions=["Intercity highway corridors", "Tolls applicable", "Min distance 25 km"]
            ),
            ProviderCoverageRecord(
                id="ola_outstation_kochi",
                name="Ola Outstation",
                vehicle_type="Cab",
                service_type="outstation",
                coverage_type="state",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Kochi", "Aluva"],
                supported_routes=["Kochi - Munnar", "Kochi - Alappuzha", "Kochi - Thrissur", "Kochi - Thekkady"],
                destinations=["Munnar", "Alappuzha", "Thrissur", "Kottayam", "Thekkady", "Vagamon", "Idukki", "Wayanad"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=30.0,
                maximum_distance=300.0,
                base_fare=500.0,
                per_km_rate=17.5,
                per_min_rate=1.0,
                platform_fee=45.0,
                rating=4.6,
                category_tag="Outstation Cab",
                restrictions=["Outstation journeys", "Min distance 30 km", "Dedicated driver allowance"]
            ),
            ProviderCoverageRecord(
                id="kerala_tourist_taxi_kochi",
                name="Kerala Tourism Tourist Taxi",
                vehicle_type="Cab",
                service_type="outstation",
                coverage_type="state",
                coverage_regions=["Kochi"],
                areas=["Ernakulam", "Fort Kochi", "CIAL Airport", "Aluva"],
                supported_routes=["Kochi - Munnar Hill Route", "Kochi - Alappuzha Backwaters", "Kochi - Thekkady Wildlife", "Kochi - Thrissur"],
                destinations=["Munnar", "Alappuzha", "Thekkady", "Thrissur", "Vagamon", "Kovalam", "Kumarakom", "Athirappilly", "Idukki"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=20.0,
                maximum_distance=300.0,
                base_fare=600.0,
                per_km_rate=18.0,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.8,
                is_government_backed=True,
                category_tag="Govt-Regulated Tourism",
                regulatory_body="Kerala Tourism Development Corp (KTDC)",
                zero_surge=True,
                restrictions=["Licensed commercial tourist drivers", "Zero surge state tariffs", "Mountain & scenic highway certified"]
            ),

            # ==========================================
            # BANGALORE / KARNATAKA FLEET
            # ==========================================
            ProviderCoverageRecord(
                id="rapido_bike_bangalore",
                name="Rapido Bike",
                vehicle_type="Bike",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Bangalore"],
                areas=["Indiranagar", "Koramangala", "HSR", "Whitefield", "Bellandur", "MG Road", "Jayanagar", "Hebbal", "Yelahanka"],
                supported_routes=["Bangalore Urban Commute"],
                destinations=["Indiranagar", "Koramangala", "Whitefield", "Electronic City", "Bellandur"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=18.0,
                base_fare=15.0,
                per_km_rate=7.0,
                per_min_rate=1.0,
                platform_fee=5.0,
                rating=4.4,
                restrictions=["Intra-city only", "Max 18 km", "No highway/outstation"]
            ),
            ProviderCoverageRecord(
                id="rapido_auto_bangalore",
                name="Rapido Auto",
                vehicle_type="Auto",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Bangalore"],
                areas=["Indiranagar", "Koramangala", "HSR", "Whitefield", "Electronic City", "Hebbal"],
                supported_routes=["Bangalore City Limits"],
                destinations=["Indiranagar", "Koramangala", "Whitefield", "Electronic City"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=30.0,
                base_fare=28.0,
                per_km_rate=10.0,
                per_min_rate=1.5,
                platform_fee=10.0,
                rating=4.3,
                restrictions=["City limits only", "Max 30 km"]
            ),
            ProviderCoverageRecord(
                id="namma_yatri_auto_bangalore",
                name="Namma Yatri Auto",
                vehicle_type="Auto",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Bangalore"],
                areas=["Indiranagar", "Koramangala", "Whitefield", "Electronic City", "Jayanagar", "Hebbal"],
                supported_routes=["Bangalore Metro"],
                destinations=["Indiranagar", "Koramangala", "Whitefield", "Electronic City"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=30.0,
                base_fare=30.0,
                per_km_rate=15.0,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.8,
                is_government_backed=True,
                category_tag="Open Mobility",
                regulatory_body="ARDU / Open Mobility Network",
                zero_surge=True,
                restrictions=["Regulated auto meter", "Bangalore BBMP limits"]
            ),
            ProviderCoverageRecord(
                id="namma_yatri_cab_bangalore",
                name="Namma Yatri Cab",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Bangalore"],
                areas=["Indiranagar", "Whitefield", "Electronic City", "KIA Airport", "Hebbal"],
                supported_routes=["Bangalore Urban & KIA Airport"],
                destinations=["KIA Airport", "Whitefield", "Electronic City", "Hebbal", "Devenahalli"],
                intercity_supported=True,
                outstation_supported=False,
                minimum_distance=1.0,
                maximum_distance=75.0,
                base_fare=60.0,
                per_km_rate=16.0,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.7,
                is_government_backed=True,
                category_tag="Open Mobility",
                regulatory_body="ARDU / Open Mobility Network",
                zero_surge=True,
                restrictions=["Zero commission", "Bangalore & KIA airport"]
            ),
            ProviderCoverageRecord(
                id="kstdc_airport_taxi_bangalore",
                name="KSTDC Airport Taxi",
                vehicle_type="Cab",
                service_type="airport",
                coverage_type="airport",
                coverage_regions=["Bangalore"],
                areas=["Kempegowda International Airport", "KIA Airport", "Bangalore City", "Hebbal", "Whitefield"],
                supported_routes=["Bangalore City - KIA Airport"],
                destinations=["KIA Airport", "Kempegowda International Airport", "Devenahalli", "Bangalore City"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=10.0,
                maximum_distance=90.0,
                base_fare=100.0,
                per_km_rate=18.0,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.5,
                is_government_backed=True,
                category_tag="Govt-Backed",
                regulatory_body="Karnataka State Tourism Dev Corp (KSTDC)",
                zero_surge=True,
                restrictions=["Airport transfer specialized", "Zero surge state meter"]
            ),
            ProviderCoverageRecord(
                id="uber_go_bangalore",
                name="Uber Go",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Bangalore"],
                areas=["Indiranagar", "Koramangala", "Whitefield", "Electronic City", "KIA Airport"],
                supported_routes=["Bangalore Urban"],
                destinations=["Indiranagar", "Whitefield", "Electronic City", "KIA Airport"],
                intercity_supported=True,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=80.0,
                base_fare=50.0,
                per_km_rate=14.0,
                per_min_rate=2.0,
                platform_fee=15.0,
                rating=4.6,
                restrictions=["Bangalore urban & airport"]
            ),
            ProviderCoverageRecord(
                id="uber_intercity_bangalore",
                name="Uber Intercity",
                vehicle_type="Cab",
                service_type="intercity",
                coverage_type="intercity_corridor",
                coverage_regions=["Bangalore"],
                areas=["Bangalore", "Indiranagar", "Whitefield", "Electronic City"],
                supported_routes=["Bangalore - Mysore", "Bangalore - Nandi Hills", "Bangalore - Hosur", "Bangalore - Tumkur"],
                destinations=["Mysore", "Nandi Hills", "Coorg", "Ooty", "Chikmagalur", "Hosur", "Tumkur", "Kolar", "Hassan"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=30.0,
                maximum_distance=300.0,
                base_fare=550.0,
                per_km_rate=17.5,
                per_min_rate=1.5,
                platform_fee=40.0,
                rating=4.7,
                category_tag="Intercity Fleet",
                restrictions=["Highway corridors", "Min distance 30 km"]
            ),
            ProviderCoverageRecord(
                id="kstdc_outstation_bangalore",
                name="KSTDC Outstation Taxi",
                vehicle_type="Cab",
                service_type="outstation",
                coverage_type="state",
                coverage_regions=["Bangalore"],
                areas=["Bangalore"],
                supported_routes=["Bangalore - Mysore Expressway", "Bangalore - Coorg", "Bangalore - Nandi Hills"],
                destinations=["Mysore", "Nandi Hills", "Coorg", "Ooty", "Chikmagalur", "Bandipur", "Kabini", "Hampi"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=25.0,
                maximum_distance=300.0,
                base_fare=650.0,
                per_km_rate=18.5,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.6,
                is_government_backed=True,
                category_tag="Govt-Regulated Tourism",
                regulatory_body="Karnataka State Tourism Dev Corp",
                zero_surge=True,
                restrictions=["Licensed tourism chauffeur", "Karnataka interstate permit"]
            ),

            # ==========================================
            # GOA FLEET
            # ==========================================
            ProviderCoverageRecord(
                id="goamiles_hatchback",
                name="GoaMiles Hatchback",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="state",
                coverage_regions=["Goa"],
                areas=["Panaji", "Baga", "Calangute", "Candolim", "Vasco", "Margao", "Dabolim", "Mopa"],
                supported_routes=["North Goa", "South Goa", "Goa Airport Corridors"],
                destinations=["Baga", "Calangute", "Panaji", "Vasco", "Margao", "Dabolim Airport", "Mopa Airport", "Anjuna", "Arambol"],
                intercity_supported=True,
                outstation_supported=False,
                minimum_distance=1.0,
                maximum_distance=120.0,
                base_fare=80.0,
                per_km_rate=22.0,
                per_min_rate=1.5,
                platform_fee=0.0,
                rating=4.6,
                is_government_backed=True,
                category_tag="Govt-Backed",
                regulatory_body="Goa Tourism Development Corp (GTDC)",
                zero_surge=False,
                restrictions=["Goa state territory only"]
            ),
            ProviderCoverageRecord(
                id="gtdc_tourist_taxi_goa",
                name="GTDC Tourist Taxi",
                vehicle_type="Cab",
                service_type="outstation",
                coverage_type="state",
                coverage_regions=["Goa"],
                areas=["Panaji", "Dabolim", "Mopa", "Margao", "Baga"],
                supported_routes=["Goa Coastal & Heritage Circuit", "Goa - Gokarna", "Goa - Dudhsagar"],
                destinations=["Dudhsagar", "Gokarna", "Karwar", "Baga", "Panaji", "Dabolim Airport", "Mopa Airport"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=5.0,
                maximum_distance=250.0,
                base_fare=150.0,
                per_km_rate=26.0,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.2,
                is_government_backed=True,
                category_tag="Govt-Backed",
                regulatory_body="Goa Transport Dept & GTDC",
                zero_surge=True,
                restrictions=["Official GTDC tourism rates", "Zero surge guarantee"]
            ),

            # ==========================================
            # MUMBAI FLEET
            # ==========================================
            ProviderCoverageRecord(
                id="mumbai_kaali_peeli",
                name="Mumbai Kaali Peeli",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Mumbai"],
                areas=["South Mumbai", "Andheri", "Bandra", "Dadar", "Thane", "Navi Mumbai", "Juhu", "Colaba"],
                supported_routes=["Mumbai Metropolitan Region (MMR)"],
                destinations=["Andheri", "Bandra", "Dadar", "Thane", "Navi Mumbai", "Colaba", "CSMT"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=60.0,
                base_fare=28.0,
                per_km_rate=18.66,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.1,
                is_government_backed=True,
                category_tag="State-Regulated",
                regulatory_body="Maharashtra State Transport Authority",
                zero_surge=True,
                restrictions=["MMR zone only", "Metered tariff"]
            ),
            ProviderCoverageRecord(
                id="mumbai_cool_cab_intercity",
                name="Mumbai Cool Cab",
                vehicle_type="Cab",
                service_type="intercity",
                coverage_type="intercity_corridor",
                coverage_regions=["Mumbai"],
                areas=["Mumbai", "Dadar", "Thane", "Navi Mumbai"],
                supported_routes=["Mumbai - Pune Expressway", "Mumbai - Lonavala", "Mumbai - Alibaug", "Mumbai - Nashik"],
                destinations=["Pune", "Lonavala", "Alibaug", "Nashik", "Shirdi", "Mahabaleshwar"],
                intercity_supported=True,
                outstation_supported=True,
                minimum_distance=20.0,
                maximum_distance=300.0,
                base_fare=400.0,
                per_km_rate=18.5,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.3,
                category_tag="Intercity Fleet",
                restrictions=["Expressway toll extra", "Intercity corridor"]
            ),

            # ==========================================
            # KOLKATA FLEET
            # ==========================================
            ProviderCoverageRecord(
                id="yatri_sathi_meter_taxi",
                name="Yatri Sathi Meter Taxi",
                vehicle_type="Cab",
                service_type="local",
                coverage_type="metro",
                coverage_regions=["Kolkata"],
                areas=["Park Street", "Howrah", "Salt Lake", "New Town", "Dum Dum Airport", "Esplanade"],
                supported_routes=["Kolkata Metro & Airport"],
                destinations=["Dum Dum Airport", "Howrah", "Salt Lake", "New Town"],
                intercity_supported=False,
                outstation_supported=False,
                minimum_distance=0.5,
                maximum_distance=50.0,
                base_fare=30.0,
                per_km_rate=15.0,
                per_min_rate=0.0,
                platform_fee=0.0,
                rating=4.7,
                is_government_backed=True,
                category_tag="Govt-Backed",
                regulatory_body="Govt of West Bengal IT & Electronics Dept",
                zero_surge=True,
                restrictions=["Kolkata & Howrah metro limits", "Zero surge regulated"]
            )
        ]

        for r in default_records:
            self._providers[r.id] = r

    def _load_from_file(self, path: Path):
        """Optionally load user overrides and custom provider definitions from JSON."""
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                records = data.get("providers", [])
                for rec_dict in records:
                    rec = ProviderCoverageRecord(**rec_dict)
                    self._providers[rec.id] = rec
        except Exception as err:
            logger.warning("Could not read provider registry from %s: %s", path, err)

    def register_provider(self, record: ProviderCoverageRecord) -> None:
        """Register or update a provider in the registry dynamically."""
        self._providers[record.id] = record

    def get_all_providers(self) -> List[ProviderCoverageRecord]:
        return list(self._providers.values())

    def get_provider_by_id(self, provider_id: str) -> Optional[ProviderCoverageRecord]:
        return self._providers.get(provider_id)

    def get_providers_for_region(self, region: str) -> List[ProviderCoverageRecord]:
        r_clean = region.strip().lower()
        return [
            p for p in self._providers.values()
            if any(r_clean == cr.lower() for cr in p.coverage_regions)
        ]

    def find_provider_by_quote_name(self, quote_name: str, region: Optional[str] = None) -> Optional[ProviderCoverageRecord]:
        q_clean = quote_name.strip().lower()
        candidates = self.get_providers_for_region(region) if region else list(self._providers.values())
        for p in candidates:
            if p.name.lower() == q_clean:
                return p
            if p.name.lower() in q_clean or q_clean in p.name.lower():
                return p
        # Broader search across all
        for p in self._providers.values():
            if p.name.lower() == q_clean or p.name.lower() in q_clean:
                return p
        return None


# Global singleton instance
provider_registry = ProviderRegistry()
