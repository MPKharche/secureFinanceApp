# G3 5-year forecast

## What shipped
- Route: `/reports/forecast` (alias `/statements/forecast`)
- API: `GET /api/reports/forecast` with G4 assumption query params
- UI: horizon control, Assumptions popover (persisted prefs), year-by-year table, nav link
- Driven by recurring/P&L base + schedules metadata (premium, loan rate) and CoS SV illustration

## Assumption keys
| Key | Meaning |
|-----|---------|
| `horizon_years` | Forecast length (default 5) |
| `inflation_pct` | Annual inflation on expenses / extrapolations |
| `income_growth_pct` | Compound income growth path (from year 2) |
| `expense_growth_pct` | Compound expense growth path (stacked with inflation) |
| `loan_rate_pct` | Policy loan rate assumption |
| `rate_reset` | `none` (account rate) \| `use_assumption` |
| `sv_path` | `illus_table` \| `hold_flat` \| `live` (fallback) |
| `premium_annual` | Annual premium (default from asset/schedules metadata) |

## Gaps
- Live insurer SV quote not integrated (`sv_path=live` falls back)
- Interest-only loan principal (no amortization schedule projection)
- No jurisdiction tax engine / per-category growth drivers
