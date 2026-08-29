"""Structural protocols for substituting fakes in place of SamanthaSystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Protocol

if TYPE_CHECKING:
    from samantha.core.config import SamanthaConfig
    from samantha.core.events import EventBus
    from samantha.engine._stubs import InferenceEngine
    from samantha.security.capabilities import CapabilityPolicy
    from samantha.sessions.session import SessionStore
    from samantha.tools._stubs import BaseTool
    from samantha.tools.storage._stubs import MemoryBackend
    from samantha.traces.collector import TraceCollector
    from samantha.traces.store import TraceStore


class OrchestratorDeps(Protocol):
    """Minimum surface of SamanthaSystem that QueryOrchestrator depends on.

    Tests can satisfy this with a lightweight class — no need to construct
    the full SamanthaSystem dataclass or materialize every subsystem.
    """

    config: SamanthaConfig
    bus: EventBus
    engine: InferenceEngine
    engine_key: str
    model: str
    agent_name: str
    tools: List[BaseTool]
    memory_backend: Optional[MemoryBackend]
    capability_policy: Optional[CapabilityPolicy]
    session_store: Optional[SessionStore]
    trace_store: Optional[TraceStore]
    trace_collector: Optional[TraceCollector]  # written by _run_agent

    # Optional attribute (getattr with default) — declared for type clarity.
    _skill_few_shot_examples: Any
