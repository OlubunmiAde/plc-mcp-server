"""
PLC MCP Server entry point.

Usage:
    python -m plc_mcp_server [--config CONFIG] [--transport stdio|sse] [--port PORT]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from .server import PLCMCPServer


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        # Try default locations
        for default in ["config.yaml", "config.example.yaml"]:
            if Path(default).exists():
                path = Path(default)
                break
        else:
            logging.warning(f"Config file not found, using defaults")
            return {}
    
    with open(path) as f:
        return yaml.safe_load(f) or {}


def setup_logging(config: dict):
    """Configure logging based on config."""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO"))
    format_str = log_config.get(
        "format", 
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logging.basicConfig(
        level=level,
        format=format_str,
        stream=sys.stderr  # MCP uses stdout for protocol, logs go to stderr
    )


def main():
    parser = argparse.ArgumentParser(description="PLC MCP Server")
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse"],
        default=None,
        help="Transport type (overrides config)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="HTTP port for SSE transport (overrides config)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with simulated PLC"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Apply command-line overrides
    if args.transport:
        config.setdefault("server", {})["transport"] = args.transport
    if args.port:
        config.setdefault("server", {})["port"] = args.port
    if args.demo:
        config["demo_mode"] = True
    
    # Setup logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting PLC MCP Server v{PLCMCPServer.__module__}")
    
    # Create and run server
    server = PLCMCPServer(config)
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
