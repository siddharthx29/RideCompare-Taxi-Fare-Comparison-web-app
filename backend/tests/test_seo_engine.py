from fastapi.testclient import TestClient

from backend.app.main import app


def test_seo_catalog_sync_and_sitemap():
    with TestClient(app) as client:
        sync_res = client.post("/api/seo/admin/sync-catalog")
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert "Kochi" in sync_data["supported_cities"]
        assert "Goa" in sync_data["supported_cities"]
        assert "Delhi" not in sync_data["supported_cities"]

        pages_res = client.get("/api/seo/pages")
        assert pages_res.status_code == 200
        slugs = {p["slug"] for p in pages_res.json()["pages"]}
        assert "/compare-cab-fares/" in slugs
        assert "/taxi-fare-calculator/" in slugs
        assert "/uber-vs-ola/" in slugs
        assert "/uber-vs-rapido/" in slugs
        assert "/cab-fare/goa/" in slugs
        assert "/cab-fare/kochi/" in slugs
        assert "/airport-taxi-fare/kochi/" in slugs
        assert "/cab-fare/delhi/" not in slugs

        sitemap_res = client.get("/api/seo/sitemap.xml")
        assert sitemap_res.status_code == 200
        assert "<urlset" in sitemap_res.text
        assert "https://ridecompare.world/cab-fare/kochi/" in sitemap_res.text


def test_seo_csv_import_and_maintenance():
    with TestClient(app) as client:
        csv_payload = (
            "keyword,search_volume,keyword_difficulty,impressions,clicks,position\n"
            "Taxi fare in Kochi,720,22,180,9,8.4\n"
            "Cab price comparison in Delhi,900,35,0,0,\n"
        )
        imp_res = client.post(
            "/api/seo/admin/keywords/import-csv",
            json={"csv_text": csv_payload, "source": "csv_import"},
        )
        assert imp_res.status_code == 200

        maint_res = client.post("/api/seo/admin/maintenance/run?cadence=weekly")
        assert maint_res.status_code == 200
        assert "[WEEKLY]" in maint_res.json()["summary"]
