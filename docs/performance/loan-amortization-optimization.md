# Loan Amortization Performance Optimization Guide

This document outlines performance optimizations implemented in the loan amortization feature and recommendations for production deployments.

## Database Optimizations

### Indexes

The following indexes are critical for query performance:

```sql
-- Primary lookup by account
CREATE INDEX idx_loan_schedule_account_version 
ON loan_amortization_schedule(account_id, schedule_version);

-- Date range queries
CREATE INDEX idx_loan_schedule_due_date 
ON loan_amortization_schedule(due_date);

-- Status filtering
CREATE INDEX idx_loan_schedule_status 
ON loan_amortization_schedule(payment_status);

-- Transaction linking
CREATE INDEX idx_loan_schedule_transaction 
ON loan_amortization_schedule(linked_transaction_id) 
WHERE linked_transaction_id IS NOT NULL;

-- Workspace isolation
CREATE INDEX idx_loan_schedule_workspace 
ON loan_amortization_schedule(workspace_id);

-- Prepayment lookups
CREATE INDEX idx_loan_prepayment_account 
ON loan_prepayment(account_id);

-- Composite index for common queries
CREATE INDEX idx_loan_schedule_composite 
ON loan_amortization_schedule(workspace_id, account_id, schedule_version, emi_number);
```

**Impact**: Reduces query time from O(n) table scans to O(log n) index lookups.

### Query Optimization

#### Avoid N+1 Queries

**Bad**:
```python
accounts = await db.execute(select(Account).where(...))
for account in accounts:
    schedule = await db.execute(
        select(LoanAmortizationSchedule).where(
            LoanAmortizationSchedule.account_id == account.id
        )
    )
```

**Good**:
```python
# Use eager loading
result = await db.execute(
    select(Account)
    .options(selectinload(Account.loan_schedules))
    .where(...)
)
```

#### Batch Operations

Use bulk operations for multiple updates:

```python
# Bad: Individual updates
for entry_id in entry_ids:
    await db.execute(
        update(LoanAmortizationSchedule)
        .where(LoanAmortizationSchedule.id == entry_id)
        .values(payment_status="paid")
    )

# Good: Single batch update
await db.execute(
    update(LoanAmortizationSchedule)
    .where(LoanAmortizationSchedule.id.in_(entry_ids))
    .values(payment_status="paid")
)
```

**Impact**: Reduces database round trips from O(n) to O(1).

#### Pagination

For large schedules, implement pagination:

```python
# Paginate schedule queries
result = await db.execute(
    select(LoanAmortizationSchedule)
    .where(...)
    .order_by(LoanAmortizationSchedule.emi_number)
    .limit(page_size)
    .offset(page * page_size)
)
```

**Impact**: Prevents memory issues with 30-year loans (360+ entries).

### Connection Pooling

Configure SQLAlchemy pool size for concurrent requests:

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Base connections
    max_overflow=10,       # Additional connections under load
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections hourly
)
```

**Recommendation**: Monitor connection usage and adjust based on traffic patterns.

## Application Optimizations

### Caching Strategy

#### Schedule Calculations

Cache EMI calculations for repeated parameters:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def calculate_emi_cached(principal: Decimal, rate: Decimal, months: int) -> Decimal:
    return calculate_emi(principal, rate, months)
```

**Impact**: Avoids redundant calculations in simulations and bulk operations.

#### Dashboard Data

Cache dashboard queries with short TTL:

```python
from fastapi_cache.decorator import cache

@router.get("/loans/dashboard")
@cache(expire=300)  # 5 minutes
async def get_dashboard_summary(...):
    # Expensive aggregation query
    ...
```

**Impact**: Reduces database load for frequently accessed endpoints.

### Async Processing

#### Background Tasks

Use background tasks for expensive operations:

```python
from fastapi import BackgroundTasks

@router.post("/schedule/regenerate")
async def regenerate_schedule(
    background_tasks: BackgroundTasks,
    ...
):
    # Return immediately
    background_tasks.add_task(
        generate_schedule_async,
        account_id,
        parameters
    )
    return {"status": "processing"}
```

**Use Cases**:
- Schedule regeneration for 30+ year loans
- Bulk exports with 10+ accounts
- Large-scale auto-linking operations

#### Task Queue

For production, use Celery or similar:

```python
@celery.task
def generate_schedule_task(account_id, params):
    # Long-running schedule generation
    ...

# In route handler
task = generate_schedule_task.delay(account_id, params)
return {"task_id": task.id}
```

**Benefit**: Offload CPU-intensive calculations from request handlers.

### Serialization

#### Decimal Handling

Use optimized decimal serialization:

```python
class LoanScheduleEntryRead(BaseModel):
    emi_amount: Decimal
    
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)  # Faster than default
        }
```

#### Selective Field Loading

Load only required fields:

```python
# Instead of loading full objects
result = await db.execute(
    select(
        LoanAmortizationSchedule.emi_number,
        LoanAmortizationSchedule.due_date,
        LoanAmortizationSchedule.emi_amount
    ).where(...)
)
```

**Impact**: Reduces memory footprint and serialization overhead.

## Frontend Optimizations

### Query Optimization

#### Stale-While-Revalidate

Use TanStack Query's stale-while-revalidate pattern:

```tsx
const { data } = useQuery({
  queryKey: ['loan-schedule', accountId],
  queryFn: fetchSchedule,
  staleTime: 5 * 60 * 1000,      // 5 minutes
  cacheTime: 30 * 60 * 1000,     // 30 minutes
  refetchOnWindowFocus: false,    // Prevent excessive refetches
});
```

**Impact**: Reduces API calls while maintaining data freshness.

#### Prefetching

Prefetch likely-needed data:

```tsx
// On dashboard, prefetch first loan details
const queryClient = useQueryClient();

loans.forEach(loan => {
  queryClient.prefetchQuery({
    queryKey: ['loan-overview', loan.id],
    queryFn: () => fetchLoanOverview(loan.id),
  });
});
```

**Benefit**: Instant page transitions for prefetched data.

### Component Optimization

#### Virtualization

For large schedule tables, use virtualization:

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function LoanScheduleTable({ entries }) {
  const virtualizer = useVirtualizer({
    count: entries.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      {virtualizer.getVirtualItems().map(virtualRow => (
        <ScheduleRow key={virtualRow.key} entry={entries[virtualRow.index]} />
      ))}
    </div>
  );
}
```

**Impact**: Renders only visible rows, handling 1000+ entries smoothly.

#### Memoization

Memoize expensive calculations:

```tsx
const totalPaid = useMemo(
  () => schedule
    .filter(e => e.payment_status === 'paid')
    .reduce((sum, e) => sum + parseFloat(e.emi_amount), 0),
  [schedule]
);
```

### Bundle Optimization

Code split loan feature:

```tsx
const LoanDetailPage = lazy(() => import('./pages/loans/LoanDetailPage'));

<Route 
  path="/loans/:accountId" 
  element={
    <Suspense fallback={<Loading />}>
      <LoanDetailPage />
    </Suspense>
  } 
/>
```

**Benefit**: Reduces initial bundle size for users not accessing loans.

## API Response Optimization

### Compression

Enable gzip compression:

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Impact**: 70-90% reduction in response size for large schedules.

### Streaming Responses

Use streaming for CSV exports:

```python
from fastapi.responses import StreamingResponse

async def generate_csv_rows():
    yield "EMI,Date,Amount\n"
    async for entry in schedule_entries:
        yield f"{entry.emi_number},{entry.due_date},{entry.emi_amount}\n"

return StreamingResponse(generate_csv_rows(), media_type="text/csv")
```

**Benefit**: Constant memory usage regardless of schedule size.

### Response Pagination

Implement cursor-based pagination for large result sets:

```python
@router.get("/loans/{account_id}/schedule")
async def get_loan_schedule(
    account_id: UUID,
    cursor: Optional[int] = None,  # Last EMI number seen
    limit: int = 50,
):
    query = select(LoanAmortizationSchedule).where(...)
    if cursor:
        query = query.where(LoanAmortizationSchedule.emi_number > cursor)
    query = query.limit(limit)
    
    entries = await db.execute(query)
    return {
        "entries": entries,
        "next_cursor": entries[-1].emi_number if entries else None
    }
```

## Monitoring & Profiling

### Query Performance

Monitor slow queries:

```python
import time
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop()
    if total > 0.1:  # Log queries over 100ms
        logger.warning(f"Slow query ({total:.2f}s): {statement}")
```

### Application Metrics

Track key performance indicators:

```python
from prometheus_client import Histogram, Counter

schedule_generation_time = Histogram(
    'loan_schedule_generation_seconds',
    'Time to generate loan schedule',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

prepayment_calculations = Counter(
    'loan_prepayment_calculations_total',
    'Total prepayment calculations'
)

@schedule_generation_time.time()
async def generate_schedule(...):
    ...
```

### Frontend Performance

Use React DevTools Profiler:

```tsx
import { Profiler } from 'react';

<Profiler id="LoanScheduleTable" onRender={onRenderCallback}>
  <LoanScheduleTable />
</Profiler>
```

Monitor render times and optimize components exceeding 16ms.

## Load Testing

### Backend Load Tests

Use Locust for load testing:

```python
from locust import HttpUser, task, between

class LoanUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_schedule(self):
        account_id = self.select_random_account()
        self.client.get(f"/api/v1/loans/{account_id}/schedule")
    
    @task(1)
    def simulate_prepayment(self):
        self.client.post("/api/v1/prepayments/simulate", json={...})
```

**Target Metrics**:
- Schedule retrieval: <200ms (p95)
- Prepayment simulation: <500ms (p95)
- Dashboard load: <300ms (p95)
- Bulk operations: <2s for 100 entries

### Frontend Performance Budget

| Metric | Target | Critical |
|--------|--------|----------|
| First Contentful Paint | <1.5s | <3s |
| Time to Interactive | <3s | <5s |
| Largest Contentful Paint | <2.5s | <4s |
| Cumulative Layout Shift | <0.1 | <0.25 |

## Production Configuration

### Database

```yaml
# PostgreSQL configuration
shared_buffers: 256MB              # 25% of RAM
effective_cache_size: 1GB          # 50% of RAM
work_mem: 16MB                     # Per-operation memory
maintenance_work_mem: 128MB        # For VACUUM, CREATE INDEX
max_connections: 100               # Based on pool size
```

### Application

```python
# FastAPI with Uvicorn
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    workers=4,                     # CPU cores
    limit_concurrency=1000,        # Max concurrent requests
    limit_max_requests=10000,      # Restart worker after N requests
    timeout_keep_alive=5,
)
```

### Caching Layer

Use Redis for distributed caching:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

redis = aioredis.from_url("redis://localhost")
FastAPICache.init(RedisBackend(redis), prefix="loan-cache:")
```

## Best Practices Summary

1. **Database**:
   - Always use appropriate indexes
   - Implement connection pooling
   - Use batch operations for bulk updates
   - Paginate large result sets

2. **Application**:
   - Cache expensive calculations
   - Use background tasks for long operations
   - Enable compression for API responses
   - Implement rate limiting for expensive endpoints

3. **Frontend**:
   - Use TanStack Query for smart caching
   - Implement virtualization for large lists
   - Code split by route
   - Prefetch likely-needed data

4. **Monitoring**:
   - Track slow queries
   - Monitor API response times
   - Set up alerts for performance degradation
   - Regular load testing

5. **Scaling**:
   - Horizontal scaling of API workers
   - Read replicas for dashboard queries
   - CDN for static assets
   - Task queue for background processing

## Performance Checklist

- [ ] Database indexes created and verified
- [ ] Connection pooling configured
- [ ] Caching layer implemented
- [ ] Bulk operations used where applicable
- [ ] API responses paginated
- [ ] Compression enabled
- [ ] Frontend virtualization for large lists
- [ ] Code splitting implemented
- [ ] Monitoring and alerting set up
- [ ] Load tests passing performance targets
- [ ] Query performance profiled
- [ ] Memory leaks checked
- [ ] Database query plan analyzed
- [ ] CDN configured for static assets
- [ ] Rate limiting implemented

## Troubleshooting Performance Issues

### Slow Schedule Queries

**Symptom**: Schedule retrieval takes >1s

**Diagnose**:
```sql
EXPLAIN ANALYZE 
SELECT * FROM loan_amortization_schedule 
WHERE account_id = '...' AND schedule_version = 1;
```

**Solutions**:
- Verify index exists on (account_id, schedule_version)
- Check for table bloat (run VACUUM)
- Consider partitioning by account_id if workspace has 1000+ loans

### High Memory Usage

**Symptom**: Backend process memory grows unbounded

**Diagnose**:
- Profile with memory_profiler
- Check for unclosed database sessions
- Monitor connection pool usage

**Solutions**:
- Implement pagination for large queries
- Use streaming responses for exports
- Limit query result set size
- Close sessions explicitly

### Slow Frontend Rendering

**Symptom**: Schedule table takes >3s to render

**Diagnose**:
- Use React DevTools Profiler
- Check for unnecessary re-renders
- Measure component render times

**Solutions**:
- Implement virtualization
- Memoize expensive calculations
- Use React.memo for pure components
- Reduce prop drilling

## Resources

- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/14/faq/performance.html)
- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/concepts/)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
