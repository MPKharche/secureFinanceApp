# Priority Feature List (Post-Parking)

**Date:** 2026-09-16  
**Status:** Prioritized Backlog  
**Context:** Features remaining after parking low-priority/niche items

---

## PARKED FEATURES (Not in Roadmap)

**Reason for Parking:** Low demand, niche use case, or better solved by dedicated apps

- Income: Salary breakdown, bonus forecasting (complex, low ROI)
- Expense: UPI-first view (nice-to-have, not essential)
- Savings: RD tracker (niche, declining product usage)
- Credit: Reward optimization (CRED owns this)
- Bills: Subscription tracker (better solved by CRED/Truebill)
- Family: Child planning, parents' care (too specialized)
- Education: Health score, micro-learning, gamification (retention features, not core)
- Automation: Bill negotiation (operationally complex)
- Integrations: Account Aggregator, broker sync, UPI deep links (regulatory/partnership heavy)
- Community: Benchmarking, goal sharing (social features, low priority)
- Business: Income/expense separation, invoicing (use Zoho Books instead)
- Cultural: Festival spending, wedding, gold, house help (nice differentiation but niche)

---

## REMAINING FEATURES BY PRIORITY

**Priority Score:** 
- 🔥🔥🔥 P0 = Critical (must-have for Indian market)
- 🔥🔥 P1 = High (strong user demand, competitive necessity)
- 🔥 P2 = Medium (nice-to-have, moderate impact)
- ❄️ P3 = Low (future consideration, low demand)

**Scoring Criteria:**
- **User Value:** How much does this solve a painful problem? (1-5)
- **Demand:** How many users will use this? (1-5)
- **Competitive Gap:** Do competitors have this? (1-5)
- **Build Effort:** Implementation complexity (1-5, lower is better)
- **Total Score:** (Value × 2) + Demand + Gap - (Effort × 0.5)

---

## 1. INCOME TRACKING & MANAGEMENT

### ✅ 1.1 EPF/PF Tracker
**Priority:** 🔥🔥🔥 P0  
**Score:** 18.5/20

**Why:**
- 100% of salaried Indians have EPF
- Critical for retirement planning
- No manual tracking exists
- Simple to build (manual entry initially)

**Features:**
- Link EPFO account (UAN-based) manually
- Log EPF balance, employer contribution
- Calculate projected corpus at retirement
- Alert for inactive PF accounts from previous employers
- Consolidate multiple PF accounts

**User Value:** 5/5 (retirement blind spot)  
**Demand:** 5/5 (every salaried person)  
**Competitive Gap:** 3/5 (ET Money has it)  
**Build Effort:** 2/5 (manual entry MVP)

---

### ✅ 1.2 Multi-Income Source Tracking
**Priority:** 🔥🔥 P1  
**Score:** 14.5/20

**Why:**
- Young professionals have side hustles
- Tax filing requires tracking all income sources
- Simple categorization

**Features:**
- Separate income streams: Salary, Freelance, Rental, Interest, Dividends, Capital Gains
- Month-wise income breakdown
- Export for ITR filing

**User Value:** 4/5 (tax compliance)  
**Demand:** 4/5 (growing gig economy)  
**Competitive Gap:** 3/5 (most apps focus on salary only)  
**Build Effort:** 2/5 (categorization + reporting)

---

### ❄️ 1.3 Stock Options (ESOP/RSU) Tracker
**Priority:** 🔥 P2  
**Score:** 11/20

**Why:**
- Only tech workers have ESOPs (~5-10% of salaried)
- Complex tax implications
- High build effort for niche audience

**Features:**
- Log vesting schedule
- Track exercise windows
- Calculate perquisite value (taxable)
- Capital gains on sale

**User Value:** 5/5 (for those who have it)  
**Demand:** 2/5 (niche segment)  
**Competitive Gap:** 4/5 (no one does this well)  
**Build Effort:** 4/5 (complex tax logic)

---

## 2. EXPENSE TRACKING & CATEGORIZATION

### ✅ 2.1 SMS/Email Auto-Capture (India Banks)
**Priority:** 🔥🔥🔥 P0  
**Score:** 19/20

**Why:**
- 90% of Indian transactions trigger SMS
- Manual entry = biggest friction
- Competitive necessity (Walnut proved this)

**Features:**
- Parse SMS from 20+ banks (HDFC, ICICI, SBI, Axis, Kotak, etc.)
- Extract: amount, merchant, account, transaction type
- Handle UPI transactions (GPay, PhonePe, Paytm)
- Parse credit card emails
- Auto-categorize using ML

**User Value:** 5/5 (removes biggest friction)  
**Demand:** 5/5 (every smartphone user)  
**Competitive Gap:** 5/5 (table stakes)  
**Build Effort:** 4/5 (SMS parsing + ML)

**Build Breakdown:**
- Week 1-2: SMS permission + parser for 5 major banks
- Week 3: ML categorization model (train on labeled data)
- Week 4: UPI detection + email parser
- Week 5-6: Expand to 20+ banks, refinement

---

### ✅ 2.2 Indian Category Presets
**Priority:** 🔥🔥🔥 P0  
**Score:** 16.5/20

**Why:**
- Default categories don't match Indian spending
- Cultural relevance = user trust
- Easy to build

**Categories to Add:**
- House help (maid, cook, driver, security)
- Education (school fees, tuition, coaching)
- Gold purchases
- Religious/donations
- Pet care
- Parent support

**User Value:** 4/5 (cultural fit)  
**Demand:** 5/5 (everyone needs categories)  
**Competitive Gap:** 4/5 (Walnut has this)  
**Build Effort:** 1/5 (just config data)

---

### ✅ 2.3 Shared Expense Splitting
**Priority:** 🔥🔥 P1  
**Score:** 14/20

**Why:**
- Families need this for transparency
- Roommates, travel groups
- Splitwise exists but not integrated

**Features:**
- Create expense groups (family, roommates, trip)
- Split equally or custom %
- Track who owes whom
- Settle-up reminders
- Export settlement summary

**User Value:** 4/5 (reduces friction)  
**Demand:** 4/5 (families + young professionals)  
**Competitive Gap:** 3/5 (Splitwise dominates)  
**Build Effort:** 3/5 (group logic + settlements)

---

### ❄️ 2.4 Receipt/Bill Photo Capture (OCR)
**Priority:** 🔥 P2  
**Score:** 10.5/20

**Why:**
- Nice-to-have, not essential
- SMS already captures most transactions
- OCR accuracy issues in India

**Features:**
- Snap receipt photo
- Extract amount, merchant, date via OCR
- Attach to transaction

**User Value:** 3/5 (convenience)  
**Demand:** 3/5 (some users want it)  
**Competitive Gap:** 4/5 (few apps have OCR)  
**Build Effort:** 4/5 (OCR model + training)

---

## 3. BUDGETING & SPENDING CONTROL

### ✅ 3.1 Zero-Based Budgeting (Envelope Method)
**Priority:** 🔥🔥 P1  
**Score:** 15/20

**Why:**
- Proven method for disciplined savers
- YNAB model works globally
- Already have budget spreadsheet (RFC)

**Features:**
- Create budget envelopes per category
- Fund at start of month
- Real-time balance after each transaction
- Rollover or reset options
- Visual progress bars

**User Value:** 4/5 (behavior change)  
**Demand:** 4/5 (savers love this)  
**Competitive Gap:** 4/5 (no Indian app does YNAB well)  
**Build Effort:** 3/5 (UI + envelope logic)

---

### ✅ 3.2 Bill Reminders & Auto-Pay Tracking
**Priority:** 🔥🔥🔥 P0  
**Score:** 17/20

**Why:**
- Late fees are painful
- Recurring bills (electricity, broadband, mobile)
- Simple to build, high impact

**Features:**
- Set bill reminders (due date)
- Track amount trends (electricity spike in summer)
- Alert 3 days before due date
- Auto-detect bill payments from SMS
- Track late fees paid

**User Value:** 5/5 (avoids late fees)  
**Demand:** 5/5 (everyone has bills)  
**Competitive Gap:** 3/5 (CRED, Paytm have this)  
**Build Effort:** 2/5 (reminders + tracking)

---

### ✅ 3.3 EMI Tracker & Loan Dashboard (Enhancement)
**Priority:** 🔥🔥🔥 P0  
**Score:** 18/20

**Why:**
- Already have loan amortization (RFC #235)
- Need: multi-loan view + prepayment scenarios
- High user value

**Features to Add:**
- Track multiple loans in one dashboard
- Total EMI outgo per month
- Prepayment calculator (reduce tenure vs EMI)
- Debt-to-income ratio
- Loan payoff priority (highest interest first)

**User Value:** 5/5 (debt payoff planning)  
**Demand:** 5/5 (most Indians have loans)  
**Competitive Gap:** 3/5 (ET Money, BankBazaar have this)  
**Build Effort:** 2/5 (extend existing feature)

---

### ❄️ 3.4 Spending Pace Indicator (Current Month)
**Priority:** 🔥 P2  
**Score:** 12/20

**Why:**
- Proactive overspending prevention
- Requires daily calculation
- Nice-to-have, not critical

**Features:**
- Calculate: (actual spend / days elapsed) × days in month = projected spend
- Alert if projected > budget
- Visual progress bar

**User Value:** 4/5 (prevents overspending)  
**Demand:** 3/5 (budget-conscious users)  
**Competitive Gap:** 4/5 (few apps have this)  
**Build Effort:** 2/5 (simple math)

---

## 4. SAVINGS & GOAL PLANNING

### ✅ 4.1 Goal-Based Savings (India Templates)
**Priority:** 🔥🔥🔥 P0  
**Score:** 17.5/20

**Why:**
- Already have goals feature!
- Need India-specific templates
- Easy to add

**Templates to Add:**
- Emergency fund (6 months expenses)
- Child education (school + college)
- Marriage (self/children)
- House down payment
- Car purchase
- Parents' medical fund
- Retirement corpus

**User Value:** 5/5 (cultural relevance)  
**Demand:** 5/5 (everyone has goals)  
**Competitive Gap:** 4/5 (Scripbox, Kuvera have this)  
**Build Effort:** 1/5 (just templates + goal priority ranking)

---

### ✅ 4.2 Automated Savings Rules (Sweep/Round-Up)
**Priority:** 🔥🔥 P1  
**Score:** 15.5/20

**Why:**
- Behavioral economics works
- Jupiter, Fi Money proved this in India
- Passive savings = higher retention

**Features:**
- Round-up savings (₹47 → save ₹3)
- Rule-based sweeps (save 10% of every credit)
- Salary-day auto-transfer (save ₹5K on 1st)
- Bonus allocation (invest 50%, save 30%, spend 20%)

**User Value:** 5/5 (automates savings)  
**Demand:** 4/5 (young professionals love this)  
**Competitive Gap:** 4/5 (Jupiter has it)  
**Build Effort:** 3/5 (rules engine + bank integration)

**Note:** Requires bank account write access (risky, needs user trust)

---

## 5. INVESTMENT TRACKING & PORTFOLIO

### ✅ 5.1 Mutual Fund Portfolio (CAS Import)
**Priority:** 🔥🔥🔥 P0  
**Score:** 18/20

**Why:**
- Already have asset tracking (RFC #235)!
- CAS import = game-changer for investors
- Competitive necessity

**Features to Add:**
- Import CAS (CAMS/Karvy PDF)
- Parse holdings, SIPs, transactions
- Show XIRR, absolute returns, current value
- Track SIPs (next date, amount, fund)
- Goal-to-fund mapping
- Tax harvesting alerts (book losses before March 31)

**User Value:** 5/5 (consolidates portfolio)  
**Demand:** 5/5 (50M+ MF investors in India)  
**Competitive Gap:** 5/5 (Kuvera, ET Money have this)  
**Build Effort:** 4/5 (PDF parsing + XIRR calculations)

---

### ✅ 5.2 Stock Portfolio Enhancements (Indian Context)
**Priority:** 🔥🔥 P1  
**Score:** 16/20

**Why:**
- Already have investment ledger with average price (RFC #235)!
- Need: dividend tracking, tax classification, broker CSV import

**Features to Add:**
- Import via broker CSV (Zerodha, Groww, Upstox)
- Dividend tracker (amount, ex-date, credit date)
- Holding period classification (STCG vs LTCG)
- Sector allocation pie chart
- Realized P&L for tax reporting

**User Value:** 5/5 (tax compliance + portfolio insights)  
**Demand:** 4/5 (30M+ stock investors)  
**Competitive Gap:** 4/5 (INDmoney, Ticker Tape have this)  
**Build Effort:** 3/5 (CSV parser + tax logic)

---

### ✅ 5.3 Gold Investment Tracker
**Priority:** 🔥🔥 P1  
**Score:** 15/20

**Why:**
- Unique to India (cultural asset class)
- No competitor does this comprehensively
- Differentiation opportunity

**Features:**
- Track physical gold (jewelry, coins, bars) - weight + price
- Track digital gold (Paytm, PhonePe, MMTC-PAMP)
- Sovereign Gold Bonds (SGB) + interest tracking
- Gold ETF/mutual funds
- Current value based on live gold prices
- Gold allocation % of portfolio

**User Value:** 4/5 (portfolio completion)  
**Demand:** 4/5 (Indians love gold)  
**Competitive Gap:** 5/5 (no one does this well)  
**Build Effort:** 3/5 (gold price API + tracking)

---

### ✅ 5.4 PPF/NPS Retirement Dashboard
**Priority:** 🔥🔥🔥 P0  
**Score:** 17/20

**Why:**
- Retirement is most asked question by CFPs
- Consolidation drives planning
- Links with EPF tracker (above)

**Features:**
- **PPF:** Log account, contributions, maturity projection
- **NPS:** Link PRAN, show Tier 1+2 balance, 60/40 split calculation
- **Consolidated View:** Total retirement corpus (EPF + PPF + NPS + MF)
- Retirement readiness score
- Gap analysis (target ₹5Cr, current ₹3Cr → increase SIP by ₹5K)

**User Value:** 5/5 (retirement anxiety relief)  
**Demand:** 5/5 (everyone worries about retirement)  
**Competitive Gap:** 4/5 (Scripbox has this)  
**Build Effort:** 3/5 (projections + calculations)

---

### ❄️ 5.5 Real Estate Tracker
**Priority:** 🔥 P2  
**Score:** 11.5/20

**Why:**
- Only family earners with 2+ properties need this
- Complex valuation (manual updates needed)
- Niche segment

**Features:**
- Log properties (primary, rental, plot)
- Track property value (manual or area-based estimates)
- Rental income tracking
- Home loan mapping (property → loan → EMI)
- Property expenses (maintenance, tax, repairs)

**User Value:** 5/5 (for those with property)  
**Demand:** 2/5 (niche segment)  
**Competitive Gap:** 4/5 (INDmoney has basic tracking)  
**Build Effort:** 4/5 (valuation APIs, complex UI)

---

## 6. TAX PLANNING & OPTIMIZATION

### ✅ 6.1 Tax Projection Dashboard (Live Calculator)
**Priority:** 🔥🔥🔥 P0  
**Score:** 19/20

**Why:**
- BIGGEST GAP in Indian fintech
- High user value, underserved
- Drives investment decisions

**Features:**
- **Input:** Salary, rental, capital gains, interest, business income
- **Deductions (80C to 80U):**
  - 80C: EPF, PPF, ELSS, LIC, tuition (₹1.5L)
  - 80D: Health insurance (₹25K/₹50K)
  - 80CCD(1B): NPS (₹50K)
  - 80G: Donations
  - 24(b): Home loan interest
  - HRA calculator
- **Output:**
  - Tax liability (old vs new regime)
  - TDS deducted, tax due/refund
  - Regime comparison (which saves more?)
  - Monthly tax tracker (YTD vs projection)

**User Value:** 5/5 (saves real money)  
**Demand:** 5/5 (every taxpayer needs this)  
**Competitive Gap:** 5/5 (Cleartax has it, but not integrated)  
**Build Effort:** 4/5 (complex tax logic, regime rules)

---

### ✅ 6.2 Investment Declaration Helper (Form 12BB)
**Priority:** 🔥🔥 P1  
**Score:** 14/20

**Why:**
- Annual pain point (Jan-Feb)
- Feeds from tracked investments
- Export to PDF = huge convenience

**Features:**
- Pre-fill Form 12BB from tracked investments (EPF, PPF, ELSS, LIC, NPS)
- Upload proof documents
- Send to employer via email/PDF
- Submission reminder in Jan-Feb

**User Value:** 4/5 (saves time)  
**Demand:** 4/5 (salaried employees only)  
**Competitive Gap:** 3/5 (Cleartax has it)  
**Build Effort:** 3/5 (form template + data mapping)

---

### ✅ 6.3 Capital Gains Tax Calculator
**Priority:** 🔥🔥🔥 P0  
**Score:** 18/20

**Why:**
- Already track realized gains (RFC #235)!
- Just need to apply tax rates
- Critical for investors

**Features to Add:**
- Calculate holding period (< 1 year = STCG, > 1 year = LTCG)
- Apply tax rates:
  - Equity STCG: 15%, LTCG: 10% above ₹1L
  - Debt STCG: Slab, LTCG: 20% with indexation
- Show net proceeds after tax
- Advance tax calculator (if gains > ₹10K)
- Tax harvesting suggestions (book losses to offset gains)

**User Value:** 5/5 (tax compliance + optimization)  
**Demand:** 5/5 (every investor selling stocks/MF)  
**Competitive Gap:** 5/5 (Quicko has this standalone)  
**Build Effort:** 3/5 (tax rate logic + alerts)

---

## 7. INSURANCE MANAGEMENT

### ✅ 7.1 Insurance Policy Tracker (Enhancement)
**Priority:** 🔥🔥🔥 P0  
**Score:** 17.5/20

**Why:**
- Already have asset tracking (RFC #235)!
- Just need: renewal alerts + adequacy calculator
- High impact, easy to build

**Features to Add:**
- **Policy Types:** Life, Health, Vehicle, Home, Travel
- **Tracking:** Premium due date reminders (60/30/7 days)
- Coverage amount (sum assured)
- Nominee details
- Policy documents vault
- **Analysis:**
  - Adequacy calculator (life cover = 10x annual income)
  - Premium as % of income
  - Identify redundant policies

**User Value:** 5/5 (avoids lapses, optimizes coverage)  
**Demand:** 5/5 (everyone has insurance)  
**Competitive Gap:** 4/5 (PolicyBazaar has this)  
**Build Effort:** 2/5 (alerts + calculations)

---

### ❄️ 7.2 Health Insurance Claim Tracker
**Priority:** 🔥 P2  
**Score:** 11/20

**Why:**
- Only needed when claim happens (infrequent)
- Complex integration with insurers
- Better handled by insurer apps

**Features:**
- Log medical expenses
- Link to policy
- Track claim status (submitted, approved, paid)
- Reimbursement tracking

**User Value:** 4/5 (when needed)  
**Demand:** 2/5 (infrequent use)  
**Competitive Gap:** 3/5 (CRED, Plum have this)  
**Build Effort:** 4/5 (insurer integration)

---

## 8. CREDIT MANAGEMENT

### ✅ 8.1 Credit Card Dashboard (Enhancement)
**Priority:** 🔥🔥 P1  
**Score:** 15.5/20

**Why:**
- Already have multi-account tracking!
- Need: credit-specific features
- High value-add

**Features to Add:**
- Total credit limit vs utilization (< 30% ideal)
- Alert 3 days before bill due
- Show spending by card
- Track annual fees, reversals
- Credit utilization ratio (impacts score)
- Identify best card for category (fuel, dining, travel)

**User Value:** 5/5 (optimizes credit, avoids fees)  
**Demand:** 4/5 (urban users have 2-3 cards)  
**Competitive Gap:** 4/5 (CRED owns this)  
**Build Effort:** 3/5 (credit logic + recommendations)

---

### ✅ 8.2 Credit Score Monitoring
**Priority:** 🔥🔥 P1  
**Score:** 14.5/20

**Why:**
- User anxiety reducer
- Free APIs available (CIBIL, Experian)
- Competitive feature

**Features:**
- Fetch credit score (monthly updates)
- Show score trend
- Explain factors (payment history, utilization, age)
- Actionable tips to improve
- Alert on score changes

**User Value:** 4/5 (financial health awareness)  
**Demand:** 4/5 (loan applicants + credit users)  
**Competitive Gap:** 4/5 (CRED, BankBazaar have free scores)  
**Build Effort:** 3/5 (API integration + UI)

---

## 9. REPORTS & ANALYTICS

### ✅ 9.1 Net Worth Tracker Enhancements
**Priority:** 🔥🔥 P1  
**Score:** 16/20

**Why:**
- Already have balance sheet report (RFC #235)!
- Need: asset class breakdown + milestones
- High engagement feature

**Features to Add:**
- Breakdown by asset class (cash, equity, debt, real estate, gold)
- Year-over-year growth %
- Milestone tracking (₹10L, ₹50L, ₹1Cr) with celebrations
- Compare with age-based benchmarks

**User Value:** 5/5 (motivational + planning)  
**Demand:** 4/5 (wealth trackers love this)  
**Competitive Gap:** 4/5 (INDmoney has best implementation)  
**Build Effort:** 2/5 (visualization + milestones)

---

### ✅ 9.2 Cash Flow Visualization (Sankey Diagram)
**Priority:** 🔥 P2  
**Score:** 13/20

**Why:**
- Already have P&L report (RFC #235)!
- Visual Sankey = better insights
- Nice-to-have, not critical

**Features to Add:**
- Sankey diagram: Income → Expenses/Savings/Investments
- Show money flow (salary → rent, groceries, SIP, etc.)
- Identify leakage categories

**User Value:** 4/5 (visual clarity)  
**Demand:** 3/5 (power users)  
**Competitive Gap:** 4/5 (few apps have Sankey)  
**Build Effort:** 3/5 (charting library)

---

### ✅ 9.3 Tax Reports (Export for CA/ITR)
**Priority:** 🔥🔥 P1  
**Score:** 15/20

**Why:**
- Tax season (July-Aug) = peak demand
- Export to Excel/PDF = huge value
- Feeds from tax dashboard (above)

**Features:**
- Capital gains statement (STCG, LTCG by asset)
- TDS summary (manual entry, future: 26AS integration)
- 80C deductions summary
- Interest income summary
- Rental income statement
- Export formats: Excel, PDF, ITR JSON (for Cleartax)

**User Value:** 5/5 (tax filing ease)  
**Demand:** 4/5 (investors + high earners)  
**Competitive Gap:** 4/5 (Quicko, Cleartax have this)  
**Build Effort:** 3/5 (report generation + export)

---

## 10. SMART AUTOMATION & AI

### ✅ 10.1 Intelligent Transaction Categorization (ML)
**Priority:** 🔥🔥🔥 P0  
**Score:** 18/20

**Why:**
- Pairs with SMS auto-capture (P0 above)
- Zero manual work = biggest win
- ML models improve over time

**Features:**
- Auto-categorize transactions using ML
- Learn from user corrections
- Merchant recognition (Zerodha → Investment, BPCL → Fuel)
- Recurring detection (Netflix every 1st = Entertainment)
- Confidence score per categorization

**User Value:** 5/5 (removes friction)  
**Demand:** 5/5 (pairs with SMS capture)  
**Competitive Gap:** 5/5 (Mint, Walnut have this)  
**Build Effort:** 4/5 (ML training + ongoing learning)

---

### ✅ 10.2 Proactive Financial Assistant (India-Tuned)
**Priority:** 🔥🔥 P1  
**Score:** 16/20

**Why:**
- Already have AI Agents with tool-use!
- Need: India-specific prompts + proactive mode
- Differentiator

**Features to Add:**
- Natural language queries:
  - "How much dining last month?"
  - "Am I on track for retirement?"
  - "Should I invest in ELSS or NPS?"
  
- **Proactive suggestions (NEW):**
  - "₹50K idle in savings. Invest in liquid fund?"
  - "Car insurance expires in 30 days. Renew?"
  - "Save ₹20K tax by investing ₹50K more in 80C"
  
- Voice commands (Hindi + English)

**User Value:** 5/5 (coaching + automation)  
**Demand:** 4/5 (tech-savvy users)  
**Competitive Gap:** 4/5 (CRED has conversational UI)  
**Build Effort:** 3/5 (proactive engine + voice)

---

## 11. SECURITY & PRIVACY

### ✅ 11.1 Session Management & Device Tracking
**Priority:** 🔥🔥 P1  
**Score:** 14/20

**Why:**
- Security hygiene
- Multi-device usage is common
- Trust builder

**Features to Add:**
- Active sessions list (device, location, last active)
- Log out from all devices (remote)
- Session timeout (15 min inactivity)
- Login alerts (new device email)

**User Value:** 4/5 (security peace of mind)  
**Demand:** 4/5 (multi-device users)  
**Competitive Gap:** 3/5 (banks have this)  
**Build Effort:** 3/5 (session store + device fingerprinting)

---

### ✅ 11.2 Privacy Controls (Granular)
**Priority:** 🔥 P2  
**Score:** 12/20

**Why:**
- Multi-user workspaces exist!
- Need: hide accounts, private categories
- Family transparency vs privacy

**Features to Add:**
- Hide specific accounts from shared workspace
- Mask transaction details (show amount, hide merchant)
- Private categories (alcohol, gambling)
- Incognito mode (expenses don't sync)

**User Value:** 4/5 (family harmony)  
**Demand:** 3/5 (joint account users)  
**Competitive Gap:** 4/5 (Honeydue has this)  
**Build Effort:** 3/5 (permissions logic)

---

## SUMMARY: PRIORITY ROADMAP

### 🔥🔥🔥 P0 - CRITICAL (Ship First, 3-4 months)

**Foundation for Indian Market:**

1. **SMS/Email Auto-Capture** (19/20) - 6 weeks
2. **Tax Projection Dashboard** (19/20) - 3 weeks
3. **Indian Category Presets** (16.5/20) - 1 week
4. **EPF/PF Tracker** (18.5/20) - 2 weeks
5. **Bill Reminders** (17/20) - 2 weeks
6. **EMI Dashboard Enhancement** (18/20) - 2 weeks
7. **Goal Templates (India)** (17.5/20) - 1 week
8. **MF Portfolio (CAS Import)** (18/20) - 4 weeks
9. **Capital Gains Tax Calculator** (18/20) - 2 weeks
10. **Insurance Tracker Enhancement** (17.5/20) - 2 weeks
11. **PPF/NPS Dashboard** (17/20) - 3 weeks
12. **ML Transaction Categorization** (18/20) - 4 weeks

**Total:** ~12 weeks (3 months) if sequential, 8-10 weeks with parallelization

**Impact:** Match ET Money/CRED feature parity, establish Indian market credibility

---

### 🔥🔥 P1 - HIGH (Ship Next, 3-4 months)

**Differentiation & Competitive Features:**

1. **Multi-Income Tracking** (14.5/20) - 2 weeks
2. **Shared Expense Splitting** (14/20) - 3 weeks
3. **Zero-Based Budgeting** (15/20) - 3 weeks
4. **Automated Savings Rules** (15.5/20) - 4 weeks
5. **Stock Portfolio Enhancements** (16/20) - 3 weeks
6. **Gold Tracker** (15/20) - 3 weeks
7. **Form 12BB Helper** (14/20) - 2 weeks
8. **Credit Card Dashboard** (15.5/20) - 3 weeks
9. **Credit Score Monitoring** (14.5/20) - 2 weeks
10. **Net Worth Enhancements** (16/20) - 2 weeks
11. **Tax Reports Export** (15/20) - 2 weeks
12. **Proactive AI Assistant** (16/20) - 4 weeks
13. **Session Management** (14/20) - 2 weeks

**Total:** ~12 weeks (3 months)

**Impact:** Market leadership features, user retention

---

### 🔥 P2 - MEDIUM (Future, 6-12 months)

**Nice-to-Have & Power User Features:**

1. **ESOP/RSU Tracker** (11/20)
2. **Receipt OCR** (10.5/20)
3. **Spending Pace Indicator** (12/20)
4. **Real Estate Tracker** (11.5/20)
5. **Health Insurance Claim Tracker** (11/20)
6. **Cash Flow Sankey** (13/20)
7. **Privacy Controls** (12/20)

**Total:** Lower priority, build only if user demand spikes

---

### ❄️ P3 - LOW (Deprioritize)

**Features to Reconsider or Skip:**
- Advanced gamification (existing nudges sufficient)
- Social benchmarking (privacy concerns)
- Bill negotiation (operationally complex)
- Account Aggregator (regulatory/partnership bottleneck)

---

## BUILD EFFORT SUMMARY

| Priority | Features | Total Weeks | Team Size | Duration |
|----------|----------|-------------|-----------|----------|
| P0 (Critical) | 12 features | 32 weeks | 3 engineers | 10-12 weeks |
| P1 (High) | 13 features | 35 weeks | 3 engineers | 11-12 weeks |
| P2 (Medium) | 7 features | 20 weeks | 2 engineers | 10 weeks |

**Recommended Phasing:**
- **Q1 2027:** P0 features (foundation)
- **Q2 2027:** P1 features (differentiation)
- **H2 2027:** P2 features (based on user feedback)

---

## USER VALUE × DEMAND MATRIX

**High Value × High Demand (Do First):**
- SMS Auto-Capture (5×5)
- Tax Dashboard (5×5)
- EPF Tracker (5×5)
- Bill Reminders (5×5)
- EMI Dashboard (5×5)
- Goal Templates (5×5)
- MF Portfolio (5×5)
- Capital Gains Tax (5×5)
- Insurance Tracker (5×5)
- PPF/NPS Dashboard (5×5)
- ML Categorization (5×5)

**High Value × Medium Demand (Strategic):**
- Zero-Based Budgeting (4×4)
- Auto-Savings Rules (5×4)
- Gold Tracker (4×4)
- Credit Card Dashboard (5×4)
- Proactive AI (5×4)

**Medium Value × High Demand (Quick Wins):**
- Indian Categories (4×5)
- Multi-Income (4×4)
- Shared Expenses (4×4)

---

## COMPETITIVE POSITIONING POST-IMPLEMENTATION

**After P0 (Foundation):**
- ✅ Match ET Money (tax, MF, EPF)
- ✅ Match CRED (bill reminders, credit cards)
- ✅ Match Walnut (SMS capture, categorization)
- ⚠️ Still behind INDmoney (bank sync, broker integration)

**After P1 (Differentiation):**
- ✅ Lead on: Multi-user, self-hosted, AI coaching
- ✅ Lead on: Gold tracking (unique)
- ✅ Competitive on: All core features
- ⚠️ Still behind on: Account Aggregator (requires partnership)

**Securo's Moat:**
- Privacy (self-hosted)
- Family collaboration (multi-user workspaces)
- Open-source (community trust)
- AI with tool-use (can query your own data)

---

## NEXT STEPS

1. **Stakeholder Approval:** Review this priority list, adjust based on business goals
2. **User Research:** Validate top 5 P0 features with 20 target users
3. **Technical Spike:** SMS parser POC (1 week)
4. **Roadmap Lock:** Finalize Q1 2027 scope
5. **Team Allocation:** 3 engineers × 3 months for P0

**Decision Point:** Do we build SMS parser in-house or license (e.g., Perfios, FinBox)?

---

**Document Status:** Ready for stakeholder review
**Owner:** Product team
**Last Updated:** 2026-09-16
