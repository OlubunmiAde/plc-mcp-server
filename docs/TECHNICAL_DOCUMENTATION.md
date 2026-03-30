# PLC MCP Server - Technical Documentation

**Project:** PLC MCP Server  
**Date:** March 30, 2026  
**Author:** Olu & Juno  
**Repository:** https://github.com/OlubunmiAde/plc-mcp-server

---

## Prerequisites & Assumptions

This document assumes the reader has:

### Knowledge Requirements
- **Basic Python programming** — Ability to read/write Python code, use pip, virtual environments
- **Understanding of PLCs** — Familiarity with PLC concepts (tags, I/O, ladder logic)
- **Industrial networking basics** — IP addressing, Ethernet/IP, TCP/IP fundamentals
- **Command line proficiency** — Comfortable with PowerShell (Windows) or Bash (Linux)

### Software Requirements
- **Python 3.10 or higher** — [Download](https://python.org/downloads/)
- **Git** — [Download](https://git-scm.com/downloads)
- **Claude Desktop** — [Download](https://claude.ai/download) (for AI integration)
- **Text editor or IDE** — VS Code recommended

### Hardware Requirements (for production use)
- **Allen-Bradley ControlLogix or CompactLogix PLC** — With Ethernet/IP connectivity
- **Network access to PLC** — PC must be able to reach PLC IP address

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Operating System** | Windows 10, Ubuntu 20.04, macOS 12 | Windows 11, Ubuntu 22.04+ |
| **CPU** | Dual-core 2.0 GHz | Quad-core 3.0 GHz+ |
| **RAM** | 4 GB | 8 GB+ |
| **Disk Space** | 500 MB | 1 GB+ |
| **Network** | 100 Mbps Ethernet | 1 Gbps Ethernet |
| **Python** | 3.10 | 3.11 or 3.12 |

**Note:** These are requirements for running the MCP server only. Claude Desktop has its own requirements (~2GB RAM additional).

### Network Requirements

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 44818 | TCP | Outbound | EtherNet/IP (Allen-Bradley PLC) |
| 102 | TCP | Outbound | S7 Protocol (Siemens PLC, future) |
| 502 | TCP | Outbound | Modbus TCP (future) |
| 8080 | TCP | Inbound | SSE transport (optional, when enabled) |

**Firewall:** Ensure outbound access to PLC IP addresses on port 44818.

### Optional (for development)
- **No physical PLC required** — Demo mode simulates PLC tags for testing
- **RTX GPU** — Not required; beneficial if running local AI models

### Account Requirements
- **GitHub account** — For cloning repository and future contributions
- **Anthropic account** — For Claude Desktop (free tier available)

---

## Executive Summary

This document describes the design and implementation of a Model Context Protocol (MCP) server for industrial PLC integration. The server enables AI assistants (Claude, Cursor, etc.) to communicate with Allen-Bradley ControlLogix PLCs using natural language.

**Key Achievement:** Successfully built and deployed an MCP server that allows Claude Desktop to read PLC tags in real-time.

---

## 1. What is MCP?

### 1.1 Overview

The **Model Context Protocol (MCP)** is an open standard developed by Anthropic (November 2024) that enables seamless integration between LLM applications and external data sources/tools.

Think of it as **"USB for AI"** — a standardized way to connect any AI model to any tool.

### 1.2 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   AI Host       │────▶│   MCP Client    │────▶│   MCP Server    │
│ (Claude Desktop)│     │   (connector)   │     │  (our server)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │      PLC        │
                                                │ (ControlLogix)  │
                                                └─────────────────┘
```

### 1.3 Protocol Details

- **Transport:** JSON-RPC 2.0 over stdio (or HTTP/SSE)
- **Message Types:** Requests, Responses, Notifications
- **Capabilities:** Tools, Resources, Prompts

### 1.4 The Three Primitives

| Primitive | Controlled By | Description |
|-----------|---------------|-------------|
| **Tools** | AI Model | Functions the AI can call (e.g., `read_tag`) |
| **Resources** | Application | Data the app provides (e.g., tag database) |
| **Prompts** | User | Pre-built templates for common tasks |

---

## 2. System Architecture

### 2.1 Project Structure

```
plc-mcp-server/
├── README.md                    # Project documentation
├── config.example.yaml          # Configuration template
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Package configuration
│
└── plc_mcp_server/
    ├── __init__.py             # Package init
    ├── __main__.py             # CLI entry point
    ├── server.py               # MCP server implementation
    │
    ├── plc/
    │   ├── __init__.py
    │   ├── client.py           # PLC connection manager
    │   └── allen_bradley.py    # ControlLogix driver (pycomm3)
    │
    ├── tools/
    │   ├── __init__.py
    │   ├── tags.py             # Tag read/write/list tools
    │   ├── alarms.py           # Alarm management tools
    │   └── diagnostics.py      # PLC status tools
    │
    └── safety/
        ├── __init__.py
        ├── whitelist.py        # Write permission control
        └── audit.py            # Operation logging
```

### 2.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Server (server.py)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Tools     │  │  Resources  │  │    Safety Manager       │  │
│  │ - read_tag  │  │ - tag_db    │  │ - whitelist            │  │
│  │ - write_tag │  │ - alarms    │  │ - audit log            │  │
│  │ - list_tags │  │             │  │ - protected tags       │  │
│  │ - alarms    │  │             │  │                        │  │
│  │ - status    │  │             │  │                        │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
│                   ┌──────▼──────┐                                │
│                   │ PLC Client  │                                │
│                   └──────┬──────┘                                │
└──────────────────────────┼───────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼────┐ ┌────▼─────┐
       │Allen-Bradley│ │Siemens │ │ Modbus   │
       │   Driver    │ │ Driver │ │ Driver   │
       │  (pycomm3)  │ │(future)│ │ (future) │
       └──────┬──────┘ └────────┘ └──────────┘
              │
       ┌──────▼──────┐
       │ControlLogix │
       │    PLC      │
       └─────────────┘
```

---

## 3. Implemented Features

### 3.1 MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `read_tag` | Read single PLC tag | `tag_name: string` |
| `read_tags` | Read multiple tags | `tag_names: string[]` |
| `write_tag` | Write tag value | `tag_name: string, value: any` |
| `list_tags` | List available tags | `pattern?: string` (wildcards) |
| `get_alarms` | Get active alarms | `include_acknowledged?: bool` |
| `acknowledge_alarm` | Acknowledge alarm | `alarm_id: string` |
| `get_plc_status` | Get PLC CPU status | none |
| `get_io_status` | Get I/O module status | `module?: string` |
| `get_connection_info` | Get connection stats | none |

### 3.2 MCP Resources

| Resource URI | Description | MIME Type |
|--------------|-------------|-----------|
| `plc://tags` | Complete tag database | `application/json` |
| `plc://alarms/config` | Alarm definitions | `application/json` |

### 3.3 Safety Features

#### Write Protection (Layered Security)

```
1. Global Enable    →  allow_writes: false (default)
        ↓
2. Whitelist Check  →  Only listed tags can be written
        ↓
3. Blacklist Check  →  Protected tags NEVER writable
        ↓
4. Audit Logging    →  All operations logged
```

#### Configuration Example

```yaml
safety:
  allow_writes: false
  writable_tags:
    - "Tank_Setpoint"
    - "Conveyor_Speed"
  protected_tags:
    - "Emergency_Stop"
    - "Safety_*"         # Wildcard pattern
  audit_enabled: true
```

### 3.4 Demo Mode

For testing without a real PLC, demo mode provides simulated tags:

| Tag | Type | Description |
|-----|------|-------------|
| Motor1_Running | BOOL | Motor 1 status |
| Motor2_Running | BOOL | Motor 2 status |
| Tank_Level | REAL | Tank level (%) |
| Tank_Setpoint | REAL | Level setpoint |
| Conveyor_Speed | DINT | Speed (units/min) |
| Temperature_PV | REAL | Process temp (°F) |
| Pressure_PV | REAL | Process pressure (PSI) |
| Emergency_Stop | BOOL | E-Stop (protected) |

---

## 4. Installation & Configuration

### 4.1 Prerequisites

- Python 3.10+
- pip
- Git

### 4.2 Installation

```powershell
# Clone repository
git clone https://github.com/OlubunmiAde/plc-mcp-server.git
cd plc-mcp-server

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install package
pip install -e .
```

### 4.3 Configuration

Copy and edit configuration:

```powershell
copy config.example.yaml config.yaml
```

Key settings:

```yaml
plc:
  driver: allen_bradley
  host: "192.168.1.10"
  slot: 0

safety:
  allow_writes: false

demo_mode: true  # Set false for real PLC
```

### 4.4 Running the Server

```powershell
# Demo mode
python -m plc_mcp_server --demo

# Production mode
python -m plc_mcp_server --config config.yaml
```

---

## 5. Claude Desktop Integration

### 5.1 Configuration File Location

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### 5.2 Configuration

```json
{
  "mcpServers": {
    "plc": {
      "command": "C:\\Users\\olubu\\projects\\plc-mcp-server\\venv\\Scripts\\python.exe",
      "args": ["-m", "plc_mcp_server", "--demo"]
    }
  }
}
```

### 5.3 Usage Examples

After restarting Claude Desktop:

| User Query | AI Action |
|------------|-----------|
| "Read the Tank_Level tag" | Calls `read_tag("Tank_Level")` |
| "List all motor tags" | Calls `list_tags("Motor*")` |
| "What's the PLC status?" | Calls `get_plc_status()` |
| "Are there any active alarms?" | Calls `get_alarms()` |

---

## 6. Technical Specifications

### 6.1 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| mcp | ≥1.0.0 | MCP protocol SDK |
| pycomm3 | ≥1.2.0 | Allen-Bradley communication |
| pyyaml | ≥6.0 | Configuration parsing |
| pydantic | ≥2.0 | Data validation |

### 6.2 Supported PLCs

| Manufacturer | Models | Driver | Status |
|--------------|--------|--------|--------|
| Allen-Bradley | ControlLogix, CompactLogix | pycomm3 | ✅ Implemented |
| Siemens | S7-300/400/1200/1500 | python-snap7 | 🔜 Planned |
| Generic | Modbus TCP/RTU | pymodbus | 🔜 Planned |

### 6.3 Communication Protocol

**PLC ↔ Server:**
- Allen-Bradley: EtherNet/IP (CIP)
- Port: TCP/44818

**Server ↔ AI:**
- MCP over stdio (JSON-RPC 2.0)
- Alternative: HTTP/SSE (planned)

---

## 7. Security Considerations

### 7.1 Risks

| Risk | Mitigation |
|------|------------|
| Unauthorized writes | Whitelist + global disable |
| Safety system access | Protected tag patterns |
| Audit trail gaps | All operations logged |
| Network exposure | Stdio transport (local only) |

### 7.2 Best Practices

1. **Never enable writes in production without review**
2. **Always protect safety-related tags**
3. **Review audit logs regularly**
4. **Use SSE transport only on trusted networks**
5. **Implement additional authentication for remote access**

---

## 8. Future Roadmap

### 8.1 Short-term (1-2 weeks)

- [ ] Add Modbus TCP driver
- [ ] Implement tag trending (history)
- [ ] Add SSE transport for remote access
- [ ] MCP prompts for common tasks

### 8.2 Medium-term (1-2 months)

- [ ] Siemens S7 driver
- [ ] OPC-UA client
- [ ] Alarm historian
- [ ] Multi-PLC support

### 8.3 Long-term

- [ ] Ignition MCP Server integration
- [ ] Digital twin synchronization
- [ ] Anomaly detection
- [ ] Voice interface

---

## 9. Lessons Learned

### 9.1 MCP Protocol

- Tools are model-controlled, Resources are app-controlled
- JSON-RPC 2.0 over stdio is the simplest transport
- Type safety via JSON Schema for tool parameters

### 9.2 Industrial Integration

- Demo mode is essential for development
- Safety must be built-in from the start
- Audit logging is non-negotiable for industrial systems

### 9.3 Development Process

- Start with minimal viable implementation
- Test with Claude Desktop early
- Iterate based on real usage

---

## 10. References

- [MCP Specification](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [pycomm3 Documentation](https://pycomm3.readthedocs.io)
- [Anthropic MCP Announcement](https://www.anthropic.com/news/model-context-protocol)
- [Awesome MCP Servers](https://github.com/wong2/awesome-mcp-servers)

---

## Appendix A: Full Configuration Reference

```yaml
# PLC Connection
plc:
  driver: allen_bradley    # allen_bradley | siemens | modbus
  host: "192.168.1.10"     # PLC IP address
  slot: 0                  # CPU slot (Allen-Bradley)
  timeout: 5               # Connection timeout (seconds)
  auto_reconnect: true     # Reconnect on failure

# Safety Settings
safety:
  allow_writes: false      # Global write enable
  require_confirmation: true
  writable_tags: []        # Whitelist
  protected_tags:          # Blacklist (patterns supported)
    - "Emergency_Stop"
    - "Safety_*"
  audit_enabled: true
  audit_file: "audit.log"

# Server Settings
server:
  name: "PLC Control Server"
  version: "1.0.0"
  transport: stdio         # stdio | sse
  port: 8080              # For SSE transport

# Demo Mode
demo_mode: false

# Logging
logging:
  level: INFO
```

---

## Appendix B: Audit Log Format

Each line is a JSON object:

```json
{"timestamp": "2026-03-30T18:20:58.557Z", "action": "read", "tag": "Tank_Level", "value": "75.5"}
{"timestamp": "2026-03-30T18:21:15.123Z", "action": "write", "tag": "Tank_Setpoint", "value": 80, "success": true}
{"timestamp": "2026-03-30T18:22:01.456Z", "action": "write_denied", "tag": "Emergency_Stop", "value": false, "reason": "Tag is protected"}
```

---

**Document Version:** 1.0  
**Last Updated:** March 30, 2026
