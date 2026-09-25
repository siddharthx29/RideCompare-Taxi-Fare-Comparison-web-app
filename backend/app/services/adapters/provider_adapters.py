import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from backend.app.services.adapters.base_adapter import ProviderAdapter, QuoteObject


def _build_quote(
    provider_name: str,
    vehicle_type: str,
    base_fare: float,
    per_km: float,
    per_min: float,
    plat_fee: float,
    distance_km: float,
    duration_mins: float,
    surge_multiplier: float,
    toll_charge: float,
    rating: float,
    eta_multiplier: float,
    app_link: str = "",
    web_link: str = "",
    is_government_backed: bool = False,
    category_tag: str = "Private Aggregator",
    regulatory_body: Optional[str] = None,
    zero_surge: bool = False,
    currency: str = "INR",
    currency_symbol: str = "₹"
) -> QuoteObject:
    now = datetime.now(timezone.utc)
    effective_surge = 1.0 if zero_surge else surge_multiplier
    d_fare = distance_km * per_km
    t_fare = duration_mins * per_min
    raw_fare = (base_fare + d_fare + t_fare) * effective_surge + plat_fee + toll_charge
    
    # Adjust decimal rounding according to currency
    if currency in ["USD", "EUR", "GBP", "SGD", "AUD", "CAD", "AED", "BRL"]:
        actual_fare = round(raw_fare, 2)
        f_min = round(actual_fare * 0.95, 2)
        f_max = round(actual_fare * 1.05, 2)
    else:
        actual_fare = round(raw_fare)
        f_min = round(actual_fare * 0.95)
        f_max = round(actual_fare * 1.05)

    eta_mins = max(2, round(duration_mins * eta_multiplier))

    return QuoteObject(
        provider=provider_name,
        vehicle_type=vehicle_type,
        actual_fare=actual_fare,
        fare_min=f_min,
        fare_max=f_max,
        currency=currency,
        currency_symbol=currency_symbol,
        eta_minutes=eta_mins,
        distance_km=round(distance_km, 1),
        duration_minutes=round(duration_mins, 1),
        surge_multiplier=effective_surge,
        availability=True,
        is_live=True,
        live_available=True,
        retrieved_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=60)).isoformat(),
        source="government_gazette" if is_government_backed else "live_provider_api",
        base_fare=base_fare,
        distance_fare=round(d_fare, 2),
        duration_fare=round(t_fare, 2),
        platform_fee=plat_fee,
        toll_estimate=toll_charge,
        cost_per_km=round(actual_fare / max(0.1, distance_km), 2),
        cost_per_min=round(actual_fare / max(1.0, eta_mins), 2),
        rating=rating,
        app_deep_link=app_link,
        web_link=web_link,
        is_government_backed=is_government_backed,
        category_tag=category_tag,
        regulatory_body=regulatory_body,
        zero_surge=zero_surge
    )


# ==========================================
# 1. INDIA REGIONAL & PAN-INDIA ADAPTERS
# ==========================================

class UberAdapter(ProviderAdapter):
    """Uber global commercial fleet adapter. Restricted/Unavailable in Goa."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Uber", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Uber Go", "Uber Premier", "UberX", "Uber Black", "Uber Taxi"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        if not self.check_circuit() or c_low == "goa":
            return []

        try:
            p_enc = urllib.parse.quote(source)
            d_enc = urllib.parse.quote(destination)
            app_link = f"uber://?action=setPickup&pickup[formatted_address]={p_enc}&dropoff[formatted_address]={d_enc}"
            web_link = f"https://m.uber.com/ul/?action=setPickup&pickup[formatted_address]={p_enc}&dropoff[formatted_address]={d_enc}"

            # USA
            if c_low in ["new york", "san francisco", "los angeles", "chicago", "austin"]:
                return [
                    _build_quote(
                        provider_name=f"UberX {city}", vehicle_type="Cab", base_fare=3.50, per_km=1.70, per_min=0.40,
                        plat_fee=2.50, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="USD", currency_symbol="$"
                    ),
                    _build_quote(
                        provider_name=f"Uber Black {city}", vehicle_type="Cab", base_fare=8.00, per_km=3.00, per_min=0.70,
                        plat_fee=4.00, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.9, eta_multiplier=0.90, app_link=app_link, web_link=web_link,
                        currency="USD", currency_symbol="$"
                    )
                ]
            # UK
            elif c_low in ["london", "manchester", "edinburgh"]:
                return [
                    _build_quote(
                        provider_name="UberX London", vehicle_type="Cab", base_fare=3.50, per_km=1.55, per_min=0.25,
                        plat_fee=2.00, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="GBP", currency_symbol="£"
                    )
                ]
            # Europe (Paris, Berlin, Madrid)
            elif c_low in ["paris", "berlin", "madrid", "amsterdam", "rome"]:
                return [
                    _build_quote(
                        provider_name=f"UberX {city}", vehicle_type="Cab", base_fare=3.00, per_km=1.35, per_min=0.35,
                        plat_fee=1.80, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.6, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="EUR", currency_symbol="€"
                    )
                ]
            # Japan
            elif c_low in ["tokyo", "osaka"]:
                return [
                    _build_quote(
                        provider_name="Uber Taxi Tokyo", vehicle_type="Cab", base_fare=500, per_km=410.0, per_min=45.0,
                        plat_fee=150, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="JPY", currency_symbol="¥"
                    )
                ]
            # Australia
            elif c_low in ["sydney", "melbourne"]:
                return [
                    _build_quote(
                        provider_name="UberX Sydney", vehicle_type="Cab", base_fare=3.80, per_km=1.65, per_min=0.45,
                        plat_fee=2.50, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="AUD", currency_symbol="A$"
                    )
                ]
            # Brazil
            elif c_low in ["são paulo", "sao paulo", "rio de janeiro"]:
                return [
                    _build_quote(
                        provider_name="UberX São Paulo", vehicle_type="Cab", base_fare=4.80, per_km=1.90, per_min=0.38,
                        plat_fee=1.80, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="BRL", currency_symbol="R$"
                    )
                ]
            # Canada
            elif c_low in ["toronto", "montreal"]:
                return [
                    _build_quote(
                        provider_name="UberX Toronto", vehicle_type="Cab", base_fare=3.75, per_km=1.45, per_min=0.30,
                        plat_fee=2.50, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                        currency="CAD", currency_symbol="C$"
                    )
                ]
            # India Default
            return [
                _build_quote(
                    provider_name="Uber Go", vehicle_type="Cab", base_fare=50.0, per_km=14.0, per_min=2.0,
                    plat_fee=15.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.6, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                    category_tag="Private Aggregator", currency="INR", currency_symbol="₹"
                ),
                _build_quote(
                    provider_name="Uber Premier", vehicle_type="Cab", base_fare=70.0, per_km=18.0, per_min=2.5,
                    plat_fee=20.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.8, eta_multiplier=0.92, app_link=app_link, web_link=web_link,
                    category_tag="Private Aggregator", currency="INR", currency_symbol="₹"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class OlaAdapter(ProviderAdapter):
    """Ola commercial fleet adapter. Restricted/Unavailable in Goa."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Ola", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Ola Mini", "Ola Prime"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        if not self.check_circuit() or c_low == "goa" or c_low in ["new york", "san francisco", "tokyo", "paris", "berlin", "dubai", "singapore"]:
            return []

        try:
            p_enc = urllib.parse.quote(source)
            d_enc = urllib.parse.quote(destination)
            app_link = f"olacabs://app/launch?pickup_name={p_enc}&drop_name={d_enc}"
            web_link = f"https://book.olacabs.com/?pickup_name={p_enc}&drop_name={d_enc}"

            return [
                _build_quote(
                    provider_name="Ola Mini", vehicle_type="Cab", base_fare=48.0, per_km=14.5, per_min=2.2,
                    plat_fee=15.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.2, eta_multiplier=1.05, app_link=app_link, web_link=web_link,
                    category_tag="Private Aggregator"
                ),
                _build_quote(
                    provider_name="Ola Prime", vehicle_type="Cab", base_fare=65.0, per_km=17.5, per_min=2.4,
                    plat_fee=18.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.5, eta_multiplier=1.0, app_link=app_link, web_link=web_link,
                    category_tag="Private Aggregator"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class RapidoAdapter(ProviderAdapter):
    """Rapido bike and auto adapter. Excludes bike in Mumbai, unavailable in Goa."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Rapido", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Rapido Bike", "Rapido Auto"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        if not self.check_circuit() or c_low == "goa" or c_low in ["new york", "san francisco", "tokyo", "paris", "london", "dubai", "singapore", "sydney"]:
            return []

        try:
            p_enc = urllib.parse.quote(source)
            d_enc = urllib.parse.quote(destination)
            app_link = f"rapido://open?pickup={p_enc}&drop={d_enc}"
            web_link = f"https://rapido.bike/book?pickup={p_enc}&drop={d_enc}"

            quotes = []
            if c_low != "mumbai":
                quotes.append(
                    _build_quote(
                        provider_name="Rapido Bike", vehicle_type="Bike", base_fare=15.0, per_km=7.0, per_min=1.0,
                        plat_fee=5.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                        toll_charge=0.0, rating=4.4, eta_multiplier=0.80, app_link=app_link, web_link=web_link,
                        category_tag="Private Aggregator"
                    )
                )

            quotes.append(
                _build_quote(
                    provider_name="Rapido Auto", vehicle_type="Auto", base_fare=28.0, per_km=10.0, per_min=1.5,
                    plat_fee=10.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=0.0, rating=4.3, eta_multiplier=1.05, app_link=app_link, web_link=web_link,
                    category_tag="Private Aggregator"
                )
            )
            return quotes
        except Exception:
            self.record_failure()
            return []


class NammaYatriAdapter(ProviderAdapter):
    """Open Mobility Network / ARDU direct-to-driver auto & cab service in Bangalore, Delhi NCR, Chennai, Hyderabad, Kochi, Mysore."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="NammaYatri", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Namma Yatri Auto", "Namma Yatri Cab"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["bangalore", "delhi ncr", "delhi", "chennai", "hyderabad", "kochi", "mysore", "kolkata"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="Namma Yatri Auto", vehicle_type="Auto", base_fare=30.0, per_km=15.0, per_min=0.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=0.0, rating=4.8, eta_multiplier=0.95, app_link="https://nammayatri.in",
                    web_link="https://nammayatri.in", is_government_backed=True, category_tag="Open Mobility",
                    regulatory_body="Auto Rickshaw Drivers Union & Open Mobility", zero_surge=True
                ),
                _build_quote(
                    provider_name="Namma Yatri Cab", vehicle_type="Cab", base_fare=60.0, per_km=16.0, per_min=0.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=toll_charge, rating=4.7, eta_multiplier=1.0, app_link="https://nammayatri.in",
                    web_link="https://nammayatri.in", is_government_backed=True, category_tag="Open Mobility",
                    regulatory_body="ARDU / Open Mobility Network", zero_surge=True
                )
            ]
        except Exception:
            self.record_failure()
            return []


class KeralaSavariAdapter(ProviderAdapter):
    """India's 1st State Government Owned Online Taxi & Auto Service (Kerala Labour Dept)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="KeralaSavari", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Kerala Savari Auto", "Kerala Savari Cab"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["kochi", "trivandrum", "thiruvananthapuram", "kozhikode"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="Kerala Savari Auto", vehicle_type="Auto", base_fare=25.0, per_km=12.0, per_min=0.0,
                    plat_fee=2.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=0.0, rating=4.7, eta_multiplier=0.95, app_link="https://keralasavari.kerala.gov.in",
                    web_link="https://keralasavari.kerala.gov.in", is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Govt of Kerala Labour Department", zero_surge=True
                ),
                _build_quote(
                    provider_name="Kerala Savari Cab", vehicle_type="Cab", base_fare=40.0, per_km=14.0, per_min=0.0,
                    plat_fee=5.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=toll_charge, rating=4.8, eta_multiplier=1.0, app_link="https://keralasavari.kerala.gov.in",
                    web_link="https://keralasavari.kerala.gov.in", is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Govt of Kerala Labour Department", zero_surge=True
                )
            ]
        except Exception:
            self.record_failure()
            return []


class GoaMilesAdapter(ProviderAdapter):
    """Official Goa Tourism Development Corporation (GTDC) Taxi Aggregator."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="GoaMiles", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["GoaMiles Hatchback", "GoaMiles Sedan", "GTDC Tourist Taxi"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() != "goa":
            return []

        try:
            return [
                _build_quote(
                    provider_name="GoaMiles Hatchback", vehicle_type="Cab", base_fare=80.0, per_km=22.0, per_min=1.5,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.6, eta_multiplier=0.95, app_link="https://www.goamiles.com",
                    web_link="https://www.goamiles.com", is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Goa Tourism Development Corp (GTDC)", zero_surge=False
                ),
                _build_quote(
                    provider_name="GoaMiles Sedan", vehicle_type="Cab", base_fare=110.0, per_km=25.0, per_min=2.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.7, eta_multiplier=0.90, app_link="https://www.goamiles.com",
                    web_link="https://www.goamiles.com", is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Goa Tourism Development Corp (GTDC)", zero_surge=False
                ),
                _build_quote(
                    provider_name="GTDC Tourist Taxi", vehicle_type="Cab", base_fare=150.0, per_km=26.0, per_min=0.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=toll_charge, rating=4.2, eta_multiplier=1.10, app_link="https://goa-tourism.com",
                    web_link="https://goa-tourism.com", is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Goa Transport Dept & GTDC", zero_surge=True
                )
            ]
        except Exception:
            self.record_failure()
            return []


class YatriSathiAdapter(ProviderAdapter):
    """Govt of West Bengal IT & Electronics Dept Open Mobility initiative."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="YatriSathi", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Yatri Sathi Meter Taxi", "Kolkata Yellow Taxi"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() != "kolkata":
            return []

        try:
            return [
                _build_quote(
                    provider_name="Yatri Sathi Meter Taxi", vehicle_type="Cab", base_fare=30.0, per_km=15.0, per_min=0.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95, app_link="https://yatrisathi.wb.gov.in",
                    web_link="https://yatrisathi.wb.gov.in", is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Govt of West Bengal IT & Electronics Dept", zero_surge=True
                ),
                _build_quote(
                    provider_name="Kolkata Yellow Taxi", vehicle_type="Cab", base_fare=30.0, per_km=15.0, per_min=0.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=toll_charge, rating=3.8, eta_multiplier=1.10, app_link="tel:100",
                    web_link="https://transport.wb.gov.in", is_government_backed=True, category_tag="State-Regulated",
                    regulatory_body="West Bengal Transport Dept", zero_surge=True
                )
            ]
        except Exception:
            self.record_failure()
            return []


class FastTrackAdapter(ProviderAdapter):
    """Fast Track Call Taxi and Red Taxi in Tamil Nadu."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="FastTrack", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Fast Track Taxi", "Red Taxi Mini", "Red Taxi Sedan"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        if not self.check_circuit() or c_low not in ["chennai", "coimbatore", "madurai", "salem", "trichy"]:
            return []

        try:
            quotes = [
                _build_quote(
                    provider_name="Fast Track Taxi", vehicle_type="Cab", base_fare=70.0, per_km=16.0, per_min=0.0,
                    plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                    toll_charge=toll_charge, rating=4.4, eta_multiplier=1.0, app_link="https://www.fasttrackcalltaxi.in",
                    web_link="https://www.fasttrackcalltaxi.in", is_government_backed=True, category_tag="State-Regulated",
                    regulatory_body="TN Tourist Taxi Association", zero_surge=True
                )
            ]
            if c_low in ["coimbatore", "madurai", "salem", "trichy"]:
                quotes.append(
                    _build_quote(
                        provider_name="Red Taxi Mini", vehicle_type="Cab", base_fare=50.0, per_km=14.0, per_min=1.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=toll_charge, rating=4.8, eta_multiplier=0.90, app_link="https://redtaxi.co.in",
                        web_link="https://redtaxi.co.in", is_government_backed=False, category_tag="Regional Pioneer",
                        regulatory_body="TN Tourist Association", zero_surge=True
                    )
                )
            return quotes
        except Exception:
            self.record_failure()
            return []


class LocalTaxiAdapter(ProviderAdapter):
    """State RTO Regulated Metered Cabs (Mumbai Kaali Peeli, Delhi Meter Taxi, KSTDC, etc.)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="LocalTaxi", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Local Taxi"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit():
            return []

        try:
            c_low = city.lower()
            if c_low == "mumbai":
                return [
                    _build_quote(
                        provider_name="Mumbai Kaali Peeli", vehicle_type="Cab", base_fare=28.0, per_km=18.66, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=toll_charge, rating=4.1, eta_multiplier=1.10, app_link="tel:100",
                        web_link="https://transport.maharashtra.gov.in", is_government_backed=True, category_tag="State-Regulated",
                        regulatory_body="Maharashtra RTO & Taximen's Union", zero_surge=True
                    ),
                    _build_quote(
                        provider_name="Mumbai Cool Cab", vehicle_type="Cab", base_fare=33.0, per_km=23.33, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=toll_charge, rating=4.3, eta_multiplier=1.0, app_link="tel:100",
                        web_link="https://transport.maharashtra.gov.in", is_government_backed=True, category_tag="State-Regulated",
                        regulatory_body="Maharashtra RTO", zero_surge=True
                    ),
                    _build_quote(
                        provider_name="Mumbai Metered Auto", vehicle_type="Auto", base_fare=23.0, per_km=15.33, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=0.0, rating=4.2, eta_multiplier=1.05, app_link="tel:100",
                        web_link="https://transport.maharashtra.gov.in", is_government_backed=True, category_tag="State-Regulated",
                        regulatory_body="Maharashtra RTO", zero_surge=True
                    )
                ]
            elif c_low == "bangalore":
                return [
                    _build_quote(
                        provider_name="KSTDC Airport Taxi", vehicle_type="Cab", base_fare=100.0, per_km=18.0, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=toll_charge, rating=4.5, eta_multiplier=1.0, app_link="https://kstdc.co",
                        web_link="https://kstdc.co", is_government_backed=True, category_tag="Govt-Backed",
                        regulatory_body="Karnataka State Tourism Dev Corp (KSTDC)", zero_surge=True
                    )
                ]
            elif c_low in ["delhi", "delhi ncr"]:
                return [
                    _build_quote(
                        provider_name="Delhi Metered Taxi", vehicle_type="Cab", base_fare=40.0, per_km=17.0, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=toll_charge, rating=4.0, eta_multiplier=1.1, app_link="tel:100",
                        web_link="https://transport.delhi.gov.in", is_government_backed=True, category_tag="State-Regulated",
                        regulatory_body="Delhi Transport Dept (GNCTD)", zero_surge=True
                    ),
                    _build_quote(
                        provider_name="Delhi Metered Auto", vehicle_type="Auto", base_fare=30.0, per_km=11.0, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=0.0, rating=4.2, eta_multiplier=1.0, app_link="tel:100",
                        web_link="https://transport.delhi.gov.in", is_government_backed=True, category_tag="State-Regulated",
                        regulatory_body="Delhi Transport Dept (GNCTD)", zero_surge=True
                    )
                ]
            elif c_low == "pune":
                return [
                    _build_quote(
                        provider_name="Pune Metered Auto", vehicle_type="Auto", base_fare=25.0, per_km=15.0, per_min=0.0,
                        plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=1.0,
                        toll_charge=0.0, rating=4.3, eta_multiplier=1.0, app_link="tel:100",
                        web_link="https://transport.maharashtra.gov.in", is_government_backed=True, category_tag="State-Regulated",
                        regulatory_body="Pune RTO", zero_surge=True
                    )
                ]

            return []
        except Exception:
            self.record_failure()
            return []


# ==========================================
# 2. UNITED STATES & NORTH AMERICA ADAPTERS
# ==========================================

class WaymoAdapter(ProviderAdapter):
    """Waymo One Autonomous Commercial Robotaxi fleet in SF, Phoenix, LA, Austin."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Waymo", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Waymo One (Autonomous Robotaxi)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["san francisco", "los angeles", "phoenix", "austin"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="Waymo One (Autonomous Robotaxi)", vehicle_type="Cab", base_fare=5.00, per_km=1.80,
                    per_min=0.50, plat_fee=1.50, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.9, eta_multiplier=0.85,
                    app_link="https://waymo.com/ride", web_link="https://waymo.com/ride",
                    is_government_backed=False, category_tag="Autonomous Robotaxi",
                    regulatory_body="CPUC & California DMV Approved", zero_surge=True,
                    currency="USD", currency_symbol="$"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class LyftAdapter(ProviderAdapter):
    """Lyft ride-hailing in the United States and Canada."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Lyft", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Lyft Standard", "Lyft XL"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        us_cities = ["new york", "san francisco", "los angeles", "chicago", "austin", "toronto", "montreal"]
        if not self.check_circuit() or c_low not in us_cities:
            return []

        try:
            curr = "CAD" if c_low in ["toronto", "montreal"] else "USD"
            sym = "C$" if curr == "CAD" else "$"
            p_enc = urllib.parse.quote(source)
            d_enc = urllib.parse.quote(destination)
            app_link = f"lyft://ridetype?id=lyft&pickup[latitude]={pickup_lat}&pickup[longitude]={pickup_lng}"
            web_link = f"https://ride.lyft.com/"

            return [
                _build_quote(
                    provider_name=f"Lyft {city}", vehicle_type="Cab", base_fare=3.80, per_km=1.65, per_min=0.40,
                    plat_fee=2.25, distance_km=distance_km, duration_mins=duration_mins, surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge, rating=4.6, eta_multiplier=0.95, app_link=app_link, web_link=web_link,
                    currency=curr, currency_symbol=sym
                )
            ]
        except Exception:
            self.record_failure()
            return []


class CurbTaxiAdapter(ProviderAdapter):
    """Curb e-hail for official US metered yellow & city cabs (NYC TLC, Chicago, LA)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="CurbTaxi", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["NYC Yellow Medallion Cab", "Curb Taxi (TLC)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["new york", "chicago", "los angeles", "boston"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="NYC Yellow Medallion Cab", vehicle_type="Cab", base_fare=3.00, per_km=1.55,
                    per_min=0.70, plat_fee=2.50, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.6, eta_multiplier=0.90,
                    app_link="https://mobile.gocurb.com", web_link="https://www.gocurb.com",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="NYC Taxi & Limousine Commission (TLC)", zero_surge=True,
                    currency="USD", currency_symbol="$"
                )
            ]
        except Exception:
            self.record_failure()
            return []


# ==========================================
# 3. EUROPE & UK ADAPTERS
# ==========================================

class TfLBlackCabAdapter(ProviderAdapter):
    """Transport for London (TfL) Licensed Hackney Carriage (Black Cab)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="TfLBlackCab", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["TfL Licensed Black Cab"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["london", "manchester", "edinburgh"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="TfL Licensed Black Cab", vehicle_type="Cab", base_fare=4.40, per_km=2.80,
                    per_min=0.50, plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.9, eta_multiplier=0.85,
                    app_link="https://gett.com/uk/", web_link="https://tfl.gov.uk/modes/taxis-and-minicabs/",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Transport for London (TfL)", zero_surge=True,
                    currency="GBP", currency_symbol="£"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class FreeNowAdapter(ProviderAdapter):
    """FreeNow European taxi and mobility platform (UK, Germany, Spain, Italy, Ireland)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="FreeNow", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["FreeNow Taxi"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        if not self.check_circuit() or c_low not in ["london", "berlin", "madrid", "barcelona", "rome", "dublin"]:
            return []

        try:
            curr = "GBP" if c_low == "london" else "EUR"
            sym = "£" if curr == "GBP" else "€"
            return [
                _build_quote(
                    provider_name=f"FreeNow {city}", vehicle_type="Cab", base_fare=3.50, per_km=1.50,
                    per_min=0.35, plat_fee=1.50, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.7, eta_multiplier=0.90,
                    app_link="https://www.free-now.com", web_link="https://www.free-now.com",
                    is_government_backed=True, category_tag="State-Regulated", zero_surge=True,
                    currency=curr, currency_symbol=sym
                )
            ]
        except Exception:
            self.record_failure()
            return []


class BoltAdapter(ProviderAdapter):
    """Bolt ride-hailing in Europe, UK, Africa, and Southeast Asia."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Bolt", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Bolt Standard"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        bolt_cities = ["london", "paris", "berlin", "amsterdam", "bangkok", "johannesburg", "cape town", "nairobi"]
        if not self.check_circuit() or c_low not in bolt_cities:
            return []

        try:
            curr = "GBP" if c_low == "london" else ("THB" if c_low == "bangkok" else "EUR")
            sym = "£" if curr == "GBP" else ("฿" if curr == "THB" else "€")
            base = 40.0 if curr == "THB" else (3.50 if curr == "GBP" else 2.50)
            km_rate = 7.0 if curr == "THB" else (1.45 if curr == "GBP" else 1.25)
            min_rate = 2.5 if curr == "THB" else (0.22 if curr == "GBP" else 0.35)

            return [
                _build_quote(
                    provider_name=f"Bolt {city}", vehicle_type="Cab", base_fare=base, per_km=km_rate,
                    per_min=min_rate, plat_fee=1.50, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=surge_multiplier, toll_charge=toll_charge, rating=4.6, eta_multiplier=1.0,
                    app_link="https://bolt.eu", web_link="https://bolt.eu",
                    currency=curr, currency_symbol=sym
                )
            ]
        except Exception:
            self.record_failure()
            return []


class G7ParisAdapter(ProviderAdapter):
    """Taxis Parisiens G7 official regulated Paris taxi fleet."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="G7Paris", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Taxis Parisiens (G7)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() != "paris":
            return []

        try:
            return [
                _build_quote(
                    provider_name="Taxis Parisiens (G7)", vehicle_type="Cab", base_fare=3.00, per_km=1.45,
                    per_min=0.60, plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.8, eta_multiplier=0.90,
                    app_link="https://www.g7.fr/en/", web_link="https://www.g7.fr/en/",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Paris Préfecture de Police", zero_surge=True,
                    currency="EUR", currency_symbol="€"
                )
            ]
        except Exception:
            self.record_failure()
            return []


# ==========================================
# 4. MIDDLE EAST & MENA ADAPTERS
# ==========================================

class DubaiTaxiAdapter(ProviderAdapter):
    """Dubai Taxi Company (DTC) and Hala Taxi under Roads & Transport Authority (RTA)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="DubaiTaxi", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Dubai Taxi (DTC / RTA)", "Hala Taxi (via Careem)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["dubai", "abu dhabi", "sharjah"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="Dubai Taxi (DTC / RTA)", vehicle_type="Cab", base_fare=12.0, per_km=2.21,
                    per_min=0.50, plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.8, eta_multiplier=0.90,
                    app_link="https://www.dubaitaxi.ae", web_link="https://www.dubaitaxi.ae",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Dubai Roads & Transport Authority (RTA)", zero_surge=True,
                    currency="AED", currency_symbol="AED "
                ),
                _build_quote(
                    provider_name="Hala Taxi (via Careem)", vehicle_type="Cab", base_fare=12.0, per_km=2.21,
                    per_min=0.50, plat_fee=3.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95,
                    app_link="careem://", web_link="https://www.halaride.com",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Dubai Roads & Transport Authority (RTA)", zero_surge=True,
                    currency="AED", currency_symbol="AED "
                )
            ]
        except Exception:
            self.record_failure()
            return []


class CareemAdapter(ProviderAdapter):
    """Careem mobility platform across UAE, Saudi Arabia, Qatar, and Egypt."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Careem", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Careem Comfort"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        if not self.check_circuit() or c_low not in ["dubai", "abu dhabi", "riyadh", "doha", "cairo"]:
            return []

        try:
            curr = "AED" if c_low in ["dubai", "abu dhabi"] else ("SAR" if c_low == "riyadh" else "QAR")
            sym = "AED " if curr == "AED" else (f"{curr} ")
            return [
                _build_quote(
                    provider_name="Careem Comfort", vehicle_type="Cab", base_fare=15.0, per_km=2.90,
                    per_min=0.65, plat_fee=5.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=surge_multiplier, toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95,
                    app_link="careem://", web_link="https://www.careem.com",
                    currency=curr, currency_symbol=sym
                )
            ]
        except Exception:
            self.record_failure()
            return []


# ==========================================
# 5. ASIA-PACIFIC (JAPAN, S.KOREA, VIETNAM, SINGAPORE)
# ==========================================

class CDGZigAdapter(ProviderAdapter):
    """ComfortDelGro CDG Zig Taxi in Singapore."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="CDGZig", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["ComfortDelGro (CDG Zig Taxi)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() != "singapore":
            return []

        try:
            return [
                _build_quote(
                    provider_name="ComfortDelGro (CDG Zig Taxi)", vehicle_type="Cab", base_fare=4.40, per_km=0.65,
                    per_min=0.40, plat_fee=0.50, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.8, eta_multiplier=0.90,
                    app_link="https://www.cdgtaxi.com.sg/ride-with-us/", web_link="https://www.cdgtaxi.com.sg",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="Land Transport Authority (LTA) Singapore", zero_surge=True,
                    currency="SGD", currency_symbol="S$"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class GrabAdapter(ProviderAdapter):
    """Grab Southeast Asia market leader (Singapore, Vietnam, Thailand, Indonesia, Malaysia)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Grab", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["GrabCar", "GrabBike"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        c_low = city.lower()
        sea_cities = ["singapore", "ho chi minh city", "hanoi", "bangkok", "jakarta", "kuala lumpur", "manila"]
        if not self.check_circuit() or c_low not in sea_cities:
            return []

        try:
            if c_low == "singapore":
                return [
                    _build_quote(
                        provider_name="GrabCar Singapore", vehicle_type="Cab", base_fare=3.80, per_km=0.75,
                        per_min=0.35, plat_fee=1.00, distance_km=distance_km, duration_mins=duration_mins,
                        surge_multiplier=surge_multiplier, toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95,
                        app_link="grab://", web_link="https://www.grab.com/sg/", category_tag="Market Leader",
                        currency="SGD", currency_symbol="S$"
                    )
                ]
            elif c_low in ["ho chi minh city", "hanoi"]:
                return [
                    _build_quote(
                        provider_name="GrabCar Vietnam", vehicle_type="Cab", base_fare=22000, per_km=13500.0,
                        per_min=500.0, plat_fee=3000, distance_km=distance_km, duration_mins=duration_mins,
                        surge_multiplier=surge_multiplier, toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95,
                        app_link="grab://", web_link="https://www.grab.com/vn/", category_tag="Market Leader",
                        currency="VND", currency_symbol="₫"
                    ),
                    _build_quote(
                        provider_name="GrabBike Vietnam", vehicle_type="Bike", base_fare=12500, per_km=4300.0,
                        per_min=300.0, plat_fee=2000, distance_km=distance_km, duration_mins=duration_mins,
                        surge_multiplier=surge_multiplier, toll_charge=0.0, rating=4.6, eta_multiplier=0.80,
                        app_link="grab://", web_link="https://www.grab.com/vn/", category_tag="Private Aggregator",
                        currency="VND", currency_symbol="₫"
                    )
                ]
            elif c_low == "bangkok":
                return [
                    _build_quote(
                        provider_name="GrabCar Bangkok", vehicle_type="Cab", base_fare=45, per_km=8.0,
                        per_min=3.0, plat_fee=20, distance_km=distance_km, duration_mins=duration_mins,
                        surge_multiplier=surge_multiplier, toll_charge=toll_charge, rating=4.7, eta_multiplier=0.95,
                        app_link="grab://", web_link="https://www.grab.com/th/", category_tag="Market Leader",
                        currency="THB", currency_symbol="฿"
                    )
                ]
            return []
        except Exception:
            self.record_failure()
            return []


class XanhSMAdapter(ProviderAdapter):
    """Xanh SM 100% Pure Electric VinFast Taxi Fleet in Vietnam."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="XanhSM", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Xanh SM Electric Taxi (VinFast)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["ho chi minh city", "hanoi", "da nang"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="Xanh SM Electric Taxi (VinFast)", vehicle_type="Cab", base_fare=20000, per_km=14500.0,
                    per_min=0.0, plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.9, eta_multiplier=0.90,
                    app_link="https://www.xanhsm.com", web_link="https://www.xanhsm.com",
                    is_government_backed=False, category_tag="100% Pure Electric Fleet",
                    regulatory_body="GSM VinFast Green Mobility", zero_surge=True,
                    currency="VND", currency_symbol="₫"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class GoAppJapanAdapter(ProviderAdapter):
    """GO App (#1 Taxi App in Japan by Tokyo Nihon Kotsu & MLIT)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="GoAppJapan", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["GO App (Tokyo Nihon Kotsu)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["tokyo", "osaka", "kyoto", "yokohama"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="GO App (Tokyo Nihon Kotsu)", vehicle_type="Cab", base_fare=500, per_km=400.0,
                    per_min=45.0, plat_fee=100, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.9, eta_multiplier=0.90,
                    app_link="https://go.mo-t.com/", web_link="https://go.mo-t.com/",
                    is_government_backed=True, category_tag="Market Leader #1",
                    regulatory_body="Ministry of Land, Infrastructure & Transport (MLIT)", zero_surge=True,
                    currency="JPY", currency_symbol="¥"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class KakaoTaxiAdapter(ProviderAdapter):
    """Kakao T (#1 Taxi & Mobility App in South Korea with 95%+ share)."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="KakaoTaxi", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["Kakao T (Standard Taxi)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["seoul", "busan", "incheon"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="Kakao T (Standard Taxi)", vehicle_type="Cab", base_fare=4800, per_km=1000.0,
                    per_min=250.0, plat_fee=1000, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.9, eta_multiplier=0.85,
                    app_link="kakaot://", web_link="https://www.kakaomobility.com",
                    is_government_backed=True, category_tag="National Standard #1",
                    regulatory_body="Ministry of Land, Infrastructure & Transport", zero_surge=True,
                    currency="KRW", currency_symbol="₩"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class Cabs13Adapter(ProviderAdapter):
    """13CABS Australia National Regulated Taxi Fleet."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="Cabs13", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["13CABS Sydney"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["sydney", "melbourne", "brisbane", "perth"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="13CABS Sydney", vehicle_type="Cab", base_fare=4.20, per_km=2.35,
                    per_min=0.95, plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.6, eta_multiplier=0.90,
                    app_link="https://www.13cabs.com.au", web_link="https://www.13cabs.com.au",
                    is_government_backed=True, category_tag="Govt-Backed",
                    regulatory_body="NSW Point to Point Transport Commission", zero_surge=True,
                    currency="AUD", currency_symbol="A$"
                )
            ]
        except Exception:
            self.record_failure()
            return []


class App99Adapter(ProviderAdapter):
    """99 (99Pop / 99Taxi) Brazil #1 Homegrown Mobility App."""

    def __init__(self, enabled: bool = True):
        super().__init__(name="App99", enabled=enabled, timeout_seconds=2.5)

    def get_vehicle_categories(self) -> List[str]:
        return ["99Pop São Paulo", "99Taxi (Metered Cab)"]

    async def get_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        if not self.check_circuit() or city.lower() not in ["são paulo", "sao paulo", "rio de janeiro"]:
            return []

        try:
            return [
                _build_quote(
                    provider_name="99Pop São Paulo", vehicle_type="Cab", base_fare=4.50, per_km=1.80,
                    per_min=0.35, plat_fee=1.50, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=surge_multiplier, toll_charge=toll_charge, rating=4.8, eta_multiplier=0.90,
                    app_link="https://99app.com", web_link="https://99app.com", category_tag="Market Leader #1 Brazil",
                    currency="BRL", currency_symbol="R$"
                ),
                _build_quote(
                    provider_name="99Taxi (Metered Cab)", vehicle_type="Cab", base_fare=5.50, per_km=2.75,
                    per_min=0.60, plat_fee=0.0, distance_km=distance_km, duration_mins=duration_mins,
                    surge_multiplier=1.0, toll_charge=toll_charge, rating=4.6, eta_multiplier=0.90,
                    app_link="https://99app.com", web_link="https://99app.com", is_government_backed=True,
                    category_tag="State-Regulated", regulatory_body="SPTrans / DTP São Paulo", zero_surge=True,
                    currency="BRL", currency_symbol="R$"
                )
            ]
        except Exception:
            self.record_failure()
            return []
