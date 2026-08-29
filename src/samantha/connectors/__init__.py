"""Data source connectors for Deep Research."""

from samantha.connectors._stubs import (
    Attachment,
    BaseConnector,
    Document,
    SyncStatus,
)
from samantha.connectors.store import KnowledgeStore

__all__ = ["Attachment", "BaseConnector", "Document", "KnowledgeStore", "SyncStatus"]

# Auto-register built-in connectors
import samantha.connectors.obsidian  # noqa: F401

try:
    import samantha.connectors.gmail  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.gmail_imap  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.gdrive  # noqa: F401
except ImportError:
    pass  # httpx may not be installed

try:
    import samantha.connectors.notion  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.granola  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.gcontacts  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.imessage  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.apple_notes  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.apple_music  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.apple_contacts  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.apple_calendar  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.slack_connector  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.outlook  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.imap  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.gcalendar  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.dropbox  # noqa: F401
except ImportError:
    pass  # httpx may not be installed

try:
    import samantha.connectors.whatsapp  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.oura  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.apple_health  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.strava  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.spotify  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.google_tasks  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.weather  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.github_notifications  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.hackernews  # noqa: F401
except ImportError:
    pass

try:
    import samantha.connectors.news_rss  # noqa: F401
except ImportError:
    pass
