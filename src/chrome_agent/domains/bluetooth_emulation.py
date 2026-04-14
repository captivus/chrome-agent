"""CDP BluetoothEmulation domain.

This domain allows configuring virtual Bluetooth devices to test
the web-bluetooth API.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Indicates the various states of Central.
CentralState = str  # Literal enum: "absent", "powered-off", "powered-on"

# Indicates the various types of GATT event.
GATTOperationType = str  # Literal enum: "connection", "discovery"

# Indicates the various types of characteristic write.
CharacteristicWriteType = str  # Literal enum: "write-default-deprecated", "write-with-response", "write-without-response"

# Indicates the various types of characteristic operation.
CharacteristicOperationType = str  # Literal enum: "read", "write", "subscribe-to-notifications", "unsubscribe-from-notifications"

# Indicates the various types of descriptor operation.
DescriptorOperationType = str  # Literal enum: "read", "write"

# Stores the manufacturer data
ManufacturerData = dict  # Object type

# Stores the byte data of the advertisement packet sent by a Bluetooth device.
ScanRecord = dict  # Object type

# Stores the advertisement packet information that is sent by a Bluetooth device.
ScanEntry = dict  # Object type

# Describes the properties of a characteristic. This follows Bluetooth Core
# Specification BT 4.2 Vol 3 Part G 3.3.1. Characteristic Properties.
CharacteristicProperties = dict  # Object type

class BluetoothEmulation:
    """This domain allows configuring virtual Bluetooth devices to test
the web-bluetooth API."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self, state: CentralState, le_supported: bool) -> dict:
        """Enable the BluetoothEmulation domain."""
        params: dict[str, Any] = {}
        params["state"] = state
        params["leSupported"] = le_supported
        return await self._client.send(method="BluetoothEmulation.enable", params=params)

    async def set_simulated_central_state(self, state: CentralState) -> dict:
        """Set the state of the simulated central."""
        params: dict[str, Any] = {}
        params["state"] = state
        return await self._client.send(method="BluetoothEmulation.setSimulatedCentralState", params=params)

    async def disable(self) -> dict:
        """Disable the BluetoothEmulation domain."""
        return await self._client.send(method="BluetoothEmulation.disable")

    async def simulate_preconnected_peripheral(
        self,
        address: str,
        name: str,
        manufacturer_data: list[ManufacturerData],
        known_service_uuids: list[str],
    ) -> dict:
        """Simulates a peripheral with |address|, |name| and |knownServiceUuids|
that has already been connected to the system.
        """
        params: dict[str, Any] = {}
        params["address"] = address
        params["name"] = name
        params["manufacturerData"] = manufacturer_data
        params["knownServiceUuids"] = known_service_uuids
        return await self._client.send(method="BluetoothEmulation.simulatePreconnectedPeripheral", params=params)

    async def simulate_advertisement(self, entry: ScanEntry) -> dict:
        """Simulates an advertisement packet described in |entry| being received by
the central.
        """
        params: dict[str, Any] = {}
        params["entry"] = entry
        return await self._client.send(method="BluetoothEmulation.simulateAdvertisement", params=params)

    async def simulate_gatt_operation_response(
        self,
        address: str,
        type_: GATTOperationType,
        code: int,
    ) -> dict:
        """Simulates the response code from the peripheral with |address| for a
GATT operation of |type|. The |code| value follows the HCI Error Codes from
Bluetooth Core Specification Vol 2 Part D 1.3 List Of Error Codes.
        """
        params: dict[str, Any] = {}
        params["address"] = address
        params["type"] = type_
        params["code"] = code
        return await self._client.send(method="BluetoothEmulation.simulateGATTOperationResponse", params=params)

    async def simulate_characteristic_operation_response(
        self,
        characteristic_id: str,
        type_: CharacteristicOperationType,
        code: int,
        data: str | None = None,
    ) -> dict:
        """Simulates the response from the characteristic with |characteristicId| for a
characteristic operation of |type|. The |code| value follows the Error
Codes from Bluetooth Core Specification Vol 3 Part F 3.4.1.1 Error Response.
The |data| is expected to exist when simulating a successful read operation
response.
        """
        params: dict[str, Any] = {}
        params["characteristicId"] = characteristic_id
        params["type"] = type_
        params["code"] = code
        if data is not None:
            params["data"] = data
        return await self._client.send(method="BluetoothEmulation.simulateCharacteristicOperationResponse", params=params)

    async def simulate_descriptor_operation_response(
        self,
        descriptor_id: str,
        type_: DescriptorOperationType,
        code: int,
        data: str | None = None,
    ) -> dict:
        """Simulates the response from the descriptor with |descriptorId| for a
descriptor operation of |type|. The |code| value follows the Error
Codes from Bluetooth Core Specification Vol 3 Part F 3.4.1.1 Error Response.
The |data| is expected to exist when simulating a successful read operation
response.
        """
        params: dict[str, Any] = {}
        params["descriptorId"] = descriptor_id
        params["type"] = type_
        params["code"] = code
        if data is not None:
            params["data"] = data
        return await self._client.send(method="BluetoothEmulation.simulateDescriptorOperationResponse", params=params)

    async def add_service(self, address: str, service_uuid: str) -> dict:
        """Adds a service with |serviceUuid| to the peripheral with |address|."""
        params: dict[str, Any] = {}
        params["address"] = address
        params["serviceUuid"] = service_uuid
        return await self._client.send(method="BluetoothEmulation.addService", params=params)

    async def remove_service(self, service_id: str) -> dict:
        """Removes the service respresented by |serviceId| from the simulated central."""
        params: dict[str, Any] = {}
        params["serviceId"] = service_id
        return await self._client.send(method="BluetoothEmulation.removeService", params=params)

    async def add_characteristic(
        self,
        service_id: str,
        characteristic_uuid: str,
        properties: CharacteristicProperties,
    ) -> dict:
        """Adds a characteristic with |characteristicUuid| and |properties| to the
service represented by |serviceId|.
        """
        params: dict[str, Any] = {}
        params["serviceId"] = service_id
        params["characteristicUuid"] = characteristic_uuid
        params["properties"] = properties
        return await self._client.send(method="BluetoothEmulation.addCharacteristic", params=params)

    async def remove_characteristic(self, characteristic_id: str) -> dict:
        """Removes the characteristic respresented by |characteristicId| from the
simulated central.
        """
        params: dict[str, Any] = {}
        params["characteristicId"] = characteristic_id
        return await self._client.send(method="BluetoothEmulation.removeCharacteristic", params=params)

    async def add_descriptor(self, characteristic_id: str, descriptor_uuid: str) -> dict:
        """Adds a descriptor with |descriptorUuid| to the characteristic respresented
by |characteristicId|.
        """
        params: dict[str, Any] = {}
        params["characteristicId"] = characteristic_id
        params["descriptorUuid"] = descriptor_uuid
        return await self._client.send(method="BluetoothEmulation.addDescriptor", params=params)

    async def remove_descriptor(self, descriptor_id: str) -> dict:
        """Removes the descriptor with |descriptorId| from the simulated central."""
        params: dict[str, Any] = {}
        params["descriptorId"] = descriptor_id
        return await self._client.send(method="BluetoothEmulation.removeDescriptor", params=params)

    async def simulate_gatt_disconnection(self, address: str) -> dict:
        """Simulates a GATT disconnection from the peripheral with |address|."""
        params: dict[str, Any] = {}
        params["address"] = address
        return await self._client.send(method="BluetoothEmulation.simulateGATTDisconnection", params=params)
