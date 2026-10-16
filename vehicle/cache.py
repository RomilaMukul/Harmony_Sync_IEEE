"""Vehicle-side local SQLite preference cache."""

import sqlite3
import json
from contextlib import closing
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple


class VehicleCache:
    """Local SQLite cache storing immutable preference snapshot versions."""

    def __init__(self, db_path: str = "vehicle_preferences.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with closing(self._connect()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS preferences_cache (
                        version INTEGER PRIMARY KEY,
                        snapshot TEXT NOT NULL,
                        synced_at TIMESTAMP NOT NULL
                    )
                    """
                )

    def store_snapshot(self, version: int, snapshot: Dict[str, Any], synced_at: Optional[str] = None) -> bool:
        """Store or update a snapshot version in local SQLite cache."""
        ts = synced_at or datetime.now(timezone.utc).isoformat()
        snapshot_json = json.dumps(snapshot)
        with closing(self._connect()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO preferences_cache (version, snapshot, synced_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(version) DO UPDATE SET
                        snapshot=excluded.snapshot,
                        synced_at=excluded.synced_at
                    """,
                    (version, snapshot_json, ts),
                )
            return True

    def get_latest_cached_version(self) -> int:
        """Get the highest snapshot version currently stored in local cache."""
        with closing(self._connect()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version FROM preferences_cache ORDER BY version DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return row["version"] if row else 0

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Retrieve the latest preference snapshot dict from cache."""
        with closing(self._connect()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version, snapshot, synced_at FROM preferences_cache ORDER BY version DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "version": row["version"],
                "snapshot": json.loads(row["snapshot"]),
                "synced_at": row["synced_at"],
            }

    def get_snapshot_by_version(self, version: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific version from local cache."""
        with closing(self._connect()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version, snapshot, synced_at FROM preferences_cache WHERE version = ?",
                (version,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "version": row["version"],
                "snapshot": json.loads(row["snapshot"]),
                "synced_at": row["synced_at"],
            }

