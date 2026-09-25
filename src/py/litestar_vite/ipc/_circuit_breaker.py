"""Circuit breaker state machine protecting against cascading SSR worker failures."""

import enum
import time
from types import TracebackType

import anyio
from typing_extensions import Self

from litestar_vite.ipc._base import CircuitBreakerOpenError

__all__ = ("CircuitState", "SSRCircuitBreaker")


class CircuitState(str, enum.Enum):
    """Lifecycle states of the SSR circuit breaker."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class SSRCircuitBreaker:
    """Three-state circuit breaker pattern for SSR worker stability."""

    __slots__ = ("_cooldown", "_failure_count", "_failure_threshold", "_last_state_change", "_lock", "_state")

    def __init__(self, failure_threshold: int = 3, cooldown: float = 30.0) -> None:
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening the circuit.
            cooldown: Time in seconds to wait in OPEN state before transitioning to HALF_OPEN.
        """
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown
        self._failure_count = 0
        self._last_state_change = 0.0
        self._state = CircuitState.CLOSED
        self._lock = anyio.Lock()

    @property
    def state(self) -> CircuitState:
        """Return the current circuit state, evaluating cooldown if currently OPEN.

        Returns:
            The effective CircuitState.
        """
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_state_change
            if elapsed >= self._cooldown:
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        """Return the current consecutive failure tally.

        Returns:
            Failure count integer.
        """
        return self._failure_count

    @property
    def failure_threshold(self) -> int:
        """Return the threshold of failures required to open the circuit.

        Returns:
            Failure threshold integer.
        """
        return self._failure_threshold

    @property
    def cooldown(self) -> float:
        """Return the configured cooldown period in seconds.

        Returns:
            Cooldown duration in seconds.
        """
        return self._cooldown

    def can_execute(self) -> bool:
        """Determine whether an outbound request is permitted through the breaker.

        Returns:
            True if request is allowed, False if breaker is open.
        """
        current_state = self.state
        return current_state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful execution, resetting failures and closing the circuit."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record an execution failure, potentially tripping the circuit to OPEN."""
        self._failure_count += 1
        if self._state == CircuitState.HALF_OPEN or self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            self._last_state_change = time.monotonic()

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._failure_count = 0
        self._last_state_change = 0.0
        self._state = CircuitState.CLOSED

    async def __aenter__(self) -> Self:
        """Enter protected execution block or raise CircuitBreakerOpenError.

        Returns:
            Active circuit breaker instance.

        Raises:
            CircuitBreakerOpenError: When the circuit is open and refusing traffic.
        """
        async with self._lock:
            if not self.can_execute():
                remaining = max(0.0, self._cooldown - (time.monotonic() - self._last_state_change))
                msg = f"SSR circuit breaker is OPEN. Cooldown expires in {remaining:.1f}s"
                raise CircuitBreakerOpenError(msg)
            return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Exit protected block, updating circuit state based on whether an error occurred.

        Args:
            exc_type: Exception type if raised during block.
            exc_val: Exception instance if raised.
            exc_tb: Traceback object if raised.
        """
        async with self._lock:
            if exc_type is not None and issubclass(exc_type, Exception):
                self.record_failure()
            else:
                self.record_success()
