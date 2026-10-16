"""In-vehicle head unit device simulator with confidence weight = 0.9."""

from simulators.base_client import DeviceSimulator


class CarSimulator(DeviceSimulator):
    def __init__(self, user_id: str, device_id: str = "car_01", broker_host: str = "localhost", broker_port: int = 1883):
        super().__init__(
            device_id=device_id,
            source_type="car",
            user_id=user_id,
            broker_host=broker_host,
            broker_port=broker_port,
        )
