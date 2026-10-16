"""Base client simulator for publishing preference update events over MQTT."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Union, Optional
import paho.mqtt.client as mqtt

from resolver_service.models import CONFIDENCE_WEIGHTS, SourceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("device_simulator")


class DeviceSimulator:
    """Base class for device simulators publishing synthetic preference updates."""

    def __init__(
        self,
        device_id: str,
        source_type: SourceType,
        user_id: str,
        broker_host: str = "localhost",
        broker_port: int = 1883,
    ):
        self.device_id = device_id
        self.source_type = source_type
        self.user_id = user_id
        self.confidence_weight = CONFIDENCE_WEIGHTS.get(source_type, 0.5)
        self.vector_clock: Dict[str, int] = {
            "phone": 0,
            "car": 0,
            "laptop": 0,
        }
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client: Optional[mqtt.Client] = None

    def connect(self):
        """Connect to the MQTT broker."""
        self.client = mqtt.Client(
            client_id=f"sim_{self.device_id}",
            protocol=mqtt.MQTTv311,
        )
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()
        logger.info(f"{self.device_id} ({self.source_type}) connected to MQTT broker at {self.broker_host}:{self.broker_port}")

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None

    def increment_clock(self):
        """Increment this device's logical clock."""
        self.vector_clock[self.source_type] = self.vector_clock.get(self.source_type, 0) + 1

    def create_payload(
        self,
        field_updates: Dict[str, Union[float, str]],
        custom_timestamp: Optional[str] = None,
        custom_clock: Optional[Dict[str, int]] = None,
    ) -> dict:
        """Construct the standardized Preference Update Event payload."""
        if custom_clock:
            clock = custom_clock
        else:
            self.increment_clock()
            clock = dict(self.vector_clock)

        ts = custom_timestamp or datetime.now(timezone.utc).isoformat()

        return {
            "device_id": self.device_id,
            "source_type": self.source_type,
            "user_id": self.user_id,
            "vector_clock": clock,
            "timestamp": ts,
            "confidence_weight": self.confidence_weight,
            "field_updates": field_updates,
        }

    def publish_update(
        self,
        field_updates: Dict[str, Union[float, str]],
        custom_timestamp: Optional[str] = None,
        custom_clock: Optional[Dict[str, int]] = None,
    ) -> dict:
        """Publish an update event to the MQTT broker."""
        payload = self.create_payload(field_updates, custom_timestamp, custom_clock)
        topic = f"users/{self.user_id}/updates/{self.device_id}"

        if self.client and self.client.is_connected():
            self.client.publish(topic, json.dumps(payload), qos=1)
            logger.info(f"[{self.device_id}] Published to {topic}: {payload}")
        else:
            logger.warning(f"[{self.device_id}] MQTT not connected; payload generated: {payload}")

        return payload
