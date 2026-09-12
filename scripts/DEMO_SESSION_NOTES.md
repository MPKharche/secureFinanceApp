# Planet Finance / secureFinanceApp demo session notes

## Login (UNCHANGED)
- URL: http://localhost:3000
- API: http://localhost:8000
- Name: **Alex Rivera** (display name retained by request)
- Email: alex.rivera.demo@example.com
- Password: DemoFinance2026!
- Auth: `POST /api/auth/login` with `application/x-www-form-urlencoded` fields `username` + `password` → `{ access_token, token_type: bearer }`
- User is superuser; onboarding_completed true via PATCH /api/users/me

## Currency / persona (2026-09-11 India reseed)
- **Persona:** middle-aged urban India (~45), Bengaluru dual-ish household
- Workspace `default_currency`: **INR**, `locale`: **en-IN**, `tax_jurisdiction`: **IN**
- User preference `currency_display`: **INR**
- Seed script: `scripts/seed_demo_alex_india.py` (wipe+seed, **does not delete user**)
- Result artifact: `scripts/seed_demo_india_result.json`

### How to re-run
```bash
cd /workspace/secureFinanceApp
# API must be up: sudo docker compose up -d
python3 scripts/seed_demo_alex_india.py
```
Script cancels commitments → deletes budgets/goals/assets/recurring/extra rules/payees/transactions/accounts → sets INR → reseeds accounts + lifestyle + Home/Car loans + combined-plan commitment.

Legacy USD seeds kept for reference only (do not run against India DB unless you want USD again):
- `scripts/seed_demo_alex.py`
- `scripts/seed_loans_alex.py`
- `scripts/seed_loan_combined_plan.py` (hard-codes old mortgage UUID)

## Part A fixes (still applicable)
Restored from upstream `securo-finance/securo` (raw/git show):
- `frontend/src/components/category-select.tsx` (was empty → blank dashboard)
- `frontend/src/types/index.ts` (was empty)
- `frontend/src/lib/rule-match-utils.ts` (was stub ~196B)

Frontend container restarted; Vite serves dashboard + category-select cleanly.

Known leftover stub (lazy, module-gated — does not break home shell):
- `frontend/src/pages/invoices.tsx` truncated vs upstream; many `invoice-*.tsx` components missing from fork. Visiting /invoices may fail until those are restored.

## Part E — India seed totals (after scripts/seed_demo_alex_india.py)

### Accounts (all INR)
| Account | Type | Opening / outstanding |
|---------|------|------------------------|
| HDFC Salary Savings | checking | ₹3,85,000 |
| SBI Savings | savings | ₹6,12,000 |
| HDFC Regalia Credit Card | credit_card | ₹42,500 owed (limit ₹3L) |
| Cash Wallet | wallet | ₹8,500 |
| SBI Home Loan — Prestige Lakeside | loan/home | outstanding ~₹56.6L after ₹2L prepay (orig ₹65L @ 8.40%, 240m, EMI ≈ ₹55,997.79) |
| HDFC Car Loan — Hyundai Creta | loan/auto | outstanding ~₹8.76L (orig ₹12L @ 9.00%, 60m, EMI ≈ ₹24,910.03) |

### Cashflows
- Primary salary: **₹2,20,000**/mo (Infosys) on 1st → HDFC
- Spouse/secondary: **₹45,000**/mo mid-month → SBI
- Society maintenance ₹12,500; BESCOM; Jio ₹799; SIP ₹25,000; school fees; parents support ₹15k; Swiggy/Zomato; BigBasket/DMart; Ola/Uber; petrol; Amazon.in; Netflix/Spotify
- ~75 days of activity; transfers: savings sweep ₹40k, CC payment ₹35k, ATM ₹5k

### Counts (approx after seed)
- accounts: 6 · payees: 22 · categories: 19 · transactions: ~151
- budgets: 10–11 (Housing/Groceries/Dining/Transport/Utilities/Education & Family/Subscriptions/Shopping/Leisure/Health + commitment Housing budget)
- goals: 3 — Emergency Fund ₹10L, Goa+Kerala vacation ₹1.5L, Child Education Corpus ₹25L
- assets: 3 — MF SIP corpus ₹18.5L, Hyundai Creta ₹9.8L, Prestige flat equity ₹1.35Cr
- recurring: 5–6 (salary, society, SIP, Jio, Netflix + commitment extra principal)
- rules: default packs + BigBasket, Swiggy/Zomato, BESCOM, Amazon.in

### Loans + Combined plan
| Loan | ID | EMI | Outstanding | EMIs paid |
|------|----|-----|-------------|-----------|
| SBI Home Loan — Prestige Lakeside | `57d38017-cecc-48b4-9235-714934154128` | ₹55,997.79 | ~₹56,59,245 | 51 (+ ₹2L reduce_tenure prepay) |
| HDFC Car Loan — Hyundai Creta | `c8ca7e85-e4b1-4c06-9479-da5701e6e5df` | ₹24,910.03 | ~₹8,76,411 | 19 |

Combined sim (home): interest_saved ≈ **₹17.35L**, months_saved = **50**, payoff ~2037-04-05 (baseline ~2041-06).
Active commitment: **+₹15,000/mo** extra principal (`84ded9bb-…`) → Housing budget + recurring debit on HDFC Salary Savings; surfaces in `/api/dashboard/projected-transactions?month=2026-10-01`.

Loans dashboard: active_loans=2, total_outstanding≈65.36L, total_monthly_emi≈80,907.82

### Verify quickly
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=alex.rivera.demo@example.com&password=DemoFinance2026!' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/users/me | jq .preferences
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/workspaces | jq '.[0].default_currency'
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/accounts | jq '[.[]|{name,currency,balance,type}]'
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/loans/dashboard | jq
HID=57d38017-cecc-48b4-9235-714934154128
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/loans/$HID/overview | jq
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/dashboard/projected-transactions?month=2026-10-01" \
  | jq '[.[]|select(.description|test("extra principal";"i"))]'
```

UI:
1. Login → dashboard should show ₹ / INR balances (no leftover USD demo banks)
2. **Loans** → SBI Home Loan → **Combined plan** tab → Run combined sim / see ₹15k commitment
3. Budgets / Goals / Assets show INR targets

## Skipped / blocked
- Bank sync (Pluggy/SimpleFIN/Enable Banking), OIDC, live AI agents, real email
- Multipart CSV/OFX import (use Import page in UI)
- Invoices module full restore (missing components)

## Docker note
Use `sudo docker compose` on this box (user `box` not in docker group).

## Part C/D historical (USD — superseded by Part E)
Earlier USD mortgage/auto/personal loans and $200/mo commitment were wiped by the India seed. See git history / `seed_loans_result.json` / `seed_loan_combined_result.json` if needed for reference.
