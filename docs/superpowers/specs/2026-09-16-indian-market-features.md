# Indian Personal Finance Features - Comprehensive Market Analysis

**Date:** 2026-09-16  
**Status:** Research & Discovery  
**Target Segments:** Young Professionals (25-35) · Family Primary Earners (35-50) · Mass Market (Tier 2/3)

---

## Executive Summary

This document catalogs **end-user driven features** for a personal finance app targeting Indian customers, mapped to market-leading apps, expert recommendations (CFPs, RIAs), and community insights from Reddit/LinkedIn. Features are organized by user journey stage and personalization opportunity.

**Key Insight:** Indian users need a blend of **tracking + goal planning + tax optimization + investment guidance**, with strong support for India-specific instruments (PPF, EPF, NPS, tax-saving funds) and cultural financial patterns (family obligations, festival spending, gold purchases).

---

## Feature Inventory by Category

### 1. INCOME TRACKING & MANAGEMENT

#### 1.1 Salary Breakdown & Components
**User Need:** Indian salaries have complex structures (basic + HRA + special allowance + PF + gratuity)

**Features:**
- Auto-parse salary slip (PDF/image upload)
- Categorize components: Basic, HRA, Special Allowance, LTA, Medical, Transport
- Track employer contributions: EPF, Gratuity, NPS
- Show taxable vs non-taxable components
- Track variable pay: bonuses, incentives, stock options (RSUs/ESOPs)
- Multi-income tracking: freelance, rental, capital gains, interest

**Market Leaders:**
- **ET Money:** Salary slip parser, CTC breakdown
- **CRED:** Income tracking with tax impact preview
- **INDmoney:** Multi-source income aggregation
- **Niyo Money:** Salary advance tracking

**Expert Insight (CFPs):** "Young professionals don't understand their CTC structure. Breaking down components helps them optimize tax planning (80C, HRA, etc.)"

**Personalization Hook:** Show different views based on employment type (salaried vs freelancer vs business owner)

---

#### 1.2 EPF/PF Tracker
**User Need:** Track EPF balance, employer contributions, interest earned

**Features:**
- Link EPFO account (UAN-based)
- Auto-sync EPF balance monthly
- Show employee + employer contribution split
- Calculate projected EPF corpus at retirement
- Track PF withdrawals (advance, settlement)
- Alert for inactive PF accounts from previous employers

**Market Leaders:**
- **ET Money:** EPF tracking, consolidated view across employers
- **Scripbox:** EPF retirement projections
- **Kuvera:** PF balance tracking

**Reddit/Community:** "I have 3 PF accounts from different companies. Need one place to see total balance and transfer status"

---

#### 1.3 Bonus & Incentive Forecasting
**User Need:** Track variable pay patterns, forecast annual earnings

**Features:**
- Log historical bonuses (quarterly, annual, performance)
- Predict bonus timing and amount based on patterns
- Set bonus allocation rules (invest 50%, save 30%, spend 20%)
- Track stock options (vesting schedule, exercise windows)
- ESOP tax calculator (perquisite value, capital gains)

**Market Leaders:**
- **CRED:** Bonus goal tagging
- **Jupiter:** Bonus parking (auto-move to savings)

---

### 2. EXPENSE TRACKING & CATEGORIZATION

#### 2.1 SMS/Email Auto-Capture (India-Specific)
**User Need:** 90% of Indian transactions trigger SMS alerts; manual entry is friction

**Features:**
- Parse SMS from all major Indian banks (HDFC, ICICI, SBI, Axis, Kotak, etc.)
- Extract: amount, merchant, account, transaction type
- Auto-categorize using ML (groceries, fuel, dining, bills)
- Handle UPI transactions (Google Pay, PhonePe, Paytm)
- Parse credit card emails (statement alerts, transaction confirmations)
- Detect recurring payments (Netflix, Spotify, SIP)

**Market Leaders:**
- **Walnut (now CRED):** Best-in-class SMS parser, 95%+ accuracy
- **Money View:** SMS + email parsing
- **ET Money:** Transaction auto-capture

**Expert Insight:** "SMS parsing removes the biggest barrier to expense tracking in India. Users won't manually enter 50+ UPI transactions per month"

---

#### 2.2 UPI-First Transaction View
**User Need:** UPI is 60%+ of digital transactions; users want UPI-specific insights

**Features:**
- Group transactions by UPI app (GPay, PhonePe, Paytm, BHIM)
- Show UPI spending trends by merchant
- Track UPI cashback/rewards earned
- Identify UPI bill payments vs peer transfers
- Flag suspicious/duplicate UPI transactions
- Show most-used UPI contacts

**Market Leaders:**
- **Google Pay:** Transaction history, insights
- **PhonePe:** Spending reports
- **CRED:** UPI transaction reconciliation

**Reddit:** "I use 3 different UPI apps. Want to see total UPI spending across all apps in one place"

---

#### 2.3 Indian Category Presets
**User Need:** Default categories don't match Indian spending patterns

**Features:**
- **India-specific categories:**
  - House help (maid, cook, driver, security)
  - Education (school fees, tuition, coaching)
  - Healthcare (doctors, medicines, insurance premium)
  - Gold purchases (jewelry, digital gold)
  - Religious/donations (temple, charity, festivals)
  - Pet care (uncommon but growing)
  - Tobacco/alcohol (separate tracking for budgeting)
  
**Market Leaders:**
- **Walnut:** Indian category presets
- **Money Manager:** Customizable Indian categories

---

#### 2.4 Shared Expense Splitting
**User Need:** Track shared expenses with spouse, family, roommates, friends

**Features:**
- Create expense groups (family, roommates, trip buddies)
- Split bills equally or by custom percentage
- Track who owes whom
- Settle up reminders
- Recurring shared expenses (rent, utilities, maid salary)
- Export settlement summary for UPI payment

**Market Leaders:**
- **Splitwise:** Leader in group expense splitting
- **Settle Up:** Indian alternative

**User Persona:** Family primary earners need this for household expense transparency with spouse

---

### 3. BUDGETING & SPENDING CONTROL

#### 3.1 Zero-Based Budgeting (Envelope Method)
**User Need:** Assign every rupee a purpose; popular with disciplined savers

**Features:**
- Create budget envelopes for each category
- Fund envelopes at start of month
- Real-time envelope balance after each transaction
- Rollover unused amounts or reset monthly
- Visual progress bars (70% spent = yellow, 90% = red)
- Budget vs actual variance reports

**Market Leaders:**
- **YNAB (You Need A Budget):** Gold standard for envelope budgeting (US)
- **Goodbudget:** Envelope budgeting app
- **ET Money:** Budget tracking

**CFP Insight:** "Zero-based budgeting works best for salaried Indians with predictable income. Forces intentional spending"

---

#### 3.2 Festival & Seasonal Budgets
**User Need:** Indian spending spikes during Diwali, weddings, summer vacations

**Features:**
- Pre-create festival budgets (Diwali, Holi, Christmas)
- Wedding season planner (gifts, travel, clothing)
- Summer vacation budget (April-May school holidays)
- Track year-over-year festival spending trends
- Savings goals for upcoming festivals (6-month countdown)

**Unique to India:** No global app handles this well; huge opportunity

**Reddit/LinkedIn:** "Every Diwali I overspend on gifts. Need a dedicated Diwali budget that tracks against last year"

---

#### 3.3 Bill Reminders & Auto-Pay Tracking
**User Need:** Track recurring bills, avoid late fees

**Features:**
- Set bill reminders (electricity, gas, water, broadband, DTH, mobile)
- Track bill amount trends (electricity spike in summer)
- Alert if bill not paid 3 days before due date
- Link to bill payment platforms (Paytm, PhonePe, CRED)
- Track late fees paid (shame metric)
- Auto-detect bill payments from SMS/transactions

**Market Leaders:**
- **CRED:** Best bill payment UX + rewards
- **Paytm:** Bill reminders, auto-pay
- **PhonePe:** Recurring bill payments

---

#### 3.4 EMI Tracker & Loan Dashboard
**User Need:** Track multiple loans (home, car, personal, credit card EMI)

**Features:**
- Log all active loans with details (principal, rate, tenure, EMI)
- Show total EMI outgo per month
- Calculate remaining principal, interest paid to date
- Prepayment calculator (reduce tenure vs reduce EMI)
- Alert for EMI due dates
- Debt-to-income ratio tracking
- Loan payoff priority recommendation (highest interest first)

**Market Leaders:**
- **ET Money:** Loan tracker, prepayment calculator
- **BankBazaar:** Loan dashboard
- **Paisabazaar:** EMI calculator

**Already in Securo:** Loan amortization tracking exists! Needs enhancement for multiple loans + prepayment scenarios

---

### 4. SAVINGS & GOAL PLANNING

#### 4.1 Goal-Based Savings (India-Specific Goals)
**User Need:** Indians save for specific goals, not generic "emergency fund"

**Features:**
- **Goal templates:**
  - Emergency fund (6 months expenses)
  - Child education (school, college, coaching)
  - Marriage (self/children)
  - House down payment
  - Car purchase
  - Vacation/travel
  - Parents' medical fund
  - Retirement corpus
  - Gold purchase (festival/wedding)
- Show goal priority ranking
- Calculate required monthly savings per goal
- Link goals to specific accounts/investments
- Track goal progress with visual milestones
- Celebrate goal completion (confetti animation!)
- Adjust goals dynamically (inflation-adjusted targets)

**Market Leaders:**
- **Scripbox:** Goal-based investing, retirement planner
- **Kuvera:** Goal planning + mutual fund mapping
- **ET Money:** Goal tracker
- **INDmoney:** Goal-based SIP recommendations

**Already in Securo:** Goals feature exists! Needs India-specific templates + priority ranking

---

#### 4.2 Automated Savings Rules (Sweep/Round-Up)
**User Need:** Save without thinking about it

**Features:**
- Round-up savings (₹47 transaction → save ₹3)
- Rule-based sweeps (save 10% of every credit transaction)
- Salary-day auto-transfer (move ₹5000 to savings on 1st)
- Bonus allocation (invest 50%, save 30%, spend 20%)
- Cashback auto-save (GPay/PhonePe rewards → savings)
- Spending guilt-save (ordered Swiggy? Save ₹50)

**Market Leaders:**
- **Jupiter:** Auto-save rules, round-ups
- **Fi Money:** Rule-based savings
- **Digit:** AI-based auto-savings

---

#### 4.3 Recurring Deposit (RD) Tracker
**User Need:** Track RDs across banks, predict maturity amounts

**Features:**
- Log RD details (bank, amount, tenure, rate)
- Show upcoming RD installments
- Calculate maturity value
- Alert 1 month before maturity (renewal decision)
- Compare RD vs debt mutual fund returns
- Track missed RD payments (penalty warnings)

**Market Leaders:**
- **BankBazaar:** RD calculator
- **Groww:** RD tracking

**Mass Market Need:** Tier 2/3 users heavily use RDs; this feature is underserved

---

### 5. INVESTMENT TRACKING & PORTFOLIO

#### 5.1 Mutual Fund Portfolio (India-Focused)
**User Need:** Track MFs across platforms (Zerodha, Groww, Paytm Money, direct AMC)

**Features:**
- Import portfolio via email (CAMS/Karvy statements)
- Auto-sync via CAS (Consolidated Account Statement)
- Show holdings by fund, category (equity, debt, hybrid)
- Display XIRR, absolute returns, current value
- Track SIPs (next SIP date, amount, fund)
- Goal-to-fund mapping (retirement goal → ELSS + index funds)
- Tax harvesting alerts (book losses before March 31)
- Fund performance vs benchmark
- Direct vs regular plan comparison

**Market Leaders:**
- **Kuvera:** Best MF portfolio tracker, CAS import
- **Groww:** Portfolio X-ray, SIP tracking
- **ET Money:** Direct MF platform + tracking
- **INDmoney:** Multi-platform aggregation

**Already in Securo:** Asset tracking exists (RFC #235)! Needs India-specific: CAS import, SIP tracking, ELSS tagging

---

#### 5.2 Stock Portfolio (Preço Médio for India)
**User Need:** Track stocks/ETFs across brokers (Zerodha, Groww, Upstox, Angel One)

**Features:**
- Import holdings via broker API or CSV
- Calculate average buy price (weighted average)
- Show unrealized P&L per stock
- Track realized gains (for tax reporting)
- Dividend tracker (amount, ex-date, credit date)
- Corporate actions (bonus, split, rights)
- Sector allocation pie chart
- Stock-wise holding period (STCG vs LTCG)

**Market Leaders:**
- **INDmoney:** Multi-broker portfolio sync
- **Ticker Tape:** Portfolio analytics
- **Smallcase:** Thematic portfolio tracking

**Already in Securo:** Investment ledger (RFC #235) with average price! Needs: dividend tracking, tax classification (STCG/LTCG), broker sync

---

#### 5.3 Gold Investment Tracker
**User Need:** Track physical gold, digital gold (apps), Sovereign Gold Bonds, Gold ETFs

**Features:**
- Log gold purchases (jewelry, coins, bars) with weight and price
- Track digital gold (Paytm, PhonePe, MMTC-PAMP)
- Sovereign Gold Bond (SGB) holdings + interest tracking
- Gold ETF/mutual fund tracking
- Current value based on live gold prices
- Gold allocation as % of portfolio
- Track gold given as gifts/collateral

**Unique to India:** Gold is a cultural asset class; no global app handles this well

**Market Leaders:**
- **AUGMONT:** Digital gold tracking
- **SafeGold:** Gold portfolio

**Reddit:** "I have gold jewelry worth ₹5L, SGB worth ₹2L, and gold in Paytm. Want one dashboard to see total gold holdings"

---

#### 5.4 PPF/NPS/EPF Retirement Dashboard
**User Need:** Track all retirement savings in one place

**Features:**
- **PPF Tracker:**
  - Log PPF account, contributions, interest rate
  - Show current balance, maturity year
  - Calculate projected corpus at maturity
  - Track 15-year extension decisions
  
- **NPS Tracker:**
  - Link NPS account (PRAN)
  - Show Tier 1 + Tier 2 balances
  - Track employer NPS contributions (if any)
  - Calculate 60% withdrawable + 40% annuity split
  - Compare NPS vs EPF returns
  
- **Consolidated Retirement View:**
  - Total retirement corpus (EPF + PPF + NPS + MF)
  - Retirement readiness score
  - Gap analysis (target ₹5Cr, current trajectory ₹3Cr)

**Market Leaders:**
- **Scripbox:** Retirement planner
- **ET Money:** NPS tracking
- **Kuvera:** Retirement calculator

**CFP Insight:** "Most Indians don't know their total retirement savings. Consolidation drives better planning"

---

#### 5.5 Real Estate Tracker
**User Need:** Track property investments, rental income, home loan

**Features:**
- Log properties (primary residence, rental, plot)
- Track property value (manual updates or area-based estimates)
- Rental income tracking + arrears
- Home loan mapping (property → loan → EMI)
- Property-wise expenses (maintenance, tax, repairs)
- ROI calculation (rental yield, capital appreciation)
- Property document vault (registry, agreements)

**Market Leaders:**
- **Housing.com:** Property valuation estimates
- **NoBroker:** Rent agreement management
- **INDmoney:** Real estate tracking

**Family Earners:** This segment often has 2-3 properties; critical feature

---

### 6. TAX PLANNING & OPTIMIZATION

#### 6.1 Tax Projection Dashboard (Live Calculator)
**User Need:** Know tax liability in real-time, optimize throughout the year

**Features:**
- **Input Sources:**
  - Salary (auto-parsed from income tracking)
  - Rental income
  - Capital gains (STCG, LTCG from stocks/MF/property)
  - Interest income (FD, savings account)
  - Business income (for freelancers)
  
- **Deductions Tracker (80C to 80U):**
  - 80C: EPF, PPF, ELSS, LIC, tuition fees (₹1.5L limit)
  - 80D: Health insurance (₹25K self, ₹50K parents)
  - 80CCD(1B): NPS (additional ₹50K)
  - 80G: Donations
  - 80E: Education loan interest
  - 24(b): Home loan interest
  - HRA: House Rent Allowance calculator
  
- **Output:**
  - Estimated tax liability (old vs new regime)
  - Tax already paid (TDS deducted)
  - Tax due/refund estimate
  - Regime comparison (which saves more tax?)
  - Monthly tax tracker (YTD tax vs projection)

**Market Leaders:**
- **Cleartax:** Best tax calculator + filing
- **Quicko:** Tax optimization, capital gains
- **ET Money:** Tax calculator
- **CRED:** Tax filing integration

**Expert Insight (RIAs):** "Live tax dashboard is a game-changer. Users can make tax-saving decisions (ELSS, NPS) in Nov-Dec before deadline"

---

#### 6.2 Investment Declaration & Form 12BB Helper
**User Need:** Simplify annual tax declaration to employer (Form 12BB)

**Features:**
- Pre-fill Form 12BB from tracked investments
- Upload proof documents (LIC policy, HRA receipts)
- Send declaration to employer via email/PDF
- Track declaration submission status
- Reminder in Jan-Feb (before tax season)

**Market Leaders:**
- **Cleartax:** Form 12BB generator
- **Zoho Books:** Expense + tax declaration

---

#### 6.3 Capital Gains Tax Calculator
**User Need:** Calculate STCG/LTCG on stock/MF/property sales

**Features:**
- Import trades (buy/sell) from broker statements
- Calculate holding period (< 1 year = STCG, > 1 year = LTCG)
- Apply correct tax rates:
  - Equity STCG: 15%
  - Equity LTCG: 10% above ₹1L
  - Debt STCG: Slab rate
  - Debt LTCG: 20% with indexation
- Show net proceeds after tax
- Advance tax calculator (if gains > ₹10K)
- Tax harvesting suggestions (book losses to offset gains)

**Market Leaders:**
- **Quicko:** Best capital gains calculator
- **Cleartax:** Capital gains reporting

**Already in Securo:** Investment ledger tracks realized gains (RFC #235)! Needs: tax rate application, advance tax alerts

---

### 7. INSURANCE MANAGEMENT

#### 7.1 Insurance Policy Tracker
**User Need:** Track all insurance policies in one place, avoid lapses

**Features:**
- **Policy Types:**
  - Life insurance (term, endowment, ULIP)
  - Health insurance (self, family floater, super top-up, parents)
  - Vehicle insurance (car, bike)
  - Home insurance
  - Travel insurance
  
- **Tracking:**
  - Premium amount + due date reminders
  - Coverage amount (sum assured)
  - Nominee details
  - Policy documents vault
  - Claim history
  - Renewal alerts (60 days, 30 days, 7 days)
  
- **Analysis:**
  - Insurance coverage adequacy (life cover = 10x annual income?)
  - Premium as % of income
  - Identify redundant policies (multiple endowment plans)

**Market Leaders:**
- **PolicyBazaar:** Policy tracking + recommendations
- **Turtlemint:** Insurance aggregator
- **Ditto Insurance:** Advisory + tracking

**Already in Securo:** Asset tracking (RFC #235) could support insurance! Needs: renewal alerts, adequacy calculator

---

#### 7.2 Health Insurance Claim Tracker
**User Need:** Track medical expenses vs insurance coverage

**Features:**
- Log medical expenses (doctor, pharmacy, tests, hospitalization)
- Link to health insurance policy
- Track reimbursement claims (submitted, approved, paid)
- Pre-approval requests for planned procedures
- Cashless treatment history
- Health insurance utilization (₹X used of ₹Y cover)

**Market Leaders:**
- **CRED (Health insurance):** Claim tracking
- **Plum (Corporate insurance):** Digital health card + claims

---

### 8. CREDIT MANAGEMENT

#### 8.1 Credit Card Dashboard (Multi-Card)
**User Need:** Track multiple credit cards, optimize spends, avoid late fees

**Features:**
- Link all credit cards (auto-sync via SMS/email)
- Show total credit limit vs utilization (< 30% is ideal)
- Track spending by card
- Alert 3 days before bill due date
- Show reward points balance (per card + total)
- Identify best card for each category (fuel, dining, travel)
- Track annual fees, reversals
- Credit utilization ratio (impacts credit score)

**Market Leaders:**
- **CRED:** Best credit card management UX + rewards
- **OneCard:** Single card, great tracking
- **Jupiter:** Credit card bill payments

**Already in Securo:** Multi-account management exists! Needs: credit-specific features (utilization, rewards, category optimization)

---

#### 8.2 Credit Score Monitoring
**User Need:** Track credit score, understand factors, improve score

**Features:**
- Fetch credit score from CIBIL/Experian/Equifax
- Show score trend (monthly updates)
- Explain score factors (payment history, credit utilization, age of credit)
- Actionable tips to improve score
- Alert on score changes (+ or -)
- Track credit inquiries (hard pulls)

**Market Leaders:**
- **CRED:** Free credit score + tips
- **BankBazaar:** Credit score monitoring
- **Paytm:** Free CIBIL score

---

#### 8.3 Reward Points Optimizer
**User Need:** Maximize credit card rewards, track redemptions

**Features:**
- Track reward points across cards
- Show points expiry dates
- Calculate points value (₹ equivalent)
- Recommend best redemption options (travel, cashback, vouchers)
- Suggest which card to use for upcoming purchases
- Track annual benefits (lounge access, golf, concierge)

**Market Leaders:**
- **CRED:** Reward points tracking + exclusive redemptions
- **Niyo:** Travel reward optimization

---

### 9. BILL PAYMENTS & SUBSCRIPTIONS

#### 9.1 Subscription Tracker (Cancel Unused)
**User Need:** Track all subscriptions, identify wasteful spending

**Features:**
- Auto-detect subscriptions from transactions (Netflix, Spotify, Prime, Hotstar)
- Show total monthly subscription cost
- Alert for price increases
- Identify unused subscriptions (no usage last 30 days)
- One-click unsubscribe links
- Track free trials (cancel before charge)
- Family plan optimization (share with family members)

**Market Leaders:**
- **Truebill (US):** Subscription cancellation service
- **Bobby (US):** Subscription tracking
- **CRED:** Subscription bill payments

**Reddit:** "I'm paying for 5 OTT platforms but only use 2. Need a tool to show me what I'm wasting money on"

---

#### 9.2 Utility Bill Analyzer
**User Need:** Understand bill patterns, reduce costs

**Features:**
- Track electricity, water, gas bills over time
- Show seasonal trends (AC usage spike in summer)
- Compare with similar households (benchmarking)
- Suggest cost-saving tips (switch to LED, solar)
- Alert for abnormal bills (₹8K electricity vs usual ₹3K)

**Market Leaders:**
- **Paytm:** Bill payment history
- **CRED:** Bill analysis insights

---

### 10. FAMILY & SHARED FINANCES

#### 10.1 Joint Account Management (Spouse/Partner)
**User Need:** Track shared expenses, split contributions, maintain transparency

**Features:**
- Create joint workspace (invite spouse/partner)
- Shared budget view (household expenses)
- Track individual contributions to joint expenses
- Split bills (groceries, utilities, maid, school fees)
- Private accounts (personal spending stays private)
- Joint goal planning (house, vacation, child education)

**Market Leaders:**
- **Honeydue (US):** Couples finance app
- **Zeta (US):** Joint account for couples

**Already in Securo:** Multi-user workspace exists! Needs: split expense workflows, privacy controls

---

#### 10.2 Dependent/Child Financial Planning
**User Need:** Track child-related expenses, plan for education

**Features:**
- Create child profile (name, age, school)
- Track child-specific expenses:
  - School fees + uniform + books
  - Tuition/coaching classes
  - Extracurriculars (sports, music, art)
  - Medical expenses
  - Toys, clothing, birthday parties
- Education goal calculator (₹50L for engineering at age 18)
- Child insurance tracker (term cover, education plans)
- Sukanya Samriddhi Yojana (SSY) tracker (for daughters)

**Market Leaders:**
- **Scripbox:** Child education planner
- **ET Money:** Education goal calculator

**Family Earners:** Critical feature for this segment

---

#### 10.3 Parents/Elderly Care Budget
**User Need:** Track expenses for parents, plan for medical costs

**Features:**
- Create parent profile (age, medical conditions)
- Track parent-related expenses:
  - Medical bills, medicines, checkups
  - Health insurance premiums (parents' policy)
  - Monthly support/allowance
  - Travel/visits
- Emergency medical fund goal
- Parent insurance adequacy check (₹10L+ recommended)
- Tax benefits tracking (80D for parents' health insurance)

**CFP Insight:** "Sandwich generation (caring for parents + children) needs dual financial planning. Often overlooked until medical emergency"

---

### 11. FINANCIAL EDUCATION & INSIGHTS

#### 11.1 Personalized Financial Health Score
**User Need:** Understand overall financial health in one number

**Features:**
- Calculate score (0-100) based on:
  - Emergency fund coverage (6 months = full marks)
  - Debt-to-income ratio (< 30% = good)
  - Savings rate (> 20% = good)
  - Investment diversification
  - Insurance adequacy
  - Credit score
  - Retirement readiness
- Show score trend over time
- Actionable recommendations to improve score
- Benchmark against peers (anonymized)

**Market Leaders:**
- **CRED:** CRED Score
- **ET Money:** Financial health score
- **INDmoney:** Wealth score

---

#### 11.2 AI-Powered Spending Insights
**User Need:** Understand spending patterns, get personalized tips

**Features:**
- "You spent 30% more on dining this month vs last month"
- "Your grocery spending is 20% higher than similar households"
- "You could save ₹5000/month by canceling unused subscriptions"
- Anomaly detection (₹15K Swiggy order? Unusual!)
- Predict upcoming expenses (school fees due next month)
- Smart alerts (on track to overspend rent budget)

**Market Leaders:**
- **CRED:** AI insights
- **Jupiter:** Financial coaching
- **Cleo (US):** AI financial assistant

**Already in Securo:** AI Agents feature exists! Needs: India-specific coaching prompts, spending benchmarks

---

#### 11.3 Financial Literacy Content (Micro-Learning)
**User Need:** Learn while using the app (passive education)

**Features:**
- Daily financial tips (notifications)
- Explainer videos (5-min max):
  - "What is ELSS and how it saves tax"
  - "Term insurance vs endowment: which to buy?"
  - "How to read mutual fund factsheet"
- Glossary (XIRR, NAV, CAGR explained simply)
- Calculators with education:
  - SIP calculator + "Why SIP beats lump sum"
  - Retirement calculator + "Power of compounding"
- Community Q&A (Reddit-style, moderated)

**Market Leaders:**
- **Zerodha Varsity:** Best financial education content in India
- **Groww:** Learn section
- **ET Money:** Financial guides

**Reddit/LinkedIn:** "Most Indian users don't understand basic concepts like NAV, XIRR. In-app education builds trust and engagement"

---

#### 11.4 Contextual Nudges & Gamification
**User Need:** Stay motivated, build good habits

**Features:**
- **Nudges:**
  - "You haven't tracked expenses in 3 days. Tap to add"
  - "Great job! You stayed under budget this month"
  - "₹50K bonus credited. Allocate it now?"
  
- **Gamification:**
  - Streaks (30-day expense tracking streak)
  - Badges (Emergency fund builder, Tax saver, Debt-free warrior)
  - Leaderboards (opt-in, anonymized)
  - Challenges (No Swiggy for 7 days = save ₹1000)
  
- **Celebrations:**
  - Goal completion confetti
  - Debt payoff animation
  - Savings milestone rewards

**Market Leaders:**
- **CRED:** Gamification + rewards
- **Jupiter:** Challenges + badges

---

### 12. REPORTS & ANALYTICS

#### 12.1 Net Worth Tracker & Trends
**User Need:** See total wealth across all accounts

**Features:**
- Calculate net worth:
  - Assets: Bank accounts, investments (MF, stocks, gold), PPF, EPF, NPS, real estate
  - Liabilities: Loans, credit card debt
- Net worth = Assets - Liabilities
- Show trend chart (monthly snapshots)
- Breakdown by asset class (cash 20%, equity 40%, debt 30%, real estate 10%)
- Year-over-year growth
- Milestone tracking (₹10L, ₹50L, ₹1Cr)

**Market Leaders:**
- **INDmoney:** Net worth tracker (best in India)
- **ET Money:** Net worth dashboard

**Already in Securo:** Reports feature exists (balance sheet, P&L, forecast)! Needs: asset class breakdown, milestone celebrations

---

#### 12.2 Cash Flow Statement (Monthly/Yearly)
**User Need:** Understand money in vs money out

**Features:**
- Cash inflows: Salary, bonus, rental, interest, dividends
- Cash outflows: Expenses, EMIs, investments, taxes
- Net cash flow (positive = saving, negative = deficit)
- Show cash flow trend over 12 months
- Identify leakage categories (where money is going)

**Market Leaders:**
- **Quicken (US):** Cash flow reports
- **Money Manager:** Cash flow tracking

**Already in Securo:** P&L report (RFC #235) covers this! Needs: visual Sankey diagram for cash flow

---

#### 12.3 Tax Reports (Capital Gains, Deductions)
**User Need:** Simplified tax filing with ready reports

**Features:**
- Capital gains statement (STCG, LTCG by asset)
- TDS summary (26AS integration)
- 80C deductions summary (₹1.5L limit tracking)
- Interest income summary (FD, savings account)
- Rental income statement
- Export to Excel/PDF for CA
- Pre-fill ITR JSON (for Cleartax integration)

**Market Leaders:**
- **Quicko:** Tax reports + ITR filing
- **Cleartax:** Capital gains reports

---

#### 12.4 Custom Dashboards (Power User Feature)
**User Need:** Create personalized views for specific needs

**Features:**
- Drag-and-drop dashboard builder
- Widget library:
  - Net worth chart
  - Budget vs actual
  - Investment performance
  - Upcoming bills
  - Credit score
  - Goal progress
  - Spending by category
- Save multiple dashboard views (daily driver, month-end review, tax planning)
- Share dashboard with spouse/CA

**Market Leaders:**
- **Notion (productivity):** Custom dashboards
- **Tableau (analytics):** Dashboard builder

---

### 13. SMART AUTOMATION & AI

#### 13.1 Intelligent Transaction Categorization
**User Need:** Zero manual categorization; ML learns from behavior

**Features:**
- Auto-categorize transactions using ML
- Learn from user corrections (Swiggy = dining, not groceries)
- Merchant recognition (Zerodha → Investment, BPCL → Fuel)
- Recurring transaction detection (Netflix every 1st = Entertainment)
- Split complex transactions (Amazon order with grocery + electronics)
- Confidence score per categorization

**Market Leaders:**
- **Mint (US):** Best auto-categorization
- **YNAB:** Manual + suggested categories
- **Walnut:** ML-based categorization

---

#### 13.2 Proactive Financial Assistant (Conversational AI)
**User Need:** Ask questions, get instant answers

**Features:**
- Natural language queries:
  - "How much did I spend on dining last month?"
  - "Am I on track for my retirement goal?"
  - "Should I invest in ELSS or NPS?"
  - "What's my tax liability if I sell these stocks?"
  
- Proactive suggestions:
  - "You have ₹50K idle in savings. Invest in liquid fund?"
  - "Your car insurance expires in 30 days. Renew now?"
  - "You can save ₹20K tax by investing ₹50K more in 80C"
  
- Voice commands (Hindi + English)

**Market Leaders:**
- **CRED:** Conversational UI for bill payments
- **Cleo (US):** AI financial coach
- **Plum (US):** AI savings assistant

**Already in Securo:** AI Agents with tool-use exists! Needs: India-specific prompts, voice interface, proactive mode

---

#### 13.3 Smart Bill Negotiation (Auto-Save)
**User Need:** Reduce recurring bills automatically

**Features:**
- Analyze bills (broadband, mobile, DTH)
- Identify cheaper alternatives (same provider or switch)
- Auto-negotiate with provider on behalf of user
- Track savings achieved
- Switch assistance (port number, cancel old connection)

**Market Leaders:**
- **Billshark (US):** Bill negotiation service
- **Trim (US):** Auto-cancel subscriptions

**India Opportunity:** Telecom/DTH market is competitive; huge savings potential

---

### 14. SECURITY & PRIVACY

#### 14.1 Bank-Level Security
**User Need:** Trust that financial data is safe

**Features:**
- End-to-end encryption (data at rest + in transit)
- 2FA/MFA (SMS OTP, authenticator app, biometrics)
- Session timeout (15 min inactivity)
- Device management (log out from all devices)
- No third-party data sharing (GDPR-compliant even for India)
- Regular security audits (SOC 2, ISO 27001)
- Open-source transparency (Securo is AGPL!)

**Market Leaders:**
- All fintech apps must meet RBI guidelines
- **Securo advantage:** Self-hosted = user owns data

**Already in Securo:** Multi-factor auth, passkeys exist! Needs: session management, device tracking

---

#### 14.2 Privacy Controls (Granular Permissions)
**User Need:** Control what family members can see

**Features:**
- Hide specific accounts from shared workspace
- Mask transaction details (show amount, hide merchant)
- Private categories (tobacco, alcohol, gambling)
- Incognito mode (expenses don't sync to shared view)
- Export data (GDPR right to portability)
- Delete account + all data (right to be forgotten)

**Market Leaders:**
- **Honeydue:** Privacy controls for couples
- **Mint:** Account hiding

**Already in Securo:** Multi-user workspaces exist! Needs: granular privacy settings

---

### 15. INTEGRATIONS & ECOSYSTEM

#### 15.1 Bank Account Linking (Account Aggregator)
**User Need:** Auto-sync bank balances, transactions

**Features:**
- Link bank accounts via Account Aggregator (RBI-approved)
- Supported banks: HDFC, ICICI, SBI, Axis, Kotak, Yes Bank, etc.
- Auto-fetch transactions daily
- Balance sync (real-time or daily)
- Multi-bank view (all accounts in one dashboard)
- Alert for low balance

**Market Leaders:**
- **INDmoney:** Best bank sync in India (30+ banks)
- **ET Money:** Account Aggregator integration
- **Perfios:** Account Aggregator platform

**Regulatory:** RBI Account Aggregator framework (2021) enables this

---

#### 15.2 Broker Integrations (Zerodha, Groww, Upstox)
**User Need:** Auto-import stock/MF holdings

**Features:**
- OAuth-based broker linking
- Supported brokers: Zerodha, Groww, Upstox, Angel One, ICICI Direct, HDFC Securities
- Auto-sync holdings, trades, P&L
- Real-time portfolio updates
- Broker fee tracking

**Market Leaders:**
- **INDmoney:** Multi-broker sync
- **Ticker Tape:** Portfolio import

---

#### 15.3 UPI Deep Links (Quick Payments)
**User Need:** Pay bills directly from app

**Features:**
- Generate UPI payment links for bills
- One-tap payment via GPay/PhonePe/Paytm
- Track payment status (pending, success, failed)
- Send payment reminders to family members
- Split expense → generate UPI request

**Market Leaders:**
- **CRED:** UPI payment integration
- **Paytm:** Bill payment via UPI

---

#### 15.4 WhatsApp Bot (Expense Logging)
**User Need:** Log expenses via chat (fastest UX)

**Features:**
- WhatsApp bot number for expense logging
- Send message: "Swiggy ₹450" → auto-categorized as Dining
- Voice notes supported (Hindi + English)
- Daily expense summary on WhatsApp
- Bill reminders via WhatsApp
- Account balance query via chat

**Market Leaders:**
- **Walnut:** WhatsApp expense logging (discontinued)
- **Khatabook:** WhatsApp business integration

**Reddit:** "SMS parsing is great, but I want to log cash expenses via WhatsApp. Fastest UX"

---

### 16. COMMUNITY & SOCIAL

#### 16.1 Anonymous Benchmarking (Compare with Peers)
**User Need:** "Am I spending too much on dining?"

**Features:**
- Compare spending with anonymized cohorts:
  - Age group (25-30, 30-35, etc.)
  - Income bracket (₹5-10L, ₹10-20L, etc.)
  - City (Mumbai, Bangalore, Delhi, etc.)
  
- Show percentile ranking (you spend more than 70% of peers on dining)
- Category-wise comparison (groceries, transport, entertainment)
- Savings rate comparison
- Opt-in only (privacy-first)

**Market Leaders:**
- **Mint (US):** Peer comparison (discontinued)
- **Clarity Money (US):** Spending benchmarks

**Reddit:** "I want to know if my ₹10K dining spend is normal or excessive for my income level"

---

#### 16.2 Financial Goals Sharing (Accountability Partner)
**User Need:** Share goals with friends/family for motivation

**Features:**
- Share goal progress publicly (opt-in)
- Goal accountability partners (friend tracks your progress)
- Celebrate milestones together
- Goal challenges (save ₹50K in 6 months, compete with friend)
- Privacy controls (share with selected people only)

**Market Leaders:**
- **Strava (fitness):** Social sharing + challenges
- **Habitica:** Gamified habit tracking with friends

---

### 17. BUSINESS & FREELANCE (Self-Employed)

#### 17.1 Business Income/Expense Separation
**User Need:** Freelancers/business owners need to track business finances separately

**Features:**
- Create business profile (separate from personal)
- Track business income (invoices, payments)
- Track business expenses (software, equipment, travel)
- Business vs personal spending split
- GST tracking (input + output)
- Profit/loss statement (business)
- ITR-3/ITR-4 ready reports

**Market Leaders:**
- **Zoho Books:** Small business accounting
- **Vyapar:** GST billing + accounting
- **Khatabook:** Business ledger

**User Persona:** Business owners segment needs this

---

#### 17.2 Invoice & Payment Tracking
**User Need:** Freelancers need to track unpaid invoices

**Features:**
- Create invoices (with GST)
- Send invoices to clients
- Track payment status (pending, overdue, paid)
- Payment reminders (auto-send after 7 days)
- Aging report (invoices > 30 days overdue)
- Revenue recognition (invoice date vs payment date)

**Market Leaders:**
- **Zoho Invoice:** Invoicing + payment tracking
- **FreshBooks:** Freelancer accounting

---

### 18. UNIQUE INDIAN FEATURES (Cultural)

#### 18.1 Festival Spending Tracker
**User Need:** Track Diwali, Holi, Eid, Christmas, Pongal, Onam spending

**Features:**
- Festival budget templates
- Track festival-specific spending:
  - Gifts (family, friends, employees)
  - Decorations (lights, rangoli, flowers)
  - Clothing (new clothes for festival)
  - Food (sweets, special meals)
  - Donations (charity, temple)
  - Travel (visiting family)
- Compare festival spending year-over-year
- Pre-festival savings goal (6-month countdown)

**Unique to India:** No global app has this; massive differentiation

---

#### 18.2 Wedding Budget Planner
**User Need:** Indian weddings are expensive (₹10L-₹50L+); need dedicated tracking

**Features:**
- Wedding budget breakdown:
  - Venue, catering, photography, decoration
  - Clothing, jewelry, makeup
  - Guest list + gifts received tracking
  - Travel, accommodation for guests
  - Priest, rituals, music
- Track payments to vendors
- Gifts received tracker (cash + kind)
- Loan for wedding tracking
- Savings goal for wedding

**Market Leaders:**
- **WedMeGood:** Wedding planning + budgeting
- **WeddingWire:** Budget tracker

**Reddit:** "We spent ₹25L on our wedding and lost track. Wish we had a dedicated wedding budget app"

---

#### 18.3 Gold Purchase Planning (Dhanteras, Akshaya Tritiya)
**User Need:** Indians buy gold on auspicious days; plan for it

**Features:**
- Gold purchase goal (₹2L gold for Dhanteras)
- Gold price alerts (notify when gold < ₹60K/10g)
- Digital gold auto-invest (SIP in gold)
- Physical gold purchase tracker
- Gold purity verification (hallmark reminder)

**Unique to India:** Cultural importance of gold

---

#### 18.4 House Help (Maid/Cook/Driver) Salary Tracker
**User Need:** Track monthly payments to domestic help

**Features:**
- Create profiles for house help
- Track monthly salary + bonuses (Diwali bonus)
- Payment reminders (1st of every month)
- Leave tracking + salary deductions
- Advance payments tracking
- Tax implications (if applicable)

**Unique to India:** Common in urban households; often tracked manually

---

### 19. PERSONALIZATION ENGINE (Journey Mapping)

#### User Type Detection (Onboarding Quiz)
**Goal:** Tailor app experience based on user profile

**Quiz Questions:**
1. What's your primary source of income?
   - Salaried (corporate job)
   - Self-employed/freelancer
   - Business owner
   - Investor/passive income

2. What's your age group?
   - 20-25 (just starting)
   - 25-35 (building wealth)
   - 35-50 (family responsibilities)
   - 50+ (retirement planning)

3. What's your top financial goal?
   - Build emergency fund
   - Save for house down payment
   - Retire early
   - Child education
   - Wealth creation

4. How do you prefer to save/invest?
   - Bank FD/RD (conservative)
   - Mutual funds (moderate)
   - Direct stocks (aggressive)
   - Mix of all

5. What's your biggest financial pain point?
   - Can't track expenses
   - Overspending on dining/shopping
   - Not saving enough
   - Confused about investments
   - Tax planning is hard

**Personalized Journeys:**

#### Journey 1: Young Professional (25-35, Salaried)
**Default Features:**
- Salary slip parser
- 50/30/20 budget template (50% needs, 30% wants, 20% savings)
- Emergency fund goal (6 months expenses)
- Credit card optimization
- Tax-saving investments (ELSS, NPS)
- SIP recommendations

**Nudges:**
- "Start your first SIP today"
- "Build ₹3L emergency fund in 12 months"
- "You're spending 40% on dining. Consider meal prep?"

---

#### Journey 2: Family Primary Earner (35-50, Multiple Goals)
**Default Features:**
- Joint account with spouse
- Child education planner
- Parents' medical fund
- Home loan tracker
- Insurance adequacy check
- Retirement calculator
- Multi-goal tracking (house + education + retirement)

**Nudges:**
- "Your child's college is 10 years away. Start SIP of ₹10K now"
- "Your term cover is only ₹50L. Recommended: ₹2Cr for your income"
- "You're on track for retirement at 60. Great job!"

---

#### Journey 3: Mass Market (Tier 2/3, Budget-Conscious)
**Default Features:**
- Simple Hindi UI
- SMS expense tracking (no manual entry)
- RD tracker
- UPI spending analysis
- Festival budget templates
- Gold savings goal

**Nudges:**
- "आपने इस महीने ₹500 बचाए। बढ़िया!" (You saved ₹500 this month. Great!)
- "Diwali में ₹10,000 खर्च करना है? अभी ₹1,500/महीना बचाना शुरू करें"

---

### 20. COMPETITIVE FEATURE MATRIX

| Feature Category | Securo (Current) | ET Money | CRED | INDmoney | Kuvera | Walnut/Money View | Gap/Opportunity |
|-----------------|------------------|----------|------|----------|---------|-------------------|-----------------|
| **Expense Tracking** | Manual + CSV | SMS parsing | Manual + CC sync | Manual | Manual | SMS auto-capture ✓ | Need SMS parser |
| **Budgeting** | Single month | Multi-month | Basic | Basic | No | Good | Spreadsheet view exists (RFC) |
| **Investments** | Asset tracking | MF tracking | No | Best-in-class ✓ | MF focused | Basic | Need CAS import, SIP tracking |
| **Tax Planning** | No | Calculator | ITR filing | Calculator | No | No | Big gap - add tax dashboard |
| **Insurance** | Basic | Tracker | Health only | Tracker | No | No | Need renewal alerts |
| **Goals** | Yes ✓ | Yes | No | Yes | Yes | Basic | Add India templates |
| **Credit Cards** | Account tracking | No | Best UX ✓ | Basic | No | Good | Need reward optimization |
| **Bank Sync** | Manual | Account Aggregator | Manual | Account Aggregator ✓ | Manual | SMS only | Need AA integration |
| **AI/Insights** | AI Agents ✓ | Basic | Good | Basic | No | Good | Leverage existing AI |
| **Multi-user** | Workspaces ✓ | No | No | No | No | No | Unique advantage! |
| **Self-hosted** | Yes ✓ | No | No | No | No | No | Privacy differentiator |

**Securo's Unique Advantages:**
1. ✅ Self-hosted (privacy, data ownership)
2. ✅ Multi-user workspaces (family/business)
3. ✅ AI Agents with tool-use (can be India-tuned)
4. ✅ Open-source (community trust)
5. ✅ Already has: Goals, Asset tracking, Loan amortization, Budget spreadsheet (in progress)

**Priority Gaps to Close:**
1. 🚨 SMS/email transaction auto-capture (table stakes in India)
2. 🚨 Tax planning dashboard (high value, underserved)
3. 🚨 CAS import for mutual funds (investor segment need)
4. 🔥 Account Aggregator integration (bank sync)
5. 🔥 India-specific categories & templates

---

## IMPLEMENTATION ROADMAP (Prioritized)

### Phase 1: Foundation (Must-Have for Indian Market)
**Timeline:** 3-4 months

1. **SMS/Email Transaction Parser** (4 weeks)
   - Parse 20+ Indian bank SMS formats
   - UPI transaction detection
   - Email parser (credit card statements)
   - Auto-categorization ML model

2. **Indian Category Presets** (1 week)
   - Add India categories (house help, gold, donations, etc.)
   - Festival spending tags
   - Translation (Hindi, Tamil, Bengali)

3. **Tax Planning Dashboard** (3 weeks)
   - Income aggregation (salary, rental, capital gains)
   - 80C to 80U deduction tracker
   - Old vs new regime comparison
   - Form 12BB generator

4. **EPF/PPF/NPS Tracking** (2 weeks)
   - Manual entry UI for now
   - Retirement corpus projection
   - Goal linkage

5. **Insurance Tracker Enhancement** (2 weeks)
   - Renewal date alerts
   - Adequacy calculator
   - Premium budget tracking

**Success Metrics:**
- 80% of transactions auto-captured (vs 0% now)
- Tax dashboard used by 60% of users
- 5-star reviews mentioning "India-specific"

---

### Phase 2: Differentiation (Market Leadership)
**Timeline:** 3-4 months

1. **Account Aggregator Integration** (4 weeks)
   - RBI-approved AA onboarding
   - Bank account linking (10+ banks)
   - Auto-sync transactions daily

2. **Mutual Fund CAS Import** (3 weeks)
   - Upload CAMS/Karvy PDF
   - Parse holdings, SIPs, transactions
   - Portfolio analytics (XIRR, category allocation)

3. **Credit Card Optimizer** (3 weeks)
   - Multi-card tracking
   - Reward points aggregator
   - Best card recommendation engine

4. **Festival Budget Templates** (2 weeks)
   - Diwali, Holi, Eid, Christmas, Pongal templates
   - Year-over-year comparison
   - Pre-festival savings goals

5. **WhatsApp Expense Bot** (4 weeks)
   - WhatsApp Business API integration
   - Voice note expense logging (Hindi + English)
   - Daily summary messages

**Success Metrics:**
- Bank sync adoption: 40% of users
- MF tracking: 30% of investors
- WhatsApp bot: 20% monthly active

---

### Phase 3: Advanced (Power Users)
**Timeline:** 3-4 months

1. **AI Financial Coach (India-Tuned)** (4 weeks)
   - Proactive suggestions based on Indian context
   - Voice assistant (Hindi + English)
   - Tax-saving recommendations (ELSS, NPS)

2. **Family Financial Planning Suite** (4 weeks)
   - Child education planner (school + college goals)
   - Parents medical fund tracker
   - Joint account optimization

3. **Business/Freelance Module** (4 weeks)
   - GST tracking
   - Invoice management
   - ITR-3/ITR-4 reports

4. **Anonymous Benchmarking** (3 weeks)
   - Spending comparison by cohort
   - Percentile ranking
   - Privacy-first design

5. **Custom Dashboards** (3 weeks)
   - Widget library
   - Drag-and-drop builder
   - Multiple saved views

**Success Metrics:**
- AI coach engagement: 50% weekly active
- Family suite adoption: 25% of family earners
- Benchmarking opt-in: 30%

---

## EXPERT QUOTES (CFPs, RIAs, Reddit)

**CFP (Certified Financial Planner):**
> "Indian users need hand-holding on tax optimization. Most don't know they can save ₹50K tax by just investing ₹1.5L in 80C. An app that shows real-time tax impact of investments will win."

**RIA (Registered Investment Advisor):**
> "The biggest gap in Indian fintech is retirement planning. Everyone focuses on short-term goals (vacation, phone). Apps should calculate: 'You need ₹8Cr at 60. You're only saving ₹1Cr. Increase SIP by ₹5K now.'"

**Reddit r/IndiaInvestments:**
> "I use 4 apps: Kuvera for MFs, INDmoney for stocks, ET Money for insurance, Cleartax for tax. I want ONE app that does all this. Preferably self-hosted so I own my data."

**LinkedIn (Finance Influencer):**
> "Indian millennials are great at earning, terrible at saving. Behavioral nudges (round-up, auto-invest) work better than complex planning tools. Make saving invisible."

**Twitter (FinTwit India):**
> "Credit card rewards are money on the table. Most people use the wrong card for fuel, dining, travel. An app that tells me 'Use HDFC Regalia for this ₹5K dining bill' = instant value."

---

## CONCLUSION

**Key Takeaways:**
1. **India-specific = table stakes:** SMS parsing, tax dashboard, EPF/PPF/NPS, insurance alerts are non-negotiable
2. **Cultural features = differentiation:** Festival budgets, wedding planner, gold tracking, house help salary
3. **Personalization = retention:** Young professionals need different features than family earners
4. **Privacy = moat:** Securo's self-hosted model is a unique advantage in privacy-conscious times

**Securo's Path to Indian Market Leadership:**
- **Short-term (6 months):** Close foundational gaps (SMS, tax, AA integration)
- **Medium-term (12 months):** Build differentiated features (festival budgets, family suite)
- **Long-term (18 months):** Become the "everything app" for Indian personal finance (investments + tax + insurance + goals)

**Final Recommendation:**
Start with Phase 1 (Foundation). Ship SMS parser + Tax dashboard + Indian categories in Q1 2027. This alone will make Securo competitive with ET Money/CRED for the salaried segment. Then layer in differentiation (festivals, family suite) in Phase 2.

---

**Document Status:** Ready for review and prioritization
**Next Steps:** Stakeholder review → Feature prioritization → Technical feasibility assessment → Roadmap finalization
