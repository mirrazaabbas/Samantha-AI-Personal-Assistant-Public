"""Agents primitive — multi-turn reasoning and tool use."""

from __future__ import annotations

import logging

from samantha.agents._stubs import (
    AgentContext,
    AgentResult,
    BaseAgent,
    ToolUsingAgent,
)

logger = logging.getLogger(__name__)

# Import agent modules to trigger @AgentRegistry.register() decorators
try:
    import samantha.agents.simple  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.orchestrator  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.native_react  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.native_openhands  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.react  # noqa: F401 -- backward-compat shim
except ImportError:
    pass

try:
    import samantha.agents.openhands  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.rlm  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.claude_code  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.opencode  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.operative  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.monitor  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.monitor_operative  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.deep_research  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.morning_digest  # noqa: F401
except ImportError:
    pass

try:
    import samantha.agents.daily_briefing  # noqa: F401
except ImportError:
    pass

# Hybrid local+cloud paradigm agents (Minions, Conductor, Archon, Advisors,
# SkillOrchestra, ToolOrchestra). Each module registers under its own name
# via @AgentRegistry.register(). Optional deps may make some unavailable.
try:
    import samantha.agents.hybrid  # noqa: F401
except ImportError:
    pass

# Registry alias: "react" -> NativeReActAgent (for backward compat)
try:
    from samantha.core.registry import AgentRegistry

    if AgentRegistry.contains("native_react") and not AgentRegistry.contains("react"):
        AgentRegistry.register_value("react", AgentRegistry.get("native_react"))
except Exception as exc:
    logger.debug("Registry alias 'react' creation skipped: %s", exc)

__all__ = ["AgentContext", "AgentResult", "BaseAgent", "ToolUsingAgent"]
