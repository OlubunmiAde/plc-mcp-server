"""
PLC Client - Manages connection and communication with PLCs.
"""

import logging
from typing import Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PLCDriver(ABC):
    """Abstract base class for PLC drivers."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to PLC."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from PLC."""
        pass
    
    @abstractmethod
    async def read_tag(self, tag_name: str) -> Any:
        """Read a single tag."""
        pass
    
    @abstractmethod
    async def read_tags(self, tag_names: list[str]) -> dict[str, Any]:
        """Read multiple tags."""
        pass
    
    @abstractmethod
    async def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write a single tag."""
        pass
    
    @abstractmethod
    async def get_tag_list(self) -> list[dict]:
        """Get list of all tags."""
        pass
    
    @abstractmethod
    async def get_plc_info(self) -> dict:
        """Get PLC information."""
        pass


class DemoPLCDriver(PLCDriver):
    """
    Demo PLC driver with simulated tags for testing.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.connected = False
        
        # Simulated tag values
        self._tags = {
            "Motor1_Running": True,
            "Motor2_Running": False,
            "Tank_Level": 75.5,
            "Tank_Setpoint": 80.0,
            "Conveyor_Speed": 120,
            "Pump1_Status": True,
            "Pump2_Status": False,
            "Alarm_Active": False,
            "Production_Count": 1542,
            "Batch_Number": 42,
            "Temperature_PV": 165.3,
            "Temperature_SP": 170.0,
            "Pressure_PV": 45.2,
            "Pressure_SP": 50.0,
            "Emergency_Stop": False,
            "Safety_Interlock": True,
        }
        
        # Tag metadata
        self._tag_info = {
            "Motor1_Running": {"type": "BOOL", "description": "Motor 1 run status"},
            "Motor2_Running": {"type": "BOOL", "description": "Motor 2 run status"},
            "Tank_Level": {"type": "REAL", "description": "Tank level in %", "unit": "%"},
            "Tank_Setpoint": {"type": "REAL", "description": "Tank level setpoint", "unit": "%"},
            "Conveyor_Speed": {"type": "DINT", "description": "Conveyor speed", "unit": "units/min"},
            "Pump1_Status": {"type": "BOOL", "description": "Pump 1 running"},
            "Pump2_Status": {"type": "BOOL", "description": "Pump 2 running"},
            "Alarm_Active": {"type": "BOOL", "description": "Any alarm active"},
            "Production_Count": {"type": "DINT", "description": "Parts produced today"},
            "Batch_Number": {"type": "DINT", "description": "Current batch number"},
            "Temperature_PV": {"type": "REAL", "description": "Process temperature", "unit": "°F"},
            "Temperature_SP": {"type": "REAL", "description": "Temperature setpoint", "unit": "°F"},
            "Pressure_PV": {"type": "REAL", "description": "Process pressure", "unit": "PSI"},
            "Pressure_SP": {"type": "REAL", "description": "Pressure setpoint", "unit": "PSI"},
            "Emergency_Stop": {"type": "BOOL", "description": "E-Stop activated"},
            "Safety_Interlock": {"type": "BOOL", "description": "Safety interlock OK"},
        }
        
        # Simulated alarms
        self._alarms = [
            {"id": "ALM001", "message": "Tank level high warning", "priority": 2, "active": False, "acknowledged": True},
            {"id": "ALM002", "message": "Motor 2 overload", "priority": 1, "active": False, "acknowledged": True},
            {"id": "ALM003", "message": "Temperature deviation", "priority": 3, "active": False, "acknowledged": False},
        ]
    
    async def connect(self) -> bool:
        logger.info("Demo PLC: Connected (simulated)")
        self.connected = True
        return True
    
    async def disconnect(self):
        logger.info("Demo PLC: Disconnected")
        self.connected = False
    
    async def read_tag(self, tag_name: str) -> Any:
        if tag_name not in self._tags:
            raise ValueError(f"Tag not found: {tag_name}")
        return self._tags[tag_name]
    
    async def read_tags(self, tag_names: list[str]) -> dict[str, Any]:
        result = {}
        for name in tag_names:
            if name in self._tags:
                result[name] = self._tags[name]
            else:
                result[name] = {"error": "Tag not found"}
        return result
    
    async def write_tag(self, tag_name: str, value: Any) -> bool:
        if tag_name not in self._tags:
            raise ValueError(f"Tag not found: {tag_name}")
        self._tags[tag_name] = value
        logger.info(f"Demo PLC: Wrote {tag_name} = {value}")
        return True
    
    async def get_tag_list(self) -> list[dict]:
        tags = []
        for name, value in self._tags.items():
            info = self._tag_info.get(name, {})
            tags.append({
                "name": name,
                "value": value,
                "type": info.get("type", "UNKNOWN"),
                "description": info.get("description", ""),
                "unit": info.get("unit", ""),
            })
        return tags
    
    async def get_plc_info(self) -> dict:
        return {
            "name": "Demo ControlLogix",
            "ip": "192.168.1.10 (simulated)",
            "slot": 0,
            "mode": "RUN",
            "faults": [],
            "uptime": "3d 14h 22m",
            "firmware": "v33.011",
        }
    
    async def get_alarms(self, include_acknowledged: bool = False) -> list[dict]:
        if include_acknowledged:
            return self._alarms
        return [a for a in self._alarms if a["active"] and not a["acknowledged"]]
    
    async def acknowledge_alarm(self, alarm_id: str) -> bool:
        for alarm in self._alarms:
            if alarm["id"] == alarm_id:
                alarm["acknowledged"] = True
                logger.info(f"Demo PLC: Acknowledged alarm {alarm_id}")
                return True
        raise ValueError(f"Alarm not found: {alarm_id}")


class PLCClient:
    """
    PLC Client - Factory and manager for PLC connections.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.driver: Optional[PLCDriver] = None
        
        # Select driver based on config
        if config.get("demo_mode", False):
            self.driver = DemoPLCDriver(config)
        else:
            driver_type = config.get("plc", {}).get("driver", "allen_bradley")
            if driver_type == "allen_bradley":
                from .allen_bradley import AllenBradleyDriver
                self.driver = AllenBradleyDriver(config.get("plc", {}))
            elif driver_type == "siemens":
                from .siemens import SiemensDriver
                self.driver = SiemensDriver(config.get("plc", {}))
            elif driver_type == "modbus":
                from .modbus import ModbusDriver
                self.driver = ModbusDriver(config.get("plc", {}))
            else:
                raise ValueError(f"Unknown PLC driver: {driver_type}")
    
    async def connect(self) -> bool:
        """Connect to the PLC."""
        return await self.driver.connect()
    
    async def disconnect(self):
        """Disconnect from the PLC."""
        await self.driver.disconnect()
    
    async def read_tag(self, tag_name: str) -> Any:
        """Read a single tag value."""
        return await self.driver.read_tag(tag_name)
    
    async def read_tags(self, tag_names: list[str]) -> dict[str, Any]:
        """Read multiple tags."""
        return await self.driver.read_tags(tag_names)
    
    async def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write a tag value."""
        return await self.driver.write_tag(tag_name, value)
    
    async def get_tag_list(self) -> list[dict]:
        """Get all tags."""
        return await self.driver.get_tag_list()
    
    async def get_tag_database(self) -> dict:
        """Get tag database as resource."""
        tags = await self.get_tag_list()
        return {
            "tags": tags,
            "count": len(tags),
        }
    
    async def get_plc_info(self) -> dict:
        """Get PLC information."""
        return await self.driver.get_plc_info()
    
    async def get_alarms(self, include_acknowledged: bool = False) -> list[dict]:
        """Get alarms."""
        if hasattr(self.driver, "get_alarms"):
            return await self.driver.get_alarms(include_acknowledged)
        return []
    
    async def acknowledge_alarm(self, alarm_id: str) -> bool:
        """Acknowledge an alarm."""
        if hasattr(self.driver, "acknowledge_alarm"):
            return await self.driver.acknowledge_alarm(alarm_id)
        raise NotImplementedError("Alarm acknowledgment not supported by this driver")
    
    async def get_alarm_config(self) -> dict:
        """Get alarm configuration as resource."""
        alarms = await self.get_alarms(include_acknowledged=True)
        return {
            "alarms": alarms,
            "count": len(alarms),
        }
    
    async def get_io_status(self, module: Optional[str] = None) -> dict:
        """Get I/O module status."""
        # Demo implementation
        return {
            "modules": [
                {"name": "Local", "type": "1756-L83E", "status": "OK"},
                {"name": "Slot 1", "type": "1756-IF16", "status": "OK", "channels": 16},
                {"name": "Slot 2", "type": "1756-OF8", "status": "OK", "channels": 8},
                {"name": "Slot 3", "type": "1756-IB32", "status": "OK", "channels": 32},
                {"name": "Slot 4", "type": "1756-OB32", "status": "OK", "channels": 32},
            ]
        }
    
    async def get_connection_info(self) -> dict:
        """Get connection statistics."""
        plc_config = self.config.get("plc", {})
        return {
            "host": plc_config.get("host", "unknown"),
            "slot": plc_config.get("slot", 0),
            "connected": self.driver.connected if hasattr(self.driver, "connected") else True,
            "driver": plc_config.get("driver", "demo"),
            "demo_mode": self.config.get("demo_mode", False),
        }
