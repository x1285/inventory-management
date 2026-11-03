"""
Tests for report API endpoints, including global filter support.
"""
import pytest


class TestReportsEndpoints:
    """Test suite for the reports endpoints."""

    def test_quarterly_unfiltered_returns_all_quarters(self, client):
        """Unfiltered quarterly report returns chronologically sorted quarters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        quarters = [q["quarter"] for q in response.json()]
        assert quarters == ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"]

    def test_quarterly_respects_month_filter(self, client):
        """Month filter narrows quarterly results to the matching quarter."""
        response = client.get("/api/reports/quarterly", params={"month": "2025-03"})
        assert response.status_code == 200

        quarters = [q["quarter"] for q in response.json()]
        assert quarters == ["Q1-2025"]

    def test_quarterly_respects_warehouse_filter(self, client):
        """Warehouse filter reduces order counts."""
        all_orders = sum(q["total_orders"] for q in client.get("/api/reports/quarterly").json())
        tokyo_orders = sum(
            q["total_orders"]
            for q in client.get("/api/reports/quarterly", params={"warehouse": "Tokyo"}).json()
        )
        assert 0 < tokyo_orders < all_orders

    def test_quarterly_ignores_all_filter_values(self, client):
        """'all' means no filter, matching the other pages."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get(
            "/api/reports/quarterly",
            params={"warehouse": "all", "category": "all", "status": "all", "month": "all"},
        ).json()
        assert filtered == unfiltered

    def test_monthly_trends_respects_status_filter(self, client):
        """Status filter only counts matching orders per month."""
        response = client.get(
            "/api/reports/monthly-trends", params={"status": "Delivered", "month": "2025-01"}
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["month"] == "2025-01"
        assert data[0]["order_count"] == data[0]["delivered_count"]

    def test_monthly_trends_respects_category_filter(self, client):
        """Category filter is case-insensitive and reduces the monthly totals."""
        all_count = sum(m["order_count"] for m in client.get("/api/reports/monthly-trends").json())
        sensor_count = sum(
            m["order_count"]
            for m in client.get("/api/reports/monthly-trends", params={"category": "Sensors"}).json()
        )
        assert 0 < sensor_count < all_count

    def test_monthly_trends_sorted_chronologically(self, client):
        """Monthly trends are returned in ascending month order."""
        months = [m["month"] for m in client.get("/api/reports/monthly-trends").json()]
        assert months == sorted(months)
