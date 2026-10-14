"""Per-problem token budget (plan §6.4).

Before a call, its worst case (prompt + max output) is reserved; afterwards the reservation
is replaced by what was actually used. Calls running in parallel therefore can't overshoot
together, and a call that wouldn't fit isn't made: BudgetExhausted is raised instead.
"""

import threading
from collections import defaultdict
from contextlib import contextmanager


class BudgetExhausted(RuntimeError):
    def __init__(self, stage: str, needed: int, left: int):
        super().__init__(f"token budget exhausted at stage {stage} (needs {needed}, {left} left)")
        self.stage = stage


class Budget:
    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0
        self.reserved = 0
        self.by_stage: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    @property
    def left(self) -> int:
        return self.limit - self.used - self.reserved

    @contextmanager
    def reserve(self, tokens: int, stage: str):
        with self._lock:
            if tokens > self.left:
                raise BudgetExhausted(stage, tokens, self.left)
            self.reserved += tokens
        spent = {"n": tokens}  # if the call fails, the whole reservation counts as used

        def charge(actual: int) -> None:
            spent["n"] = actual

        try:
            yield charge
        finally:
            with self._lock:
                self.reserved -= tokens
                self.used += spent["n"]
                self.by_stage[stage] += spent["n"]

    def report(self) -> dict:
        return {"limit": self.limit, "used": self.used, "by_stage": dict(self.by_stage)}
