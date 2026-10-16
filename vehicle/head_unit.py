"""Vehicle Head Unit handling MQTT preference synchronization and cache management."""

import json
import logging
from typing import Optional, Callable, Dict, Any
import requests
import paho.mqtt.client as mqtt

from vehicle.cache import VehicleCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vehicle_head_unit")


class HeadUnit:
    """In-vehicle head unit that receives merged snapshots and syncs to SQLite."""

    def __init__(
        self,
        user_id: str,
        cache_db_path: str = "vehicle_preferences.db",
        broker_host: str = "localhost",
        broker_port: int = 1883,
        resolver_api_url: str = "http://localhost:8000",
    ):
        self.user_id = user_id
        self.cache = VehicleCache(db_path=cache_db_path)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.resolver_api_url = resolver_api_url
        self.mqtt_client: Optional[mqtt.Client] = None
        self.on_preference_updated_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set a callback invoked when a new preference version is cached."""
        self.on_preference_updated_callback = callback

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"[HeadUnit] Connected to MQTT broker with rc={rc}")
        topic = f"users/{self.user_id}/preferences"
        client.subscribe(topic, qos=1)
        logger.info(f"[HeadUnit] Subscribed to topic: {topic}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            version = payload.get("version")
            snapshot = payload.get("snapshot", {})
            created_at = payload.get("created_at")

            if version is not None:
                self.cache.store_snapshot(version, snapshot, created_at)
                logger.info(
                    f"[HeadUnit] Received and cached snapshot version {version}: {snapshot}"
                )
                if self.on_preference_updated_callback:
                    self.on_preference_updated_callback(snapshot)
        except Exception as e:
            logger.error(f"[HeadUnit] Error processing preference message: {e}")

    def connect(self):
        """Connect to MQTT broker."""
        self.mqtt_client = mqtt.Client(
            client_id=f"head_unit_{self.user_id}",
            protocol=mqtt.MQTTv311,
        )
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.mqtt_client.loop_start()

    def disconnect(self):
        """Disconnect from MQTT broker (simulate offline mode)."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None
            logger.info("[HeadUnit] Disconnected from MQTT broker (offline mode).")

    def sync_recovery_from_cloud(self) -> Optional[Dict[str, Any]]:
        """
        Query cloud resolver service on reconnect with last_known_version to fetch latest snapshot.
        """
        last_version = self.cache.get_latest_cached_version()
        try:
            url = f"{self.resolver_api_url}/users/{self.user_id}/preferences/latest"
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                cloud_version = data.get("version", 0)
                if cloud_version > last_version:
                    self.cache.store_snapshot(
                        version=cloud_version,
                        snapshot=data.get("snapshot", {}),
                        synced_at=data.get("created_at"),
                    )
                    logger.info(
                        f"[HeadUnit] Synced newer version {cloud_version} from cloud (local was {last_version})"
                    )
                return data
            elif resp.status_code == 404:
                logger.info("[HeadUnit] No snapshot available on cloud yet.")
                return None
        except Exception as e:
            logger.warning(f"[HeadUnit] Cloud sync recovery failed: {e}")
            return None
