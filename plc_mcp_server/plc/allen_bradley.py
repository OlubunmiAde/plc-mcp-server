"""
Allen-Bradley ControlLogix PLC Driver using pycomm3.
"""

import logging
from typing import Any, Optional

from .client import PLCDriver

logger = logging.getLogger(__name__)


class AllenBradleyDriver(PLCDriver):
    """
    Driver for Allen-Bradley ControlLogix PLCs using pycomm3.
    """
    
    def __init__(self, config: dict):
        self.host = config.get("host", "192.168.1.10")
        self.slot = config.get("slot", 0)
        self.timeout = config.get("timeout", 5)
        self.plc = None
        self.connected = False
        self._tag_cache = None
    
    async def connect(self) -> bool:
        """Connect to the PLC."""
        try:
            from pycomm3 import LogixDriver
            
            # pycomm3 uses context manager, but we can also use it directly
            self.plc = LogixDriver(
                self.host,
                slot=self.slot,
                timeout=self.timeout
            )
            self.plc.open()
            
            logger.info(f"Connected to Allen-Bradley PLC at {self.host}")
            self.connected = True
            
            # Cache tag list on connect
            self._tag_cache = self.plc.get_tag_list()
            
            return True
            
        except ImportError:
            logger.error("pycomm3 not installed. Run: pip install pycomm3")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to PLC: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from the PLC."""
        if self.plc:
            try:
                self.plc.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self.plc = None
                self.connected = False
                logger.info("Disconnected from PLC")
    
    def _ensure_connected(self):
        """Ensure we have an active connection."""
        if not self.connected or not self.plc:
            raise ConnectionError("Not connected to PLC. Call connect() first.")
    
    async def read_tag(self, tag_name: str) -> Any:
        """Read a single tag value."""
        self._ensure_connected()
        
        try:
            result = self.plc.read(tag_name)
            
            if result.error:
                raise ValueError(f"Error reading tag {tag_name}: {result.error}")
            
            logger.debug(f"Read {tag_name} = {result.value}")
            return result.value
            
        except Exception as e:
            logger.error(f"Failed to read tag {tag_name}: {e}")
            raise
    
    async def read_tags(self, tag_names: list[str]) -> dict[str, Any]:
        """Read multiple tags at once."""
        self._ensure_connected()
        
        try:
            results = self.plc.read(*tag_names)
            
            # Handle single vs multiple results
            if not isinstance(results, list):
                results = [results]
            
            output = {}
            for result in results:
                if result.error:
                    output[result.tag] = {"error": str(result.error)}
                else:
                    output[result.tag] = result.value
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to read tags: {e}")
            raise
    
    async def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write a value to a tag."""
        self._ensure_connected()
        
        try:
            result = self.plc.write(tag_name, value)
            
            if result.error:
                raise ValueError(f"Error writing tag {tag_name}: {result.error}")
            
            logger.info(f"Wrote {tag_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write tag {tag_name}: {e}")
            raise
    
    async def get_tag_list(self) -> list[dict]:
        """Get list of all tags in the PLC."""
        self._ensure_connected()
        
        try:
            # Use cached list if available
            if self._tag_cache is None:
                self._tag_cache = self.plc.get_tag_list()
            
            tags = []
            for tag in self._tag_cache:
                tags.append({
                    "name": tag.tag_name,
                    "type": tag.data_type_name,
                    "description": getattr(tag, "description", ""),
                    "dimensions": tag.dimensions if hasattr(tag, "dimensions") else None,
                })
            
            return tags
            
        except Exception as e:
            logger.error(f"Failed to get tag list: {e}")
            raise
    
    async def get_plc_info(self) -> dict:
        """Get PLC information."""
        self._ensure_connected()
        
        try:
            info = self.plc.info
            
            return {
                "name": info.get("name", "Unknown"),
                "ip": self.host,
                "slot": self.slot,
                "vendor": info.get("vendor", "Allen-Bradley"),
                "product_type": info.get("product_type", ""),
                "product_name": info.get("product_name", ""),
                "revision": f"{info.get('revision', {}).get('major', '?')}.{info.get('revision', {}).get('minor', '?')}",
                "serial": info.get("serial", ""),
                "keyswitch": info.get("keyswitch", ""),
            }
            
        except Exception as e:
            logger.error(f"Failed to get PLC info: {e}")
            return {
                "name": "Unknown",
                "ip": self.host,
                "slot": self.slot,
                "error": str(e),
            }
    
    async def get_alarms(self, include_acknowledged: bool = False) -> list[dict]:
        """
        Get alarms from the PLC.
        
        Note: Allen-Bradley doesn't have a standard alarm interface.
        This would need to be customized based on how alarms are implemented
        in your specific PLC program (e.g., reading from an alarm UDT array).
        """
        # This is a placeholder - real implementation depends on PLC program
        logger.warning("Alarm reading not implemented for Allen-Bradley driver")
        return []
    
    async def acknowledge_alarm(self, alarm_id: str) -> bool:
        """
        Acknowledge an alarm.
        
        Note: Implementation depends on PLC program structure.
        """
        logger.warning("Alarm acknowledgment not implemented for Allen-Bradley driver")
        raise NotImplementedError(
            "Alarm acknowledgment requires custom implementation based on PLC program"
        )
