"""
Safety manager for controlling write access to PLC tags.
"""

import fnmatch
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class SafetyManager:
    """
    Manages write permissions for PLC tags.
    
    Implements a layered security model:
    1. Global write enable/disable
    2. Whitelist of writable tags
    3. Blacklist of protected tags (always takes precedence)
    """
    
    def __init__(self, config: dict):
        """
        Initialize safety manager.
        
        Args:
            config: Safety configuration dict with:
                - allow_writes: bool - Global write enable
                - writable_tags: list - Tags allowed for writing
                - protected_tags: list - Tags never allowed (supports wildcards)
                - require_confirmation: bool - Require user confirmation
        """
        self.allow_writes = config.get("allow_writes", False)
        self.writable_tags = set(config.get("writable_tags", []))
        self.protected_tags = config.get("protected_tags", [])
        self.require_confirmation = config.get("require_confirmation", True)
        
        logger.info(
            f"SafetyManager initialized: writes={'enabled' if self.allow_writes else 'disabled'}, "
            f"whitelist={len(self.writable_tags)} tags, "
            f"protected={len(self.protected_tags)} patterns"
        )
    
    def is_protected(self, tag_name: str) -> bool:
        """
        Check if a tag is protected (never writable).
        
        Supports wildcard patterns like "Safety_*", "*_Interlock".
        """
        for pattern in self.protected_tags:
            if fnmatch.fnmatch(tag_name, pattern):
                return True
        return False
    
    def is_whitelisted(self, tag_name: str) -> bool:
        """Check if a tag is in the writable whitelist."""
        return tag_name in self.writable_tags
    
    def can_write(self, tag_name: str) -> Tuple[bool, str]:
        """
        Check if writing to a tag is allowed.
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check global write enable
        if not self.allow_writes:
            return False, "Writes are disabled globally (allow_writes: false)"
        
        # Check protected list (blacklist takes precedence)
        if self.is_protected(tag_name):
            return False, f"Tag '{tag_name}' is protected and cannot be written"
        
        # Check whitelist
        if not self.is_whitelisted(tag_name):
            return False, f"Tag '{tag_name}' is not in the writable whitelist"
        
        return True, "OK"
    
    def add_to_whitelist(self, tag_name: str):
        """Add a tag to the writable whitelist."""
        if self.is_protected(tag_name):
            raise ValueError(f"Cannot whitelist protected tag: {tag_name}")
        self.writable_tags.add(tag_name)
        logger.info(f"Added '{tag_name}' to write whitelist")
    
    def remove_from_whitelist(self, tag_name: str):
        """Remove a tag from the writable whitelist."""
        self.writable_tags.discard(tag_name)
        logger.info(f"Removed '{tag_name}' from write whitelist")
    
    def get_writable_tags(self) -> list[str]:
        """Get list of all writable tags."""
        return sorted(self.writable_tags)
    
    def get_protected_patterns(self) -> list[str]:
        """Get list of protected tag patterns."""
        return self.protected_tags.copy()
