# G2 Profit & Loss (YTD + annual projection)

## What shipped
- Route: `/reports/profit-loss` (alias `/statements/profit-loss`)
- API: `GET /api/reports/profit-loss?year=&income_growth_pct=&expense_growth_pct=&include_tax=&effective_tax_rate=`
- UI: year picker, YTD income/expenses/net, annual projection, G4-lite Assumptions (income/expense growth %, tax toggle + rate)
- YTD from posted transactions (`counts_as_user_pnl`)
- Annual projection: remaining recurring schedules when available, else day-count run-rate

## Gaps (not in G2)
- G3 multi-year forecast — shipped (`/reports/forecast`)
- Jurisdiction-aware tax brackets
- Per-category growth drivers
