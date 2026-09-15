"""Test Prometheus metrics without database."""
from metrics import (
    mcp_calls_total, 
    retry_queue_size,
    call_duration_seconds,
    sync_lag_seconds,
    circuit_breaker_state_gauge,
    wal_size_mb_gauge,
    get_metrics_content
)

# Test counter increment
mcp_calls_total.labels(tool='propose_create_transaction', status='success').inc()
mcp_calls_total.labels(tool='propose_create_transaction', status='failure').inc()

# Test gauge setting
retry_queue_size.set(5)
circuit_breaker_state_gauge.set(0)  # CLOSED
wal_size_mb_gauge.set(1.5)
sync_lag_seconds.set(0.5)

# Test histogram observation
call_duration_seconds.observe(0.3)
call_duration_seconds.observe(1.2)

# Get metrics output
content, content_type = get_metrics_content()
metrics_text = content.decode()

print("First 1000 characters of metrics output:")
print(metrics_text[:1000])
print("\n" + "="*60)

# Verify all metrics are present
required_metrics = [
    'mcp_proxy_calls_total',
    'mcp_proxy_retry_queue_size',
    'mcp_proxy_call_duration_seconds',
    'telegram_sync_lag_seconds',
    'mcp_proxy_circuit_breaker_state',
    'mcp_proxy_wal_size_mb'
]

print("\nVerifying metrics presence:")
all_present = True
for metric in required_metrics:
    present = metric in metrics_text
    status = "✓" if present else "✗"
    print(f"{status} {metric}")
    if not present:
        all_present = False

# Verify specific values
assert b'mcp_proxy_calls_total' in content
assert b'mcp_proxy_retry_queue_size' in content
assert b'tool="propose_create_transaction"' in content
assert b'status="success"' in content
assert b'status="failure"' in content

if all_present:
    print("\n✓ All 6 metrics present")
    print("✓ Metrics test passed")
else:
    print("\n✗ Some metrics missing")
    exit(1)
