"""Circuit breaker pattern for backend protection."""
import time
import logging
from enum import Enum

from config import config

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Backend is down, skip calls
    HALF_OPEN = "HALF_OPEN"  # Testing if backend recovered

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    Opens after threshold consecutive failures, preventing further attempts.
    After timeout, enters half-open state to test recovery.
    Closes after successful calls in half-open state.
    """
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.last_state_change = time.time()
    
    def record_failure(self) -> None:
        """Record a failed MCP call."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= config.CIRCUIT_BREAKER_THRESHOLD:
                self._open_circuit()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, reopen circuit
            self._open_circuit()
    
    def record_success(self) -> None:
        """Record a successful MCP call."""
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Need 2 successes to close circuit
            if self.success_count >= 2:
                self._close_circuit()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def should_attempt(self) -> bool:
        """Check if MCP call should be attempted."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if time.time() - self.last_failure_time > config.CIRCUIT_BREAKER_TIMEOUT:
                self._half_open_circuit()
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def get_state(self) -> str:
        """Get current circuit state."""
        return self.state.value
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change
        }
    
    def _open_circuit(self) -> None:
        """Open the circuit (block calls)."""
        logger.error(
            f"Circuit breaker OPENED after {self.failure_count} failures. "
            f"Backend appears to be down."
        )
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()
        self.failure_count = 0
    
    def _half_open_circuit(self) -> None:
        """Enter half-open state (test recovery)."""
        logger.warning("Circuit breaker HALF-OPEN. Testing backend recovery...")
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.success_count = 0
    
    def _close_circuit(self) -> None:
        """Close the circuit (resume normal operation)."""
        logger.info("Circuit breaker CLOSED. Backend recovered successfully.")
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.failure_count = 0
        self.success_count = 0

# Global instance
circuit_breaker = CircuitBreaker()
