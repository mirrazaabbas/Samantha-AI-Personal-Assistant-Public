# Privacy

Samantha is designed so each installation keeps its personal runtime data on
that user's device under `~/.samantha`. The public source repository does not
contain any user's memory, profile, voiceprint, recordings, credentials,
calendar, email, databases, schedules, conversations, or logs.

Runtime files and common credential files are excluded by `.gitignore`.
Configuration examples contain no working credentials. Telemetry, analytics,
and traces are disabled by default.

Local storage does not mean every optional feature is offline. Web search,
cloud model providers, connectors, and media services send the query or content
required to the service selected by the user. Review configuration and tool
permissions before enabling those features.

Never commit `~/.samantha`, `.env` files, tokens, API keys, voiceprints,
recordings, databases, or logs. Revoke and rotate any credential that is ever
committed, even if the commit is later removed.
