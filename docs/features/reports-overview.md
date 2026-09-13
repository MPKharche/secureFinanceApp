# Reports overview (Screener-style)

## What shipped
- Route: `/reports` (alias `/reports/overview` → `/reports`)
- Single-scroll personal finance overview reusing existing APIs
- **KPI strip (glossary):** Net worth · As-of net worth · Savings rate · Debt/assets · Insurance SV
- **Time spine (Excel-tight):** Mo · YTD · FY · 5Y — frozen label column + header, horizontal swipe on mobile
- **P&L rows:** Income · Living · Premiums · Interest · Surplus
- **Balance sheet T:** Owe LEFT | Own RIGHT — Cash · Property · Invest · Insurance | Loans · Cards · Net worth
- **Forecast** continuous 5Y projection
- **Assumption chips (short):** As-of · Ins. basis · Pol. loan · Growth · Infl. · SV path · Rate reset
- Deep links to `/reports/balance-sheet`, `/reports/profit-loss`, `/reports/forecast`
- Charts at `/reports/charts`

## Non-goals
- No new report APIs
- No on-page narrative / Screener prose — purposeful short labels only
