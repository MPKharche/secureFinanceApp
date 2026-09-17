# 4 High-Priority Features - Complete Implementation Plan

**Date:** September 17, 2026  
**Branch:** feature/mf-portfolio  
**Goal:** Complete all 4 P0 features with passing tests

---

## Current Status Assessment

### Feature 1: EMI Dashboard (P0) - 95% Complete ✅
**Status:** Code complete, deployment blocked by DB auth  
**Backend:** ✅ Complete (services, APIs, tests)  
**Frontend:** ✅ Complete (7 components, route)  
**Tests:** ✅ Unit tests written  
**Blocker:** Database authentication error (infrastructure issue)

**Remaining Work:**
- Fix DB connection issue
- Run integration tests
- Manual verification

---

### Feature 2: SMS Auto-Capture (P0) - 60% Complete 🟡
**Status:** Models done, service layer incomplete  
**Backend:** 
- ✅ Models (SMSLog, SMSReviewQueue, MerchantMapping)
- ✅ Parser skeleton (backend/app/services/sms_parser.py)
- ❌ API endpoints incomplete
- ❌ Celery task not implemented
- ❌ LLM integration incomplete

**Frontend:**
- ❌ Review queue page missing
- ❌ Settings/status page missing

**Tests:**
- ⚠️ Some tests exist, need completion

**Remaining Work:**
- Complete SMS parser with LLM integration
- Implement API endpoints
- Build review queue UI
- Integration tests

---

### Feature 3: Tax Dashboard (P0) - 85% Complete 🟢
**Status:** Backend complete, frontend mostly done  
**Backend:**
- ✅ Models (4 tables)
- ✅ Tax engine (dual regime calculation)
- ✅ API endpoints (all 8 endpoints)
- ✅ Service layer complete

**Frontend:**
- ✅ Dashboard view component
- ✅ Planning mode component
- ✅ Settings components
- ⚠️ Integration with API needs verification
- ❌ Testing incomplete

**Tests:**
- ✅ Unit tests for engine (backend/tests/tax/test_engine.py)
- ⚠️ Integration tests need environment

**Remaining Work:**
- Verify frontend-backend integration
- Complete integration tests
- Manual testing

---

### Feature 4: Capital Gains Calculator (P0) - 40% Complete 🟡
**Status:** Engine exists, API and frontend missing  
**Backend:**
- ✅ Capital gains engine (backend/app/tax/capital_gains_engine.py)
- ❌ API endpoints not created
- ❌ Service layer incomplete

**Frontend:**
- ❌ Calculator page missing
- ❌ Results display missing

**Tests:**
- ❌ Tests not created

**Remaining Work:**
- Create API endpoints
- Build calculator UI
- Write tests
- Integration

---

## Implementation Plan - Phase by Phase

### Phase 1: Fix EMI Dashboard Blocker (1 hour)
**Priority:** Critical - unlocks verification

**Tasks:**
1. Investigate DB authentication issue
2. Check docker-compose.yml credentials
3. Restart database and backend containers
4. Verify backend starts successfully
5. Run existing integration tests

**Success Criteria:**
- Backend container running without crashes
- Can connect to database
- API endpoints respond

---

### Phase 2: Complete Tax Dashboard (4 hours)
**Priority:** High - 85% done, closest to completion

**Backend Tasks:**
1. ✅ Already complete - verify only

**Frontend Tasks:**
1. Test tax dashboard page loads
2. Verify income/deduction forms work
3. Test what-if calculator
4. Fix any API integration issues
5. Add error handling

**Testing:**
1. Run unit tests (already exist)
2. Create integration test for full flow
3. Manual testing of UI

**Success Criteria:**
- Dashboard shows projections correctly
- What-if calculator works
- Both regimes calculated accurately
- Tests pass

---

### Phase 3: Complete Capital Gains Calculator (6 hours)
**Priority:** High - leverages existing tax infrastructure

**Backend Tasks:**
1. Create API endpoints in `/api/tax/capital-gains`
   - POST /api/tax/capital-gains/calculate
   - GET /api/tax/capital-gains/summary/{fy}
2. Create service layer methods
3. Wire up capital_gains_engine.py

**Frontend Tasks:**
1. Create calculator page at `/tax/capital-gains`
2. Input form:
   - Asset type (equity/debt/real estate)
   - Purchase date/price
   - Sale date/price
   - Expenses
3. Results display:
   - STCG/LTCG classification
   - Tax liability
   - Net proceeds
4. Add route to navigation

**Testing:**
1. Unit tests for API
2. Integration test for full calculation
3. Manual testing of UI scenarios

**Success Criteria:**
- Calculator page accessible
- Correct STCG/LTCG classification
- Accurate tax calculations
- Tests pass

---

### Phase 4: Complete SMS Auto-Capture (8 hours)
**Priority:** High - most complex remaining work

**Backend Tasks:**
1. Complete SMS parser service:
   - LLM integration (use existing AI agents infrastructure)
   - Bank SMS pattern detection
   - Transaction extraction logic
2. Create API endpoints:
   - POST /api/sms/ingest (receive from Android)
   - GET /api/sms/review-queue
   - POST /api/sms/review-queue/{id}/approve
   - POST /api/sms/review-queue/{id}/reject
3. Implement duplicate detection
4. Merchant mapping logic
5. Create transaction from SMS

**Frontend Tasks:**
1. Review queue page:
   - List pending SMS
   - Show parsed data vs existing transactions
   - Approve/reject buttons
2. SMS status dashboard:
   - Count of processed SMS
   - Success rate
   - Failed parses
3. Merchant category mapping UI

**Testing:**
1. Unit tests for SMS parser
2. Integration tests for full flow
3. Test with sample SMS texts

**Success Criteria:**
- SMS ingestion API works
- Parser extracts amount/merchant/date
- Review queue functional
- Transactions auto-created
- Tests pass

---

### Phase 5: Integration Testing (4 hours)
**Priority:** Critical - ensures everything works together

**Tasks:**
1. Run all integration tests
2. Test cross-feature interactions:
   - SMS creates transaction → Tax projection updates
   - Capital gains → Tax calculation
   - EMI payment → Loan dashboard updates
3. Fix any integration issues
4. Performance testing (ensure < 2s load times)

**Success Criteria:**
- All integration tests pass
- No regressions
- Features work together
- Acceptable performance

---

### Phase 6: Documentation & Finalization (2 hours)

**Tasks:**
1. Update README with new features
2. API documentation
3. User guide (how to use each feature)
4. Known limitations
5. Future enhancements

**Deliverables:**
- Updated README.md
- API_DOCS.md
- USER_GUIDE.md
- KNOWN_ISSUES.md

---

## Execution Timeline

**Total Estimated Time:** 25 hours (~3 working days)

| Phase | Feature | Time | Status |
|-------|---------|------|--------|
| 1 | EMI Dashboard Fix | 1h | Ready |
| 2 | Tax Dashboard | 4h | 85% done |
| 3 | Capital Gains | 6h | 40% done |
| 4 | SMS Auto-Capture | 8h | 60% done |
| 5 | Integration Testing | 4h | Not started |
| 6 | Documentation | 2h | Not started |

---

## Risk Mitigation

### Risk 1: Database Issues Persist
**Mitigation:** 
- Document exact error
- Check PostgreSQL logs
- Recreate database if needed
- Use docker-compose down -v && docker-compose up

### Risk 2: LLM Integration Complexity
**Mitigation:**
- Use existing AI agents infrastructure
- Start with simple regex patterns as fallback
- Phase 2: Add LLM after basic flow works

### Risk 3: Test Environment Setup
**Mitigation:**
- Use existing test infrastructure
- Fix one test file as template
- Copy working patterns

### Risk 4: Frontend-Backend Mismatch
**Mitigation:**
- Check API contracts carefully
- Use TypeScript types
- Test each endpoint individually

---

## Success Metrics

### Feature Completion
- ✅ All 4 features have working UI
- ✅ All backend APIs functional
- ✅ All integration tests pass
- ✅ Manual testing completed

### Quality
- ✅ Code follows project standards
- ✅ No TypeScript/Python errors
- ✅ Responsive UI (mobile + desktop)
- ✅ Error handling in place

### Documentation
- ✅ API endpoints documented
- ✅ User guide written
- ✅ Known issues listed
- ✅ Future work identified

---

## Next Immediate Actions

1. **Start Phase 1:** Fix EMI Dashboard DB issue (NOW)
2. **Then Phase 2:** Complete Tax Dashboard verification
3. **Then Phase 3:** Build Capital Gains Calculator
4. **Then Phase 4:** Finish SMS Auto-Capture
5. **Then Phase 5:** Integration testing
6. **Finally Phase 6:** Documentation

---

**Last Updated:** September 17, 2026, 7:40 PM  
**Estimated Completion:** September 20, 2026 (3 days)
