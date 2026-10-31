"""Circuit breaker per fonte: dopo N errori consecutivi apre il circuito."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitBreaker:
    fail_threshold: int = 3
    cooldown_s: float = 300.0
    _fails: int = 0
    _opened_at: float = 0.0

    def allow(self) -> bool:
        if self._fails < self.fail_threshold:
            return True
        if (time.monotonic() - self._opened_at) >= self.cooldown_s:
            self._fails = 0
            return True
        return False

    def record_success(self) -> None:
        self._fails = 0

    def record_failure(self) -> None:
        self._fails += 1
        if self._fails >= self.fail_threshold:
            self._opened_at = time.monotonic()

    @property
    def is_open(self) -> bool:
        return not self.allow()
