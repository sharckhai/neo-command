from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TraceEvent:
    name: str
    input: Dict[str, Any]
    output: Dict[str, Any]


@dataclass
class TraceRecorder:
    steps: List[TraceEvent] = field(default_factory=list)

    def add_step(self, name: str, input: Dict[str, Any], output: Dict[str, Any]) -> None:
        self.steps.append(TraceEvent(name=name, input=input, output=output))

    def snapshot(self) -> List[TraceEvent]:
        return list(self.steps)
