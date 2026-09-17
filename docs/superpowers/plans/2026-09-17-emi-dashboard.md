# EMI Dashboard Enhancement — Implementation Plan

**Priority:** P0  
**Date:** 2026-09-17  
**Status:** Ready for implementation  
**Design Spec:** [2026-09-17-emi-dashboard-design.md](../specs/2026-09-17-emi-dashboard-design.md)

## Overview

Implement comprehensive EMI Dashboard with prepayment strategy comparison (Avalanche, Snowball, Balanced), debt health metrics (DTI/FOIR), smart allocation simulator, timeline view, and priority ranking. 5-week phased rollout.

## Success Criteria

- [ ] Dashboard page loads in <2s with all metrics
- [ ] Strategy comparison completes in <500ms for 10 loans
- [ ] DTI/FOIR calculation matches manual calculation (100% accuracy)
- [ ] All 3 strategies (Avalanche, Snowball, Balanced) produce correct allocations
- [ ] Mobile responsive (works on 375px width)
- [ ] 80%+ test coverage on calculation logic
- [ ] Zero-state handling (no loans, no income data)

## Phase 1: Dashboard Summary (Week 1)

**Goal:** Dashboard page exists, shows KPIs and upcoming payments

### Backend Tasks

**1.1 Dashboard Summary Endpoint**
- [ ] Create `app/api/v1/loans/dashboard.py`
- [ ] Implement `GET /api/v1/loans/dashboard/summary`
  - Query all active loans (is_closed=False)
  - Aggregate: total_monthly_emi, total_outstanding, active_loan_count
  - Calculate principal_paid_ytd, interest_paid_ytd from schedule entries
  - Calculate debt_free_date (max remaining_months across loans)
  - Return JSON response
- [ ] Add workspace_id scoping (multi-tenancy)
- [ ] Add caching (5 min TTL)

**1.2 Upcoming Payments Endpoint**
- [ ] Implement `GET /api/v1/loans/dashboard/upcoming-payments?days=30`
  - Query loan_amortization_schedules WHERE due_date BETWEEN today AND today+30
  - Join with accounts to get loan names
  - Filter payment_status IN ('scheduled', 'overdue')
  - Sort by due_date ASC
  - Return list with days_until_due calculated
- [ ] Add pagination (limit 100)

**1.3 Tests**
- [ ] Unit test: dashboard summary calculation
- [ ] Unit test: upcoming payments query
- [ ] Integration test: GET /summary endpoint
- [ ] Integration test: GET /upcoming-payments endpoint
- [ ] Edge case: user with no loans
- [ ] Edge case: all loans closed

### Frontend Tasks

**1.4 Dashboard Page Structure**
- [ ] Create `frontend/src/pages/loans/dashboard.tsx`
- [ ] Add route in router: `/loans/dashboard`
- [ ] Update sidebar navigation: Loans → Dashboard (new), All Loans, Add Loan
- [ ] Basic page layout with shadcn Card components

**1.5 KPI Cards Component**
- [ ] Create `frontend/src/components/loans/KPICard.tsx`
  - Props: label, value, change, status, icon
  - Render Card with title, value (large), optional change badge
  - Color-code status (green/yellow/red)
- [ ] Create `frontend/src/components/loans/KPICardsSection.tsx`
  - Fetch data from /api/v1/loans/dashboard/summary
  - Render 4 KPI cards: Total EMI, Outstanding, Principal Paid YTD, Placeholder (Debt Health)
  - Grid layout: 4 columns desktop, 2 columns tablet, 1 column mobile
  - Loading skeleton while fetching

**1.6 Upcoming Payments Table**
- [ ] Create `frontend/src/components/loans/UpcomingPaymentsTable.tsx`
  - Fetch from /api/v1/loans/dashboard/upcoming-payments?days=30
  - shadcn Table component
  - Columns: Due Date, Loan Name, EMI Amount, Status, Actions
  - Status badge: color-coded (green=paid, yellow=due soon, red=overdue)
  - Action: "View Loan" button → navigate to /loans/{id}
  - Empty state: "No upcoming payments in next 30 days"
- [ ] Sortable columns (due date, amount)

**1.7 Dashboard Widget Update**
- [ ] Update `frontend/src/components/loans/LoanDashboardWidget.tsx`
  - Add "View Full Dashboard →" link to /loans/dashboard
  - Keep existing metrics (no changes to API)

**1.8 Tests**
- [ ] Component test: KPICard renders correctly
- [ ] Component test: UpcomingPaymentsTable with mock data
- [ ] Integration test: Dashboard page loads and fetches data
- [ ] Responsive test: mobile, tablet, desktop layouts

**Deliverable:** User can navigate to `/loans/dashboard`, see KPIs and upcoming payments. Takes ~2 days backend, 3 days frontend.

## Phase 2: Debt Health Metrics (Week 2)

**Goal:** DTI and FOIR calculation with visual gauges

### Backend Tasks

**2.1 Debt Health Calculation Logic**
- [ ] Create `app/services/debt_health_service.py`
- [ ] Implement `calculate_dti(loans, monthly_income) -> Decimal`
  - Formula: (sum(emi_amount) / monthly_income) * 100
  - Return percentage with 2 decimal places
- [ ] Implement `calculate_foir(loans, monthly_income, other_obligations) -> Decimal`
  - Formula: ((sum(emi_amount) + other_obligations) / monthly_income) * 100
- [ ] Implement `get_dti_status(dti) -> str`
  - <30%: 'healthy', 30-40%: 'moderate', >40%: 'high_risk'
- [ ] Implement `get_foir_status(foir) -> str`
  - <50%: 'healthy', 50-60%: 'moderate', >60%: 'high_risk'

**2.2 Debt Health Endpoint**
- [ ] Implement `POST /api/v1/loans/dashboard/calculate-debt-health`
  - Request body: { monthly_income, other_obligations }
  - Call debt_health_service functions
  - Return: { dti, foir, status, breakdown, thresholds, recommendations }
  - Validate: monthly_income > 0
- [ ] Add to dashboard/summary endpoint (optional, if income stored)

**2.3 Workspace Settings (optional)**
- [ ] Add monthly_income field to workspaces table (nullable)
- [ ] Add other_monthly_obligations field (nullable, default 0)
- [ ] Migration: alembic revision
- [ ] If stored, include debt_health in /summary response automatically

**2.4 Tests**
- [ ] Unit test: calculate_dti with various inputs
- [ ] Unit test: calculate_foir
- [ ] Unit test: status categorization (boundary values)
- [ ] Integration test: POST /calculate-debt-health endpoint
- [ ] Edge case: monthly_income = 0 (return dti=0 or error)
- [ ] Edge case: no loans (dti=0)

### Frontend Tasks

**2.5 Debt Health Gauge Component**
- [ ] Create `frontend/src/components/loans/DebtHealthGauge.tsx`
  - Props: type ('dti' | 'foir'), percentage, thresholds
  - Use recharts PieChart for circular gauge
  - Three colored zones: green 0-30%, yellow 30-40%, red 40-100% (DTI)
  - Three colored zones: green 0-50%, yellow 50-60%, red 60-100% (FOIR)
  - Needle/pointer at current percentage
  - Label: percentage + status text below
- [ ] Style with shadcn theme colors

**2.6 Debt Health Section**
- [ ] Create `frontend/src/components/loans/DebtHealthSection.tsx`
  - State: monthly_income, other_obligations (local or fetched from workspace)
  - Inline editable inputs for income and obligations
  - "Calculate" button or auto-calculate on input change (debounced)
  - Display two gauges side-by-side: DTI and FOIR
  - Breakdown table below gauges:
    - Each loan with EMI
    - Other obligations (editable)
    - Total obligations
    - Monthly income (editable)
    - Calculated DTI %, FOIR %
  - Recommendations (from API response)
- [ ] Add to LoansD ashboardPage above Timeline

**2.7 KPI Card Update**
- [ ] Update Card 4 (Debt Health Score) in KPICardsSection
  - Show status badge: "Healthy", "Moderate", "High Risk"
  - Show primary metric (DTI or FOIR, user preference)
  - Color-code: green/yellow/red

**2.8 Tests**
- [ ] Component test: DebtHealthGauge renders correctly
- [ ] Component test: DebtHealthSection calculates on input
- [ ] Test: income=0 shows helpful message, not error
- [ ] Visual regression test: gauge colors match spec

**Deliverable:** User enters monthly income, sees DTI and FOIR gauges with color-coded health status. Takes ~2 days backend, 3 days frontend.

## Phase 3: Strategy Simulator (Week 3)

**Goal:** Compare Avalanche, Snowball, Balanced prepayment strategies

### Backend Tasks

**3.1 Strategy Calculation Service**
- [ ] Create `app/services/prepayment_strategy_service.py`
- [ ] Implement `calculate_avalanche(loans, amount) -> StrategyResult`
  - Sort loans by interest_rate DESC
  - Allocate amount to highest rate first, then next, etc.
  - Return allocations list, interest_saved, months_saved
- [ ] Implement `calculate_snowball(loans, amount) -> StrategyResult`
  - Sort loans by current_balance ASC
  - Allocate to smallest first until closed, then next
  - Return allocations, interest_saved, months_saved, loans_closed
- [ ] Implement `calculate_balanced(loans, amount) -> StrategyResult`
  - Find completable loans (balance <= amount)
  - Sort completable by balance ASC, close all
  - Allocate remainder to highest interest rate
  - Return allocations, interest_saved, months_saved, loans_closed
- [ ] Implement `calculate_interest_saved(loans, allocations) -> Decimal`
  - For each allocation, call existing LoanSimulations.simulate_prepayment
  - Sum interest_saved from all simulations (reduce_tenure method)
  - Return total
- [ ] Implement `calculate_months_saved(loans, allocations) -> int`
  - Calculate original max(remaining_months)
  - After prepayments, calculate new max(remaining_months)
  - Return difference

**3.2 Strategy Comparison Endpoint**
- [ ] Implement `POST /api/v1/loans/dashboard/compare-strategies`
  - Request: { prepayment_amount }
  - Fetch all active loans for workspace
  - Call calculate_avalanche, calculate_snowball, calculate_balanced
  - Mark strategy with highest interest_saved as recommended
  - Return: { strategies: [avalanche, snowball, balanced] }
  - Add response caching (5 min, keyed by workspace_id + amount)
  - Validate: prepayment_amount > 0

**3.3 Tests**
- [ ] Unit test: calculate_avalanche with 3 loans
- [ ] Unit test: calculate_snowball
- [ ] Unit test: calculate_balanced
  - Case 1: No completable loans (behaves like avalanche)
  - Case 2: One completable loan
  - Case 3: Multiple completable loans
- [ ] Unit test: calculate_interest_saved (mock simulate_prepayment)
- [ ] Integration test: POST /compare-strategies endpoint
- [ ] Performance test: 10 loans, response time <500ms
- [ ] Edge case: prepayment > total outstanding (handle gracefully)
- [ ] Edge case: single loan (all strategies identical)

### Frontend Tasks

**3.4 Strategy Card Component**
- [ ] Create `frontend/src/components/loans/StrategyCard.tsx`
  - Props: strategy (name, interest_saved, months_saved, allocations, recommended)
  - Card layout:
    - Header: Strategy name + icon
    - "Recommended" badge if recommended
    - Interest Saved (large, green text)
    - Months Saved
    - Allocations list:
      - Loan name, amount, reason (e.g., "9.5% highest rate")
      - "Closed" badge if allocation closes loan
  - Color accent by strategy type (indigo/teal/violet)
- [ ] Responsive: stack on mobile, side-by-side on desktop

**3.5 Prepayment Strategy Simulator**
- [ ] Create `frontend/src/components/loans/PrepaymentStrategySimulator.tsx`
  - State: amount (string), strategies (array), loading (boolean)
  - Amount input with currency formatting (₹)
  - "Calculate Strategies" button
  - On click: POST /compare-strategies, set loading=true
  - Display 3 StrategyCards in grid (3 columns desktop, 1 mobile)
  - Empty state: "Enter amount to compare strategies"
  - Error state: "Failed to calculate. Try again."
- [ ] Add to LoansD ashboardPage below Debt Health

**3.6 Tests**
- [ ] Component test: StrategyCard renders allocations
- [ ] Component test: Simulator triggers API call on button click
- [ ] Test: Recommended badge shows on correct strategy
- [ ] Test: Loading state during calculation
- [ ] Test: Error state on API failure
- [ ] Visual test: Cards responsive on mobile

**Deliverable:** User enters prepayment amount (e.g., ₹2L), sees 3 strategies compared with savings and allocations. Takes ~3 days backend, 2 days frontend.

## Phase 4: Timeline & Priority Ranking (Week 4)

**Goal:** Visual timeline and priority ranking tabs

### Backend Tasks

**4.1 Timeline Service**
- [ ] Create `app/services/emi_timeline_service.py`
- [ ] Implement `generate_emi_timeline(workspace_id, months=24) -> List[Dict]`
  - For each month in range:
    - Query schedule entries for that month across all loans
    - Group by loan, sum EMI amounts
    - Return: [{ month, total_emi, breakdown: [{ loan_id, loan_name, emi }] }]
  - Optimize: single query with GROUP BY month, loan_id
- [ ] Implement `is_loan_active_in_month(loan, month_date) -> bool`
  - Check if schedule entries exist for that month
  - Handle loans that finish mid-timeline

**4.2 Timeline Endpoint**
- [ ] Implement `GET /api/v1/loans/dashboard/timeline?months=24`
  - Default months=24, max 60
  - Call generate_emi_timeline
  - Return timeline array
  - Cache for 1 hour

**4.3 Priority Ranking Endpoint**
- [ ] Implement `GET /api/v1/loans/dashboard/priority-ranking`
  - Fetch all active loans
  - Avalanche: sort by interest_rate DESC
  - Snowball: sort by current_balance ASC
  - Balanced:
    - Group 1: loans <= median(balances) (completable candidates)
    - Group 2: remaining loans sorted by interest_rate DESC
  - Return: { avalanche: [], snowball: [], balanced: {completable, remainder_priority} }

**4.4 Tests**
- [ ] Unit test: generate_emi_timeline for 3 loans, 12 months
- [ ] Unit test: timeline handles loan closing mid-period
- [ ] Integration test: GET /timeline endpoint
- [ ] Integration test: GET /priority-ranking endpoint
- [ ] Edge case: no loans (return empty timeline)
- [ ] Performance: 10 loans, 24 months, <200ms

### Frontend Tasks

**4.5 EMI Timeline Component**
- [ ] Create `frontend/src/components/loans/EMITimeline.tsx`
  - Fetch from /api/v1/loans/dashboard/timeline?months=24
  - Use recharts BarChart
  - X-axis: Month labels (Oct 2026, Nov 2026, ...)
  - Y-axis: EMI amount
  - Stacked bars: each loan's contribution (color-coded by loan type)
  - Tooltip on hover: breakdown per loan for that month
  - Horizontal scroll on mobile
  - Legend: loan names with colors
  - "Debt-Free by: [date]" annotation at end
- [ ] Add to LoansD ashboardPage

**4.6 Priority Ranking Tabs**
- [ ] Create `frontend/src/components/loans/PriorityRankingTabs.tsx`
  - Fetch from /api/v1/loans/dashboard/priority-ranking
  - shadcn Tabs component with 3 tabs: Avalanche, Snowball, Balanced
  - Each tab renders ranked list of loans
  - Card per loan:
    - Rank badge (1, 2, 3) with color (red/yellow/green)
    - Loan name + type
    - Key metric (interest rate for Avalanche, balance for Snowball)
    - Reason text (e.g., "Prepay this first to save most interest")
  - Click on loan card → navigate to /loans/{id}
- [ ] Add to LoansD ashboardPage

**4.7 Loan Composition Pie Chart (bonus)**
- [ ] Create `frontend/src/components/loans/LoanCompositionChart.tsx`
  - Fetch loans, calculate % of total outstanding
  - recharts PieChart
  - Toggle: by loan type vs by individual loan
  - Labels with percentages
- [ ] Add to sidebar or dashboard page

**4.8 Tests**
- [ ] Component test: EMITimeline renders bars correctly
- [ ] Component test: PriorityRankingTabs switches between tabs
- [ ] Test: Timeline data matches backend response
- [ ] Visual test: Chart responsive on mobile
- [ ] Test: Click on ranked loan navigates correctly

**Deliverable:** User sees month-by-month EMI timeline chart and can compare priority rankings across 3 strategies. Takes ~2 days backend, 3 days frontend.

## Phase 5: Polish & Integration (Week 5)

**Goal:** Production-ready, responsive, tested, integrated

### Backend Tasks

**5.1 Caching & Performance**
- [ ] Add Redis caching for dashboard/summary (5 min TTL)
- [ ] Add Redis caching for compare-strategies (keyed by workspace + amount)
- [ ] Optimize timeline query (single query with JOINs, not N+1)
- [ ] Add database indexes:
  - loan_amortization_schedules (account_id, due_date)
  - accounts (workspace_id, type, is_closed)
- [ ] Load test: 100 concurrent requests to /summary, <2s response time

**5.2 Error Handling**
- [ ] Add input validation middleware (Pydantic schemas)
- [ ] Graceful handling of edge cases:
  - No loans: return empty arrays, not errors
  - Monthly income = 0: return null for DTI/FOIR, not divide-by-zero
  - Prepayment > total outstanding: cap at total, return warning
- [ ] Structured error responses (JSON with error codes)

**5.3 Logging & Monitoring**
- [ ] Add structured logging for all endpoints
- [ ] Add metrics: request count, latency, error rate (Prometheus format)
- [ ] Add alerts: strategy calculation >1s, error rate >1%

### Frontend Tasks

**5.4 Responsive Design**
- [ ] Mobile layout (<768px):
  - KPI cards: 1 column stack
  - Strategy cards: swipeable carousel or accordion
  - Debt health gauges: vertical stack
  - Timeline: scrollable, 6 months visible
  - Priority tabs: full-screen modal or accordion
- [ ] Tablet layout (768-1023px):
  - KPI cards: 2x2 grid
  - Strategy cards: 2 columns (Balanced wraps)
- [ ] Test on real devices (iOS Safari, Android Chrome)

**5.5 Loading & Empty States**
- [ ] Add skeleton loaders for KPI cards during fetch
- [ ] Add spinner on "Calculate Strategies" button
- [ ] Empty state: "No loans yet. Add your first loan to see dashboard."
- [ ] Empty state: "Enter monthly income to see debt health metrics."
- [ ] Error state: "Failed to load dashboard. Refresh page."

**5.6 Accessibility**
- [ ] All interactive elements keyboard navigable (Tab, Enter)
- [ ] All gauges have aria-labels ("DTI gauge showing 38 percent")
- [ ] Color not sole indicator (use icons + text)
- [ ] Focus visible on buttons and inputs
- [ ] Screen reader testing with NVDA/VoiceOver

**5.7 Tooltips & Help Text**
- [ ] Tooltip on DTI gauge: "Debt-to-Income Ratio. Healthy: <30%"
- [ ] Tooltip on FOIR gauge: "Fixed Obligation to Income Ratio. Banks prefer <50%"
- [ ] Info icon on Avalanche: "Math-based: Highest interest rate first"
- [ ] Info icon on Snowball: "Psychology-based: Smallest balance first"
- [ ] Info icon on Balanced: "Hybrid: Close completable loans, then highest rate"

**5.8 Integration with Existing Features**
- [ ] Update LoanDashboardWidget to show debt health score
- [ ] Add debt health score to widget (color badge + percentage)
- [ ] Link from /loans page to dashboard ("View Dashboard Insights →")
- [ ] Add dashboard link to loan detail page (/loans/{id})

**5.9 Tests**
- [ ] End-to-end test: full user flow (visit dashboard → enter income → calculate strategies)
- [ ] Responsive test: screenshot comparison on mobile/tablet/desktop
- [ ] Accessibility audit: aXe DevTools, 0 violations
- [ ] Performance test: Lighthouse score >90 on all metrics
- [ ] Cross-browser: Chrome, Firefox, Safari, Edge

**Deliverable:** Production-ready dashboard with all features, fully responsive, accessible, tested. Takes ~2 days backend, 3 days frontend.

## Phase 6: Advanced Features (Future / P1)

**Not in initial release, prioritize for next iteration:**

- [ ] EMI calendar (month grid view with clickable dates)
- [ ] Historical trend charts (principal vs interest paid over time)
- [ ] Goal integration (link loans to goals, show progress)
- [ ] What-if scenarios ("Increase home loan EMI by ₹5k")
- [ ] Refinance alerts (detect rate drops in market)
- [ ] Balance transfer ROI calculator
- [ ] Export dashboard as PDF report
- [ ] Email digest: monthly debt health report
- [ ] Push notifications: EMI due reminders

## Resource Allocation

**Backend (Python/FastAPI):**
- Phase 1: 2 days
- Phase 2: 2 days
- Phase 3: 3 days
- Phase 4: 2 days
- Phase 5: 2 days
- **Total: 11 days (2.2 weeks @ 5 days/week)**

**Frontend (React/TypeScript):**
- Phase 1: 3 days
- Phase 2: 3 days
- Phase 3: 2 days
- Phase 4: 3 days
- Phase 5: 3 days
- **Total: 14 days (2.8 weeks)**

**Testing & QA:**
- Unit tests: ongoing during each phase
- Integration tests: 1 day (end of Phase 3)
- E2E tests: 1 day (Phase 5)
- Performance testing: 0.5 day (Phase 5)
- Accessibility audit: 0.5 day (Phase 5)
- **Total: 3 days**

**Total Effort: 28 days (5.6 weeks) for 1 full-stack engineer, or 3.5 weeks for 2 engineers (1 backend, 1 frontend)**

## Dependencies & Blockers

**Hard Dependencies:**
- Existing loan accounts and amortization schedules (✅ exists)
- LoanSimulations component with prepayment simulation (✅ exists)
- recharts library (✅ installed)
- shadcn/ui components (✅ installed)

**Potential Blockers:**
- If monthly_income storage decision changes → affects Phase 2 (debt health)
- If strategy calculation is too slow (>1s for 10 loans) → need optimization before Phase 3
- If mobile layout is unusable → may need to defer some components to desktop-only

**Mitigation:**
- Make monthly_income optional (frontend state, not persisted) → unblocks Phase 2
- Set timeout on strategy calculation (5s) → fail fast, don't hang
- Progressive enhancement: desktop-first, mobile views can be simplified

## Rollout Plan

**Alpha (Week 5, end of Phase 5):**
- Deploy to staging environment
- Internal testing by team (5 users, 1 week)
- Bug bash: collect issues, prioritize fixes

**Beta (Week 6):**
- Deploy to production with feature flag (opt-in)
- Invite 50 beta users
- Monitor metrics: page views, API latency, error rate
- Collect feedback: survey + in-app feedback widget

**General Availability (Week 7):**
- Remove feature flag, enable for all users
- Add dashboard link to main navigation (promote visibility)
- Announcement: blog post, changelog, in-app notification
- Monitor adoption: % of users with loans who visit dashboard

**Post-Launch (Week 8+):**
- Monitor success metrics (see Design Spec)
- Iterate on feedback (top 3 issues/requests)
- Plan Phase 6 features based on user demand

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Strategy calculation slow | Medium | High | Optimize queries, add caching, set timeout |
| Users don't enter income | High | Medium | Make debt health optional, show prompt |
| Mobile layout cramped | Medium | Medium | Simplify mobile view, defer non-critical components |
| Confusing strategy names | Medium | Low | Add tooltips, help text, "Learn more" modal |
| Low adoption | Low | High | Prominent placement, in-app tour, announcement |

## Success Metrics (30 days post-launch)

**Adoption:**
- ✅ Target: 60% of users with loans visit dashboard in first 30 days
- ✅ Target: 40% of users enter monthly income (enabling debt health)

**Engagement:**
- ✅ Target: 30% of users use strategy simulator
- ✅ Target: Avg 2 strategies compared per simulator use

**Technical:**
- ✅ Target: Dashboard page load time <2s (P95)
- ✅ Target: Strategy calculation <500ms (P95)
- ✅ Target: Error rate <0.1% on dashboard endpoints
- ✅ Target: Lighthouse score >90 (performance, accessibility)

**Value (harder to measure, proxy metrics):**
- Track: # of prepayments made after simulator use (via transactions tagged to dashboard)
- Track: Loans closed (proxy for Snowball/Balanced strategy success)
- Survey: "Did the dashboard help you decide how to prepay?" (qualitative)

## Communication Plan

**Stakeholders:**
- Product: Weekly progress updates, demo at end of each phase
- Design: Collab on Phase 1 (layout), Phase 2 (gauges), Phase 5 (polish)
- Support: Training doc before GA, FAQ for common questions
- Users: Beta announcement (Week 6), GA announcement (Week 7)

**Artifacts:**
- ✅ Design spec (this document)
- ✅ Implementation plan (this document)
- [ ] API documentation (OpenAPI spec, auto-generated)
- [ ] User guide (Help Center article, screenshots)
- [ ] Changelog entry (GA announcement)

## Next Steps

1. **Approval:** Product review of design spec + plan
2. **Kickoff:** Schedule kickoff meeting (backend + frontend devs)
3. **Sprint Planning:** Break phases into 2-week sprints
4. **Phase 1 Start:** Create branches, set up project structure
5. **Daily Standups:** Track progress, unblock issues
6. **Demo:** End of each phase, demo to team
7. **Launch:** Week 7, GA rollout

---

**Status:** Ready for kickoff  
**Assigned:** TBD (need 1 backend, 1 frontend engineer)  
**Start Date:** TBD (after approval)  
**Target GA:** 7 weeks from start