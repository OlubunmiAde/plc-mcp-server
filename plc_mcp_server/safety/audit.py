"""
Audit logging for PLC operations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Logs all PLC operations for audit trail.
    
    Records:
    - Tag reads (optional, can be noisy)
    - Tag writes (always)
    - Write denials
    - Alarm acknowledgments
    - Other significant actions
    """
    
    def __init__(self, config: dict):
        """
        Initialize audit logger.
        
        Args:
            config: Audit configuration with:
                - audit_enabled: bool - Enable audit logging
                - audit_file: str - Path to audit log file
                - log_reads: bool - Log read operations (default: False)
        """
        self.enabled = config.get("audit_enabled", True)
        self.audit_file = config.get("audit_file", "audit.log")
        self.log_reads = config.get("log_reads", False)
        
        if self.enabled:
            # Ensure audit file directory exists
            Path(self.audit_file).parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Audit logging enabled: {self.audit_file}")
    
    def _write_entry(self, entry: dict):
        """Write an entry to the audit log."""
        if not self.enabled:
            return
        
        # Add timestamp
        entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        try:
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def log_read(self, tag_name: str, value: Any):
        """Log a tag read operation."""
        if not self.log_reads:
            return
        
        self._write_entry({
            "action": "read",
            "tag": tag_name,
            "value": str(value)[:100],  # Truncate large values
        })
    
    def log_write(self, tag_name: str, value: Any, success: bool, error: Optional[str] = None):
        """Log a tag write operation."""
        entry = {
            "action": "write",
            "tag": tag_name,
            "value": value,
            "success": success,
        }
        if error:
            entry["error"] = error
        
        self._write_entry(entry)
        
        # Also log to standard logger
        if success:
            logger.info(f"AUDIT: Write {tag_name} = {value}")
        else:
            logger.warning(f"AUDIT: Write FAILED {tag_name} = {value}: {error}")
    
    def log_write_denied(self, tag_name: str, value: Any, reason: str):
        """Log a denied write attempt."""
        self._write_entry({
            "action": "write_denied",
            "tag": tag_name,
            "value": value,
            "reason": reason,
        })
        
        logger.warning(f"AUDIT: Write DENIED {tag_name} = {value}: {reason}")
    
    def log_action(self, action: str, details: dict):
        """Log a general action."""
        entry = {
            "action": action,
            **details
        }
        self._write_entry(entry)
        logger.info(f"AUDIT: {action} - {details}")
    
    def get_recent_entries(self, count: int = 100) -> list[dict]:
        """Get recent audit log entries."""
        if not self.enabled or not Path(self.audit_file).exists():
            return []
        
        try:
            with open(self.audit_file, "r") as f:
                lines = f.readlines()
            
            entries = []
            for line in lines[-count:]:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")
            return []
