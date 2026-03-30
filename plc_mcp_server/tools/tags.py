"""
Tag operation tools for PLC MCP Server.
"""

import fnmatch
import json
import logging
from typing import Any, Optional

from ..plc.client import PLCClient
from ..safety.whitelist import SafetyManager
from ..safety.audit import AuditLogger

logger = logging.getLogger(__name__)


class TagTools:
    """Tools for reading and writing PLC tags."""
    
    def __init__(self, plc: PLCClient, safety: SafetyManager, audit: AuditLogger):
        self.plc = plc
        self.safety = safety
        self.audit = audit
    
    async def read_tag(self, tag_name: str) -> str:
        """
        Read a single PLC tag.
        
        Returns formatted string with tag name, value, and type.
        """
        try:
            value = await self.plc.read_tag(tag_name)
            
            # Log the read
            self.audit.log_read(tag_name, value)
            
            # Format response
            return json.dumps({
                "tag": tag_name,
                "value": value,
                "status": "ok"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error reading tag {tag_name}: {e}")
            return json.dumps({
                "tag": tag_name,
                "error": str(e),
                "status": "error"
            }, indent=2)
    
    async def read_tags(self, tag_names: list[str]) -> str:
        """
        Read multiple PLC tags at once.
        
        More efficient than multiple single reads.
        """
        try:
            values = await self.plc.read_tags(tag_names)
            
            # Log reads
            for tag, value in values.items():
                if not isinstance(value, dict) or "error" not in value:
                    self.audit.log_read(tag, value)
            
            return json.dumps({
                "tags": values,
                "count": len(values),
                "status": "ok"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error reading tags: {e}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            }, indent=2)
    
    async def write_tag(self, tag_name: str, value: Any) -> str:
        """
        Write a value to a PLC tag.
        
        Requires:
        - Write permissions enabled in config
        - Tag must be in whitelist
        - Tag must not be in protected list
        """
        try:
            # Check write permissions
            can_write, reason = self.safety.can_write(tag_name)
            
            if not can_write:
                self.audit.log_write_denied(tag_name, value, reason)
                return json.dumps({
                    "tag": tag_name,
                    "value": value,
                    "status": "denied",
                    "reason": reason
                }, indent=2)
            
            # Perform write
            success = await self.plc.write_tag(tag_name, value)
            
            # Log the write
            self.audit.log_write(tag_name, value, success)
            
            return json.dumps({
                "tag": tag_name,
                "value": value,
                "status": "ok" if success else "failed"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error writing tag {tag_name}: {e}")
            self.audit.log_write(tag_name, value, False, str(e))
            return json.dumps({
                "tag": tag_name,
                "value": value,
                "error": str(e),
                "status": "error"
            }, indent=2)
    
    async def list_tags(self, pattern: Optional[str] = None) -> str:
        """
        List all available tags, optionally filtered by pattern.
        
        Pattern supports wildcards: * (any chars), ? (single char)
        Examples: "Motor*", "*_Level", "Tank_*"
        """
        try:
            all_tags = await self.plc.get_tag_list()
            
            # Filter by pattern if provided
            if pattern:
                filtered_tags = []
                for tag in all_tags:
                    if fnmatch.fnmatch(tag["name"], pattern):
                        filtered_tags.append(tag)
                tags = filtered_tags
            else:
                tags = all_tags
            
            # Add writability info
            for tag in tags:
                can_write, _ = self.safety.can_write(tag["name"])
                tag["writable"] = can_write
            
            return json.dumps({
                "tags": tags,
                "count": len(tags),
                "total": len(all_tags),
                "pattern": pattern,
                "status": "ok"
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error listing tags: {e}")
            return json.dumps({
                "error": str(e),
                "status": "error"
            }, indent=2)
