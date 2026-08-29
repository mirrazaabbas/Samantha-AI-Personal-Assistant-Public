"""Safe macOS control actions for Samantha."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from samantha.core.registry import ToolRegistry
from samantha.core.types import ToolResult
from samantha.tools._stubs import BaseTool, ToolSpec

_SAFE_APP_NAME = re.compile(r"^[A-Za-z0-9 ._+\-&()]+$")

_ALLOWED_APPS = {
    "Google Chrome",
    "Safari",
    "Notes",
    "Finder",
    "Calendar",
    "Terminal",
    "System Settings",
    "Music",
    "Messages",
    "FaceTime",
    "Mail",
    "Preview",
    "Microsoft Excel",
}


@ToolRegistry.register("macos_control")
class MacOSControlTool(BaseTool):
    """Perform explicitly allowed, low-risk macOS actions."""

    tool_id = "macos_control"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="macos_control",
            description=(
                "Safely control low-risk macOS actions. "
                "Currently supports opening an installed application. "
                "Use this instead of shell_exec for requests such as "
                "'open Chrome', 'launch Notes', or 'start Safari'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open_app"],
                        "description": "The safe macOS action to perform.",
                    },
                    "app": {
                        "type": "string",
                        "description": "Application name, for example Google Chrome.",
                    },
                },
                "required": ["action", "app"],
                "additionalProperties": False,
            },
            category="system",
            requires_confirmation=False,
            timeout_seconds=10.0,
            required_capabilities=["code:execute"],
        )

    def execute(self, **params: Any) -> ToolResult:
        action = str(params.get("action", "")).strip()
        app = str(params.get("app", "")).strip()

        if action != "open_app":
            return ToolResult(
                tool_name=self.tool_id,
                content="Unsupported macOS action.",
                success=False,
            )

        if (
            not app
            or len(app) > 100
            or not _SAFE_APP_NAME.fullmatch(app)
            or app not in _ALLOWED_APPS
        ):
            return ToolResult(
                tool_name=self.tool_id,
                content="Application is not approved for automatic opening.",
                success=False,
            )

        try:
            result = subprocess.run(
                ["/usr/bin/open", "-a", app],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ToolResult(
                tool_name=self.tool_id,
                content=f"Could not open application: {exc}",
                success=False,
            )

        if result.returncode != 0:
            error = result.stderr.strip() or "Application could not be opened."
            return ToolResult(
                tool_name=self.tool_id,
                content=error,
                success=False,
            )

        return ToolResult(
            tool_name=self.tool_id,
            content=f"Opened {app}.",
            success=True,
        )


__all__ = ["MacOSControlTool"]
