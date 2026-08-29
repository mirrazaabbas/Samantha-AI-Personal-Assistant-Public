"""Creative design, video assembly, and long-running project tools for Samantha."""
# ruff: noqa: E501

from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from samantha.core.config import DEFAULT_CONFIG_DIR
from samantha.core.registry import ToolRegistry
from samantha.core.types import ToolResult
from samantha.tasks.manager import LongTaskManager
from samantha.tools._stubs import BaseTool, ToolSpec

_SAFE_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
_MANAGER: Optional[LongTaskManager] = None


def _svg_text(text: str, x: int, y: int, size: int, weight: str = "400") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="{size}px" font-weight="{weight}" fill="white">'
        f"{html.escape(text)}</text>"
    )


def _write_design(path: Path, title: str, subtitle: str, kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "square":
        width, height = 1080, 1080
    elif kind == "story":
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080
    accent = "#7c3aed" if kind != "story" else "#db2777"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="{accent}"/></linearGradient></defs>
<rect width="100%" height="100%" fill="url(#bg)"/>
<circle cx="{width - 120}" cy="120" r="220" fill="white" opacity=".08"/>
<circle cx="120" cy="{height - 100}" r="300" fill="white" opacity=".05"/>
{_svg_text(title, 80, int(height * 0.46), 82, "700")}
{_svg_text(subtitle, 80, int(height * 0.54), 34, "400")}
<text x="80" y="{height - 70}" font-family="Arial,Helvetica,sans-serif" font-size="24px" fill="white" opacity=".65">Designed by Samantha</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def _default_manager() -> LongTaskManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = LongTaskManager(DEFAULT_CONFIG_DIR / "samantha_tasks.db")
        _MANAGER.configure(_run_long_goal)
    return _MANAGER


def _run_long_goal(task: dict[str, Any], checkpoint, cancelled, paused) -> str:
    """Execute a large goal in bounded orchestrator turns with checkpoints."""
    from samantha import Samantha

    goal = task["goal"]
    state = dict(task.get("checkpoint") or {})
    metadata = dict(state.get("metadata") or {})
    max_iterations = max(1, min(int(metadata.get("max_iterations", 200)), 2000))
    tools = metadata.get("tools") or [
        "think",
        "calculator",
        "web_search",
        "file_read",
        "file_write",
        "macos_control",
        "office",
        "office_control",
        "image_generate",
        "creative_media",
    ]
    tools = [name for name in tools if name != "long_task"]
    iteration = int(state.get("iteration", 0))

    with Samantha() as samantha:
        while iteration < max_iterations:
            if cancelled() or paused():
                return ""
            iteration += 1
            prompt = f"""You are Samantha executing a persistent long-running project.

GOAL:
{goal}

CURRENT CHECKPOINT:
{json.dumps(state, default=str)[:14000]}

ITERATION: {iteration}/{max_iterations}

Execute the next concrete step. Do not just explain what should be done: use the available tools and create/update real artifacts.
For large projects, work in small recoverable phases and leave files in their final or intermediate locations.
Do not start another long_task job from inside this job.
When the complete goal is genuinely finished, end your response with <SAMANTHA_TASK_DONE>.
Otherwise end with <SAMANTHA_TASK_CONTINUE> and a concise status summary.
"""
            result = samantha.ask(
                prompt, agent="orchestrator", tools=tools, context=False
            )
            text = (
                result.get("content", "") if isinstance(result, dict) else str(result)
            )
            done = "<SAMANTHA_TASK_DONE>" in text
            state.update(
                {
                    "iteration": iteration,
                    "phase": "complete" if done else "working",
                    "last_output": text[-10000:],
                }
            )
            checkpoint(
                progress=(1.0 if done else min(0.99, iteration / max_iterations)),
                phase=state["phase"],
                iteration=iteration,
                last_output=state["last_output"],
            )
            if done:
                return text.replace("<SAMANTHA_TASK_DONE>", "").strip()
    return "Maximum task iterations reached. The job remains resumable from its latest checkpoint."


@ToolRegistry.register("creative_media")
class CreativeMediaTool(BaseTool):
    """Create design assets, storyboards, and short or long-form videos."""

    tool_id = "creative_media"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="creative_media",
            description=(
                "Create Canva-compatible SVG posters, ads and social graphics; create storyboards; "
                "and assemble image sequences into MP4 videos. Video duration is user-controlled and "
                "can be 10 minutes, 30 minutes, or longer. For long projects, use long_task to manage "
                "the multi-step production process. Use image_generate for AI-generated scenes. "
                "File creation is local and does not execute downloaded code."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["poster", "ad", "storyboard", "video"],
                    },
                    "output_path": {"type": "string"},
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "format": {
                        "type": "string",
                        "enum": ["square", "landscape", "story"],
                    },
                    "scenes": {"type": "array"},
                    "image_paths": {"type": "array"},
                    "seconds_per_scene": {"type": "number"},
                    "target_duration_seconds": {
                        "type": "number",
                        "description": "Desired final duration. No 60-second limit.",
                    },
                    "fps": {"type": "integer"},
                    "loop_to_target": {
                        "type": "boolean",
                        "description": "Repeat the supplied scene sequence until target duration is reached.",
                    },
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            category="creative",
            requires_confirmation=True,
            timeout_seconds=180.0,
            required_capabilities=["file:write"],
        )

    def execute(self, **params: Any) -> ToolResult:
        action = str(params.get("action", ""))
        try:
            if action in {"poster", "ad"}:
                output = (
                    Path(
                        str(
                            params.get("output_path") or "~/Desktop/samantha-design.svg"
                        )
                    )
                    .expanduser()
                    .resolve()
                )
                if output.suffix.lower() != ".svg":
                    output = output.with_suffix(".svg")
                fmt = str(params.get("format", "square"))
                _write_design(
                    output,
                    str(params.get("title", "Your Title")),
                    str(params.get("subtitle", "Your message")),
                    fmt,
                )
                return ToolResult(
                    tool_name=self.tool_id,
                    content=f"Created {action}: {output}",
                    success=True,
                    metadata={"path": str(output), "format": fmt},
                )

            if action == "storyboard":
                scenes = params.get("scenes") or []
                if not isinstance(scenes, list) or not scenes:
                    return ToolResult(
                        tool_name=self.tool_id,
                        content="scenes must be a non-empty array.",
                        success=False,
                    )
                output = (
                    Path(
                        str(
                            params.get("output_path")
                            or "~/Desktop/samantha-storyboard.txt"
                        )
                    )
                    .expanduser()
                    .resolve()
                )
                output.parent.mkdir(parents=True, exist_ok=True)
                lines = ["SAMANTHA STORYBOARD", ""]
                for i, scene in enumerate(scenes, 1):
                    if isinstance(scene, dict):
                        lines.append(f"SCENE {i}: {scene.get('title', '')}")
                        lines.append(f"Visual: {scene.get('visual', '')}")
                        lines.append(f"Dialogue: {scene.get('dialogue', '')}")
                        lines.append(f"Camera: {scene.get('camera', 'cinematic')}")
                    else:
                        lines.append(f"SCENE {i}: {scene}")
                    lines.append("")
                output.write_text("\n".join(lines), encoding="utf-8")
                return ToolResult(
                    tool_name=self.tool_id,
                    content=f"Created storyboard: {output}",
                    success=True,
                    metadata={"path": str(output), "scenes": len(scenes)},
                )

            if action == "video":
                images = params.get("image_paths") or []
                if not isinstance(images, list) or not images:
                    return ToolResult(
                        tool_name=self.tool_id,
                        content="image_paths must contain at least one local image.",
                        success=False,
                    )
                ffmpeg = shutil.which("ffmpeg")
                if not ffmpeg:
                    return ToolResult(
                        tool_name=self.tool_id,
                        content="ffmpeg is required for video assembly. Install it with Homebrew: brew install ffmpeg",
                        success=False,
                    )
                paths = [Path(str(p)).expanduser().resolve() for p in images]
                if any(
                    not p.exists() or p.suffix.lower() not in _SAFE_SUFFIXES
                    for p in paths
                ):
                    return ToolResult(
                        tool_name=self.tool_id,
                        content="Every image_path must exist and use png, jpg, jpeg, or webp.",
                        success=False,
                    )
                output = (
                    Path(
                        str(params.get("output_path") or "~/Desktop/samantha-video.mp4")
                    )
                    .expanduser()
                    .resolve()
                )
                output.parent.mkdir(parents=True, exist_ok=True)
                seconds = max(
                    0.5, min(float(params.get("seconds_per_scene", 3.0)), 300.0)
                )
                target = float(params.get("target_duration_seconds", 0) or 0)
                loop_to_target = bool(params.get("loop_to_target", False))
                sequence = list(paths)
                if target > 0 and loop_to_target:
                    needed = max(1, int(target / seconds + 0.999))
                    repeats = (needed + len(paths) - 1) // len(paths)
                    sequence = (paths * repeats)[:needed]
                fps = max(12, min(int(params.get("fps", 24)), 60))
                concat = output.with_suffix(".samantha-concat.txt")
                lines = []
                for p in sequence:
                    safe = p.as_posix().replace("'", "'\\''")
                    lines.append(f"file '{safe}'")
                    lines.append(f"duration {seconds:.3f}")
                lines.append(f"file '{sequence[-1].as_posix()}'")
                concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
                cmd = [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat),
                    "-vf",
                    f"fps={fps},format=yuv420p",
                    "-movflags",
                    "+faststart",
                    str(output),
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=180, check=False
                )
                try:
                    concat.unlink()
                except OSError:
                    pass
                if result.returncode != 0:
                    return ToolResult(
                        tool_name=self.tool_id,
                        content=f"Video assembly failed: {result.stderr[-3000:]}",
                        success=False,
                    )
                duration = len(sequence) * seconds
                return ToolResult(
                    tool_name=self.tool_id,
                    content=f"Created video: {output}",
                    success=True,
                    metadata={
                        "path": str(output),
                        "scenes": len(sequence),
                        "duration_seconds": duration,
                        "seconds_per_scene": seconds,
                    },
                )

            return ToolResult(
                tool_name=self.tool_id,
                content=f"Unsupported creative action: {action}",
                success=False,
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.tool_id,
                content=f"Creative operation failed: {exc}",
                success=False,
            )


@ToolRegistry.register("long_task")
class LongTaskTool(BaseTool):
    """Create and control persistent background projects."""

    tool_id = "long_task"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="long_task",
            description=(
                "Persistent background project manager for work that may take many tool calls or minutes. "
                "Use for large research, Excel/Office work, poster/ad campaigns, animation, and long-form "
                "10+ minute video production. Jobs are persisted in SQLite and resume from checkpoints after restart."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create",
                            "status",
                            "list",
                            "pause",
                            "resume",
                            "cancel",
                        ],
                    },
                    "goal": {"type": "string"},
                    "task_id": {"type": "string"},
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 2000,
                    },
                    "tools": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            category="automation",
        )

    def execute(self, **params: Any) -> ToolResult:
        manager = _default_manager()
        action = str(params.get("action", "")).lower()
        try:
            if action == "create":
                metadata = {
                    "max_iterations": int(params.get("max_iterations", 200)),
                    "tools": params.get("tools") or [],
                }
                task = manager.create(str(params.get("goal", "")), metadata=metadata)
                return self._ok(task)
            if action == "status":
                task = manager.get(str(params.get("task_id", "")))
                return self._ok(task) if task else self._fail("Task not found")
            if action == "list":
                return self._ok(manager.list(params.get("status")))
            if action == "pause":
                return self._ok(manager.pause(str(params.get("task_id", ""))))
            if action == "resume":
                return self._ok(manager.resume(str(params.get("task_id", ""))))
            if action == "cancel":
                return self._ok(manager.cancel(str(params.get("task_id", ""))))
            return self._fail(f"Unknown action: {action}")
        except Exception as exc:
            return self._fail(str(exc))

    @staticmethod
    def _ok(value: Any) -> ToolResult:
        return ToolResult(
            tool_name="long_task",
            content=json.dumps(value, indent=2, default=str),
            success=True,
        )

    @staticmethod
    def _fail(message: str) -> ToolResult:
        return ToolResult(tool_name="long_task", content=message, success=False)


__all__ = ["CreativeMediaTool", "LongTaskTool"]
