# SMS Auto-Capture Implementation Plan

**Date:** 2026-09-17  
**Project:** Securo Finance - SMS Auto-Capture  
**Source:** [Design Spec](../specs/2026-09-17-sms-auto-capture-design.md)

---

## Summary

5-week implementation delivering automated SMS transaction capture for Indian banks. Users install Android companion app → bank SMS auto-forwarded to self-hosted Securo → LLM parses → transaction created. Zero manual entry for 90% of transactions.

**Critical Path:** Backend API → Celery processor → Android app → Web review queue  
**Total Effort:** ~160 hours (~4 weeks full-time)

---

## Phase 1: Backend Infrastructure (Week 1-2)

### 1.1 Database Schema
**Tasks:**
- [ ] Create migration: `sms_logs` table with indexes
- [ ] Create migration: `merchant_mappings` table with unique constraints
- [ ] Create migration: `review_queue` table with status indexes
- [ ] Alter `transactions` table: add `source` column + index
- [ ] Add SQLAlchemy models for all new tables
- [ ] Write DB model unit tests (basic CRUD)

**Effort:** 8 hours  
**Dependencies:** None  
**Validation:** Migrations run clean, models load, tests pass

---

### 1.2 API Endpoint (`POST /api/sms/ingest`)
**Tasks:**
- [ ] Create Pydantic schemas: `SMSIngestRequest`, `SMSIngestResponse`
- [ ] Implement `/api/sms/ingest` endpoint with auth (API token)
- [ ] Add idempotency check (sender + body + timestamp)
- [ ] Add rate limiting (100 SMS/min per user via decorator)
- [ ] Create SMS log record in DB
- [ ] Enqueue Celery task `process_sms_task`
- [ ] Write endpoint tests (success, duplicate, auth failure, rate limit)

**Effort:** 10 hours  
**Dependencies:** 1.1 (database schema)  
**Validation:** `curl` test creates SMS log, Celery task enqueued

---

### 1.3 LLM SMS Parser
**Tasks:**
- [ ] Create `sms_parser.py` service module
- [ ] Implement `parse_sms_with_llm()` function
- [ ] Design LLM prompt for Indian bank SMS parsing
- [ ] Integrate with existing AI Agents infrastructure (reuse client)
- [ ] Add JSON validation for LLM response
- [ ] Handle parse failures gracefully (confidence < 0.5)
- [ ] Create test suite with 20+ real SMS samples (HDFC, ICICI, SBI, Axis, UPI)

**Effort:** 12 hours  
**Dependencies:** None (uses existing AI Agents)  
**Validation:** 95%+ accuracy on test SMS corpus

---

### 1.4 Celery Task (SMS Processor)
**Tasks:**
- [ ] Create `sms_processor.py` Celery task module
- [ ] Implement `process_sms_task()` with 5-step flow
- [ ] Add retry logic (3 retries, exponential backoff)
- [ ] Integrate LLM parser (call `parse_sms_with_llm`)
- [ ] Implement confidence check (< 0.5 → review queue)
- [ ] Implement duplicate detection (call `check_duplicate`)
- [ ] Implement category lookup (call `get_category_for_merchant`)
- [ ] Create transaction or add to review queue
- [ ] Add error handling and status updates
- [ ] Write task unit tests (mock LLM, DB)

**Effort:** 16 hours  
**Dependencies:** 1.1, 1.3, 1.5, 1.6  
**Validation:** End-to-end test: mock SMS → transaction created

---

### 1.5 Duplicate Detection
**Tasks:**
- [ ] Create `duplicate_checker.py` service module
- [ ] Implement `check_duplicate()` strict matching logic
- [ ] Query: same amount + same day + same account
- [ ] Handle edge cases (multiple matches, missing account)
- [ ] Write unit tests (10+ scenarios: exact match, near-miss, no match)

**Effort:** 6 hours  
**Dependencies:** 1.1 (database schema)  
**Validation:** Test coverage >90%, edge cases handled

---

### 1.6 Category Learning System
**Tasks:**
- [ ] Create `category_learning.py` service module
- [ ] Implement merchant name normalization (lowercase, strip special chars)
- [ ] Implement `get_category_for_merchant()` lookup
- [ ] Implement `learn_merchant_category()` upsert logic
- [ ] Update usage stats (transaction count, last used timestamp)
- [ ] Write unit tests (new merchant, existing merchant, updates)

**Effort:** 8 hours  
**Dependencies:** 1.1 (database schema)  
**Validation:** Merchant learning persists, lookups return correct category

---

### 1.7 Review Queue Logic
**Tasks:**
- [ ] Create `review_queue.py` service module
- [ ] Implement `add_to_review_queue()` for all 4 types
- [ ] Create API endpoint `GET /api/sms/review-queue` (list pending)
- [ ] Create API endpoint `POST /api/sms/review/{id}/approve`
- [ ] Create API endpoint `POST /api/sms/review/{id}/reject`
- [ ] Create API endpoint `POST /api/sms/review/{id}/merge` (duplicates)
- [ ] Add review action handlers (approve → learn category, merge → delete duplicate)
- [ ] Write API tests for review workflows

**Effort:** 10 hours  
**Dependencies:** 1.1, 1.6  
**Validation:** Full review flow works end-to-end

---

### 1.8 Notification System
**Tasks:**
- [ ] Add notification helpers for failures, duplicates, new merchants
- [ ] Integrate with existing notification system (email/push)
- [ ] Make notifications configurable per user (settings table)
- [ ] Write notification tests

**Effort:** 4 hours  
**Dependencies:** 1.4 (Celery task)  
**Validation:** Notifications sent on failures, duplicates

---

**Phase 1 Total:** 74 hours (~2 weeks)

---

## Phase 2: Android App (Week 3)

### 2.1 Project Setup
**Tasks:**
- [ ] Create Android Studio project (Kotlin, min SDK 24)
- [ ] Add dependencies: WorkManager, Retrofit, kotlinx-serialization
- [ ] Set up project structure (package layout)
- [ ] Configure ProGuard rules
- [ ] Add app icon and branding

**Effort:** 3 hours  
**Dependencies:** None  
**Validation:** App builds and runs

---

### 2.2 SMS Receiver (Background Service)
**Tasks:**
- [ ] Create `SMSReceiver.kt` BroadcastReceiver
- [ ] Implement SMS broadcast listener (`SMS_RECEIVED_ACTION`)
- [ ] Add bank sender filter (20+ Indian banks + UPI apps)
- [ ] Parse SMS message (sender, body, timestamp)
- [ ] Call API client to forward SMS
- [ ] Add logging for debugging
- [ ] Test on real device with SMS

**Effort:** 8 hours  
**Dependencies:** None  
**Validation:** Receives SMS, filters banks correctly

---

### 2.3 API Client (WorkManager)
**Tasks:**
- [ ] Create `SecuroAPIClient.kt` with Retrofit
- [ ] Implement `sendSMS()` method (POST to `/api/sms/ingest`)
- [ ] Add auth header (Bearer token)
- [ ] Create `SMSUploadWorker` for WorkManager
- [ ] Add offline queue with retry logic (exponential backoff)
- [ ] Add network constraints (connected network required)
- [ ] Handle HTTP errors (401, 429, 500)
- [ ] Write unit tests (mock server)

**Effort:** 10 hours  
**Dependencies:** 2.1, Backend 1.2  
**Validation:** SMS uploaded successfully, retries on failure

---

### 2.4 Setup & Settings Screen
**Tasks:**
- [ ] Create `SetupActivity.kt` (server URL + API token input)
- [ ] Add HTTPS validation (reject HTTP)
- [ ] Implement connection test ("Test Connection" button)
- [ ] Save settings to encrypted SharedPreferences
- [ ] Create `SettingsActivity.kt` (edit server, view stats)
- [ ] Add SMS permission requests (READ_SMS, RECEIVE_SMS)
- [ ] Handle permission denial gracefully
- [ ] Design simple UI (Material Design 3)

**Effort:** 10 hours  
**Dependencies:** 2.3  
**Validation:** User can configure app, permissions requested

---

### 2.5 Status Screen & Notifications
**Tasks:**
- [ ] Create `StatusActivity.kt` (main screen)
- [ ] Show stats: SMS captured (30d), last sync time
- [ ] Add persistent notification ("SMS Reader active")
- [ ] Add foreground service for Android 8+ compatibility
- [ ] Implement battery optimization handling
- [ ] Add "Pause/Resume" toggle
- [ ] Design UI (clean, minimal)

**Effort:** 6 hours  
**Dependencies:** 2.2, 2.3  
**Validation:** Status updates correctly, notification visible

---

### 2.6 Testing & Polish
**Tasks:**
- [ ] Test on 5+ Android devices (different versions)
- [ ] Test offline queue (airplane mode → reconnect)
- [ ] Test battery usage (24-hour monitoring)
- [ ] Fix bugs from device testing
- [ ] Add ProGuard rules for release build
- [ ] Generate signed APK
- [ ] Write user documentation (setup guide)

**Effort:** 8 hours  
**Dependencies:** 2.2, 2.3, 2.4, 2.5  
**Validation:** App stable on all test devices

---

**Phase 2 Total:** 45 hours (~1 week)

---

## Phase 3: Frontend (Week 4)

### 3.1 Review Queue Page
**Tasks:**
- [ ] Create `SMSReviewPage.tsx` component
- [ ] Add React Query hooks for review queue API
- [ ] Create `ReviewCard.tsx` component (4 types: duplicate, uncategorized, failed, low confidence)
- [ ] Implement duplicate comparison UI (side-by-side cards)
- [ ] Add category dropdown for uncategorized merchants
- [ ] Add "Approve", "Reject", "Merge" action buttons
- [ ] Add optimistic updates for smooth UX
- [ ] Handle API errors gracefully
- [ ] Add empty state ("All caught up!")
- [ ] Write component tests (React Testing Library)

**Effort:** 12 hours  
**Dependencies:** Backend 1.7  
**Validation:** Review workflow works end-to-end

---

### 3.2 Settings Page
**Tasks:**
- [ ] Create `SMSSettingsPage.tsx` component
- [ ] Add API token generation endpoint (backend)
- [ ] Show generated token with copy-to-clipboard button
- [ ] Add Android app download link (GitHub releases)
- [ ] Display setup instructions (step-by-step)
- [ ] Show SMS capture stats dashboard (30d summary)
- [ ] Add "Test SMS" button (trigger test parse)
- [ ] Add notification preferences (enable/disable)
- [ ] Write component tests

**Effort:** 8 hours  
**Dependencies:** Backend 1.2, 1.7  
**Validation:** Token generation works, instructions clear

---

### 3.3 Notification System Integration
**Tasks:**
- [ ] Add toast notifications for review queue updates
- [ ] Implement real-time updates (WebSocket or polling)
- [ ] Add notification badge on nav menu (pending review count)
- [ ] Test notification delivery

**Effort:** 4 hours  
**Dependencies:** 3.1, Backend 1.8  
**Validation:** Notifications appear when SMS processed

---

### 3.4 Mobile Responsive Design
**Tasks:**
- [ ] Ensure review queue works on mobile viewport
- [ ] Test on iOS Safari, Chrome Android
- [ ] Optimize for touch interactions
- [ ] Fix any layout issues

**Effort:** 3 hours  
**Dependencies:** 3.1, 3.2  
**Validation:** UI usable on mobile

---

**Phase 3 Total:** 27 hours (~0.75 week)

---

## Phase 4: Testing & Quality (Week 5)

### 4.1 Integration Testing
**Tasks:**
- [ ] End-to-end test: Android app → backend → transaction created
- [ ] Test duplicate detection flow (manual txn + SMS)
- [ ] Test category learning flow (new merchant → review → future auto-categorized)
- [ ] Test retry logic (simulate LLM timeout, network failure)
- [ ] Test idempotency (same SMS sent twice)
- [ ] Load test: 100 SMS in 1 minute (rate limit)
- [ ] Fix bugs found during testing

**Effort:** 10 hours  
**Dependencies:** All previous phases  
**Validation:** All critical paths work, no regressions

---

### 4.2 LLM Parser Accuracy Validation
**Tasks:**
- [ ] Collect 50+ real SMS samples from beta users
- [ ] Run parser on all samples, measure accuracy
- [ ] Fix parser prompt for common failures
- [ ] Re-test until >95% accuracy
- [ ] Document known limitations (unsupported SMS formats)

**Effort:** 8 hours  
**Dependencies:** Backend 1.3  
**Validation:** Parser accuracy >95%

---

### 4.3 Security Audit
**Tasks:**
- [ ] Review API auth (token validation)
- [ ] Test rate limiting (brute force protection)
- [ ] Verify HTTPS enforcement (reject HTTP)
- [ ] Check for SQL injection vectors
- [ ] Verify SMS data privacy (no leaks in logs)
- [ ] Test Android app permissions (only SMS)
- [ ] Fix security issues found

**Effort:** 6 hours  
**Dependencies:** All previous phases  
**Validation:** No critical security issues

---

### 4.4 Performance Optimization
**Tasks:**
- [ ] Profile Celery task performance (target <5s per SMS)
- [ ] Optimize LLM prompt (reduce token usage)
- [ ] Add DB query indexes if needed
- [ ] Test with high SMS volume (500 SMS/day per user)
- [ ] Monitor memory usage (Android app)

**Effort:** 5 hours  
**Dependencies:** Backend complete  
**Validation:** Performance meets SLAs

---

### 4.5 Documentation
**Tasks:**
- [ ] User guide: Android app setup (screenshots)
- [ ] User guide: Review queue workflow
- [ ] User guide: Merchant category training
- [ ] Developer docs: SMS parser customization
- [ ] Admin guide: Monitoring & troubleshooting
- [ ] Create video tutorial (5-minute walkthrough)

**Effort:** 6 hours  
**Dependencies:** All features complete  
**Validation:** Docs reviewed, video recorded

---

**Phase 4 Total:** 35 hours (~1 week)

---

## Summary

### Effort Breakdown
| Phase | Effort | Duration |
|-------|--------|----------|
| Phase 1: Backend Infrastructure | 74 hours | 2 weeks |
| Phase 2: Android App | 45 hours | 1 week |
| Phase 3: Frontend | 27 hours | 0.75 week |
| Phase 4: Testing & Quality | 35 hours | 1 week |
| **Total** | **181 hours** | **~4.75 weeks** |

### Critical Path
```
Backend Schema (1.1)
    ↓
Backend API (1.2) → LLM Parser (1.3)
    ↓                    ↓
Celery Processor (1.4) ← Duplicate Detection (1.5) + Category Learning (1.6)
    ↓
Review Queue Logic (1.7)
    ↓
Android App (Phase 2) ← can start in parallel after 1.2
    ↓
Frontend (Phase 3)
    ↓
Integration Testing (Phase 4)
```

### Risk Mitigation
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM parser accuracy <95% | High | Test with 50+ real SMS, iterate prompt |
| Duplicate detection false positives | Medium | Start strict, add fuzzy matching in Phase 2 |
| Android battery drain | High | Use WorkManager, test 24h battery usage |
| Rate limit too restrictive | Low | Make configurable, monitor in production |
| iOS users left out | Medium | Communicate Android-first, iOS in roadmap |

### Success Criteria
- ✅ Backend API handles 100 SMS/min
- ✅ LLM parser >95% accuracy
- ✅ Android app <5% battery usage over 24h
- ✅ Duplicate detection >90% caught, <5% false positives
- ✅ Review queue cleared within 24h (80% of users)
- ✅ Zero critical security issues

---

## Next Steps

1. **Kick-off:** Review plan with team, assign owners
2. **Sprint 1 (Week 1-2):** Backend infrastructure
3. **Sprint 2 (Week 3):** Android app
4. **Sprint 3 (Week 4):** Frontend UI
5. **Sprint 4 (Week 5):** Testing & launch prep
6. **Launch:** Gradual rollout with feature flag

---

**Plan Status:** ✅ Ready for implementation  
**Estimated Launch:** Week 7 (including buffer)
