"""
MCP Server implementation for PLC integration.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from .plc.client import PLCClient
from .tools.tags import TagTools
from .tools.alarms import AlarmTools
from .tools.diagnostics import DiagnosticTools
from .safety.whitelist import SafetyManager
from .safety.audit import AuditLogger

logger = logging.getLogger(__name__)


class PLCMCPServer:
    """
    MCP Server that exposes PLC operations as tools.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.server = Server(
            name=config.get("server", {}).get("name", "PLC Control Server"),
            version=config.get("server", {}).get("version", "1.0.0"),
        )
        
        # Initialize components
        self.plc = PLCClient(config)
        self.safety = SafetyManager(config.get("safety", {}))
        self.audit = AuditLogger(config.get("safety", {}))
        
        # Initialize tool handlers
        self.tag_tools = TagTools(self.plc, self.safety, self.audit)
        self.alarm_tools = AlarmTools(self.plc, self.audit)
        self.diagnostic_tools = DiagnosticTools(self.plc)
        
        # Register handlers
        self._register_tools()
        self._register_resources()
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            tools = [
                # Tag Operations
                Tool(
                    name="read_tag",
                    description="Read a PLC tag value. Returns the current value of the specified tag.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tag_name": {
                                "type": "string",
                                "description": "Name of the tag to read (e.g., 'Motor1_Running', 'Tank_Level')"
                            }
                        },
                        "required": ["tag_name"]
                    }
                ),
                Tool(
                    name="read_tags",
                    description="Read multiple PLC tags at once. More efficient than multiple single reads.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tag_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tag names to read"
                            }
                        },
                        "required": ["tag_names"]
                    }
                ),
                Tool(
                    name="write_tag",
                    description="Write a value to a PLC tag. Requires write permissions and tag must be in whitelist.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tag_name": {
                                "type": "string",
                                "description": "Name of the tag to write"
                            },
                            "value": {
                                "description": "Value to write (type depends on tag)"
                            }
                        },
                        "required": ["tag_name", "value"]
                    }
                ),
                Tool(
                    name="list_tags",
                    description="List all available tags in the PLC. Can filter by pattern.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Optional filter pattern (e.g., 'Motor*', '*_Level')"
                            }
                        }
                    }
                ),
                
                # Alarm Operations
                Tool(
                    name="get_alarms",
                    description="Get active alarms from the PLC.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_acknowledged": {
                                "type": "boolean",
                                "description": "Include already acknowledged alarms",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="acknowledge_alarm",
                    description="Acknowledge an active alarm.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "alarm_id": {
                                "type": "string",
                                "description": "ID of the alarm to acknowledge"
                            }
                        },
                        "required": ["alarm_id"]
                    }
                ),
                
                # Diagnostics
                Tool(
                    name="get_plc_status",
                    description="Get PLC status including CPU state, mode, and faults.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_io_status",
                    description="Get I/O module status and health.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "module": {
                                "type": "string",
                                "description": "Specific module to check (optional, all if not specified)"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_connection_info",
                    description="Get connection information and statistics.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            logger.info(f"Tool call: {name} with args: {arguments}")
            
            try:
                # Route to appropriate handler
                if name == "read_tag":
                    result = await self.tag_tools.read_tag(arguments["tag_name"])
                elif name == "read_tags":
                    result = await self.tag_tools.read_tags(arguments["tag_names"])
                elif name == "write_tag":
                    result = await self.tag_tools.write_tag(
                        arguments["tag_name"], 
                        arguments["value"]
                    )
                elif name == "list_tags":
                    result = await self.tag_tools.list_tags(arguments.get("pattern"))
                elif name == "get_alarms":
                    result = await self.alarm_tools.get_alarms(
                        arguments.get("include_acknowledged", False)
                    )
                elif name == "acknowledge_alarm":
                    result = await self.alarm_tools.acknowledge_alarm(arguments["alarm_id"])
                elif name == "get_plc_status":
                    result = await self.diagnostic_tools.get_plc_status()
                elif name == "get_io_status":
                    result = await self.diagnostic_tools.get_io_status(
                        arguments.get("module")
                    )
                elif name == "get_connection_info":
                    result = await self.diagnostic_tools.get_connection_info()
                else:
                    result = f"Unknown tool: {name}"
                
                return [TextContent(type="text", text=str(result))]
                
            except Exception as e:
                logger.error(f"Tool error: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _register_resources(self):
        """Register MCP resources."""
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """Return list of available resources."""
            return [
                Resource(
                    uri="plc://tags",
                    name="Tag Database",
                    description="Complete list of PLC tags with metadata",
                    mimeType="application/json"
                ),
                Resource(
                    uri="plc://alarms/config",
                    name="Alarm Configuration",
                    description="Alarm definitions and thresholds",
                    mimeType="application/json"
                ),
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a resource."""
            if uri == "plc://tags":
                tags = await self.plc.get_tag_database()
                import json
                return json.dumps(tags, indent=2)
            elif uri == "plc://alarms/config":
                alarms = await self.plc.get_alarm_config()
                import json
                return json.dumps(alarms, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def run(self):
        """Run the MCP server."""
        transport = self.config.get("server", {}).get("transport", "stdio")
        
        if transport == "stdio":
            logger.info("Starting MCP server with stdio transport")
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        elif transport == "sse":
            # HTTP/SSE transport for remote access
            port = self.config.get("server", {}).get("port", 8080)
            logger.info(f"Starting MCP server with SSE transport on port {port}")
            # SSE implementation would go here
            raise NotImplementedError("SSE transport not yet implemented")
        else:
            raise ValueError(f"Unknown transport: {transport}")
