#!/usr/bin/env python3
"""Wipe demo numbers and reseed Alex Rivera as an India middle-aged urban persona (INR).

KEEP login: alex.rivera.demo@example.com / DemoFinance2026! (display name Alex Rivera OK).
Does NOT delete the user.

Idempotent wipe+seed:
  1) Cancel loan commitments
  2) Delete budgets, goals, assets, recurring, extra merchant rules, payees
  3) Bulk-delete transactions
  4) Delete all accounts (incl. USD loans) — currency is create-only
  5) Set workspace default_currency=INR + user currency_display=INR
  6) Reseed INR accounts / payees / ~75d txs / budgets / goals / assets /
     recurring / rules / Home+Car loans / combined-plan commitment
  7) Exercise dashboard + reports; write seed_demo_india_result.json

Run: python3 scripts/seed_demo_alex_india.py
Requires API at http://localhost:8000 (sudo docker compose up).
"""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

BASE = "http://localhost:8000"
EMAIL = "alex.rivera.demo@example.com"
PASSWORD = "DemoFinance2026!"
TODAY = date(2026, 9, 11)
RNG = random.Random(20260911)
OUT = Path(__file__).resolve().parent / "seed_demo_india_result.json"
CURRENCY = "INR"

# Coherent lifestyle numbers (Bengaluru urban, ~45, dual-ish household)
SALARY_PRIMARY = 220000.00  # Infosys salary credit, 1st
SALARY_SPOUSE = 45000.00  # spouse freelancing / part income to SBI, 15th
SOCIETY_MAINT = 12500.00
SIP_AMOUNT = 25000.00
PHONE_JIO = 799.00
NETFLIX_INR = 649.00
SPOTIFY_INR = 119.00

# Home loan ~ tens of lakhs outstanding; car loan separate
HOME_PRINCIPAL = "6500000.00"  # ₹65L
HOME_RATE = "8.40"
HOME_TENURE = 240  # 20y
HOME_DISBURSED = date(2022, 6, 5)
CAR_PRINCIPAL = "1200000.00"  # ₹12L
CAR_RATE = "9.00"
CAR_TENURE = 60
CAR_DISBURSED = date(2025, 2, 10)
COMBINED_EXTRA = "15000.00"  # ₹15k/mo extra principal


class Api:
    def __init__(self) -> None:
        self.token: str | None = None

    def login(self, retries: int = 10) -> None:
        body = urllib.parse.urlencode(
            {"username": EMAIL, "password": PASSWORD}
        ).encode()
        last: Exception | None = None
        for i in range(retries):
            req = urllib.request.Request(
                f"{BASE}/api/auth/login",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    self.token = json.loads(resp.read())["access_token"]
                print(f"logged in as {EMAIL}")
                return
            except urllib.error.HTTPError as e:
                err = e.read().decode(errors="replace")
                last = RuntimeError(f"login {e.code}: {err[:200]}")
                if e.code == 429:
                    wait = 20 + i * 12
                    print(f"rate limited, sleep {wait}s...")
                    time.sleep(wait)
                    continue
                raise last from e
        raise last or RuntimeError("login failed")

    def request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        raw: bool = False,
        query: dict | None = None,
    ) -> Any:
        url = f"{BASE}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        data = None
        headers = {"Authorization": f"Bearer {self.token}"}
        if payload is not None:
            data = json.dumps(payload, default=str).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
                if raw:
                    return body
                if not body or resp.status == 204:
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} -> {e.code}: {err[:1000]}") from e

    def get(self, path: str, **kw: Any) -> Any:
        return self.request("GET", path, **kw)

    def post(self, path: str, payload: Any | None = None, **kw: Any) -> Any:
        return self.request("POST", path, payload=payload, **kw)

    def patch(self, path: str, payload: Any) -> Any:
        return self.request("PATCH", path, payload=payload)

    def put(self, path: str, payload: Any) -> Any:
        return self.request("PUT", path, payload=payload)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)


def money(x: float | str | Decimal) -> str:
    return f"{Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def month_back(base: date, offset: int) -> date:
    y, m = base.year, base.month - offset
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def wipe(api: Api, notes: list[str]) -> dict[str, int]:
    """Thoroughly remove demo entities; keep user + workspace shell."""
    wiped: dict[str, int] = {}

    # 1) Cancel loan commitments
    try:
        commitments = api.get("/api/v1/loans/commitments") or []
        for c in commitments:
            if c.get("status") == "active":
                try:
                    api.post(f"/api/v1/loans/commitments/{c['id']}/cancel")
                    wiped["commitments_cancelled"] = wiped.get("commitments_cancelled", 0) + 1
                except RuntimeError as e:
                    notes.append(f"cancel commitment {c['id']}: {e}")
    except RuntimeError as e:
        notes.append(f"list commitments: {e}")

    # 2) Budgets
    budgets = api.get("/api/budgets") or []
    for b in budgets:
        try:
            api.delete(f"/api/budgets/{b['id']}")
            wiped["budgets"] = wiped.get("budgets", 0) + 1
        except RuntimeError as e:
            notes.append(f"budget delete: {e}")

    # 3) Goals
    for g in api.get("/api/goals") or []:
        try:
            api.delete(f"/api/goals/{g['id']}")
            wiped["goals"] = wiped.get("goals", 0) + 1
        except RuntimeError as e:
            notes.append(f"goal delete: {e}")

    # 4) Assets
    for a in api.get("/api/assets") or []:
        try:
            api.delete(f"/api/assets/{a['id']}")
            wiped["assets"] = wiped.get("assets", 0) + 1
        except RuntimeError as e:
            notes.append(f"asset delete: {e}")

    # 5) Recurring
    for r in api.get("/api/recurring-transactions") or []:
        try:
            api.delete(f"/api/recurring-transactions/{r['id']}")
            wiped["recurring"] = wiped.get("recurring", 0) + 1
        except RuntimeError as e:
            notes.append(f"recurring delete: {e}")

    # 6) Extra merchant rules (keep default packs; drop US demo + any prior custom)
    keep_substrings = ("default", "pack", "salary", "transfer", "atm", "interest")
    us_or_custom = (
        "whole foods",
        "pg&e",
        "chipotle",
        "bigbasket",
        "swiggy",
        "bescom",
        "amazon.in",
        "zomato",
        "dmart",
    )
    for r in api.get("/api/rules") or []:
        name = (r.get("name") or "").lower()
        if any(k in name for k in us_or_custom) or not any(k in name for k in keep_substrings):
            # Only delete clearly merchant-demo rules; skip if looks like pack default
            if any(k in name for k in us_or_custom) or r.get("is_system") is False:
                try:
                    # Prefer deleting known demo extras; skip pack-installed if protected
                    if any(k in name for k in us_or_custom):
                        api.delete(f"/api/rules/{r['id']}")
                        wiped["rules"] = wiped.get("rules", 0) + 1
                except RuntimeError as e:
                    notes.append(f"rule delete {name}: {e}")

    # 7) All transactions (paginate + bulk delete)
    tx_ids: list[str] = []
    page = 1
    while True:
        page_data = api.get("/api/transactions", query={"limit": 100, "page": page})
        items = page_data.get("items") or []
        if not items:
            break
        tx_ids.extend(t["id"] for t in items)
        if len(tx_ids) >= (page_data.get("total") or 0):
            break
        page += 1
        if page > 50:
            break
    for i in range(0, len(tx_ids), 50):
        chunk = tx_ids[i : i + 50]
        try:
            api.post("/api/transactions/bulk-delete", {"transaction_ids": chunk})
            wiped["transactions"] = wiped.get("transactions", 0) + len(chunk)
        except RuntimeError as e:
            notes.append(f"bulk-delete txs: {e}")
            for tid in chunk:
                try:
                    api.delete(f"/api/transactions/{tid}")
                    wiped["transactions"] = wiped.get("transactions", 0) + 1
                except RuntimeError:
                    pass

    # 8) Payees
    payees = api.get("/api/payees") or []
    if payees:
        try:
            api.post("/api/payees/bulk-delete", {"ids": [p["id"] for p in payees]})
            wiped["payees"] = len(payees)
        except RuntimeError as e:
            notes.append(f"payee bulk-delete: {e}")
            for p in payees:
                try:
                    api.delete(f"/api/payees/{p['id']}")
                    wiped["payees"] = wiped.get("payees", 0) + 1
                except RuntimeError as e2:
                    notes.append(f"payee delete: {e2}")

    # 9) Accounts (loans + bank) — currency cannot be patched
    for a in api.get("/api/accounts") or []:
        try:
            api.delete(f"/api/accounts/{a['id']}")
            wiped["accounts"] = wiped.get("accounts", 0) + 1
        except RuntimeError as e:
            notes.append(f"account delete {a.get('name')}: {e}")

    print("wipe:", wiped)
    return wiped


def ensure_categories(api: Api, counts: dict[str, int]) -> dict[str, Any]:
    cats = {c["name"]: c for c in api.get("/api/categories")}
    housing = cats["Housing"]
    dining = cats["Food & Dining"]
    if "Utilities" not in cats:
        cats["Utilities"] = api.post(
            "/api/categories",
            {
                "name": "Utilities",
                "icon": "zap",
                "color": "#F97316",
                "group_id": housing.get("group_id"),
            },
        )
        counts["categories_added"] = counts.get("categories_added", 0) + 1
    if "Education & Family" not in cats:
        cats["Education & Family"] = api.post(
            "/api/categories",
            {
                "name": "Education & Family",
                "icon": "users",
                "color": "#6366F1",
                "group_id": dining.get("group_id"),
            },
        )
        counts["categories_added"] = counts.get("categories_added", 0) + 1
    return cats


def set_inr(api: Api, notes: list[str]) -> dict[str, Any]:
    workspaces = api.get("/api/workspaces")
    ws = workspaces[0]
    patched = api.patch(
        f"/api/workspaces/{ws['id']}",
        {"default_currency": "INR", "locale": "en-IN", "tax_jurisdiction": "IN"},
    )
    me = api.get("/api/users/me")
    prefs = dict(me.get("preferences") or {})
    prefs["currency_display"] = "INR"
    prefs["display_name"] = "Alex Rivera"
    prefs["onboarding_completed"] = True
    prefs["language"] = "en"
    try:
        me2 = api.patch("/api/users/me", {"preferences": prefs})
    except RuntimeError as e:
        notes.append(f"user prefs: {e}")
        me2 = me
    return {
        "workspace_id": ws["id"],
        "workspace_currency": patched.get("default_currency"),
        "locale": patched.get("locale"),
        "user_currency_display": (me2.get("preferences") or {}).get("currency_display"),
    }


def seed_accounts(api: Api, counts: dict[str, int]) -> dict[str, Any]:
    open_date = (TODAY - timedelta(days=90)).isoformat()
    specs = [
        {
            "name": "HDFC Salary Savings",
            "type": "checking",
            "balance": "385000.00",
            "currency": CURRENCY,
            "balance_date": open_date,
        },
        {
            "name": "SBI Savings",
            "type": "savings",
            "balance": "612000.00",
            "currency": CURRENCY,
            "balance_date": open_date,
        },
        {
            "name": "HDFC Regalia Credit Card",
            "type": "credit_card",
            "balance": "42500.00",
            "currency": CURRENCY,
            "credit_limit": "300000.00",
            "statement_close_day": 20,
            "payment_due_day": 10,
            "minimum_payment": "2000.00",
            "card_brand": "visa",
            "card_level": "platinum",
            "balance_date": open_date,
        },
        {
            "name": "Cash Wallet",
            "type": "wallet",
            "balance": "8500.00",
            "currency": CURRENCY,
            "balance_date": open_date,
        },
    ]
    acct: dict[str, Any] = {}
    for spec in specs:
        created = api.post("/api/accounts", spec)
        acct[spec["name"]] = created
        counts["accounts_created"] = counts.get("accounts_created", 0) + 1
    print("accounts:", {k: v["id"] for k, v in acct.items()})
    return acct


def seed_payees(api: Api, counts: dict[str, int]) -> dict[str, Any]:
    specs = [
        ("Infosys Ltd Payroll", "company", None),
        ("Spouse Freelance Credits", "person", None),
        ("Prestige Lakeside Society", "company", None),
        ("BigBasket", "company", "https://www.bigbasket.com"),
        ("DMart", "company", None),
        ("Swiggy", "company", None),
        ("Zomato", "company", None),
        ("Ola Cabs", "company", None),
        ("Uber India", "company", None),
        ("BESCOM", "company", None),
        ("Jio Fiber / Mobile", "company", None),
        ("Airtel", "company", None),
        ("DPS Bangalore Fees", "company", None),
        ("Parents Support UPI", "person", None),
        ("Indian Oil Petrol", "company", None),
        ("Amazon.in", "company", "https://www.amazon.in"),
        ("Netflix India", "company", None),
        ("Spotify India", "company", None),
        ("Apollo Pharmacy", "company", None),
        ("HDFC Mutual Fund SIP", "company", None),
        ("SBI Home Loan EMI", "company", None),
        ("HDFC Car Loan EMI", "company", None),
    ]
    payees: dict[str, Any] = {}
    for name, typ, website in specs:
        payload: dict[str, Any] = {"name": name, "type": typ}
        if website:
            payload["website"] = website
        payees[name] = api.post("/api/payees", payload)
        counts["payees"] = counts.get("payees", 0) + 1
    return payees


def seed_transactions(
    api: Api,
    acct: dict[str, Any],
    cats: dict[str, Any],
    payees: dict[str, Any],
    counts: dict[str, int],
) -> None:
    hdfc = acct["HDFC Salary Savings"]
    sbi = acct["SBI Savings"]
    card = acct["HDFC Regalia Credit Card"]
    cash = acct["Cash Wallet"]

    salary_cat = cats["Salary & Income"]
    grocery = cats["Groceries"]
    dining = cats["Food & Dining"]
    housing = cats["Housing"]
    transport = cats["Transport"]
    subs = cats["Subscriptions"]
    shopping = cats["Shopping"]
    health = cats["Health"]
    leisure = cats["Leisure"]
    utilities = cats["Utilities"]
    family = cats["Education & Family"]

    tx_count = 0
    transfer_count = 0
    start = TODAY - timedelta(days=75)

    def add_tx(
        account_id: str,
        description: str,
        amount: float,
        d: date,
        typ: str,
        category_id: str | None = None,
        payee_id: str | None = None,
        notes: str | None = None,
    ) -> Any:
        nonlocal tx_count
        payload: dict[str, Any] = {
            "account_id": account_id,
            "description": description,
            "amount": money(amount),
            "date": d.isoformat(),
            "type": typ,
            "currency": CURRENCY,
        }
        if category_id:
            payload["category_id"] = category_id
        if payee_id:
            payload["payee_id"] = payee_id
        if notes:
            payload["notes"] = notes
        res = api.post("/api/transactions", payload)
        tx_count += 1
        return res

    for month_offset in range(0, 4):
        mstart = month_back(TODAY, month_offset)
        # Primary salary 1st
        d_sal = mstart
        if start <= d_sal <= TODAY:
            add_tx(
                hdfc["id"],
                "INFOSYS LTD SALARY CREDIT",
                SALARY_PRIMARY,
                d_sal,
                "credit",
                salary_cat["id"],
                payees["Infosys Ltd Payroll"]["id"],
                notes="Monthly salary",
            )
        # Spouse / secondary mid-month
        try:
            d_sp = date(mstart.year, mstart.month, 15)
        except ValueError:
            d_sp = mstart
        if start <= d_sp <= TODAY:
            add_tx(
                sbi["id"],
                "SPOUSE FREELANCE UPI CREDIT",
                SALARY_SPOUSE,
                d_sp,
                "credit",
                salary_cat["id"],
                payees["Spouse Freelance Credits"]["id"],
            )
        # Society maintenance 5th
        d_soc = date(mstart.year, mstart.month, 5)
        if start <= d_soc <= TODAY:
            add_tx(
                hdfc["id"],
                "Prestige Lakeside Society — Maintenance",
                SOCIETY_MAINT,
                d_soc,
                "debit",
                housing["id"],
                payees["Prestige Lakeside Society"]["id"],
            )
        # BESCOM ~7th
        d_pow = date(mstart.year, mstart.month, 7)
        if start <= d_pow <= TODAY:
            add_tx(
                hdfc["id"],
                "BESCOM Electricity Bill",
                RNG.uniform(2800, 4200),
                d_pow,
                "debit",
                utilities["id"],
                payees["BESCOM"]["id"],
            )
        # Jio
        d_jio = date(mstart.year, mstart.month, 8)
        if start <= d_jio <= TODAY:
            add_tx(
                hdfc["id"],
                "Jio Fiber + Mobile",
                PHONE_JIO,
                d_jio,
                "debit",
                utilities["id"],
                payees["Jio Fiber / Mobile"]["id"],
            )
        # School fees quarterly-ish: months 7 and 9 (Jul/Sep) already in window for Sep; also June if in range
        if mstart.month in (6, 7, 9):
            d_fee = date(mstart.year, mstart.month, 3)
            if start <= d_fee <= TODAY:
                add_tx(
                    hdfc["id"],
                    "DPS Bangalore — Term Fees",
                    48500.00,
                    d_fee,
                    "debit",
                    family["id"],
                    payees["DPS Bangalore Fees"]["id"],
                )
        # Parents support
        d_par = date(mstart.year, mstart.month, 10)
        if start <= d_par <= TODAY:
            add_tx(
                hdfc["id"],
                "UPI to Parents — Monthly Support",
                15000.00,
                d_par,
                "debit",
                family["id"],
                payees["Parents Support UPI"]["id"],
            )
        # SIP
        d_sip = date(mstart.year, mstart.month, 5)
        if start <= d_sip <= TODAY:
            add_tx(
                hdfc["id"],
                "HDFC Flexi Cap SIP",
                SIP_AMOUNT,
                d_sip,
                "debit",
                cats.get("Transfers", shopping)["id"] if False else shopping["id"],
                payees["HDFC Mutual Fund SIP"]["id"],
                notes="Monthly SIP (investment outflow)",
            )
        # Streaming on card
        for day, desc, amt, payee, cat in [
            (9, "NETFLIX.COM", NETFLIX_INR, "Netflix India", subs),
            (11, "SPOTIFY PREMIUM", SPOTIFY_INR, "Spotify India", subs),
        ]:
            d = date(mstart.year, mstart.month, day)
            if start <= d <= TODAY:
                add_tx(
                    card["id"],
                    desc,
                    amt,
                    d,
                    "debit",
                    cat["id"],
                    payees[payee]["id"],
                )

    # Daily-ish lifestyle over window
    d = start
    while d <= TODAY:
        if d.weekday() == 5:  # Saturday groceries
            store = RNG.choice(["BigBasket", "DMart"])
            add_tx(
                hdfc["id"] if RNG.random() > 0.4 else card["id"],
                f"{store} groceries",
                RNG.uniform(2200, 5800),
                d,
                "debit",
                grocery["id"],
                payees[store]["id"],
            )
        if d.weekday() in (1, 3, 5) and RNG.random() > 0.3:
            app = RNG.choice(["Swiggy", "Zomato"])
            add_tx(
                card["id"],
                f"{app} Order",
                RNG.uniform(280, 850),
                d,
                "debit",
                dining["id"],
                payees[app]["id"],
            )
        if d.weekday() < 5 and RNG.random() > 0.55:
            cab = RNG.choice(["Ola Cabs", "Uber India"])
            add_tx(
                card["id"],
                f"{cab} trip",
                RNG.uniform(120, 450),
                d,
                "debit",
                transport["id"],
                payees[cab]["id"],
            )
        if (d - start).days % 9 == 0:
            add_tx(
                card["id"],
                "Indian Oil Petrol",
                RNG.uniform(2500, 4200),
                d,
                "debit",
                transport["id"],
                payees["Indian Oil Petrol"]["id"],
            )
        if d.weekday() == 0 and RNG.random() > 0.45:
            add_tx(
                card["id"],
                "AMAZON.IN*ORDER",
                RNG.uniform(499, 4500),
                d,
                "debit",
                shopping["id"],
                payees["Amazon.in"]["id"],
            )
        if d.day == 18:
            add_tx(
                card["id"],
                "Apollo Pharmacy",
                RNG.uniform(350, 1800),
                d,
                "debit",
                health["id"],
                payees["Apollo Pharmacy"]["id"],
            )
        if d.weekday() == 6 and RNG.random() > 0.45:
            add_tx(
                card["id"],
                "Weekend outing / movie",
                RNG.uniform(800, 3500),
                d,
                "debit",
                leisure["id"],
            )
        # small cash spends
        if d.weekday() == 4 and RNG.random() > 0.4:
            add_tx(
                cash["id"],
                "Local kirana / chai cash",
                RNG.uniform(80, 350),
                d,
                "debit",
                grocery["id"],
            )
        d += timedelta(days=1)

    # Transfers: savings sweep, CC payment, ATM
    for month_offset in range(0, 4):
        mstart = month_back(TODAY, month_offset)
        d_save = date(mstart.year, mstart.month, 2)
        if start <= d_save <= TODAY:
            api.post(
                "/api/transactions/transfer",
                {
                    "from_account_id": hdfc["id"],
                    "to_account_id": sbi["id"],
                    "amount": money(40000),
                    "date": d_save.isoformat(),
                    "description": "Transfer to SBI savings",
                },
            )
            transfer_count += 1
        d_pay = date(mstart.year, mstart.month, 10)
        if start <= d_pay <= TODAY:
            api.post(
                "/api/transactions/transfer",
                {
                    "from_account_id": hdfc["id"],
                    "to_account_id": card["id"],
                    "amount": money(35000),
                    "date": d_pay.isoformat(),
                    "description": "HDFC Regalia credit card payment",
                },
            )
            transfer_count += 1
        d_atm = date(mstart.year, mstart.month, 18)
        if start <= d_atm <= TODAY:
            api.post(
                "/api/transactions/transfer",
                {
                    "from_account_id": hdfc["id"],
                    "to_account_id": cash["id"],
                    "amount": money(5000),
                    "date": d_atm.isoformat(),
                    "description": "ATM cash withdrawal",
                },
            )
            transfer_count += 1

    counts["transactions"] = tx_count
    counts["transfers"] = transfer_count


def seed_budgets_goals_assets_recurring_rules(
    api: Api,
    acct: dict[str, Any],
    cats: dict[str, Any],
    payees: dict[str, Any],
    counts: dict[str, int],
    notes: list[str],
) -> None:
    hdfc = acct["HDFC Salary Savings"]
    sbi = acct["SBI Savings"]
    card = acct["HDFC Regalia Credit Card"]
    month_start = date(TODAY.year, TODAY.month, 1)

    budget_specs = [
        (cats["Housing"], 45000),  # society + buffers (EMI tracked via loans)
        (cats["Groceries"], 18000),
        (cats["Food & Dining"], 8000),
        (cats["Transport"], 12000),
        (cats["Utilities"], 6000),
        (cats["Education & Family"], 35000),
        (cats["Subscriptions"], 1500),
        (cats["Shopping"], 10000),
        (cats["Leisure"], 5000),
        (cats["Health"], 3000),
    ]
    for cat, amt in budget_specs:
        api.post(
            "/api/budgets",
            {
                "category_id": cat["id"],
                "amount": money(amt),
                "month": month_start.isoformat(),
                "is_recurring": True,
            },
        )
        counts["budgets"] = counts.get("budgets", 0) + 1

    goal_specs = [
        {
            "name": "Emergency Fund (6 months)",
            "target_amount": money(1000000),
            "current_amount": money(450000),
            "currency": CURRENCY,
            "target_date": date(2027, 6, 1).isoformat(),
            "tracking_type": "account",
            "account_id": sbi["id"],
            "icon": "shield",
            "color": "#10B981",
        },
        {
            "name": "Goa + Kerala Family Vacation",
            "target_amount": money(150000),
            "current_amount": money(65000),
            "currency": CURRENCY,
            "target_date": date(2026, 12, 20).isoformat(),
            "tracking_type": "manual",
            "icon": "plane",
            "color": "#3B82F6",
        },
        {
            "name": "Child Education Corpus",
            "target_amount": money(2500000),
            "current_amount": money(820000),
            "currency": CURRENCY,
            "target_date": date(2032, 4, 1).isoformat(),
            "tracking_type": "manual",
            "icon": "graduation-cap",
            "color": "#8B5CF6",
        },
    ]
    for spec in goal_specs:
        api.post("/api/goals", spec)
        counts["goals"] = counts.get("goals", 0) + 1

    asset_specs = [
        {
            "name": "Mutual Fund SIP Corpus (HDFC/Parag Parikh)",
            "type": "investment",
            "currency": CURRENCY,
            "valuation_method": "manual",
            "purchase_date": "2019-04-01",
            "purchase_price": money(950000),
            "current_value": money(1850000),
        },
        {
            "name": "2022 Hyundai Creta",
            "type": "vehicle",
            "currency": CURRENCY,
            "valuation_method": "manual",
            "purchase_date": "2022-02-15",
            "purchase_price": money(1450000),
            "current_value": money(980000),
        },
        {
            "name": "Prestige Lakeside Flat Equity",
            "type": "real_estate",
            "currency": CURRENCY,
            "valuation_method": "manual",
            "purchase_date": "2022-05-01",
            "purchase_price": money(9500000),
            "current_value": money(13500000),
        },
    ]
    for spec in asset_specs:
        try:
            api.post("/api/assets", spec)
            counts["assets"] = counts.get("assets", 0) + 1
        except RuntimeError as e:
            notes.append(f"asset {spec['name']}: {e}")

    rec_specs = [
        {
            "description": "Infosys Salary",
            "amount": money(SALARY_PRIMARY),
            "currency": CURRENCY,
            "type": "credit",
            "frequency": "monthly",
            "day_of_month": 1,
            "start_date": (TODAY - timedelta(days=60)).isoformat(),
            "account_id": hdfc["id"],
            "category_id": cats["Salary & Income"]["id"],
            "skip_first": True,
            "auto_generate": True,
        },
        {
            "description": "Society Maintenance — Prestige",
            "amount": money(SOCIETY_MAINT),
            "currency": CURRENCY,
            "type": "debit",
            "frequency": "monthly",
            "day_of_month": 5,
            "start_date": (TODAY - timedelta(days=60)).isoformat(),
            "account_id": hdfc["id"],
            "category_id": cats["Housing"]["id"],
            "skip_first": True,
            "auto_generate": True,
        },
        {
            "description": "HDFC Flexi Cap SIP",
            "amount": money(SIP_AMOUNT),
            "currency": CURRENCY,
            "type": "debit",
            "frequency": "monthly",
            "day_of_month": 5,
            "start_date": (TODAY - timedelta(days=60)).isoformat(),
            "account_id": hdfc["id"],
            "category_id": cats["Shopping"]["id"],
            "skip_first": True,
            "auto_generate": True,
        },
        {
            "description": "Jio Fiber + Mobile",
            "amount": money(PHONE_JIO),
            "currency": CURRENCY,
            "type": "debit",
            "frequency": "monthly",
            "day_of_month": 8,
            "start_date": (TODAY - timedelta(days=60)).isoformat(),
            "account_id": hdfc["id"],
            "category_id": cats["Utilities"]["id"],
            "skip_first": True,
            "auto_generate": True,
        },
        {
            "description": "Netflix India",
            "amount": money(NETFLIX_INR),
            "currency": CURRENCY,
            "type": "debit",
            "frequency": "monthly",
            "day_of_month": 9,
            "start_date": (TODAY - timedelta(days=60)).isoformat(),
            "account_id": card["id"],
            "category_id": cats["Subscriptions"]["id"],
            "skip_first": True,
            "auto_generate": True,
        },
    ]
    for spec in rec_specs:
        api.post("/api/recurring-transactions", spec)
        counts["recurring"] = counts.get("recurring", 0) + 1

    rule_specs = [
        {
            "name": "BigBasket → Groceries",
            "conditions_op": "or",
            "conditions": [
                {"field": "description", "op": "contains", "value": "BigBasket"},
                {"field": "description", "op": "contains", "value": "BIGBASKET"},
            ],
            "actions": [{"op": "set_category", "value": cats["Groceries"]["id"]}],
            "priority": 10,
            "is_active": True,
            "apply_to_existing": True,
            "overwrite_existing_categories": False,
        },
        {
            "name": "Swiggy/Zomato → Dining",
            "conditions_op": "or",
            "conditions": [
                {"field": "description", "op": "contains", "value": "Swiggy"},
                {"field": "description", "op": "contains", "value": "Zomato"},
            ],
            "actions": [{"op": "set_category", "value": cats["Food & Dining"]["id"]}],
            "priority": 10,
            "is_active": True,
            "apply_to_existing": True,
            "overwrite_existing_categories": False,
        },
        {
            "name": "BESCOM → Utilities",
            "conditions_op": "or",
            "conditions": [
                {"field": "description", "op": "contains", "value": "BESCOM"},
            ],
            "actions": [{"op": "set_category", "value": cats["Utilities"]["id"]}],
            "priority": 10,
            "is_active": True,
            "apply_to_existing": True,
            "overwrite_existing_categories": False,
        },
        {
            "name": "Amazon.in → Shopping",
            "conditions_op": "or",
            "conditions": [
                {"field": "description", "op": "contains", "value": "AMAZON.IN"},
                {"field": "description", "op": "contains", "value": "Amazon.in"},
            ],
            "actions": [{"op": "set_category", "value": cats["Shopping"]["id"]}],
            "priority": 10,
            "is_active": True,
            "apply_to_existing": True,
            "overwrite_existing_categories": False,
        },
    ]
    for spec in rule_specs:
        api.post("/api/rules", spec)
        counts["rules_added"] = counts.get("rules_added", 0) + 1


def ensure_schedule(api: Api, account_id: str) -> list[dict]:
    schedule = api.get(f"/api/v1/loans/{account_id}/schedule")
    if schedule:
        return schedule
    return api.post(f"/api/v1/loans/{account_id}/schedule/generate", {"version": 1})


def mark_paid_up_to(api: Api, schedule: list[dict], through: date) -> list[dict]:
    paid: list[dict] = []
    for entry in schedule:
        due = date.fromisoformat(entry["due_date"])
        if due > through:
            break
        if entry.get("payment_status") == "paid":
            paid.append(entry)
            continue
        updated = api.put(
            f"/api/v1/loans/schedule/{entry['id']}/status",
            {
                "payment_status": "paid",
                "actual_payment_date": entry["due_date"],
                "actual_amount_paid": money(entry["emi_amount"]),
            },
        )
        paid.append(updated)
    return paid


def sync_outstanding(api: Api, account_id: str, schedule: list[dict]) -> dict:
    paid = [e for e in schedule if e.get("payment_status") == "paid"]
    scheduled = [e for e in schedule if e.get("payment_status") == "scheduled"]
    if paid:
        outstanding = paid[-1]["closing_balance"]
    elif scheduled:
        outstanding = scheduled[0]["opening_balance"]
    else:
        outstanding = 0
    return api.patch(f"/api/accounts/{account_id}", {"balance": money(outstanding)})


def link_recent_emis(
    api: Api,
    *,
    funding_id: str,
    category_id: str | None,
    loan_name: str,
    paid_entries: list[dict],
) -> list[str]:
    tx_ids: list[str] = []
    for entry in paid_entries:
        if entry.get("linked_transaction_id"):
            tx_ids.append(str(entry["linked_transaction_id"]))
            continue
        tx = api.post(
            "/api/transactions",
            {
                "account_id": funding_id,
                "description": f"{loan_name} EMI #{entry['emi_number']}",
                "amount": money(entry["emi_amount"]),
                "date": entry["due_date"],
                "type": "debit",
                "currency": CURRENCY,
                "category_id": category_id,
                "payee_raw": loan_name,
                "notes": f"Seeded EMI linked to schedule {entry['id']}",
                "status": "posted",
            },
        )
        api.post(
            f"/api/v1/loans/schedule/{entry['id']}/link",
            {"transaction_id": tx["id"]},
        )
        tx_ids.append(tx["id"])
    return tx_ids


def seed_loans(
    api: Api,
    acct: dict[str, Any],
    cats: dict[str, Any],
    counts: dict[str, int],
    notes: list[str],
) -> dict[str, Any]:
    hdfc = acct["HDFC Salary Savings"]
    housing = cats["Housing"]["id"]
    transport = cats["Transport"]["id"]
    results: dict[str, Any] = {}

    loan_specs = [
        {
            "key": "home",
            "name": "SBI Home Loan — Prestige Lakeside",
            "loan_kind": "home",
            "original_principal": HOME_PRINCIPAL,
            "balance": HOME_PRINCIPAL,
            "interest_rate": HOME_RATE,
            "tenure_months": HOME_TENURE,
            "emi_day": 5,
            "disbursed_on": HOME_DISBURSED.isoformat(),
            "category_id": housing,
            "prepay": True,
        },
        {
            "key": "car",
            "name": "HDFC Car Loan — Hyundai Creta",
            "loan_kind": "auto",
            "original_principal": CAR_PRINCIPAL,
            "balance": CAR_PRINCIPAL,
            "interest_rate": CAR_RATE,
            "tenure_months": CAR_TENURE,
            "emi_day": 10,
            "disbursed_on": CAR_DISBURSED.isoformat(),
            "category_id": transport,
            "prepay": False,
        },
    ]

    for spec in loan_specs:
        payload = {
            "name": spec["name"],
            "type": "loan",
            "balance": spec["balance"],
            "currency": CURRENCY,
            "loan_kind": spec["loan_kind"],
            "original_principal": spec["original_principal"],
            "interest_rate": spec["interest_rate"],
            "tenure_months": spec["tenure_months"],
            "emi_day": spec["emi_day"],
            "disbursed_on": spec["disbursed_on"],
            "balance_date": spec["disbursed_on"],
        }
        print(f"creating loan {spec['name']}...")
        loan = api.post("/api/accounts", payload)
        counts["loans_created"] = counts.get("loans_created", 0) + 1
        schedule = ensure_schedule(api, loan["id"])
        if schedule and not loan.get("emi_amount"):
            loan = api.patch(
                f"/api/accounts/{loan['id']}",
                {"emi_amount": money(schedule[0]["emi_amount"])},
            )
        paid = mark_paid_up_to(api, schedule, TODAY - timedelta(days=1))
        schedule = api.get(f"/api/v1/loans/{loan['id']}/schedule")
        loan = sync_outstanding(api, loan["id"], schedule)
        sample = [e for e in schedule if e.get("payment_status") == "paid"][-6:]
        tx_ids = link_recent_emis(
            api,
            funding_id=hdfc["id"],
            category_id=spec["category_id"],
            loan_name=spec["name"],
            paid_entries=sample,
        )
        overview = api.get(f"/api/v1/loans/{loan['id']}/overview")
        entry: dict[str, Any] = {
            "id": loan["id"],
            "name": spec["name"],
            "loan_kind": spec["loan_kind"],
            "original_principal": spec["original_principal"],
            "interest_rate": spec["interest_rate"],
            "tenure_months": spec["tenure_months"],
            "emi_amount": loan.get("emi_amount"),
            "balance": loan.get("balance"),
            "emis_paid": overview.get("emis_paid"),
            "emis_remaining": overview.get("emis_remaining"),
            "schedule_rows": len(schedule),
            "linked_tx_sample": tx_ids,
        }
        if spec["prepay"]:
            prepay_date = (TODAY - timedelta(days=4)).isoformat()
            prepay_amt = "200000.00"  # ₹2L principal prepay
            try:
                prepay_tx = api.post(
                    "/api/transactions",
                    {
                        "account_id": hdfc["id"],
                        "description": f"{spec['name']} principal prepayment",
                        "amount": prepay_amt,
                        "date": prepay_date,
                        "type": "debit",
                        "currency": CURRENCY,
                        "category_id": housing,
                        "payee_raw": spec["name"],
                        "notes": "Demo principal prepayment (reduce_tenure)",
                        "status": "posted",
                    },
                )
                recorded = api.post(
                    "/api/v1/loans/prepayments",
                    {
                        "account_id": loan["id"],
                        "prepayment_amount": prepay_amt,
                        "prepayment_date": prepay_date,
                        "recalculation_method": "reduce_tenure",
                        "transaction_id": prepay_tx["id"],
                    },
                )
                loan = next(a for a in api.get("/api/accounts") if a["id"] == loan["id"])
                entry["prepayment"] = {
                    "amount": prepay_amt,
                    "date": prepay_date,
                    "id": recorded.get("id"),
                    "balance_after": loan.get("balance"),
                }
            except RuntimeError as e:
                notes.append(f"home prepay: {e}")
        results[spec["key"]] = entry
        print(
            f"  {spec['key']}: id={entry['id']} emi={entry['emi_amount']} "
            f"bal={entry.get('balance')} paid={entry.get('emis_paid')}"
        )
    return results


def seed_combined_plan(
    api: Api,
    home_id: str,
    funding_id: str,
    housing_cat_id: str,
    notes: list[str],
) -> dict[str, Any]:
    sim = api.post(
        "/api/v1/loans/simulations/combined",
        {
            "account_id": home_id,
            "strategy": "reduce_tenure",
            "as_of_date": TODAY.isoformat(),
            "events": [
                {
                    "type": "one_time_prepayment",
                    "date": "2026-12-20",
                    "amount": "150000.00",
                    "label": "Year-end bonus lump sum",
                },
                {
                    "type": "recurring_prepayment",
                    "date": "2026-10-01",
                    "amount": COMBINED_EXTRA,
                    "months": 60,
                    "label": "+₹15k/mo extra principal",
                },
                {
                    "type": "rate_change",
                    "date": "2027-04-01",
                    "new_rate": "8.00",
                    "label": "Repo-linked rate cut",
                },
            ],
        },
    )
    existing = api.get("/api/v1/loans/commitments", query={"account_id": home_id}) or []
    active = [
        c
        for c in existing
        if c.get("status") == "active" and c.get("kind") == "recurring_prepayment"
    ]
    if active:
        commitment = active[0]
    else:
        commitment = api.post(
            "/api/v1/loans/commitments",
            {
                "account_id": home_id,
                "kind": "recurring_prepayment",
                "amount": COMBINED_EXTRA,
                "start_date": "2026-10-01",
                "day_of_month": 1,
                "funding_account_id": funding_id,
                "category_id": housing_cat_id,
                "notes": "Demo: +₹15,000/mo home-loan principal — combined plan commit",
            },
        )
    projected = None
    try:
        projected = api.get(
            "/api/dashboard/projected-transactions", query={"month": "2026-10-01"}
        )
    except RuntimeError as e:
        notes.append(f"projected: {e}")
        projected = []
    return {
        "combined_kpis": sim.get("kpis"),
        "timeline_rows": len(sim.get("timeline") or []),
        "commitment": {
            "id": commitment["id"],
            "amount": commitment["amount"],
            "budget_id": commitment.get("budget_id"),
            "recurring_transaction_id": commitment.get("recurring_transaction_id"),
            "status": commitment.get("status"),
        },
        "projected_extra_hits": [
            p
            for p in (projected or [])
            if isinstance(p, dict)
            and "extra principal" in (p.get("description") or "").lower()
        ][:3],
        "ui_path": f"http://localhost:3000/loans/{home_id} → Combined plan tab",
    }


def exercise(api: Api, notes: list[str]) -> dict[str, Any]:
    exercised: dict[str, Any] = {}
    try:
        summary = api.get("/api/dashboard/summary")
        exercised["dashboard_summary_balance_primary"] = summary.get("total_balance_primary")
        exercised["dashboard_monthly_income"] = summary.get("monthly_income")
        exercised["dashboard_monthly_expenses"] = summary.get("monthly_expenses")
        exercised["dashboard_currency"] = summary.get("currency") or summary.get(
            "primary_currency"
        )
    except RuntimeError as e:
        notes.append(f"dashboard: {e}")

    for path, q in [
        ("/api/dashboard/spending-by-category", None),
        ("/api/dashboard/monthly-trend", None),
        ("/api/reports/net-worth", {"months": 6}),
        ("/api/reports/income-expenses", {"months": 3}),
        ("/api/reports/cash-flow", {"months": 3}),
        ("/api/search", {"q": "BigBasket"}),
        ("/api/search", {"q": "BESCOM"}),
        ("/api/v1/loans/dashboard", None),
    ]:
        try:
            res = api.get(path, query=q)
            if isinstance(res, list):
                exercised[path] = f"list len={len(res)}"
            elif isinstance(res, dict):
                exercised[path] = {
                    k: res.get(k)
                    for k in list(res.keys())[:8]
                }
            else:
                exercised[path] = type(res).__name__
        except RuntimeError as e:
            notes.append(f"{path}: {e}")
    return exercised


def main() -> int:
    api = Api()
    api.login()
    counts: dict[str, int] = {}
    notes: list[str] = []

    wiped = wipe(api, notes)
    currency_info = set_inr(api, notes)
    print("currency:", currency_info)

    cats = ensure_categories(api, counts)
    acct = seed_accounts(api, counts)
    payees = seed_payees(api, counts)
    seed_transactions(api, acct, cats, payees, counts)
    seed_budgets_goals_assets_recurring_rules(api, acct, cats, payees, counts, notes)
    loans = seed_loans(api, acct, cats, counts, notes)
    combined = seed_combined_plan(
        api,
        loans["home"]["id"],
        acct["HDFC Salary Savings"]["id"],
        cats["Housing"]["id"],
        notes,
    )
    exercised = exercise(api, notes)

    # Final totals
    accounts = api.get("/api/accounts")
    final = {
        "accounts": len(accounts),
        "accounts_detail": [
            {
                "name": a["name"],
                "type": a["type"],
                "currency": a.get("currency"),
                "balance": a.get("balance"),
                "loan_kind": a.get("loan_kind"),
                "emi_amount": a.get("emi_amount"),
            }
            for a in accounts
        ],
        "payees": len(api.get("/api/payees")),
        "categories": len(api.get("/api/categories")),
        "transactions_total": api.get("/api/transactions", query={"limit": 1}).get("total"),
        "budgets": len(api.get("/api/budgets")),
        "goals": len(api.get("/api/goals")),
        "assets": len(api.get("/api/assets")),
        "recurring": len(api.get("/api/recurring-transactions")),
        "rules": len(api.get("/api/rules")),
        "loan_commitments": len(api.get("/api/v1/loans/commitments") or []),
    }

    me = api.get("/api/users/me")
    ws = api.get("/api/workspaces")[0]

    result = {
        "persona": "India middle-aged urban (Bengaluru), dual-ish household, INR",
        "login": {
            "email": EMAIL,
            "password": PASSWORD,
            "display_name": "Alex Rivera",
            "auth": "POST /api/auth/login form username+password -> Bearer JWT",
        },
        "currency": {
            "workspace_default": ws.get("default_currency"),
            "locale": ws.get("locale"),
            "user_currency_display": (me.get("preferences") or {}).get("currency_display"),
        },
        "wiped": wiped,
        "created_this_run": counts,
        "final_totals": final,
        "loans": loans,
        "combined_plan": combined,
        "key_cashflows": {
            "salary_primary_inr": SALARY_PRIMARY,
            "salary_spouse_inr": SALARY_SPOUSE,
            "society_maintenance_inr": SOCIETY_MAINT,
            "sip_inr": SIP_AMOUNT,
            "combined_extra_principal_inr": COMBINED_EXTRA,
        },
        "exercised": exercised,
        "notes": notes,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({k: result[k] for k in ["currency", "wiped", "created_this_run", "final_totals", "loans", "combined_plan"]}, indent=2, default=str))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("SEED FAILED:", exc, file=sys.stderr)
        raise
