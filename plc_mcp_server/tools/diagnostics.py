"""
Diagnostic tools for PLC MCP Server.
"""

import json
import logging
from typing import Optional

from ..plc.client import PLCClient

logger = logging.getLogger(__name__)


class DiagnosticTools:
    """Tools for PLC diagnostics and status."""
    
    def __init__(self, plc: PLCClient):
        self.plc = plc
    
    async def get_plc_status(self) -> str:
        """
        Get PLC status including CPU state, mode, and faults.
        """
        try:
            info = await self.plc.get_plc_info()
            
            # Build status response
            result = {
                "plc_info": info,
                "status": "ok"
            }
            
            # Add human-readable summary
            mode = info.get("mode", info.get("keyswitch", "unknown"))
            result["summary"] = f"PLC is in {mode} mode"
            
            faults = info.get("faults", [])
            if faults:
                result["summary"] += f" with {len(faults)} fault(s)"
                result["has_faults"] = True
            else:
                result["has_faults"] = False
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting PLC status: {e}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            }, indent=2)
    
    async def get_io_status(self, module: Optional[str] = None) -> str:
        """
        Get I/O module status and health.
        
        Args:
            module: Specific module name to check (optional)
        """
        try:
            io_info = await self.plc.get_io_status(module)
            
            modules = io_info.get("modules", [])
            
            # Filter by module name if specified
            if module:
                modules = [m for m in modules if m.get("name") == module]
            
            # Check for any faulted modules
            faulted = [m for m in modules if m.get("status") != "OK"]
            
            result = {
                "modules": modules,
                "count": len(modules),
                "faulted_count": len(faulted),
                "status": "ok"
            }
            
            if faulted:
                result["summary"] = f"{len(faulted)} module(s) with issues"
                result["faulted_modules"] = faulted
            else:
                result["summary"] = "All I/O modules OK"
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting I/O status: {e}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            }, indent=2)
    
    async def get_connection_info(self) -> str:
        """
        Get connection information and statistics.
        """
        try:
            conn_info = await self.plc.get_connection_info()
            
            result = {
                "connection": conn_info,
                "status": "ok"
            }
            
            # Add summary
            if conn_info.get("connected"):
                result["summary"] = f"Connected to {conn_info.get('host', 'PLC')}"
            else:
                result["summary"] = "Not connected"
            
            if conn_info.get("demo_mode"):
                result["summary"] += " (DEMO MODE)"
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            }, indent=2)
