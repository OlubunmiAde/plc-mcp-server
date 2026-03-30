# PLC MCP Server

A Model Context Protocol (MCP) server for industrial PLC integration. Enables AI assistants to read tags, monitor alarms, and interact with Allen-Bradley ControlLogix PLCs using natural language.

## Features

- 🏭 **Tag Operations** - Read/write PLC tags
- 🚨 **Alarm Management** - View and acknowledge alarms
- 📊 **Diagnostics** - PLC status, I/O health, connection info
- 🔒 **Safety First** - Read-only by default, write whitelist, audit logging
- 🔌 **MCP Standard** - Works with Claude Desktop, Cursor, and any MCP client

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your PLC connection
cp config.example.yaml config.yaml
# Edit config.yaml with your PLC IP and settings

# Run the server (stdio mode for MCP)
python -m plc_mcp_server

# Or run in HTTP/SSE mode
python -m plc_mcp_server --transport sse --port 8080
```

## Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "plc": {
      "command": "python",
      "args": ["-m", "plc_mcp_server"],
      "cwd": "/path/to/plc-mcp-server"
    }
  }
}
```

## Project Structure

```
plc-mcp-server/
├── plc_mcp_server/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── server.py            # MCP server implementation
│   ├── plc/
│   │   ├── __init__.py
│   │   ├── client.py        # PLC connection manager
│   │   ├── allen_bradley.py # ControlLogix driver
│   │   ├── siemens.py       # S7 driver (future)
│   │   └── modbus.py        # Modbus driver (future)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tags.py          # Tag read/write tools
│   │   ├── alarms.py        # Alarm tools
│   │   └── diagnostics.py   # Status/diagnostic tools
│   ├── resources/
│   │   ├── __init__.py
│   │   └── tag_database.py  # Tag list resource
│   └── safety/
│       ├── __init__.py
│       ├── whitelist.py     # Write permission control
│       └── audit.py         # Audit logging
├── config.example.yaml
├── requirements.txt
├── pyproject.toml
└── tests/
    └── ...
```

## Safety

**This server controls industrial equipment. Safety is paramount.**

- Read-only mode by default (`allow_writes: false`)
- Tag whitelist for write operations
- All operations logged to audit trail
- Confirmation required for writes (via MCP confirmation flow)

## License

MIT
