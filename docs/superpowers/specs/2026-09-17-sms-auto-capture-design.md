# SMS Auto-Capture System Design

**Date:** 2026-09-17  
**Priority:** P0 (Critical)  
**Score:** 19/20  
**Status:** Design Approved

---

## Overview

Automated SMS and transaction capture system for Indian banks. Removes the biggest friction in expense tracking (90% of Indian transactions trigger SMS). Users receive bank SMS → Android app forwards to backend → LLM parses → transaction auto-created.

### User Value

- **Zero manual entry:** SMS arrives → transaction appears in Securo automatically
- **Privacy-first:** Self-hosted, all processing on user's server
- **Smart learning:** System learns merchant categorization from user behavior
- **Duplicate detection:** Prevents double-entry when manual + SMS both exist

### Scope

**In Scope:**
- SMS parsing for 20+ Indian banks (HDFC, ICICI, SBI, Axis, Kotak, etc.)
- UPI transaction detection (GPay, PhonePe, Paytm)
- LLM-based parser (handles any format, no regex maintenance)
- User-driven category learning (merchant → category mapping)
- Strict duplicate detection (same amount + same day + same account)
- Review queue (duplicates, uncategorized merchants, failed parses)
- Android companion app (SMS reader only)

**Out of Scope (Phase 2):**
- Email parsing (credit card statements)
- iOS app (Android only for MVP)
- Real-time notifications (only for failures/duplicates)
- Fuzzy duplicate matching (strict only)
- Shared ML model across users (privacy conflict)

---

## Architecture Overview

### System Components

```
┌─────────────────┐
│  Android App    │  Kotlin, minimal companion
│  SMS Reader     │  - Background service monitors SMS
└────────┬────────┘  - Filters bank SMS (sender ID)
         │ HTTPS      - Sends to user's Securo server
         ▼
┌─────────────────────────────────────────────────┐
│         Securo Backend (User's Server)          │
│  ┌──────────────────────────────────────────┐  │
│  │  FastAPI Endpoint                        │  │
│  │  POST /api/sms/ingest                    │  │
│  │  - Validates request (auth token)        │  │
│  │  - Checks idempotency                    │  │
│  │  - Enqueues to Celery                    │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  Celery Worker (Async Processing)       │  │
│  │  1. Call LLM parser                      │  │
│  │  2. Extract: amount, merchant, date      │  │
│  │  3. Duplicate check (strict)             │  │
│  │  4. Get/learn category                   │  │
│  │  5. Create transaction or review queue   │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐  │
│  │  AI Agents / LLM Infrastructure          │  │
│  │  (Existing - reuse!)                     │  │
│  │  - Prompt: parse SMS                     │  │
│  │  - Returns JSON: {amount, merchant, ...} │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  PostgreSQL Database                     │  │
│  │  - transactions (existing)               │  │
│  │  - sms_logs (new)                        │  │
│  │  - merchant_mappings (new)               │  │
│  │  - review_queue (new)                    │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         │ Push Notification (failures only)
         ▼
┌─────────────────┐
│   Web UI        │  Review queue page
│   (React)       │  Merchant category mapping
└─────────────────┘  Settings/status dashboard
```

### Key Design Decisions

1. **LLM-based parser** (not regex) - handles format changes gracefully, no pattern maintenance
2. **User-driven category learning** (not shared ML) - preserves privacy, 100% accuracy after training
3. **Strict duplicate detection** (not fuzzy) - zero false positives, user confirms ambiguous cases
4. **Fully automated** (silent) - transactions auto-created, only notify for failures/duplicates
5. **Android-first** (iOS later) - 95%+ of Indian mass market uses Android

---

## Data Model

### New Tables

#### 1. SMS Logs Table

Stores raw SMS for debugging and reprocessing.

```sql
CREATE TABLE sms_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  
  -- SMS metadata
  sender TEXT NOT NULL,              -- e.g., "HDFCBK", "ICICIB"
  body TEXT NOT NULL,                -- Raw SMS text
  received_at TIMESTAMP WITH TIME ZONE NOT NULL,
  device_id TEXT,                    -- Android device identifier
  
  -- Processing status
  status VARCHAR(20) NOT NULL,       -- 'pending', 'processed', 'failed', 'duplicate', 'ignored'
  processed_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  
  -- Parsed data (JSON)
  parsed_data JSONB,                 -- LLM output: {amount, merchant, account, date, confidence}
  
  -- Link to created transaction (if any)
  transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sms_logs_user_status ON sms_logs(user_id, status);
CREATE INDEX idx_sms_logs_received ON sms_logs(received_at DESC);
```

**Retention:** 90 days, then archive/delete (privacy + storage optimization)

---

#### 2. Merchant Mappings Table

User's learned merchant → category mappings.

```sql
CREATE TABLE merchant_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  
  -- Merchant info
  merchant_name TEXT NOT NULL,       -- e.g., "SWIGGY", "AMAZON", "BPCL"
  merchant_normalized TEXT NOT NULL, -- Lowercase, no special chars
  
  -- Category mapping
  category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  
  -- Learning metadata
  transaction_count INT DEFAULT 1,   -- How many times user confirmed this mapping
  confidence DECIMAL(3,2) DEFAULT 1.0, -- 0.0 to 1.0
  last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(user_id, merchant_normalized)
);

CREATE INDEX idx_merchant_mappings_user ON merchant_mappings(user_id);
CREATE INDEX idx_merchant_mappings_lookup ON merchant_mappings(user_id, merchant_normalized);
```

**Retention:** Keep forever (user's learned knowledge)

---

#### 3. Review Queue Table

Transactions needing user confirmation.

```sql
CREATE TABLE review_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  
  -- What needs review
  type VARCHAR(20) NOT NULL,         -- 'duplicate', 'low_confidence', 'failed_parse', 'uncategorized'
  
  -- Transaction details
  sms_log_id UUID REFERENCES sms_logs(id) ON DELETE CASCADE,
  transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
  
  -- For duplicates: link to potential match
  potential_duplicate_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
  
  -- Review status
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'merged'
  reviewed_at TIMESTAMP WITH TIME ZONE,
  
  -- Metadata
  metadata JSONB,                    -- Additional context for review
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_review_queue_user_status ON review_queue(user_id, status);
CREATE INDEX idx_review_queue_created ON review_queue(created_at DESC);
```

**Retention:** Delete after reviewed, or 30 days if ignored

---

#### 4. Extend Transactions Table

Add one column to track source.

```sql
ALTER TABLE transactions 
  ADD COLUMN source VARCHAR(20) DEFAULT 'manual';
  
-- Values: 'manual', 'sms', 'email', 'csv', 'bank_sync'
-- Helps with duplicate detection and debugging

CREATE INDEX idx_transactions_source ON transactions(user_id, source);
```

---

## Backend Implementation

### API Endpoint

```python
# backend/app/api/sms.py

@router.post("/api/sms/ingest")
async def ingest_sms(
    request: SMSIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SMSIngestResponse:
    """
    Receive SMS from Android app, enqueue for processing.
    
    Rate limit: 100 SMS/minute per user
    Auth: Requires valid API token
    """
    
    # Validate request
    if not request.sender or not request.body:
        raise HTTPException(400, "Missing sender or body")
    
    # Check if this SMS was already processed (idempotency)
    existing = await db.execute(
        select(SMSLog).where(
            SMSLog.user_id == current_user.id,
            SMSLog.sender == request.sender,
            SMSLog.body == request.body,
            SMSLog.received_at == request.received_at
        )
    )
    if existing.scalar_one_or_none():
        return SMSIngestResponse(status="duplicate", message="Already processed")
    
    # Create SMS log
    sms_log = SMSLog(
        user_id=current_user.id,
        workspace_id=current_user.default_workspace_id,
        sender=request.sender,
        body=request.body,
        received_at=request.received_at,
        device_id=request.device_id,
        status="pending"
    )
    db.add(sms_log)
    await db.commit()
    await db.refresh(sms_log)
    
    # Enqueue Celery task (async processing)
    process_sms_task.delay(str(sms_log.id))
    
    return SMSIngestResponse(
        status="queued",
        message="SMS queued for processing",
        sms_log_id=sms_log.id
    )
```

**Schemas:**

```python
# backend/app/schemas/sms.py

class SMSIngestRequest(BaseModel):
    sender: str              # e.g., "HDFCBK"
    body: str                # Raw SMS text
    received_at: datetime    # When SMS was received on device
    device_id: Optional[str] # Android device ID

class SMSIngestResponse(BaseModel):
    status: str              # 'queued', 'duplicate', 'error'
    message: str
    sms_log_id: Optional[UUID]
```

---

### Celery Task (SMS Processing)

```python
# backend/app/tasks/sms_processor.py

@celery_app.task(bind=True, max_retries=3)
def process_sms_task(self, sms_log_id: str):
    """
    Process SMS: parse with LLM → create transaction → handle duplicates
    
    Flow:
    1. Parse SMS with LLM
    2. Check confidence (< 0.5 → review queue)
    3. Check duplicates (strict matching)
    4. Get/learn category
    5. Create transaction (fully automated)
    """
    
    db = get_sync_session()
    sms_log = db.get(SMSLog, sms_log_id)
    
    if not sms_log:
        return {"error": "SMS log not found"}
    
    try:
        # Step 1: Parse SMS with LLM
        parsed_data = parse_sms_with_llm(sms_log.body, sms_log.sender)
        
        # Update SMS log with parsed data
        sms_log.parsed_data = parsed_data
        db.commit()
        
        # Step 2: Check confidence
        if parsed_data.get("confidence", 0) < 0.5:
            add_to_review_queue(
                db, sms_log, 
                type="low_confidence", 
                reason=f"Confidence {parsed_data['confidence']}"
            )
            sms_log.status = "failed"
            db.commit()
            notify_user(sms_log.user_id, "SMS parsing failed", "low_confidence")
            return {"status": "needs_review", "reason": "low_confidence"}
        
        # Step 3: Check for duplicates (strict matching)
        duplicate = check_duplicate(db, sms_log.user_id, parsed_data)
        
        if duplicate:
            add_to_review_queue(
                db, sms_log,
                type="duplicate",
                potential_duplicate_id=duplicate.id
            )
            sms_log.status = "duplicate"
            db.commit()
            notify_user(
                sms_log.user_id,
                "Duplicate transaction detected",
                f"{parsed_data['merchant']} ₹{parsed_data['amount']}"
            )
            return {"status": "duplicate", "duplicate_id": str(duplicate.id)}
        
        # Step 4: Get or learn category
        category = get_category_for_merchant(
            db, sms_log.user_id, parsed_data["merchant"]
        )
        
        if not category:
            # First time seeing this merchant → review queue
            transaction = create_transaction_draft(db, sms_log, parsed_data)
            add_to_review_queue(
                db, sms_log,
                type="uncategorized",
                transaction_id=transaction.id
            )
            sms_log.status = "processed"
            db.commit()
            notify_user(
                sms_log.user_id,
                "New merchant detected",
                f"{parsed_data['merchant']}: Choose category"
            )
            return {"status": "needs_categorization", "transaction_id": str(transaction.id)}
        
        # Step 5: Create transaction (fully automated)
        transaction = Transaction(
            user_id=sms_log.user_id,
            workspace_id=sms_log.workspace_id,
            account_id=get_account_from_number(db, parsed_data["account_number"]),
            category_id=category.id,
            amount=Decimal(str(parsed_data["amount"])),
            description=parsed_data["merchant"],
            transaction_date=parsed_data["date"],
            type="debit" if parsed_data["type"] == "debit" else "credit",
            status="posted",
            source="sms"
        )
        db.add(transaction)
        
        # Link to SMS log
        sms_log.transaction_id = transaction.id
        sms_log.status = "processed"
        db.commit()
        
        return {
            "status": "success",
            "transaction_id": str(transaction.id),
            "amount": float(parsed_data["amount"]),
            "merchant": parsed_data["merchant"]
        }
        
    except Exception as e:
        sms_log.status = "failed"
        sms_log.error_message = str(e)
        db.commit()
        
        # Retry with exponential backoff
        if self.request.retries >= self.max_retries:
            notify_user(
                sms_log.user_id,
                "SMS processing failed",
                f"Could not process SMS from {sms_log.sender}"
            )
        
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

---

### LLM Parser

```python
# backend/app/services/sms_parser.py

def parse_sms_with_llm(sms_body: str, sender: str) -> dict:
    """
    Use existing AI Agents infrastructure to parse SMS.
    
    Returns:
    {
        "amount": 450.00,
        "merchant": "SWIGGY BANGALORE",
        "account_number": "XX1234",
        "date": "2026-09-16T19:35:00",
        "type": "debit",  # or "credit"
        "confidence": 0.95
    }
    """
    
    prompt = f"""
You are a financial SMS parser for Indian banks.

Parse this SMS and extract transaction details:

SMS Sender: {sender}
SMS Body: {sms_body}

Extract:
1. Amount (numeric, without currency symbol)
2. Merchant name (where money was spent/received)
3. Account number (last 4 digits or identifier)
4. Transaction date and time
5. Type: "debit" or "credit"

Return JSON with these fields: amount, merchant, account_number, date (ISO format), type.
Also include "confidence" (0.0 to 1.0) - how confident you are in the parse.

If SMS is not a financial transaction (OTP, marketing, etc.), return {{"confidence": 0.0}}

JSON output only, no explanation:
"""
    
    # Call LLM (reuse existing AI Agents infrastructure)
    response = call_llm(prompt, model="gpt-4o-mini")  # or local Ollama
    
    # Parse JSON response
    try:
        parsed = json.loads(response)
        
        # Validate required fields
        required = ["amount", "merchant", "date", "type", "confidence"]
        if not all(k in parsed for k in required):
            return {"confidence": 0.0, "error": "Missing required fields"}
        
        return parsed
        
    except json.JSONDecodeError:
        return {"confidence": 0.0, "error": "Invalid JSON from LLM"}
```

---

### Duplicate Detection (Strict)

```python
# backend/app/services/duplicate_checker.py

def check_duplicate(db: Session, user_id: UUID, parsed_data: dict) -> Optional[Transaction]:
    """
    Strict duplicate check:
    - Same amount (exact)
    - Same date (same day)
    - Same account (if available)
    
    Returns matching transaction or None.
    """
    
    amount = Decimal(str(parsed_data["amount"]))
    date = parsed_data["date"]
    account_number = parsed_data.get("account_number", "")
    
    # Query transactions from same day
    day_start = date.replace(hour=0, minute=0, second=0)
    day_end = date.replace(hour=23, minute=59, second=59)
    
    result = db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.amount == amount,
            Transaction.transaction_date >= day_start,
            Transaction.transaction_date <= day_end,
            Transaction.status == "posted"
        )
    )
    
    transactions = result.scalars().all()
    
    if not transactions:
        return None
    
    # If account number available, check for exact match
    if account_number:
        for txn in transactions:
            if account_number in txn.account.account_number:
                return txn
    
    # Otherwise return first match (user will review)
    return transactions[0] if transactions else None
```

---

### Category Learning

```python
# backend/app/services/category_learning.py

def get_category_for_merchant(db: Session, user_id: UUID, merchant_name: str) -> Optional[Category]:
    """
    Lookup category for merchant from user's learned mappings.
    Returns None if merchant is new (needs user input).
    """
    
    # Normalize merchant name
    normalized = merchant_name.lower().strip()
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    
    # Lookup in merchant_mappings
    result = db.execute(
        select(MerchantMapping).where(
            MerchantMapping.user_id == user_id,
            MerchantMapping.merchant_normalized == normalized
        )
    )
    
    mapping = result.scalar_one_or_none()
    
    if mapping:
        # Update usage stats
        mapping.transaction_count += 1
        mapping.last_used_at = datetime.utcnow()
        db.commit()
        
        return db.get(Category, mapping.category_id)
    
    return None

def learn_merchant_category(db: Session, user_id: UUID, workspace_id: UUID, merchant_name: str, category_id: UUID):
    """
    Save user's merchant → category mapping.
    Called when user categorizes a new merchant in review queue.
    """
    
    normalized = merchant_name.lower().strip()
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    
    # Upsert merchant mapping
    existing = db.execute(
        select(MerchantMapping).where(
            MerchantMapping.user_id == user_id,
            MerchantMapping.merchant_normalized == normalized
        )
    ).scalar_one_or_none()
    
    if existing:
        existing.category_id = category_id
        existing.transaction_count += 1
        existing.updated_at = datetime.utcnow()
    else:
        mapping = MerchantMapping(
            user_id=user_id,
            workspace_id=workspace_id,
            merchant_name=merchant_name,
            merchant_normalized=normalized,
            category_id=category_id
        )
        db.add(mapping)
    
    db.commit()
```

---

## Android App

### Core Components

**1. SMS Receiver (Background Service)**

```kotlin
// SMSReceiver.kt

@Suppress("DEPRECATION")
class SMSReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            val bundle = intent.extras
            val pdus = bundle?.get("pdus") as Array<*>
            
            for (pdu in pdus) {
                val message = SmsMessage.createFromPdu(pdu as ByteArray)
                val sender = message.originatingAddress ?: ""
                val body = message.messageBody ?: ""
                val timestamp = message.timestampMillis
                
                // Filter: only bank/financial SMS
                if (isBankSMS(sender)) {
                    sendToBackend(context, sender, body, timestamp)
                }
            }
        }
    }
    
    private fun isBankSMS(sender: String): Boolean {
        val bankSenders = listOf(
            "HDFCBK", "ICICIB", "SBIINB", "AXISBK", "KOTAKB",
            "SCBANK", "YESBNK", "INDUSB", "BOIIND", "PNBSMS",
            "UNIONI", "CANBNK", "ICICIC", "HDFCBA",
            // UPI apps
            "GOOGLEPAY", "PHONEPE", "PAYTM", "BHIMUPI"
        )
        return bankSenders.any { sender.contains(it, ignoreCase = true) }
    }
}
```

**2. API Client (WorkManager for reliability)**

```kotlin
// SecuroAPIClient.kt

class SecuroAPIClient(private val context: Context) {
    
    fun sendSMS(sender: String, body: String, timestamp: Long) {
        val prefs = context.getSharedPreferences("securo", Context.MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", "") ?: ""
        val apiToken = prefs.getString("api_token", "") ?: ""
        
        if (serverUrl.isEmpty() || apiToken.isEmpty()) {
            Log.e("Securo", "Not configured")
            return
        }
        
        val deviceId = Settings.Secure.getString(
            context.contentResolver, 
            Settings.Secure.ANDROID_ID
        )
        
        val request = JSONObject().apply {
            put("sender", sender)
            put("body", body)
            put("received_at", Instant.ofEpochMilli(timestamp).toString())
            put("device_id", deviceId)
        }
        
        // Enqueue work (retries with exponential backoff)
        val workRequest = OneTimeWorkRequestBuilder<SMSUploadWorker>()
            .setInputData(workDataOf(
                "url" to "$serverUrl/api/sms/ingest",
                "token" to apiToken,
                "payload" to request.toString()
            ))
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                WorkRequest.MIN_BACKOFF_MILLIS,
                TimeUnit.MILLISECONDS
            )
            .build()
        
        WorkManager.getInstance(context).enqueue(workRequest)
    }
}
```

**3. Setup Screen**

- User inputs: Securo server URL + API token
- Validates HTTPS (rejects HTTP for security)
- Tests connection before saving
- Requests SMS permissions (READ_SMS + RECEIVE_SMS)

**App Features:**
- Minimal UI (setup + status screen only)
- Persistent notification: "Securo SMS Reader active"
- Stats: "1,234 SMS captured this month"
- Battery-friendly (only wakes on SMS broadcast)
- Offline queue (WorkManager retries)

---

## Frontend (Web UI)

### Review Queue Page

```typescript
// frontend/src/pages/sms-review.tsx

export default function SMSReviewPage() {
  const { data: reviewQueue } = useQuery(['review-queue'], () => 
    api.get('/api/sms/review-queue')
  )
  
  return (
    <div>
      <PageHeader title="Transaction Review" />
      
      {reviewQueue?.length === 0 ? (
        <EmptyState 
          icon={CheckCircle}
          title="All caught up!"
          message="No transactions need review"
        />
      ) : (
        <div className="space-y-4">
          {reviewQueue?.map(item => (
            <ReviewCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Review Card Types:**

1. **Duplicate:** Show side-by-side comparison, buttons: "Merge" or "Keep Both"
2. **Uncategorized:** Show transaction preview, category dropdown, "Save" button
3. **Failed Parse:** Show raw SMS, buttons: "Ignore" or "Add Manually"

### Settings Page

- Android app setup instructions
- Generate API token (copy to clipboard)
- Status dashboard: SMS captured (30d), auto-created count, needs review count
- Link to download APK

---

## Security & Privacy

### Authentication
- Android app uses user-specific API token (generated in web UI)
- Token stored securely in Android encrypted SharedPreferences
- HTTPS only (HTTP rejected)

### Rate Limiting
- 100 SMS/minute per user (prevents abuse if device compromised)
- Cloudflare or nginx rate limiting on `/api/sms/ingest`

### Data Privacy
- Self-hosted: all SMS processing on user's server
- No third-party services (except LLM if using OpenAI API)
- SMS logs deleted after 90 days
- User can export/delete all data (GDPR-compliant)

### Permissions
- Android app requests only SMS permissions (no contacts, location, etc.)
- Transparent about what data is sent (raw SMS text + sender)

---

## Testing Strategy

### Unit Tests

**Backend:**
- SMS parser: 50+ real SMS samples from all major banks
- Duplicate detection: edge cases (same amount different day, etc.)
- Merchant normalization: "SWIGGY BANGALORE" vs "SWIGGY" → same
- Category learning: upsert logic, transaction count increment

**Android:**
- SMS filtering: verify only bank SMS forwarded
- API client: mock server responses, verify retry logic

### Integration Tests

- End-to-end: mock SMS → API → Celery → transaction created
- Duplicate flow: create manual transaction, then SMS arrives → review queue
- Retry logic: simulate LLM timeout → verify 3 retries → fail gracefully

### User Acceptance Testing

- **Beta users:** 10 real users with actual bank SMS
- **Track metrics:**
  - Parsing accuracy (goal: >95%)
  - Duplicate detection rate (goal: >90% caught)
  - False positives (goal: <5%)
  - User satisfaction (NPS)

---

## Migration & Rollout

### Phase 1: Infrastructure (Week 1-2)

1. Database migrations (add 3 new tables + alter transactions)
2. Backend API endpoint `/api/sms/ingest`
3. Celery task `process_sms_task`
4. LLM parser function (reuse AI Agents)

### Phase 2: Android App (Week 3-4)

1. Kotlin app: SMS receiver + API client
2. Setup screen + settings persistence
3. WorkManager integration (offline queue)
4. Testing on 5+ Android devices

### Phase 3: Web UI (Week 5)

1. Review queue page (React)
2. Settings page (API token generation)
3. Notification system (for failures)

### Phase 4: Testing & Polish (Week 6)

1. Beta testing with 10 users
2. Fix bugs based on feedback
3. Performance optimization (Celery worker tuning)
4. Documentation (user guide, video tutorial)

### Phase 5: Production Launch (Week 7)

1. Deploy to production
2. Monitor error rates (Sentry, logs)
3. Gradual rollout (feature flag, 10% → 50% → 100%)
4. Announce feature (blog post, email)

---

## Success Metrics

**Adoption:**
- 70% of users install Android app within 30 days
- 80% of transactions auto-captured (vs 0% manual entry before)

**Accuracy:**
- Parsing accuracy: >95% (measured by user corrections in review queue)
- Duplicate detection: >90% caught, <5% false positives

**Engagement:**
- Review queue cleared within 24 hours (80% of users)
- Merchant category learning: 50+ merchants per user in first month

**Business Impact:**
- User retention +20% (less friction = more usage)
- 5-star reviews mentioning "SMS auto-capture"
- NPS improvement +15 points

---

## Future Enhancements (Phase 2+)

1. **Email parsing** (credit card statements) - 3-4 weeks
2. **iOS app** (companion reader) - 6-8 weeks
3. **Fuzzy duplicate detection** (handle time mismatches) - 2 weeks
4. **LLM suggestions for categories** (instead of user-only learning) - 2 weeks
5. **Multi-device support** (multiple Android devices per user) - 2 weeks
6. **Recurring transaction detection** (Netflix every month = subscription) - 3 weeks
7. **Anomaly alerts** (₹15K Swiggy? Unusual!) - 2 weeks

---

## Open Questions

1. **LLM cost:** If using OpenAI API, ~₹5-25/user/month for 500 SMS. Accept cost or push local Ollama?
   - **Decision:** Offer both options in settings (cloud vs local)

2. **Android app distribution:** Google Play (long approval) or direct APK (fast but less trust)?
   - **Decision:** Start with direct APK (GitHub releases), submit to Play Store in parallel

3. **SMS retention:** 90 days enough or keep longer for debugging?
   - **Decision:** 90 days default, user can adjust in settings (30/90/180 days)

4. **Notification frequency:** Only failures, or also success confirmations?
   - **Decision:** Failures only (as designed), but user can enable "success" notifications in settings

---

## Document Status

- ✅ Architecture defined
- ✅ Data model designed
- ✅ Backend API specified
- ✅ Android app scoped
- ✅ Frontend UI planned
- ✅ Testing strategy outlined
- ✅ Migration plan ready

**Next Step:** User review → Writing implementation plan (writing-plans skill)

---

**End of Design Document**
