"""Durable background task manager for Samantha's long-running work."""
# ruff: noqa: E501

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LongTaskManager:
    """SQLite-backed background jobs with cooperative checkpoints."""

    def __init__(self, db_path: str | Path, *, max_workers: int = 2) -> None:
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="samantha-task",
        )
        self._runner: Optional[Callable[..., str]] = None
        self._futures: dict[str, Any] = {}
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS long_tasks (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    checkpoint TEXT NOT NULL DEFAULT '{}',
                    result TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    pause_requested INTEGER NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0
                )"""
            )
            # A process crash must never leave a job permanently "running".
            self._db.execute(
                "UPDATE long_tasks SET status='queued', updated_at=? "
                "WHERE status IN ('running', 'pausing')",
                (_now(),),
            )
            self._db.commit()

    def configure(self, runner: Callable[..., str]) -> None:
        self._runner = runner
        # Recover queued jobs once a runner is available.
        for task in self.list(status="queued"):
            self._submit(task["id"])

    def create(
        self, goal: str, *, metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        if not goal.strip():
            raise ValueError("goal is required")
        now = _now()
        task_id = f"samantha-{uuid.uuid4().hex[:12]}"
        checkpoint = {"phase": "created", "metadata": metadata or {}}
        with self._lock:
            self._db.execute(
                "INSERT INTO long_tasks(id,goal,status,created_at,updated_at,checkpoint) VALUES(?,?,?,?,?,?)",
                (task_id, goal.strip(), "queued", now, now, json.dumps(checkpoint)),
            )
            self._db.commit()
        self._submit(task_id)
        return self.get(task_id) or {}

    def get(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM long_tasks WHERE id=?", (task_id,)
            ).fetchone()
        return self._row(row) if row else None

    def list(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            if status:
                rows = self._db.execute(
                    "SELECT * FROM long_tasks WHERE status=? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT * FROM long_tasks ORDER BY created_at DESC"
                ).fetchall()
        return [self._row(row) for row in rows]

    def pause(self, task_id: str) -> dict[str, Any]:
        self._require(task_id)
        with self._lock:
            self._db.execute(
                "UPDATE long_tasks SET pause_requested=1,status='pausing',updated_at=? WHERE id=?",
                (_now(), task_id),
            )
            self._db.commit()
        return self.get(task_id) or {}

    def resume(self, task_id: str) -> dict[str, Any]:
        self._require(task_id)
        with self._lock:
            self._db.execute(
                "UPDATE long_tasks SET pause_requested=0,cancel_requested=0,status='queued',error='',updated_at=? WHERE id=?",
                (_now(), task_id),
            )
            self._db.commit()
        self._submit(task_id)
        return self.get(task_id) or {}

    def cancel(self, task_id: str) -> dict[str, Any]:
        self._require(task_id)
        with self._lock:
            self._db.execute(
                "UPDATE long_tasks SET cancel_requested=1,updated_at=? WHERE id=?",
                (_now(), task_id),
            )
            self._db.commit()
        return self.get(task_id) or {}

    def checkpoint(
        self,
        task_id: str,
        *,
        progress: Optional[float] = None,
        phase: Optional[str] = None,
        **data: Any,
    ) -> None:
        task = self.get(task_id)
        if not task:
            return
        checkpoint = dict(task.get("checkpoint") or {})
        if phase is not None:
            checkpoint["phase"] = phase
        checkpoint.update(data)
        with self._lock:
            if progress is None:
                self._db.execute(
                    "UPDATE long_tasks SET checkpoint=?,updated_at=? WHERE id=?",
                    (json.dumps(checkpoint, default=str), _now(), task_id),
                )
            else:
                self._db.execute(
                    "UPDATE long_tasks SET checkpoint=?,progress=?,updated_at=? WHERE id=?",
                    (
                        json.dumps(checkpoint, default=str),
                        max(0.0, min(1.0, float(progress))),
                        _now(),
                        task_id,
                    ),
                )
            self._db.commit()

    def is_paused(self, task_id: str) -> bool:
        task = self.get(task_id)
        return bool(task and task["pause_requested"])

    def is_cancelled(self, task_id: str) -> bool:
        task = self.get(task_id)
        return bool(task and task["cancel_requested"])

    def _submit(self, task_id: str) -> None:
        if self._runner is None:
            return
        old = self._futures.get(task_id)
        if old is not None and not old.done():
            return
        self._futures[task_id] = self._executor.submit(self._run, task_id)

    def _run(self, task_id: str) -> None:
        runner = self._runner
        task = self.get(task_id)
        if runner is None or task is None:
            return
        with self._lock:
            self._db.execute(
                "UPDATE long_tasks SET status='running',updated_at=? WHERE id=?",
                (_now(), task_id),
            )
            self._db.commit()
        try:
            result = runner(
                task,
                lambda **kwargs: self.checkpoint(task_id, **kwargs),
                lambda: self.is_cancelled(task_id),
                lambda: self.is_paused(task_id),
            )
            if self.is_cancelled(task_id):
                status = "cancelled"
            elif self.is_paused(task_id):
                status = "paused"
            else:
                status = "completed"
            with self._lock:
                self._db.execute(
                    "UPDATE long_tasks SET status=?,progress=?,result=?,updated_at=? WHERE id=?",
                    (
                        status,
                        1.0
                        if status == "completed"
                        else (self.get(task_id) or {}).get("progress", 0),
                        result or "",
                        _now(),
                        task_id,
                    ),
                )
                self._db.commit()
        except Exception as exc:
            with self._lock:
                self._db.execute(
                    "UPDATE long_tasks SET status='failed',error=?,updated_at=? WHERE id=?",
                    (str(exc), _now(), task_id),
                )
                self._db.commit()

    def _require(self, task_id: str) -> None:
        if self.get(task_id) is None:
            raise KeyError(f"Task not found: {task_id}")

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        try:
            data["checkpoint"] = json.loads(data["checkpoint"] or "{}")
        except (TypeError, json.JSONDecodeError):
            data["checkpoint"] = {}
        return data

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)
        self._db.close()


__all__ = ["LongTaskManager"]
