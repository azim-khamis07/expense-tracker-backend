"""Locust load testing file for Expense Tracker API."""

import random
from datetime import UTC, datetime, timedelta

from locust import HttpUser, between, task


class ExpenseTrackerUser(HttpUser):
    """Simulated user for load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Setup user before starting tasks."""
        # Register user
        timestamp = datetime.now(UTC).timestamp()
        email = f"loadtest_{timestamp}@example.com"
        password = "LoadTest123!"

        self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
            name="/api/v1/auth/register",
        )

        # Login
        login_response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="/api/v1/auth/login",
        )

        if login_response.status_code == 200:
            tokens = login_response.json()
            self.token = tokens.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}

            # Create default categories
            self.client.post(
                "/api/v1/categories/defaults",
                headers=self.headers,
                name="/api/v1/categories/defaults",
            )

            # Get categories for later use
            cat_response = self.client.get(
                "/api/v1/categories",
                headers=self.headers,
                name="/api/v1/categories [GET]",
            )
            if cat_response.status_code == 200:
                data = cat_response.json()
                self.categories = data.get("items", [])
            else:
                self.categories = []
        else:
            self.token = None
            self.headers = {}
            self.categories = []

    @task(3)
    def create_transaction(self):
        """Create random transaction."""
        if not self.token or not self.categories:
            return

        category = random.choice(self.categories)

        self.client.post(
            "/api/v1/transactions",
            headers=self.headers,
            json={
                "type": category.get("type", "expense"),
                "amount": round(random.uniform(10, 500), 2),
                "currency": "USD",
                "description": f"Load test transaction {random.randint(1, 1000)}",
                "occurred_at": datetime.now(UTC).isoformat(),
                "category_id": category.get("id"),
            },
            name="/api/v1/transactions [POST]",
        )

    @task(5)
    def list_transactions(self):
        """List transactions."""
        if not self.token:
            return

        self.client.get(
            "/api/v1/transactions",
            headers=self.headers,
            params={"limit": 20},
            name="/api/v1/transactions [GET]",
        )

    @task(2)
    def get_dashboard(self):
        """Get dashboard analytics."""
        if not self.token:
            return

        self.client.get(
            "/api/v1/analytics/dashboard",
            headers=self.headers,
            name="/api/v1/analytics/dashboard",
        )

    @task(1)
    def get_category_breakdown(self):
        """Get category breakdown."""
        if not self.token:
            return

        start_date = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        end_date = datetime.now(UTC).isoformat()

        self.client.get(
            "/api/v1/analytics/category-breakdown",
            headers=self.headers,
            params={"start_date": start_date, "end_date": end_date},
            name="/api/v1/analytics/category-breakdown",
        )

    @task(1)
    def get_trends(self):
        """Get trends analytics."""
        if not self.token:
            return

        start_date = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        end_date = datetime.now(UTC).isoformat()

        self.client.get(
            "/api/v1/analytics/trends",
            headers=self.headers,
            params={"start_date": start_date, "end_date": end_date, "interval": "day"},
            name="/api/v1/analytics/trends",
        )

    @task(1)
    def get_profile(self):
        """Get user profile."""
        if not self.token:
            return

        self.client.get(
            "/api/v1/users/profile",
            headers=self.headers,
            name="/api/v1/users/profile",
        )
