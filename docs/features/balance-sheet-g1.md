# G1 Balance Sheet (as-of date)

## What shipped
- Route: `/reports/balance-sheet` (alias `/statements/balance-sheet`)
- **Reports overview** (`/reports`): Screener-inspired one-pager with glossary KPIs, expandable P&L (FY·YTD), T-format BS, forecast; assumption chips; deep links. Charts at `/reports/charts`.
- API: `GET /api/reports/balance-sheet?as_of=YYYY-MM-DD&insurance_value_basis=recorded|sad|sv` (unchanged)
- UI: **T-format** — left **owe** (Loans (policy + others), Credit cards / dues), right **own** (Bank/cash, Property, MF/stocks, Insurance value); Net worth + savings buffer below
- As-of date picker; G4-lite assumptions: `reporting_currency`, `insurance_value_basis`, `include_policy_loan`, `as_of_fidelity`
- Fidelity badges: `as_of` | `reconstructed` | `≈ current`

## As-of logic
- **Manual accounts**: sum posted transactions with `date <= as_of` (real as-of).
- **Connected accounts**: today = provider balance; past = provider balance − post-cutoff activity (reconstructed).
- **Assets**: latest `AssetValue` with `date <= as_of`, else purchase price.
- **Insurance**: optional `insurance_value_basis` using metadata SAD / illustrative SV.

## Gaps
- Live insurer SV quote integration
- Dual-ledger auto-post for policy loan interest (G0 reminder mode)
