# Pending Backlog Features & Implementation Status

**Date:** 2026-09-17  
**Last Updated:** 7:21 PM IST  
**Context:** Post test suite systematic fix completion  

---

## 🎯 Recently Completed Features

### ✅ Test Suite Systematic Fix (JUST COMPLETED)
- All 4 phases complete
- Fixed ~50+ systematic test issues
- 24/24 tax engine tests passing
- Documentation: `TEST_FIXES_SUMMARY.md`

### ✅ Mutual Fund Portfolio (COMPLETE)
- CAS import parsing
- XIRR calculations
- Portfolio tracking
- Status: Code complete, needs deployment
- Documentation: `MF_PORTFOLIO_COMPLETION.md`

### ✅ EPF/PF Tracker (COMPLETE)
- Manual entry support
- Projection calculations
- Status: Deployed
- Documentation: `EPF_IMPLEMENTATION.md`

### ✅ Bill Reminders & Auto-Pay Tracking (COMPLETE)
- Due date reminders
- Payment tracking
- Status: Deployed

### ⚠️ EMI Dashboard (CODE COMPLETE - DEPLOYMENT BLOCKED)
- 100% implemented (backend + frontend)
- 2,030 lines of production-ready code
- **Blocker:** Database authentication issue (unrelated infrastructure problem)
- Status: Waiting for DB connection fix
- Documentation: `DEPLOYMENT_STATUS.md`

---

## 🔥🔥🔥 P0 - CRITICAL PRIORITY (Ship First)

Based on priority feature list analysis, here are the **highest impact** features still pending:

### 1. SMS/Email Auto-Capture (Score: 19/20) 🚀 **TOP PRIORITY**
**Status:** ❌ Not Started  
**Effort:** 6 weeks  
**Impact:** Removes biggest friction (manual entry)

**Why Critical:**
- 90% of Indian transactions trigger SMS
- Competitive necessity (Walnut, ET Money have this)
- Enables ML categorization

**Implementation:**
- Parse SMS from 20+ banks (HDFC, ICICI, SBI, Axis, Kotak, etc.)
- Extract: amount, merchant, account, transaction type
- Handle UPI transactions (GPay, PhonePe, Paytm)
- Parse credit card emails

**Technical Approach:**
- SMS permission handling
- Regex patterns for each bank format
- Background service for continuous monitoring
- Duplicate detection

**Design Spec:** `docs/superpowers/specs/2026-09-17-sms-auto-capture-design.md`

---

### 2. Tax Projection Dashboard (Score: 19/20) 🚀
**Status:** ⚠️ Partially Implemented  
**Effort:** 3 weeks remaining  
**Impact:** Tax planning throughout the year

**What's Done:**
- ✅ Tax calculation engine (working correctly - 24/24 tests pass)
- ✅ Both regime calculations
- ✅ Section 87A rebate logic
- ✅ All deduction calculations (80C, 80D, HRA, etc.)

**What's Pending:**
- ❌ Frontend dashboard UI
- ❌ Month-by-month projection view
- ❌ Tax-saving recommendations
- ❌ What-if calculator interface
- ❌ Auto-detect income from transactions

**Design Spec:** `docs/superpowers/specs/2026-09-17-tax-dashboard-design.md`  
**Implementation Plan:** `docs/superpowers/plans/2026-09-17-tax-dashboard.md`

---

### 3. Capital Gains Tax Calculator (Score: 18/20) 🚀
**Status:** ❌ Not Started  
**Effort:** 2 weeks  
**Impact:** Critical for investors

**Features:**
- STCG/LTCG calculation by asset type
- Equity: 15% STCG (<1 yr), 10% LTCG (>₹1L gains)
- Debt: Slab rate STCG, 20% indexed LTCG
- Real estate: Indexed cost, exemptions (54, 54EC, 54F)
- Tax harvesting suggestions
- Export for ITR filing

**Dependencies:**
- ✅ Stock portfolio tracking (exists)
- ✅ MF portfolio (code complete)
- ❌ Real estate tracker (pending)

---

### 4. ML Transaction Categorization (Score: 18/20) 🚀
**Status:** ❌ Not Started  
**Effort:** 4 weeks  
**Impact:** Pairs with SMS auto-capture

**Features:**
- Auto-categorize using ML model
- Learn from user corrections
- Merchant recognition database
- Recurring transaction detection
- Confidence scores

**Technical Approach:**
- Train on labeled transaction dataset
- Features: merchant name, amount, time, frequency
- Model: Random Forest or lightweight neural network
- Online learning from user feedback

**Dependency:** SMS Auto-Capture must be done first

---

### 5. PPF/NPS Dashboard (Score: 17/20)
**Status:** ❌ Not Started  
**Effort:** 3 weeks  
**Impact:** Retirement planning for Indians

**Features:**
- PPF: Track deposits, interest (7.1%), maturity projection
- NPS: Track Tier-I/II, corpus projection at 60
- Tax benefits calculation (80C for PPF, 80CCD for NPS)
- Compare PPF vs NPS vs ELSS

---

### 6. Insurance Tracker Enhancement (Score: 17.5/20)
**Status:** ⚠️ Basic tracking exists, needs enhancement  
**Effort:** 2 weeks  
**Impact:** Financial safety net

**What's Pending:**
- Coverage gap analysis (life cover = 10-15× annual income)
- Term vs traditional comparison
- Renewal reminders (already have basic bill reminders)
- Claim tracking
- Family members' policies

---

### 7. Goal Templates (India-specific) (Score: 17.5/20)
**Status:** ⚠️ Generic goals exist, need Indian templates  
**Effort:** 1 week  
**Impact:** Quick wins, localization

**Templates to Add:**
- Child education (engineering/medical: ₹20-50L)
- Marriage fund (₹10-30L)
- House down payment (20% of property)
- Car purchase
- Retirement corpus (30× annual expenses)
- Diwali shopping budget
- Vacation fund

---

### 8. Indian Category Presets (Score: 16.5/20)
**Status:** ❌ Not Started  
**Effort:** 1 week (just config data)  
**Impact:** Cultural fit, user trust

**Categories to Add:**
- House help (maid, cook, driver, security)
- Education (school fees, tuition, coaching)
- Gold purchases
- Religious/donations (temple, church, dargah)
- Pet care
- Parent support

---

## 🔥🔥 P1 - HIGH PRIORITY (Ship Next)

### 1. Zero-Based Budgeting / Envelope Method (Score: 15/20)
**Status:** ⚠️ Basic budgets exist, need envelope logic  
**Effort:** 3 weeks  
**Impact:** Behavior change for savers

**What's Needed:**
- Create budget envelopes per category
- Fund at start of month
- Real-time balance after each transaction
- Rollover or reset options
- Visual progress bars

**Design Spec:** `docs/superpowers/specs/2026-09-16-budget-spreadsheet-design.md`

---

### 2. Automated Savings Rules (Score: 15.5/20)
**Status:** ❌ Not Started  
**Effort:** 4 weeks  
**Impact:** Painless wealth building

**Features:**
- Round-up savings (₹147 → ₹150, save ₹3)
- Percentage savings (save 10% of salary)
- Fixed recurring transfer
- Milestone-based (save ₹1000 when goal reached)
- Idle cash sweep (move excess to liquid fund)

---

### 3. Stock Portfolio Enhancements (Score: 16/20)
**Status:** ⚠️ Basic tracking exists  
**Effort:** 3 weeks  
**Impact:** Power user feature

**Enhancements Needed:**
- Import from broker (Zerodha, Groww, Upstox CSVs)
- Dividend tracking
- Stock splits/bonus adjustments
- Sector allocation view
- P&L unrealized vs realized
- Tax harvesting suggestions

---

### 4. Credit Card Dashboard (Score: 15.5/20)
**Status:** ⚠️ Cards tracked as accounts, need dashboard  
**Effort:** 3 weeks  
**Impact:** Avoid late fees, maximize rewards

**Features:**
- Multiple credit cards in one view
- Due date calendar
- Credit utilization % (per card and total)
- Payment reminders
- Outstanding balance alerts
- Rewards points tracking (basic)

---

### 5. Multi-Income Source Tracking (Score: 14.5/20)
**Status:** ⚠️ Generic income exists, need categorization  
**Effort:** 2 weeks  
**Impact:** Tax compliance for gig workers

**Features:**
- Separate streams: Salary, Freelance, Rental, Interest, Dividends, Capital Gains
- Month-wise breakdown
- Export for ITR filing

---

### 6. Shared Expense Splitting (Score: 14/20)
**Status:** ❌ Not Started  
**Effort:** 3 weeks  
**Impact:** Family transparency

**Features:**
- Create expense groups (family, roommates, trip)
- Split equally or custom %
- Track who owes whom
- Settle-up reminders
- Export settlement summary

---

### 7. Gold Tracker (Score: 15/20)
**Status:** ❌ Not Started  
**Effort:** 3 weeks  
**Impact:** Cultural relevance for India

**Features:**
- Track physical gold (jewelry, bars, coins)
- Digital gold (Paytm, PhonePe, Tanishq)
- Sovereign Gold Bonds
- Gold ETFs
- Current market value (live gold price)
- Purity tracking (22K, 24K)

---

### 8. Form 12BB Helper (Score: 14/20)
**Status:** ❌ Not Started  
**Effort:** 2 weeks  
**Impact:** Simplify tax declaration for employees

**Features:**
- Pre-fill 12BB form from tracked investments
- 80C: EPF, PPF, ELSS, insurance premiums
- 80D: Health insurance
- HRA: Rent receipts
- Home loan: Principal (80C), interest (24B)
- Export PDF for employer submission

---

### 9. Credit Score Monitoring (Score: 14.5/20)
**Status:** ❌ Not Started  
**Effort:** 2 weeks (API integration)  
**Impact:** Credit health visibility

**Features:**
- Fetch CIBIL/Experian score (via CRED or direct API)
- Score history tracking
- Factors affecting score
- Improvement tips
- Alert on significant changes

**Technical:** Requires partnership or API integration

---

### 10. Net Worth Enhancements (Score: 16/20)
**Status:** ⚠️ Basic net worth exists  
**Effort:** 2 weeks  
**Impact:** Wealth tracking

**Enhancements:**
- Historical trend (monthly snapshots)
- Asset allocation pie chart
- Liability breakdown
- Net worth growth rate
- Compare to goals

---

### 11. Tax Reports Export (Score: 15/20)
**Status:** ❌ Not Started  
**Effort:** 2 weeks  
**Impact:** Tax filing ease

**Features:**
- Capital gains statement (STCG, LTCG by asset)
- TDS summary
- 80C deductions summary
- Interest income summary
- Rental income statement
- Export: Excel, PDF, ITR JSON (for Cleartax)

---

### 12. Proactive AI Assistant (Score: 16/20)
**Status:** ⚠️ AI Agents exist, need proactive mode  
**Effort:** 4 weeks  
**Impact:** Differentiator

**What's Pending:**
- Proactive suggestions:
  - "₹50K idle in savings. Invest in liquid fund?"
  - "Car insurance expires in 30 days. Renew?"
  - "Save ₹20K tax by investing ₹50K more in 80C"
- Voice commands (Hindi + English)
- Scheduled insights (weekly financial summary)

---

### 13. Session Management & Device Tracking (Score: 14/20)
**Status:** ❌ Not Started  
**Effort:** 2 weeks  
**Impact:** Security hygiene

**Features:**
- Active sessions list (device, location, last active)
- Log out from all devices
- Session timeout (15 min inactivity)
- Login alerts (new device email)

---

## 🔥 P2 - MEDIUM PRIORITY (Future)

### Nice-to-Have Features (6-12 months):
1. **ESOP/RSU Tracker** (11/20) - 4 weeks
2. **Receipt OCR** (10.5/20) - 4 weeks
3. **Spending Pace Indicator** (12/20) - 2 weeks
4. **Real Estate Tracker** (11.5/20) - 4 weeks
5. **Health Insurance Claim Tracker** (11/20) - 2 weeks
6. **Cash Flow Sankey Diagram** (13/20) - 2 weeks
7. **Privacy Controls** (12/20) - 3 weeks

---

## 🚧 Infrastructure & Technical Debt

### 1. Database Authentication Issue (BLOCKER)
**Status:** ❌ Blocking EMI Dashboard deployment  
**Impact:** Production deployment halted  
**Issue:** `asyncpg.exceptions.InvalidPasswordError`  
**Next Step:** Investigate DB credentials and connection config

### 2. Integration Tests with PostgreSQL
**Status:** ⚠️ Can't run in backend container  
**Issue:** Testcontainers needs Docker access  
**Solution:** Run from host or CI with Docker-in-Docker  
**Impact:** Development workflow friction

### 3. Deprecation Warnings
**Status:** ⚠️ Low priority, not blocking  
**Items:**
- Pydantic v2 migration (Field example → json_schema_extra)
- FastAPI regex → pattern
- Class-based config → ConfigDict

### 4. Test Coverage Gaps
**Status:** ⚠️ Some scattered test failures remain  
**Next Step:** Run full test suite and categorize remaining issues

---

## 📊 Implementation Roadmap Summary

### Q4 2026 (Next 3 months)
**Focus:** P0 Critical Features - Foundation for Indian Market

**Sprint 1-2 (6 weeks):**
1. ✅ **Week 1:** Deploy EMI Dashboard (once DB fixed)
2. 🚀 **Week 2-7:** SMS/Email Auto-Capture (TOP PRIORITY)
   - Week 2-3: SMS permission + parser for 5 major banks
   - Week 4-5: ML categorization model
   - Week 6: UPI detection + email parser
   - Week 7: Expand to 20+ banks, refinement

**Sprint 3-4 (6 weeks):**
3. 🚀 **Week 8-10:** Tax Projection Dashboard (frontend)
4. 🚀 **Week 11-12:** Capital Gains Tax Calculator
5. ✅ **Week 13:** Indian Category Presets (quick win)
6. ✅ **Week 13:** Goal Templates (quick win)

**Sprint 5-6 (6 weeks):**
7. 🚀 **Week 14-17:** ML Transaction Categorization
8. 🚀 **Week 18-20:** PPF/NPS Dashboard
9. ✅ **Week 21-22:** Insurance Tracker Enhancement

**Total:** ~22 weeks (5.5 months) for top 9 P0 features

### Q1 2027 (Next 3 months)
**Focus:** P1 High Priority - Differentiation Features

1. Zero-Based Budgeting (3 weeks)
2. Automated Savings Rules (4 weeks)
3. Stock Portfolio Enhancements (3 weeks)
4. Credit Card Dashboard (3 weeks)
5. Gold Tracker (3 weeks)
6. Form 12BB Helper (2 weeks)
7. Tax Reports Export (2 weeks)
8. Proactive AI Assistant (4 weeks)

**Total:** ~24 weeks (6 months) for 8 P1 features

### Q2-Q3 2027
**Focus:** P2 Medium Priority - Power User Features

Based on user feedback and demand

---

## 🎯 Quick Wins (High Impact, Low Effort)

Do these **first** in next sprint:

1. ✅ **Indian Category Presets** (1 week, Score: 16.5/20)
   - Just config data, immediate cultural fit
   
2. ✅ **Goal Templates** (1 week, Score: 17.5/20)
   - Pre-defined templates for Indian use cases
   
3. ✅ **Deploy EMI Dashboard** (once DB fixed)
   - 100% code complete, just needs deployment

4. 🚀 **Tax Dashboard Frontend** (3 weeks, Score: 19/20)
   - Backend engine is perfect, just need UI

---

## 🚨 Blockers & Dependencies

### Immediate Blockers:
1. **Database authentication issue** - Blocking EMI Dashboard deployment
2. **Integration test environment** - Can't run PostgreSQL tests in container

### Feature Dependencies:
- **ML Categorization** depends on → SMS Auto-Capture (must build SMS first)
- **Capital Gains Tax** depends on → Stock/MF portfolio (✅ done)
- **Tax Reports Export** depends on → Tax Dashboard (partially done)
- **Credit Score** depends on → API partnership (business decision)

### Partnership/Regulatory:
- **Account Aggregator** - Requires RBI approval, bank partnerships
- **Broker Sync** - Requires Zerodha/Groww API access
- **Credit Score** - Requires CIBIL/Experian/CRED partnership

---

## 💡 Recommendations

### Immediate (This Week):
1. **Fix database authentication issue** → Unblock EMI Dashboard
2. **Deploy EMI Dashboard** → Validate production deployment
3. **Start SMS Auto-Capture** → Highest impact feature

### Short-term (Next Month):
1. **Indian Category Presets** → Quick win
2. **Goal Templates** → Quick win
3. **Tax Dashboard Frontend** → Complete P0 feature
4. **Capital Gains Calculator** → High demand

### Medium-term (Next Quarter):
1. **Complete all P0 features** → Match ET Money/CRED parity
2. **Focus on ML Categorization** → Differentiation
3. **PPF/NPS Dashboard** → Retirement planning

### Strategic Decisions Needed:
1. **SMS Parser:** Build in-house or license (Perfios, FinBox)?
2. **Credit Score:** Partner with CRED or build direct integration?
3. **Account Aggregator:** Wait for ecosystem maturity or build now?

---

## 📈 Success Metrics

### After P0 Completion:
- ✅ Match ET Money on tax, MF, EPF
- ✅ Match CRED on bill reminders, credit cards
- ✅ Match Walnut on SMS capture, categorization
- ⚠️ Still behind INDmoney on bank sync, broker integration

### After P1 Completion:
- ✅ Lead on multi-user, self-hosted, AI coaching
- ✅ Lead on gold tracking (unique)
- ✅ Competitive on all core features

### Securo's Moat:
- 🔒 Privacy (self-hosted)
- 👨‍👩‍👧‍👦 Family collaboration (multi-user workspaces)
- 🔓 Open-source (community trust)
- 🤖 AI with tool-use (can query your own data)

---

## 📚 Documentation References

- **Priority Feature List:** `docs/superpowers/specs/2026-09-16-priority-feature-list.md`
- **Indian Market Features:** `docs/superpowers/specs/2026-09-16-indian-market-features.md`
- **Test Suite Fix:** `TEST_FIXES_SUMMARY.md`
- **MF Portfolio:** `MF_PORTFOLIO_COMPLETION.md`
- **EMI Dashboard:** `DEPLOYMENT_STATUS.md`
- **Tax Dashboard Design:** `docs/superpowers/specs/2026-09-17-tax-dashboard-design.md`
- **SMS Auto-Capture Design:** `docs/superpowers/specs/2026-09-17-sms-auto-capture-design.md`

---

**Status:** Ready for sprint planning  
**Owner:** Development team  
**Last Updated:** 2026-09-17, 7:21 PM IST
