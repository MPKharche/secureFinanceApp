# Test Suite Systematic Fix - Design Specification

**Date:** 2026-09-17  
**Status:** Approved  
**Estimated Effort:** 11-18 hours  

## Problem Statement

The backend test suite has 166 failing tests (142 failed + 24 errors) out of 3,523 total tests (94.0% pass rate). While the core application works in production, the test failures block confident refactoring, feature development, and CI/CD automation.

### Current Issues Categorized

1. **PostgreSQL vs SQLite incompatibility** - Tests use SQLite but production uses PostgreSQL, causing subtle behavior differences
2. **Test fixture errors** (~38 failures) - Wrong fixture names (`async_session` vs `session`) and attribute references (`workspace.workspace_id` vs `workspace.id`)
3. **Authentication issues** (~43 failures) - Integration tests missing `auth_headers`, resulting in 401 errors
4. **Transaction isolation** (~7 failures) - SMS integration tests create data but async tasks can't see uncommitted changes
5. **Business logic assertions** (~4 failures) - Tax calculation test expectations don't match actual (correct) results
6. **Scattered issues** (~74 failures) - Various fixture, auth, and test pattern problems across multiple modules

### Test Failure Breakdown by Module

```
test_agents_api:                    22 failures
integration/test_tax_integration:   21 failures  
test_agents_coverage_gaps:           8 failures
test_sms_api:                        8 failures
integration/test_sms_integration:    7 failures
test_agents_connections_api:         7 failures
test_agents_knowledge_api:           7 failures
test_category_learning:              7 failures
test_migrations/test_tax_tables:     7 failures
test_duplicate_checker:              6 failures
test_agents_connections:             5 failures
test_loan_prepayment_routes:         5 failures
tax/test_engine:                     4 failures
test_config:                         4 failures
test_loan_linking_routes:            4 failures
test_sms_parser:                     4 failures
[... 11 more modules with 1-3 failures each]
```

## Goals

### Primary Goals
1. Achieve 100% test pass rate (or explicit skips with documented reasons)
2. Establish PostgreSQL for integration tests (production-accurate)
3. Maintain SQLite for unit tests (fast feedback)
4. Fix all fixture references and authentication issues
5. Document clear test patterns for future contributors

### Non-Goals
- Rewriting test infrastructure from scratch
- Changing production code to accommodate tests (except where it improves testability)
- Adding new test coverage (focus on fixing existing tests)
- Performance optimization of test suite

## Solution Design

### Architecture Overview

**Dual Database Strategy:**
- **Unit tests** → SQLite in-memory (fast, no external dependencies)
- **Integration tests** → PostgreSQL via testcontainers (accurate, matches production)

**Test Markers:**
```python
@pytest.mark.integration  # Uses PostgreSQL
# No marker = unit test, uses SQLite
```

**Authentication Strategy:**
- All integration tests explicitly declare `auth_headers` parameter
- Self-documenting which tests require authentication
- No implicit global authentication

### Phase 1: PostgreSQL Test Infrastructure

#### Components Changed

**1. Add testcontainers dependency**

File: `backend/pyproject.toml`

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
    "testcontainers[postgresql]>=4.0.0",  # NEW
    # ... existing dev dependencies
]
```

**2. Update conftest.py for dual database support**

File: `backend/tests/conftest.py`

Add after existing imports:
```python
from testcontainers.postgres import PostgresContainer

# Test database selection
USE_POSTGRES = os.getenv("PYTEST_USE_POSTGRES", "").lower() in ("1", "true", "yes")
```

Add session-scoped PostgreSQL fixture:
```python
@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container for integration tests."""
    if not USE_POSTGRES:
        yield None
        return
    
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_url(postgres_container):
    """Return appropriate database URL based on test type."""
    if postgres_container:
        return postgres_container.get_connection_url().replace(
            "psycopg2", "asyncpg"
        )
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine(database_url):
    """Create engine with appropriate database."""
    if "postgres" in database_url:
        engine = create_async_engine(database_url, echo=False)
    else:
        # SQLite with StaticPool for in-memory sharing
        engine = create_async_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return engine
```

Update pytest configuration to recognize markers:
```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (uses PostgreSQL)"
    )
```

Pytest collection hook to auto-enable PostgreSQL for integration tests:
```python
def pytest_collection_modifyitems(config, items):
    """Auto-enable PostgreSQL for tests marked as integration."""
    for item in items:
        if "integration" in item.keywords:
            os.environ["PYTEST_USE_POSTGRES"] = "true"
```

**3. Mark integration test files**

Add to top of these files (after imports):
```python
pytestmark = pytest.mark.integration
```

Files to mark:
- `tests/integration/test_sms_integration.py`
- `tests/integration/test_tax_integration.py`
- Any test file that uses HTTP client with database writes

#### Success Criteria

- ✅ `pytest -m integration` runs against PostgreSQL
- ✅ `pytest -m "not integration"` runs against SQLite
- ✅ Both test modes can run in same session
- ✅ No "unsupported SQL type" errors
- ✅ Integration tests see committed data properly

#### Rollback Plan

If PostgreSQL integration causes issues:
1. Revert the conftest.py changes
2. Remove testcontainers dependency
3. All tests fall back to SQLite
4. Previous functionality maintained

---

### Phase 2: Fix Test Fixtures

#### Issue Categories

**Category A: Wrong fixture name - `async_session` doesn't exist**

The fixture is named `session`, not `async_session`. Tests incorrectly reference it.

Affected files and fix count:
- `tests/test_category_learning.py` - 7 occurrences
- `tests/test_duplicate_checker.py` - 6 occurrences  
- `tests/test_sms_api.py` - 8 occurrences
- Any other files using `async_session`

Fix pattern:
```python
# Before (ERROR: fixture 'async_session' not found)
async def test_something(async_session: AsyncSession):
    result = await async_session.execute(query)

# After (WORKS)
async def test_something(session: AsyncSession):
    result = await session.execute(query)
```

**Category B: Wrong attribute - `workspace.workspace_id` doesn't exist**

The `Workspace` model has `id`, not `workspace_id`. Tests use wrong attribute.

Search pattern: `\.workspace_id` in test files

Fix pattern:
```python
# Before (AttributeError: 'Workspace' object has no attribute 'workspace_id')
workspace_id = test_workspace.workspace_id

# After (WORKS)
workspace_id = test_workspace.id
```

**Category C: Missing fixtures**

Some tests reference fixtures that aren't declared in their parameter list or don't exist in conftest.

Approach:
1. Run test, note missing fixture name
2. Check if fixture exists in conftest.py
3. If exists: add to test parameters
4. If doesn't exist: create fixture or refactor test

#### Implementation Method

**Automated Search & Replace (Safe):**
```bash
# Find all async_session references
cd backend/tests
grep -r "async_session:" . --include="*.py"

# Replace (after manual verification)
find . -name "*.py" -exec sed -i 's/async_session: AsyncSession/session: AsyncSession/g' {} \;
find . -name "*.py" -exec sed -i 's/(async_session)/(session)/g' {} \;
```

**Manual Review Required:**
- `workspace.workspace_id` replacements (check context)
- Missing fixture additions (understand test requirements)

**Verification After Each File:**
```bash
pytest tests/test_category_learning.py -v  # Verify fixes
```

#### Success Criteria

- ✅ No "fixture 'async_session' not found" errors
- ✅ No "AttributeError: workspace_id" errors
- ✅ ~38 tests move from ERROR to PASSED/FAILED
- ✅ Test suite can collect all tests without errors

#### Files to Fix (Priority Order)

1. `tests/test_category_learning.py` (7 tests)
2. `tests/test_duplicate_checker.py` (6 tests)
3. `tests/test_sms_api.py` (8 tests)
4. `tests/test_agents_connections.py` (5 tests)
5. Search remaining: `grep -r "async_session\|workspace_id" tests/`

---

### Phase 3: Add Authentication Headers

#### Problem

Integration tests call authenticated API endpoints but don't pass authentication headers, resulting in 401 Unauthorized responses.

The `auth_headers` fixture exists in conftest.py and provides a valid JWT token for `test_user`.

#### Affected Test Files

**High Priority (21 tests):**
- `tests/integration/test_tax_integration.py` - All functions missing auth

**High Priority (22 tests):**
- `tests/test_agents_api.py` - Several functions missing auth

**Medium Priority:**
- Other scattered tests calling `/api/*` without headers

#### Fix Pattern

**Before (gets 401):**
```python
async def test_create_income_source(
    client: AsyncClient,
    session: AsyncSession,
):
    data = {"salary_annual": 1200000, "financial_year": "2026-27"}
    response = await client.post("/api/tax/income-sources", json=data)
    assert response.status_code == 201  # FAILS: gets 401
```

**After (works):**
```python
async def test_create_income_source(
    client: AsyncClient,
    auth_headers: dict,  # <-- ADD THIS
    session: AsyncSession,
):
    data = {"salary_annual": 1200000, "financial_year": "2026-27"}
    response = await client.post(
        "/api/tax/income-sources", 
        json=data,
        headers=auth_headers  # <-- ADD THIS
    )
    assert response.status_code == 201  # PASSES
```

#### Implementation Checklist

For each test file:

1. **Identify authenticated endpoints**
   - Look for `client.post("/api/...)`
   - Check if endpoint requires auth (most do except `/api/info`, `/api/auth/*`)

2. **Add auth_headers parameter**
   ```python
   async def test_name(
       client: AsyncClient,
       auth_headers: dict,  # Add this line
       ...
   ):
   ```

3. **Pass headers to client calls**
   ```python
   response = await client.post(
       "/api/endpoint",
       json=data,
       headers=auth_headers  # Add this
   )
   ```

4. **Verify fix**
   ```bash
   pytest tests/integration/test_tax_integration.py::test_name -v
   ```

#### Files to Fix (Priority Order)

1. `tests/integration/test_tax_integration.py`
   - 21 test functions
   - All call `/api/tax/*` endpoints
   - None have auth headers currently

2. `tests/test_agents_api.py`
   - 22 test functions (some already have auth)
   - Check each function individually
   - Add auth_headers where missing

3. Automated scan for remaining:
   ```bash
   # Find calls without headers
   grep -rn "client.post\|client.get\|client.put\|client.delete" tests/ | \
   grep "/api/" | \
   grep -v "headers="
   ```

#### Success Criteria

- ✅ No 401 Unauthorized errors in integration tests
- ✅ All authenticated endpoint tests have `auth_headers` parameter
- ✅ ~43 tests move from FAILED to PASSED
- ✅ Tests self-document which endpoints require auth

---

### Phase 4: Transaction Isolation & Remaining Issues

#### Sub-Phase 4a: SMS Integration Transaction Isolation

**Problem:** 
Tests create SMS log records but async processing functions can't find them because the test hasn't committed the transaction to the database.

**Root Cause:**
```python
# Test creates record
session.add(sms_log)
await session.flush()  # Only flushes to session, not DB

# Task starts new session
await _process_sms_async(sms_log.id)  # Can't find it!
```

**Solution Pattern:**
```python
# Test creates record  
session.add(sms_log)
await session.commit()        # Commit to database
await session.refresh(sms_log)  # Reload from DB to get updated state

# Task starts new session
await _process_sms_async(sms_log.id)  # Now it works!
```

**Tests to Fix (7 total):**

File: `tests/integration/test_sms_integration.py`

1. `test_sms_end_to_end_success` - Line ~207
2. `test_sms_duplicate_detection` - Line ~279  
3. `test_category_learning_workflow` - Multiple locations
4. `test_low_confidence_review_queue` - Task processing
5. `test_failed_parse_non_financial_sms` - Task processing
6. `test_celery_retry_on_llm_failure` - Task processing
7. `test_sms_missing_account` - Task processing

**Implementation:**

For each test:
1. Find where SMS log or related record is created
2. Find where `_process_sms_async` or similar task function is called
3. Add `await session.commit()` before task call
4. Add `await session.refresh(record)` if needed
5. Verify test passes

**Example Fix:**

```python
# Before
response = await client.post("/api/sms/ingest", json=sms_data, headers=auth_headers)
sms_log_id = uuid.UUID(response.json()["sms_log_id"])
await _process_sms_async(sms_log_id)  # FAILS: not found

# After  
response = await client.post("/api/sms/ingest", json=sms_data, headers=auth_headers)
sms_log_id = uuid.UUID(response.json()["sms_log_id"])

# Ensure SMS log is committed to database
await session.commit()

await _process_sms_async(sms_log_id)  # WORKS: finds it
```

#### Sub-Phase 4b: Tax Calculation Business Logic

**Problem:**
Test assertions expect specific tax calculation results, but the actual (correct) results differ.

**Not a bug** - the tax engine calculations are correct. The test expectations are wrong.

**Tests to Fix (4 total):**

File: `tests/tax/test_engine.py`

1. `test_new_regime_no_deductions`
2. `test_old_regime_with_80c`
3. `test_80d_health_insurance`
4. `test_high_deductions_old_regime_better`

**Approach:**

For each test:
1. Run test to see expected vs actual values
2. Manually verify the tax calculation is correct:
   - Check income amounts
   - Check deductions applied
   - Verify against tax slabs in `app/tax/constants.py`
   - Use tax engine logic in `app/tax/engine.py`
3. Update test assertion to match correct value
4. Add explanatory comment for complex calculations

**Example Fix:**

```python
# Before
def test_old_regime_with_80c():
    result = calculate_tax(income=800000, deductions_80c=150000, regime="old")
    assert result["tax_liability"] == 45000  # Wrong expectation

# After  
def test_old_regime_with_80c():
    result = calculate_tax(income=800000, deductions_80c=150000, regime="old")
    # Calculation: (800k - 150k = 650k taxable)
    # 0-2.5L = 0, 2.5-5L = 12.5k (5%), 5-6.5L = 30k (20%)
    # Total = 42.5k + cess = 44625
    assert result["tax_liability"] == 44625  # Correct expectation
```

#### Sub-Phase 4c: Remaining Scattered Issues

**Categories:**

1. **Migration tests** (7 failures)
   - File: `tests/test_migrations/test_tax_tables.py`
   - Likely need PostgreSQL (Phase 1 may fix)
   - May need fixture updates

2. **Config tests** (4 failures)
   - File: `tests/test_config.py`
   - Check settings fixtures exist
   - May need auth headers

3. **Loan tests** (16 failures across multiple files)
   - Various fixture issues (accounts, schedules)
   - Some auth issues
   - Transaction isolation in some cases

4. **Agents tests** (remaining after Phase 3)
   - Connections, knowledge, coverage tests
   - Mixture of auth + fixture issues

5. **Miscellaneous** (1-2 failures each)
   - Category service, recurring match, write permission
   - Address individually based on error

**Approach:**

1. Group by error pattern (fixture vs auth vs isolation)
2. Fix similar issues together  
3. Some may auto-resolve after Phase 1-3 changes
4. For each remaining failure:
   - Run test with `-vv --tb=short`
   - Identify root cause
   - Apply appropriate fix pattern from phases 1-3
   - Verify and commit

**Priority Order:**

1. Migration tests (PostgreSQL should fix)
2. Loan tests (common pattern likely)
3. Agents remaining (apply Phase 3 pattern)
4. One-off failures (case by case)

#### Success Criteria

- ✅ All SMS integration tests pass
- ✅ Tax calculation assertions match correct values
- ✅ Migration tests work with PostgreSQL
- ✅ 100% test pass rate (or explicit skips)
- ✅ No flaky tests (3 consecutive runs pass)

---

## Implementation Plan

### Time Estimates

```
Phase 1: PostgreSQL Infrastructure
  - Add testcontainers dependency: 15 min
  - Update conftest.py: 1-2 hours
  - Mark integration tests: 30 min
  - Verify and troubleshoot: 1 hour
  TOTAL: 2-3 hours

Phase 2: Fix Test Fixtures  
  - Automated search & replace: 30 min
  - Manual verification: 1 hour
  - Test each file: 1 hour
  - Fix edge cases: 30 min
  TOTAL: 2-4 hours

Phase 3: Add Authentication
  - Tax integration file: 1.5 hours
  - Agents API file: 1.5 hours
  - Scan and fix remaining: 1-2 hours
  TOTAL: 3-5 hours

Phase 4: Transaction Isolation & Remaining
  - SMS integration fixes: 2 hours
  - Tax calculation assertions: 1 hour
  - Remaining scattered issues: 2-4 hours
  TOTAL: 4-6 hours

Total Estimated Time: 11-18 hours
```

### Execution Order

1. **Phase 1** (foundation)
   - Creates infrastructure for accurate testing
   - Commit after verification

2. **Phase 2** (high impact)
   - Fixes ~38 errors immediately
   - Commit after each file or logical group

3. **Phase 3** (high impact)
   - Fixes ~43 failures
   - Commit after each file

4. **Phase 4** (cleanup)
   - Fixes remaining ~85 issues
   - Commit after each sub-phase

### Testing Strategy

**After Each Phase:**
```bash
# Run full test suite
pytest -v

# Check pass rate
pytest --tb=no -q | tail -1

# Run only changed tests
pytest tests/path/to/changed/ -v

# Verify CI passes (if applicable)
git push && check CI status
```

**Phase-Specific Verification:**

```bash
# Phase 1: Verify PostgreSQL works
pytest -m integration -v
pytest -m "not integration" -v

# Phase 2: No fixture errors
pytest --collect-only  # Should collect all tests
pytest -k "category_learning or duplicate_checker" -v

# Phase 3: No 401 errors
pytest tests/integration/test_tax_integration.py -v
pytest tests/test_agents_api.py -v

# Phase 4: Full pass
pytest -v --tb=short
pytest -v --tb=short  # Run twice to check for flakes
```

### Commit Strategy

Each phase gets its own commit:

```bash
# Phase 1
git add backend/pyproject.toml backend/tests/conftest.py
git commit -m "test: add PostgreSQL support for integration tests

- Add testcontainers[postgresql] dependency
- Update conftest.py with dual database strategy
- Mark integration test files with pytest.mark.integration
- SQLite for unit tests, PostgreSQL for integration tests
"

# Phase 2  
git add backend/tests/test_*.py
git commit -m "test: fix fixture references (async_session → session, workspace.workspace_id → workspace.id)

Fixes 38 fixture-related test errors
"

# Phase 3
git add backend/tests/integration/test_tax_integration.py backend/tests/test_agents_api.py
git commit -m "test: add auth_headers to integration tests

Fixes 43 authentication-related test failures
"

# Phase 4
git add backend/tests/integration/test_sms_integration.py backend/tests/tax/test_engine.py
git commit -m "test: fix transaction isolation in SMS tests and update tax calculation assertions

- Add proper commit/refresh in SMS integration tests
- Correct tax calculation expectations
- Fix remaining scattered issues

Achieves 100% test pass rate
"
```

---

## Rollback Plan

If any phase causes unforeseen issues:

1. **Identify the problematic commit**
   ```bash
   git log --oneline -5
   ```

2. **Revert that specific phase**
   ```bash
   git revert <commit-hash>
   ```

3. **Previous phases remain stable**
   - Each phase is independent
   - Earlier phases not affected

4. **Fix issue and retry**
   - Debug the specific problem
   - Apply corrected version
   - Re-run validation

5. **Nuclear option (if needed)**
   ```bash
   git reset --hard <commit-before-phase-1>
   # Returns to starting state
   ```

---

## Success Metrics

### Phase-by-Phase Goals

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 1 | Integration tests use PostgreSQL | 100% |
| Phase 2 | Fixture errors | 0 |
| Phase 3 | 401 errors in integration tests | 0 |
| Phase 4 | Overall pass rate | 100% |

### Final Success Criteria

- ✅ **3,523 / 3,523 tests passing** (100%)
- ✅ **Unit tests fast** (<30s for full suite)
- ✅ **Integration tests accurate** (PostgreSQL matches production)
- ✅ **CI/CD ready** (can gate merges on test pass)
- ✅ **No flaky tests** (3 consecutive runs identical)
- ✅ **Clear patterns documented** (future contributors follow examples)

### Documentation Updates

After completion, update:

1. `CONTRIBUTING.md` - Add note about integration vs unit test markers
2. `backend/README.md` (if exists) - Document PostgreSQL test setup
3. Inline comments - Document complex test patterns

---

## Risks & Mitigations

### Risk 1: PostgreSQL testcontainers slow on VPS
**Mitigation:** 
- Keep SQLite for unit tests (fast feedback)
- Run integration tests only on CI or before merge
- Document local vs CI test strategies

### Risk 2: Unknown issues revealed after fixture fixes
**Mitigation:**
- Fix phases sequentially, not parallel
- Commit after each phase for easy rollback
- Budget extra time in Phase 4 for unknowns

### Risk 3: Tax calculation assertions hard to verify
**Mitigation:**
- Use external tax calculator to verify
- Add detailed comments explaining calculations
- Review with domain expert if available

### Risk 4: Time estimate exceeded
**Mitigation:**
- Phased approach allows stopping at any phase
- Even partial completion improves test health
- Can split Phase 4 across multiple sessions

---

## Open Questions

None - all clarifying questions answered during design phase.

---

## Next Steps

After approval:
1. Run spec self-review (check for placeholders, contradictions, ambiguity)
2. User reviews written spec
3. Invoke writing-plans skill to create detailed implementation plan
4. Begin Phase 1 implementation

---

## References

- Current test results: 3,315 passing, 166 failing (94.0% pass rate)
- Test failure categories documented in design discussion
- testcontainers documentation: https://testcontainers-python.readthedocs.io/
- pytest markers: https://docs.pytest.org/en/stable/example/markers.html
