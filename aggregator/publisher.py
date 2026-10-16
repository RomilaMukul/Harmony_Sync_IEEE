"""Privacy-guarded MQTT publisher for Edge Pre-Aggregation Layer."""

import json
import logging
from typing import Optional
import paho.mqtt.client as mqtt

from aggregator.models import DeltaPayload
from aggregator.privacy import assert_no_raw_data_leaked

logger = logging.getLogger("edge_publisher")


def publish_delta_to_mqtt(
    client: mqtt.Client,
    payload: DeltaPayload,
    qos: int = 1,
) -> bool:
    """
    Publish pre-aggregated delta payload to MQTT topic users/{user_id}/updates/{device_id}.
    HARD PRIVACY GATE: Cannot be transmitted if assert_no_raw_data_leaked() fails.
    """
    # STEP 6 HARD GATE: Verify zero raw data leakage before touching network socket
    assert_no_raw_data_leaked(payload)

    topic = f"users/{payload.user_id}/updates/{payload.device_id}"
    payload_json = json.dumps(payload.model_dump())

    if client and client.is_connected():
        client.publish(topic, payload_json, qos=qos)
        logger.info(f"Published privacy-guarded delta to {topic}: {payload.field_updates}")
        return True
    else:
        logger.warning(f"MQTT client not connected; could not publish to {topic}")
        return False
