"""Vehicle Playback Engine reading solely from local SQLite cache."""

import time
import logging
from typing import Dict, Any, Optional
from vehicle.cache import VehicleCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vehicle_playback")


class PlaybackEngine:
    """
    Simulates the in-vehicle media playback engine.
    Reads exclusively from local SQLite preferences cache — completely isolated from network operations.
    """

    def __init__(self, cache: VehicleCache, default_volume: float = 50.0, default_genre: str = "acoustic"):
        self.cache = cache
        self.current_volume: float = default_volume
        self.current_genre: str = default_genre
        self.current_version: int = 0
        self.playback_history: list = []

    def tick(self) -> Dict[str, Any]:
        """
        Execute a single playback cycle by querying the local SQLite cache.
        Returns the active playback parameters.
        """
        latest = self.cache.get_latest_snapshot()
        if latest:
            version = latest["version"]
            snapshot = latest["snapshot"]

            if version != self.current_version:
                logger.info(
                    f"[PlaybackEngine] Detected updated preferences (v{self.current_version} -> v{version}): {snapshot}"
                )
                self.current_version = version

            # Apply preference fields from snapshot
            if "volume" in snapshot:
                self.current_volume = float(snapshot["volume"])
            if "genre" in snapshot:
                self.current_genre = str(snapshot["genre"])

        state = {
            "version": self.current_version,
            "volume": self.current_volume,
            "genre": self.current_genre,
            "timestamp": time.time(),
        }
        self.playback_history.append(state)
        return state

    def get_current_state(self) -> Dict[str, Any]:
        """Return the current playback state without advancing the loop."""
        return {
            "version": self.current_version,
            "volume": self.current_volume,
            "genre": self.current_genre,
        }
