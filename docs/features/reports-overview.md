# Reports overview (Screener-style)

## What shipped
- Route: `/reports` (alias `/reports/overview` → `/reports`)
- Single-scroll personal finance overview reusing existing APIs
- **KPI strip (glossary):** Net worth · As-of net worth · Savings rate · Debt-to-assets · Insurance SV (illus./live)
- **P&L:** Income (salary + other) · Living + premiums + loan interest · Cash surplus · Net after debt service · columns FY · YTD (no EPS)
- **Balance sheet T:** owe LEFT | own RIGHT — Bank/cash · Property · MF/stocks · Insurance value | Loans (policy + others) · Credit cards / dues · Net worth (+ savings buffer)
- **Forecast** year columns
- **Assumption chips:** as-of · insurance_value_basis · include_policy_loan · growth · inflation · sv_path · rate_reset
- Deep links to `/reports/balance-sheet`, `/reports/profit-loss`, `/reports/forecast`
- Charts & cash-flow at `/reports/charts`

## Non-goals
- No new report APIs
- Not company Schedule III jargon — personal glossary labels only
