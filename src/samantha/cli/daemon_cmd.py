"""``samantha start|stop|restart|status`` — daemon management commands."""

from __future__ import annotations

import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import click
from rich.console import Console

from samantha.core.config import DEFAULT_CONFIG_DIR, load_config
from samantha.core.utils import process_alive, terminate_process

_PID_FILE = DEFAULT_CONFIG_DIR / "server.pid"
_LOG_FILE = DEFAULT_CONFIG_DIR / "server.log"


def _pid_alive(pid: int) -> bool:
    """Return whether *pid* identifies a running process without signaling it."""
    return process_alive(pid)


def _read_pid() -> int | None:
    """Read PID from pid file, return None if not found or stale."""
    if not _PID_FILE.exists():
        return None
    try:
        pid = int(_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        _PID_FILE.unlink(missing_ok=True)
        return None
    # Check if process is still running (non-destructive, cross-platform).
    if not _pid_alive(pid):
        _PID_FILE.unlink(missing_ok=True)
        return None
    return pid


def _write_pid(pid: int) -> None:
    """Write PID to pid file."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(pid))


def _server_healthy(host: str, port: int) -> bool:
    """Return whether a Samantha-compatible health endpoint is reachable."""
    try:
        with urlopen(f"http://{host}:{port}/health", timeout=0.5) as response:  # noqa: S310
            return response.status == 200
    except (OSError, URLError, ValueError):
        return False


@click.group()
def daemon() -> None:
    """Manage the Samantha server daemon."""


@daemon.command()
@click.option("--host", default=None, help="Bind address.")
@click.option("--port", default=None, type=int, help="Port number.")
@click.option("-e", "--engine", "engine_key", default=None, help="Engine backend.")
@click.option("-m", "--model", "model_name", default=None, help="Default model.")
@click.option("-a", "--agent", "agent_name", default=None, help="Agent type.")
def start(
    host: str | None,
    port: int | None,
    engine_key: str | None,
    model_name: str | None,
    agent_name: str | None,
) -> None:
    """Start the Samantha server as a background daemon."""
    console = Console(stderr=True)

    existing = _read_pid()
    if existing is not None:
        console.print(f"[yellow]Server already running (PID {existing}).[/yellow]")
        console.print("Use 'samantha stop' to stop it first, or 'samantha restart'.")
        sys.exit(1)

    config = load_config()
    bind_host = host or config.server.host
    bind_port = port or config.server.port
    if _server_healthy(bind_host, bind_port):
        console.print(
            f"[yellow]A Samantha server is already reachable at "
            f"http://{bind_host}:{bind_port}.[/yellow]"
        )
        sys.exit(1)

    # Build command to run samantha serve
    cmd = [sys.executable, "-m", "samantha.cli", "serve"]
    if host:
        cmd.extend(["--host", host])
    if port:
        cmd.extend(["--port", str(port)])
    if engine_key:
        cmd.extend(["--engine", engine_key])
    if model_name:
        cmd.extend(["--model", model_name])
    if agent_name:
        cmd.extend(["--agent", agent_name])

    # Start as background process, fully detached from the launching terminal.
    #
    # ``start_new_session`` is POSIX-only: CPython's Windows ``_execute_child``
    # names the parameter ``unused_start_new_session`` and ignores it. Relying
    # on it there leaves the server sharing its parent's console, so closing
    # that console — or logging off — delivers CTRL_CLOSE_EVENT and kills the
    # daemon. DETACHED_PROCESS gives it no console at all; the new process
    # group additionally stops a Ctrl-C in the parent reaching it.
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    log_fh = open(_LOG_FILE, "a")  # noqa: SIM115
    spawn_kwargs: dict = {}
    if sys.platform == "win32":
        spawn_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        spawn_kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=log_fh,
        **spawn_kwargs,
    )
    # Do not publish a PID until the child survives startup. This prevents a
    # port collision or configuration error from being reported as success.
    for _ in range(50):
        if proc.poll() is not None:
            log_fh.close()
            console.print(
                f"[red]Samantha server failed to start. See {_LOG_FILE}.[/red]"
            )
            sys.exit(1)
        if _server_healthy(bind_host, bind_port):
            break
        time.sleep(0.1)
    else:
        proc.terminate()
        log_fh.close()
        console.print(
            f"[red]Samantha server did not become healthy. See {_LOG_FILE}.[/red]"
        )
        sys.exit(1)

    _write_pid(proc.pid)
    log_fh.close()

    console.print(
        f"[green]Samantha server started[/green] (PID {proc.pid})\n"
        f"  URL: http://{bind_host}:{bind_port}\n"
        f"  Log: {_LOG_FILE}"
    )


@daemon.command()
def stop() -> None:
    """Stop the running Samantha server daemon."""
    console = Console(stderr=True)
    pid = _read_pid()
    if pid is None:
        console.print("[yellow]No running server found.[/yellow]")
        sys.exit(1)

    # Graceful shutdown (SIGTERM / taskkill), escalating to a forced kill after
    # 10s if still running. Cross-platform — no POSIX-only os.kill/SIGKILL.
    terminate_process(pid, grace_seconds=10.0)

    _PID_FILE.unlink(missing_ok=True)
    console.print(f"[green]Server stopped[/green] (PID {pid}).")


@daemon.command()
@click.pass_context
def restart(ctx: click.Context) -> None:
    """Restart the Samantha server daemon."""
    console = Console(stderr=True)
    pid = _read_pid()
    if pid is not None:
        console.print(f"Stopping server (PID {pid})...")
        ctx.invoke(stop)
    ctx.invoke(start)


@daemon.command()
def status() -> None:
    """Show status of the Samantha server daemon."""
    console = Console(stderr=True)
    pid = _read_pid()
    if pid is None:
        console.print("[yellow]Server is not running.[/yellow]")
        return

    # Get process info
    uptime_info = ""
    try:
        import psutil

        proc = psutil.Process(pid)
        uptime = time.time() - proc.create_time()
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_info = f"\n  Uptime: {hours}h {minutes}m {seconds}s"
    except (ImportError, Exception):
        pass

    config = load_config()
    console.print(
        f"[green]Server is running[/green] (PID {pid}){uptime_info}\n"
        f"  URL: http://{config.server.host}:{config.server.port}\n"
        f"  Log: {_LOG_FILE}"
    )


__all__ = ["daemon", "start", "stop", "restart", "status"]
