# G1 Balance Sheet (as-of date)

## What shipped
- Route: `/reports/balance-sheet` (alias `/statements/balance-sheet`)
- API: `GET /api/reports/balance-sheet?as_of=YYYY-MM-DD&insurance_value_basis=recorded|sad|sv`
- UI: selectable as-of date (default today), Assets (cash + investments), Liabilities (loans), Net worth
- G4-lite Assumptions popover: `reporting_currency`, `insurance_value_basis`, `include_policy_loan`, `as_of_fidelity`
- Fidelity badges: `as_of` | `reconstructed` | `≈ current`

## As-of logic
- **Manual accounts**: sum posted transactions with `date <= as_of` (real as-of).
- **Connected accounts**: today = provider balance; past = provider balance − post-cutoff activity (reconstructed).
- **Assets**: latest `AssetValue` with `date <= as_of`, else purchase price.
- **Insurance (Pru etc.)**: optional override via `insurance_value_basis` using metadata SAD / illustrative SV.

## Gaps (not in G1)
- G2 Profit & Loss — shipped (`/reports/profit-loss`)
- G3 multi-year forecast
- Live insurer SV quote integration
- Dual-ledger auto-post for policy loan interest (G0 reminder mode)
