"""Tools primitive — tool system with ABC interface and built-in tools."""

from __future__ import annotations

from samantha.tools._stubs import BaseTool, ToolExecutor, ToolSpec

try:
    import samantha.tools.calculator  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.think  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.llm_tool  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.file_read  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.web_search  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.code_interpreter  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.code_interpreter_docker  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.repl  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.storage_tools  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.mcp_adapter  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.channel_tools  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.http_request  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.docker_shell_exec  # noqa: F401
    import samantha.tools.shell_exec  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.memory_manage  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.user_profile_manage  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.skill_manage  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.file_write  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.apply_patch  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.git_tool  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.db_query  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.pdf_tool  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.image_tool  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.audio_tool  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.knowledge_tools  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.text_to_speech  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.digest_collect  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.scan_chunks  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.knowledge_sql  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.apple_calendar  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.macos_control  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.office  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.office_control  # noqa: F401
except ImportError:
    pass
try:
    import samantha.tools.creative_media  # noqa: F401
except ImportError:
    pass

__all__ = ["BaseTool", "ToolExecutor", "ToolSpec"]
