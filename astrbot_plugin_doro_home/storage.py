from __future__ import annotations

import random
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence


@dataclass(frozen=True)
class DrawResult:
    ending_name: str
    image_file: str
    is_new_today: bool
    total_times: int


class DoroStore:
    """Small SQLite store for daily draws, collections, and history messages."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS daily_draws (
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    draw_date TEXT NOT NULL,
                    ending_name TEXT NOT NULL,
                    image_file TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (group_id, user_id, draw_date)
                );

                CREATE TABLE IF NOT EXISTS collections (
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    ending_name TEXT NOT NULL,
                    image_file TEXT NOT NULL,
                    draw_count INTEGER NOT NULL DEFAULT 1,
                    first_drawn_at REAL NOT NULL,
                    last_drawn_at REAL NOT NULL,
                    PRIMARY KEY (group_id, user_id, ending_name)
                );

                CREATE TABLE IF NOT EXISTS history_messages (
                    source_group_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    received_at REAL NOT NULL,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    last_used_at REAL,
                    PRIMARY KEY (source_group_id, message_id)
                );

                CREATE INDEX IF NOT EXISTS idx_collection_owner
                    ON collections (group_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_history_source
                    ON history_messages (source_group_id, received_at);
                """
            )

    def draw_ending(
        self,
        group_id: str,
        user_id: str,
        draw_date: str,
        candidates: Sequence[tuple[str, str]],
    ) -> DrawResult:
        if not candidates:
            raise ValueError("No Doro endings are available")

        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT ending_name, image_file
                FROM daily_draws
                WHERE group_id = ? AND user_id = ? AND draw_date = ?
                """,
                (group_id, user_id, draw_date),
            ).fetchone()

            if existing:
                count_row = connection.execute(
                    """
                    SELECT draw_count FROM collections
                    WHERE group_id = ? AND user_id = ? AND ending_name = ?
                    """,
                    (group_id, user_id, existing["ending_name"]),
                ).fetchone()
                return DrawResult(
                    ending_name=existing["ending_name"],
                    image_file=existing["image_file"],
                    is_new_today=False,
                    total_times=int(count_row["draw_count"]) if count_row else 1,
                )

            ending_name, image_file = random.SystemRandom().choice(list(candidates))
            now = time.time()
            connection.execute(
                """
                INSERT INTO daily_draws
                    (group_id, user_id, draw_date, ending_name, image_file, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, user_id, draw_date, ending_name, image_file, now),
            )
            connection.execute(
                """
                INSERT INTO collections
                    (group_id, user_id, ending_name, image_file, draw_count,
                     first_drawn_at, last_drawn_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(group_id, user_id, ending_name) DO UPDATE SET
                    image_file = excluded.image_file,
                    draw_count = collections.draw_count + 1,
                    last_drawn_at = excluded.last_drawn_at
                """,
                (group_id, user_id, ending_name, image_file, now, now),
            )
            count_row = connection.execute(
                """
                SELECT draw_count FROM collections
                WHERE group_id = ? AND user_id = ? AND ending_name = ?
                """,
                (group_id, user_id, ending_name),
            ).fetchone()
            return DrawResult(
                ending_name=ending_name,
                image_file=image_file,
                is_new_today=True,
                total_times=int(count_row["draw_count"]),
            )

    def get_collection(self, group_id: str, user_id: str) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ending_name, draw_count
                FROM collections
                WHERE group_id = ? AND user_id = ?
                ORDER BY first_drawn_at ASC
                """,
                (group_id, user_id),
            ).fetchall()
        return {row["ending_name"]: int(row["draw_count"]) for row in rows}

    def record_history(
        self, source_group_id: str, message_id: str, received_at: float | None = None
    ) -> None:
        timestamp = float(received_at if received_at is not None else time.time())
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO history_messages
                    (source_group_id, message_id, received_at)
                VALUES (?, ?, ?)
                ON CONFLICT(source_group_id, message_id) DO NOTHING
                """,
                (source_group_id, message_id, timestamp),
            )
            connection.execute(
                """
                DELETE FROM history_messages
                WHERE rowid IN (
                    SELECT rowid FROM history_messages
                    ORDER BY received_at DESC
                    LIMIT -1 OFFSET 5000
                )
                """
            )

    def import_history(
        self, source_group_id: str, entries: Iterable[tuple[str, float]]
    ) -> int:
        imported = 0
        with self._lock, self._connect() as connection:
            for message_id, received_at in entries:
                cursor = connection.execute(
                    """
                    INSERT INTO history_messages
                        (source_group_id, message_id, received_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(source_group_id, message_id) DO NOTHING
                    """,
                    (str(source_group_id), str(message_id), float(received_at)),
                )
                imported += max(0, cursor.rowcount)
        return imported

    def pick_history(self, source_group_ids: Sequence[str]) -> tuple[str, str] | None:
        source_ids = [str(item) for item in source_group_ids if str(item).strip()]
        if not source_ids:
            return None
        placeholders = ",".join("?" for _ in source_ids)
        query = f"""
            SELECT source_group_id, message_id
            FROM history_messages
            WHERE source_group_id IN ({placeholders})
            ORDER BY use_count ASC, RANDOM()
            LIMIT 1
        """
        with self._connect() as connection:
            row = connection.execute(query, source_ids).fetchone()
        if not row:
            return None
        return str(row["source_group_id"]), str(row["message_id"])

    def mark_history_used(self, source_group_id: str, message_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE history_messages
                SET use_count = use_count + 1, last_used_at = ?
                WHERE source_group_id = ? AND message_id = ?
                """,
                (time.time(), str(source_group_id), str(message_id)),
            )

    def remove_history(self, source_group_id: str, message_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                DELETE FROM history_messages
                WHERE source_group_id = ? AND message_id = ?
                """,
                (str(source_group_id), str(message_id)),
            )

    def history_count(self, source_group_ids: Sequence[str]) -> int:
        source_ids = [str(item) for item in source_group_ids if str(item).strip()]
        if not source_ids:
            return 0
        placeholders = ",".join("?" for _ in source_ids)
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM history_messages
                WHERE source_group_id IN ({placeholders})
                """,
                source_ids,
            ).fetchone()
        return int(row["count"])
