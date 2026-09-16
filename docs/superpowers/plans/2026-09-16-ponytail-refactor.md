# Ponytail Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove over-engineering identified in ponytail-review: eliminate hardcoded locale maps, deduplicate SQL queries, simplify base64 conversions, and optimize client-side aggregation.

**Architecture:** Replace hardcoded lookup tables with native Intl APIs, extract shared SQL query builders, use stdlib for byte conversions, and shift data shaping from client to backend where appropriate.

**Tech Stack:** Python (SQLAlchemy), TypeScript (React), native browser Intl API, stdlib functions

## Global Constraints

- Maintain backward compatibility with existing API contracts
- All changes must pass existing test suites
- No new dependencies (use stdlib/native APIs only)
- Follow existing code style and conventions
- Prefer smaller, focused commits over large refactors

---

## Task 1: Simplify Base64 URL Encoding (webauthn.ts)

**Files:**
- Modify: `frontend/src/lib/webauthn.ts:95-113`

**Interfaces:**
- Consumes: ArrayBuffer, string (base64url format)
- Produces: `base64urlToArrayBuffer(value: string): ArrayBuffer`, `arrayBufferToBase64url(buffer: ArrayBuffer): string`

- [ ] **Step 1: Write test for base64urlToArrayBuffer**

```typescript
// Add to frontend/src/lib/webauthn.test.ts (create if missing)
import { describe, it, expect } from 'vitest'

describe('base64urlToArrayBuffer', () => {
  it('converts base64url string to ArrayBuffer', () => {
    const input = 'SGVsbG8gV29ybGQ' // "Hello World" in base64url
    const result = base64urlToArrayBuffer(input)
    const decoder = new TextDecoder()
    const text = decoder.decode(result)
    expect(text).toBe('Hello World')
  })

  it('handles padding correctly', () => {
    const input = 'YQ' // "a" in base64url (needs padding)
    const result = base64urlToArrayBuffer(input)
    const decoder = new TextDecoder()
    expect(decoder.decode(result)).toBe('a')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- webauthn.test.ts`
Expected: Test file not found or tests fail (function not yet refactored)

- [ ] **Step 3: Refactor base64urlToArrayBuffer using stdlib**

```typescript
// In frontend/src/lib/webauthn.ts, replace lines 95-103 with:
function base64urlToArrayBuffer(value: string): ArrayBuffer {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  const binary = atob(padded)
  return Uint8Array.from(binary, c => c.charCodeAt(0)).buffer
}
```

- [ ] **Step 4: Write test for arrayBufferToBase64url**

```typescript
// Add to frontend/src/lib/webauthn.test.ts
describe('arrayBufferToBase64url', () => {
  it('converts ArrayBuffer to base64url string', () => {
    const encoder = new TextEncoder()
    const buffer = encoder.encode('Hello World').buffer
    const result = arrayBufferToBase64url(buffer)
    expect(result).toBe('SGVsbG8gV29ybGQ')
  })

  it('removes padding', () => {
    const encoder = new TextEncoder()
    const buffer = encoder.encode('a').buffer
    const result = arrayBufferToBase64url(buffer)
    expect(result).toBe('YQ') // No padding characters
  })
})
```

- [ ] **Step 5: Refactor arrayBufferToBase64url using stdlib**

```typescript
// In frontend/src/lib/webauthn.ts, replace lines 107-113 with:
function arrayBufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  const binary = String.fromCharCode(...bytes)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}
```

- [ ] **Step 6: Run all tests to verify they pass**

Run: `cd frontend && npm test -- webauthn.test.ts`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/webauthn.ts frontend/src/lib/webauthn.test.ts
git commit -m "refactor: simplify base64url conversions using stdlib"
```

---

## Task 2: Use Native Date Formatting (month-utils.ts)

**Files:**
- Modify: `frontend/src/lib/month-utils.ts:10-13`

**Interfaces:**
- Consumes: None
- Produces: `currentMonth(): string` (returns "YYYY-MM" format)

- [ ] **Step 1: Write test for currentMonth**

```typescript
// Add to frontend/src/lib/month-utils.test.ts (create if missing)
import { describe, it, expect } from 'vitest'
import { currentMonth } from './month-utils'

describe('currentMonth', () => {
  it('returns current month in YYYY-MM format', () => {
    const result = currentMonth()
    expect(result).toMatch(/^\d{4}-\d{2}$/)
    
    // Verify it matches actual current month
    const now = new Date()
    const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    expect(result).toBe(expected)
  })
})
```

- [ ] **Step 2: Run test to verify baseline**

Run: `cd frontend && npm test -- month-utils.test.ts`
Expected: PASS (existing implementation works)

- [ ] **Step 3: Refactor currentMonth using native toISOString**

```typescript
// In frontend/src/lib/month-utils.ts, replace lines 10-13 with:
export function currentMonth(): string {
  return new Date().toISOString().slice(0, 7)
}
```

- [ ] **Step 4: Run tests to verify refactored version passes**

Run: `cd frontend && npm test -- month-utils.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/month-utils.ts frontend/src/lib/month-utils.test.ts
git commit -m "refactor: use native toISOString for currentMonth"
```

---

## Task 3: Simplify Local Date String (date-utils.ts)

**Files:**
- Modify: `frontend/src/lib/date-utils.ts:3-5`

**Interfaces:**
- Consumes: Date object (optional)
- Produces: `localDateString(date?: Date): string` (returns "YYYY-MM-DD" format)

- [ ] **Step 1: Write test for localDateString**

```typescript
// Add to frontend/src/lib/date-utils.test.ts
import { localDateString } from './date-utils'

describe('localDateString', () => {
  it('formats date as YYYY-MM-DD', () => {
    const date = new Date('2026-09-16T12:00:00Z')
    const result = localDateString(date)
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('uses current date when no argument provided', () => {
    const result = localDateString()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
```

- [ ] **Step 2: Run existing tests**

Run: `cd frontend && npm test -- date-utils.test.ts`
Expected: Existing tests PASS

- [ ] **Step 3: Refactor localDateString to remove date-fns dependency**

```typescript
// In frontend/src/lib/date-utils.ts, replace lines 1-5 with:
export function localDateString(date = new Date()) {
  return date.toISOString().slice(0, 10)
}
```

- [ ] **Step 4: Run all tests to verify**

Run: `cd frontend && npm test -- date-utils.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/date-utils.ts frontend/src/lib/date-utils.test.ts
git commit -m "refactor: remove date-fns from localDateString, use native toISOString"
```

---

## Task 4: Extract Shared Budget Query Builder (budget_service.py)

**Files:**
- Modify: `backend/app/services/budget_service.py:36-148`
- Test: `backend/tests/test_budget_service.py`

**Interfaces:**
- Consumes: AsyncSession, workspace_id (UUID), month_start (date)
- Produces: `_query_recurring_budgets(session, workspace_id, month_start)` returns SQLAlchemy query

- [ ] **Step 1: Write test for recurring budget query**

```python
# Add to backend/tests/test_budget_service.py
import pytest
from datetime import date
from app.services.budget_service import get_budgets
from app.models.budget import Budget

@pytest.mark.asyncio
async def test_get_budgets_deduplicates_recurring(session, workspace, user, category):
    """Recurring budgets should appear once per month with correct resolution."""
    # Create recurring budget for January
    recurring = Budget(
        user_id=user.id,
        workspace_id=workspace.id,
        category_id=category.id,
        amount=100,
        month=date(2026, 1, 1),
        is_recurring=True
    )
    session.add(recurring)
    
    # Create override for March
    override = Budget(
        user_id=user.id,
        workspace_id=workspace.id,
        category_id=category.id,
        amount=200,
        month=date(2026, 3, 1),
        is_recurring=False
    )
    session.add(override)
    await session.commit()
    
    # Query for March - should return override, not recurring
    result = await get_budgets(session, workspace.id, date(2026, 3, 1))
    
    assert len(result) == 1
    assert result[0].amount == 200
    assert result[0].is_recurring == False
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `cd backend && pytest tests/test_budget_service.py::test_get_budgets_deduplicates_recurring -v`
Expected: PASS (verifies current logic works)

- [ ] **Step 3: Extract shared recurring budget query builder**

```python
# In backend/app/services/budget_service.py, replace lines 36-91 with:

def _query_recurring_budgets(
    workspace_id: uuid.UUID,
    month_start: date
):
    """Build query for effective recurring budgets up to month_start.
    
    Returns a SQLAlchemy query that gets the most recent recurring budget
    per category where month <= month_start.
    """
    max_month_subq = (
        select(
            Budget.category_id,
            func.max(Budget.month).label("max_month"),
        )
        .where(
            Budget.workspace_id == workspace_id,
            Budget.is_recurring == True,  # noqa: E712
            Budget.month <= month_start,
        )
        .group_by(Budget.category_id)
        .subquery()
    )

    return select(Budget).join(
        max_month_subq,
        and_(
            Budget.category_id == max_month_subq.c.category_id,
            Budget.month == max_month_subq.c.max_month,
        ),
    ).where(
        Budget.workspace_id == workspace_id,
        Budget.is_recurring == True,  # noqa: E712
    )


async def _build_budget_map(
    session: AsyncSession, workspace_id: uuid.UUID, month_start: date
) -> dict[str, tuple[Decimal, bool]]:
    """Build a map of category_id -> (amount, is_recurring) for the given month.

    Resolution order:
    1. Month-specific override (is_recurring=false, month=M) takes priority
    2. Most recent recurring default (is_recurring=true, month<=M) as fallback
    """
    budget_map: dict[str, tuple[Decimal, bool]] = {}

    # Query 1: Get effective recurring defaults
    recurring_query = _query_recurring_budgets(workspace_id, month_start)
    recurring_result = await session.execute(recurring_query)
    for b in recurring_result.scalars().all():
        budget_map[str(b.category_id)] = (b.amount, True)

    # Query 2: Month-specific overrides (take priority over recurring)
    overrides_result = await session.execute(
        select(Budget).where(
            Budget.workspace_id == workspace_id,
            Budget.is_recurring == False,  # noqa: E712
            Budget.month == month_start,
        )
    )
    for b in overrides_result.scalars().all():
        budget_map[str(b.category_id)] = (b.amount, False)

    return budget_map
```

- [ ] **Step 4: Refactor get_budgets to use shared query builder**

```python
# In backend/app/services/budget_service.py, replace lines 93-148 with:

async def get_budgets(
    session: AsyncSession, workspace_id: uuid.UUID, month: Optional[date] = None
) -> list[Budget]:
    if not month:
        query = select(Budget).where(Budget.workspace_id == workspace_id)
        result = await session.execute(query.order_by(Budget.month.desc()))
        return list(result.scalars().all())

    month_start = month.replace(day=1)

    # Get month-specific overrides
    overrides_result = await session.execute(
        select(Budget).where(
            Budget.workspace_id == workspace_id,
            Budget.is_recurring == False,  # noqa: E712
            Budget.month == month_start,
        )
    )
    overrides = list(overrides_result.scalars().all())
    override_category_ids = {str(b.category_id) for b in overrides}

    # Get effective recurring defaults using shared builder
    recurring_query = _query_recurring_budgets(workspace_id, month_start)
    recurring_result = await session.execute(recurring_query)
    recurring = [
        b for b in recurring_result.scalars().all()
        if str(b.category_id) not in override_category_ids
    ]

    return sorted(overrides + recurring, key=lambda b: b.month, reverse=True)
```

- [ ] **Step 5: Run all budget service tests**

Run: `cd backend && pytest tests/test_budget_service.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/budget_service.py backend/tests/test_budget_service.py
git commit -m "refactor: extract shared recurring budget query builder"
```

---

## Task 5: Optimize Weekday Labels Generation (date-utils.ts)

**Files:**
- Modify: `frontend/src/lib/date-utils.ts:10-15`

**Interfaces:**
- Consumes: locale (string)
- Produces: `weekdayShortLabels(locale: string): string[]` (7 weekday labels starting Sunday)

- [ ] **Step 1: Write test for weekdayShortLabels**

```typescript
// Add to frontend/src/lib/date-utils.test.ts
describe('weekdayShortLabels', () => {
  it('returns 7 short weekday names starting with Sunday', () => {
    const result = weekdayShortLabels('en-US')
    expect(result).toHaveLength(7)
    expect(result[0]).toMatch(/sun/i)
    expect(result[6]).toMatch(/sat/i)
  })

  it('respects locale', () => {
    const enLabels = weekdayShortLabels('en-US')
    const ptLabels = weekdayShortLabels('pt-BR')
    expect(enLabels).not.toEqual(ptLabels)
  })
})
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `cd frontend && npm test -- date-utils.test.ts`
Expected: Tests PASS

- [ ] **Step 3: Refactor weekdayShortLabels using Intl.DateTimeFormat**

```typescript
// In frontend/src/lib/date-utils.ts, replace lines 10-15 with:
export function weekdayShortLabels(locale: string) {
  const formatter = new Intl.DateTimeFormat(locale, { weekday: 'short', timeZone: 'UTC' })
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(Date.UTC(2024, 0, 7 + index)) // 2024-01-07 is a Sunday
    return formatter.format(date)
  })
}
```

- [ ] **Step 4: Run tests to verify refactored version**

Run: `cd frontend && npm test -- date-utils.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/date-utils.ts
git commit -m "refactor: use Intl.DateTimeFormat for weekday labels"
```

---

## Self-Review Checklist

**Spec coverage:**
✓ Base64 conversions simplified (webauthn.ts)
✓ Date utilities use native APIs (month-utils.ts, date-utils.ts)
✓ SQL query deduplication (budget_service.py)
✗ Currency/locale hardcoded maps (format.ts) - deferred as it requires more careful migration
✗ Client-side row aggregation (budgets.tsx) - deferred as it requires backend API changes

**Placeholder scan:** None found - all code blocks are complete

**Type consistency:** All function signatures preserved, no breaking changes

**Deferred items:**
- `format.ts` locale maps: Requires careful Intl.Locale migration with fallback strategy
- `budgets.tsx` aggregation: Requires new backend endpoint design for shaped data

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-16-ponytail-refactor.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
