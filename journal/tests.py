
"""
Unit and integration tests for the journal app, including models, views, API, and import/export.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from .models import Trade, UserTradeSettings
from django.core.files.uploadedfile import SimpleUploadedFile
import csv
from io import TextIOWrapper

User = get_user_model()


class TradeModelTests(TestCase):
    """Tests for Trade model logic and properties."""
    def setUp(self):
        self.user = User.objects.create_user("alice", "a@example.com", "pw123")

    def test_buy_pnl(self):
        trade = Trade.objects.create(
            owner=self.user,
            symbol="AAPL",
            side="BUY",
            quantity=10,
            price=100,
            exit_price=110,
            exit_time=timezone.now(),
        )
        self.assertEqual(trade.pnl, 100)  # (110 - 100) * 10

    def test_sell_pnl(self):
        trade = Trade.objects.create(
            owner=self.user,
            symbol="AAPL",
            side="SELL",
            quantity=5,
            price=100,
            exit_price=90,
            exit_time=timezone.now(),
        )
        self.assertEqual(trade.pnl, 50)  # (100 - 90) * 5

    def test_pnl_none_if_no_exit(self):
        trade = Trade.objects.create(
            owner=self.user,
            symbol="TSLA",
            side="BUY",
            quantity=1,
            price=500,
        )
        self.assertIsNone(trade.pnl)



class AuthAndPermissionsTests(TestCase):
    """Tests for authentication and permissions in journal views."""
    def setUp(self):
        self.user1 = User.objects.create_user("bob", "b@example.com", "pw123")
        self.user2 = User.objects.create_user("carol", "c@example.com", "pw123")
        self.trade = Trade.objects.create(
            owner=self.user1,
            symbol="MSFT",
            side="BUY",
            quantity=2,
            price=200,
            exit_price=220,
            exit_time=timezone.now(),
        )

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)  # redirect

    def test_dashboard_authenticated(self):
        self.client.force_login(self.user1)  # <- guarantee logged-in
        resp = self.client.get(reverse("dashboard"))
        # dashboard redirects to home in this project
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("home"))

    def test_trade_list_only_shows_own_trades(self):
        self.client.login(username="carol", password="pw123")
        resp = self.client.get(reverse("trades_list"))
        self.assertNotContains(resp, "MSFT")



class TradesCRUDTests(TestCase):
    """Tests for create, update, and delete operations on trades."""
    def setUp(self):
        self.user = User.objects.create_user("dave", "d@example.com", "pw123")

    def test_create_trade_valid(self):
        self.client.login(username="dave", password="pw123")
        resp = self.client.post(reverse("trades_create"), {
            "symbol": "GOOG",
            "side": "BUY",
            "quantity": 1,
            "price": 50,
            "entry_time": timezone.now().isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Trade.objects.filter(owner=self.user).count(), 1)

    def test_create_trade_invalid(self):
        self.client.login(username="dave", password="pw123")
        resp = self.client.post(reverse("trades_create"), {
            "symbol": "",
            "side": "BUY",
            "quantity": 1,
            "price": 50,
        })
        self.assertEqual(resp.status_code, 200)  # re-render form
        self.assertEqual(Trade.objects.count(), 0)

    def test_edit_trade(self):
        trade = Trade.objects.create(
            owner=self.user, symbol="X", side="BUY", quantity=1, price=1,
            entry_time=timezone.now(),  # ensure it exists pre-edit
        )
        self.client.force_login(self.user)

        resp = self.client.post(
            reverse("trades_edit", args=[trade.pk]),
            {
                "symbol": "EDITED",
                "side": "BUY",
                "quantity": 1,
                "price": 1,
                "entry_time": timezone.now().isoformat(timespec="seconds"),  # required
                # leave exit fields blank unless you require them
            },
        )
        self.assertEqual(resp.status_code, 302)
        trade.refresh_from_db()
        self.assertEqual(trade.symbol, "EDITED")

    def test_delete_trade_requires_owner(self):
        other = User.objects.create_user("eve", "e@example.com", "pw123")
        trade = Trade.objects.create(owner=other, symbol="NFLX", side="SELL", quantity=1, price=100)
        self.client.login(username="dave", password="pw123")
        resp = self.client.post(reverse("trades_delete", args=[trade.pk]))
        self.assertEqual(resp.status_code, 404)



class ImportExportTests(TestCase):
    """Tests for CSV import and export of trades."""
    def setUp(self):
        self.user = User.objects.create_user("frank", "f@example.com", "pw123")
        self.client.login(username="frank", password="pw123")

    def test_export_csv(self):
        Trade.objects.create(owner=self.user, symbol="AMD", side="BUY", quantity=1, price=10, exit_price=12, exit_time=timezone.now())
        resp = self.client.get(reverse("trades_export_csv"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("AMD", content)
        self.assertTrue(content.startswith("id,entry_time,symbol"))

    def test_import_csv_valid(self):
        # NOTE: no trailing newline at the end of the CSV string
        csv_bytes = (
            b"entry_time,symbol,side,quantity,price,exit_price,exit_time,notes\n"
            b"2025-01-01T10:00:00Z,IBM,BUY,1,100,105,2025-01-01T15:00:00Z,Note"
        )
        upload = SimpleUploadedFile("trades.csv", csv_bytes, content_type="text/csv")

        resp = self.client.post(
            reverse("trades_import"),
            {"file": upload, "dry_run": False},
            format="multipart",
        )

        # Successful import should redirect to the list
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("trades_list"))

        # Adjust the user fixture name to whatever you created in setUp
        # (self.user, self.user1, etc.)
        self.assertEqual(Trade.objects.filter(owner=self.user, symbol="IBM").count(), 1)




class CalendarTests(TestCase):
    """Tests for calendar view and monthly PnL aggregation."""
    def setUp(self):
        self.user = User.objects.create_user("gary", "g@example.com", "pw123")
        self.client.login(username="gary", password="pw123")
        self.trade = Trade.objects.create(
            owner=self.user,
            symbol="AAPL",
            side="BUY",
            quantity=1,
            price=100,
            exit_price=120,
            exit_time=timezone.now(),
        )

    def test_calendar_defaults_to_latest_trade_month(self):
        resp = self.client.get(reverse("trades_calendar"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.trade.exit_time.strftime("%B"))

    def test_calendar_context_includes_month_total_pnl(self):
        resp = self.client.get(reverse("trades_calendar"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("month_total_pnl", resp.context)
        self.assertGreater(resp.context["month_total_pnl"], 0)



class APITests(TestCase):
    """Tests for API endpoints related to trades and PnL."""
    def setUp(self):
        self.user = User.objects.create_user("henry", "h@example.com", "pw123")
        self.client.login(username="henry", password="pw123")
        self.trade = Trade.objects.create(
            owner=self.user,
            symbol="TSLA",
            side="BUY",
            quantity=1,
            price=100,
            exit_price=110,
            exit_time=timezone.now(),
        )

    def test_api_trade_pnl_series(self):
        resp = self.client.get(reverse("api_trade_pnl_series"))
        data = resp.json()
        self.assertIn("labels", data)
        self.assertIn("values", data)
        self.assertEqual(len(data["labels"]), 1)

    def test_api_daily_pnl(self):
        resp = self.client.get(reverse("api_daily_pnl"))
        data = resp.json()
        self.assertEqual(len(data["labels"]), 1)
        self.assertAlmostEqual(data["values"][0], 10.0)

    def test_api_symbol_pnl(self):
        resp = self.client.get(reverse("api_symbol_pnl"))
        data = resp.json()
        self.assertEqual(data["labels"], ["TSLA"])
        self.assertEqual(data["values"][0], 10.0)



class ProfileTests(TestCase):
    """Tests for user profile update and profile page content."""
    def setUp(self):
        self.user = User.objects.create_user("irene", "i@example.com", "pw123")
        self.client.login(username="irene", password="pw123")

    def test_update_profile_username(self):
        resp = self.client.post(
            reverse("profile"),
            {
                "username": "newirene",
                "email": "i@example.com",
                "first_name": "Irene",
                "last_name": "Smith",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("profile"))

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "newirene")

    def test_profile_page_contains_password_links(self):
        resp = self.client.get(reverse("profile"))
        self.assertContains(resp, "Change password")
