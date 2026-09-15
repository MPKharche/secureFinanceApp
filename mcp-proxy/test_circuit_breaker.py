#!/usr/bin/env python3
"""Test circuit breaker state transitions."""
import time
import sys
from circuit_breaker import CircuitBreaker, CircuitState

def test_closed_to_open():
    """Test CLOSED → OPEN after threshold failures."""
    print("Test 1: CLOSED → OPEN after 5 failures")
    cb = CircuitBreaker()
    
    assert cb.get_state() == "CLOSED", "Should start CLOSED"
    
    # Record 4 failures - should stay closed
    for i in range(4):
        cb.record_failure()
        assert cb.get_state() == "CLOSED", f"Should stay CLOSED after {i+1} failures"
    
    # 5th failure should open circuit
    cb.record_failure()
    assert cb.get_state() == "OPEN", "Should be OPEN after 5 failures"
    assert not cb.should_attempt(), "Should not attempt when OPEN"
    
    print("✓ CLOSED → OPEN works correctly\n")

def test_open_to_half_open():
    """Test OPEN → HALF_OPEN after timeout."""
    print("Test 2: OPEN → HALF_OPEN after timeout")
    cb = CircuitBreaker()
    
    # Open the circuit
    for i in range(5):
        cb.record_failure()
    
    assert cb.get_state() == "OPEN", "Should be OPEN"
    
    # Should not attempt immediately
    assert not cb.should_attempt(), "Should not attempt when just opened"
    
    # Simulate timeout by manipulating last_failure_time
    cb.last_failure_time = time.time() - 61  # 61 seconds ago
    
    # Now should_attempt should transition to HALF_OPEN
    assert cb.should_attempt(), "Should attempt after timeout"
    assert cb.get_state() == "HALF_OPEN", "Should be HALF_OPEN after timeout"
    
    print("✓ OPEN → HALF_OPEN works correctly\n")

def test_half_open_to_closed():
    """Test HALF_OPEN → CLOSED after 2 successes."""
    print("Test 3: HALF_OPEN → CLOSED after 2 successes")
    cb = CircuitBreaker()
    
    # Get to HALF_OPEN state
    for i in range(5):
        cb.record_failure()
    cb.last_failure_time = time.time() - 61
    cb.should_attempt()
    
    assert cb.get_state() == "HALF_OPEN", "Should be HALF_OPEN"
    
    # First success - should stay HALF_OPEN
    cb.record_success()
    assert cb.get_state() == "HALF_OPEN", "Should stay HALF_OPEN after 1 success"
    
    # Second success - should close
    cb.record_success()
    assert cb.get_state() == "CLOSED", "Should be CLOSED after 2 successes"
    
    print("✓ HALF_OPEN → CLOSED works correctly\n")

def test_half_open_to_open():
    """Test HALF_OPEN → OPEN on failure."""
    print("Test 4: HALF_OPEN → OPEN on failure")
    cb = CircuitBreaker()
    
    # Get to HALF_OPEN state
    for i in range(5):
        cb.record_failure()
    cb.last_failure_time = time.time() - 61
    cb.should_attempt()
    
    assert cb.get_state() == "HALF_OPEN", "Should be HALF_OPEN"
    
    # Failure in HALF_OPEN should reopen circuit
    cb.record_failure()
    assert cb.get_state() == "OPEN", "Should be OPEN after failure in HALF_OPEN"
    
    print("✓ HALF_OPEN → OPEN works correctly\n")

def test_reset_on_success():
    """Test failure count reset on success in CLOSED state."""
    print("Test 5: Failure count reset on success")
    cb = CircuitBreaker()
    
    # Record some failures
    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2, "Should have 2 failures"
    
    # Success should reset
    cb.record_success()
    assert cb.failure_count == 0, "Failure count should reset after success"
    assert cb.get_state() == "CLOSED", "Should stay CLOSED"
    
    print("✓ Failure count reset works correctly\n")

def test_stats():
    """Test get_stats method."""
    print("Test 6: Statistics reporting")
    cb = CircuitBreaker()
    
    stats = cb.get_stats()
    assert stats['state'] == 'CLOSED'
    assert stats['failure_count'] == 0
    assert stats['success_count'] == 0
    assert stats['last_failure_time'] is None
    assert stats['last_state_change'] > 0
    
    cb.record_failure()
    stats = cb.get_stats()
    assert stats['failure_count'] == 1
    assert stats['last_failure_time'] is not None
    
    print("✓ Statistics reporting works correctly\n")

if __name__ == '__main__':
    try:
        test_closed_to_open()
        test_open_to_half_open()
        test_half_open_to_closed()
        test_half_open_to_open()
        test_reset_on_success()
        test_stats()
        
        print("=" * 50)
        print("✓ All circuit breaker tests passed!")
        print("=" * 50)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
