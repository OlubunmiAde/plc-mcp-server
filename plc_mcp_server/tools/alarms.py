"""
Alarm tools for PLC MCP Server.
"""

import json
import logging
from typing import Optional

from ..plc.client import PLCClient
from ..safety.audit import AuditLogger

logger = logging.getLogger(__name__)


class AlarmTools:
    """Tools for managing PLC alarms."""
    
    def __init__(self, plc: PLCClient, audit: AuditLogger):
        self.plc = plc
        self.audit = audit
    
    async def get_alarms(self, include_acknowledged: bool = False) -> str:
        """
        Get active alarms from the PLC.
        
        Args:
            include_acknowledged: Include already acknowledged alarms
        """
        try:
            alarms = await self.plc.get_alarms(include_acknowledged)
            
            # Separate active from acknowledged
            active = [a for a in alarms if a.get("active") and not a.get("acknowledged")]
            acknowledged = [a for a in alarms if a.get("acknowledged")]
            
            # Sort by priority (1 = highest)
            active.sort(key=lambda x: x.get("priority", 999))
            
            result = {
                "active_alarms": active,
                "active_count": len(active),
                "status": "ok"
            }
            
            if include_acknowledged:
                result["acknowledged_alarms"] = acknowledged
                result["acknowledged_count"] = len(acknowledged)
            
            # Add summary
            if active:
                result["summary"] = f"{len(active)} active alarm(s)"
                highest_priority = min(a.get("priority", 999) for a in active)
                result["highest_priority"] = highest_priority
            else:
                result["summary"] = "No active alarms"
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error getting alarms: {e}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            }, indent=2)
    
    async def acknowledge_alarm(self, alarm_id: str) -> str:
        """
        Acknowledge an active alarm.
        
        Args:
            alarm_id: ID of the alarm to acknowledge
        """
        try:
            success = await self.plc.acknowledge_alarm(alarm_id)
            
            # Log the action
            self.audit.log_action("acknowledge_alarm", {
                "alarm_id": alarm_id,
                "success": success
            })
            
            return json.dumps({
                "alarm_id": alarm_id,
                "acknowledged": success,
                "status": "ok" if success else "failed"
            }, indent=2)
            
        except NotImplementedError as e:
            return json.dumps({
                "alarm_id": alarm_id,
                "error": str(e),
                "status": "not_supported"
            }, indent=2)
        except Exception as e:
            logger.error(f"Error acknowledging alarm {alarm_id}: {e}")
            return json.dumps({
                "alarm_id": alarm_id,
                "error": str(e),
                "status": "error"
            }, indent=2)
