#!/usr/bin/env python3
"""HITL Server and Shell - All in one"""

import asyncio
import threading
import argparse
import sys
import uvicorn
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.hitl.server import app
from utils.hitl.shell import HITLShell


def run_server_thread(host: str, port: int):
    """Run the FastAPI server in a background thread"""
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


async def run_shell_async(server_url: str):
    """Run the shell in the main thread"""
    # Wait a bit for server to start
    print("Waiting for server to start...")
    await asyncio.sleep(2)
    
    # Create and run shell
    shell = HITLShell(server_url=server_url)
    await shell.run()


def main():
    parser = argparse.ArgumentParser(
        description="HITL Server and Shell - All in one"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("HITL System - Server and Shell")
    print("=" * 60)
    print(f"Starting server on {args.host}:{args.port}")
    print("Shell will start automatically...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Start server in background thread
    server_thread = threading.Thread(
        target=run_server_thread,
        args=(args.host, args.port),
        daemon=True
    )
    server_thread.start()
    
    # Run shell in main thread
    try:
        server_url = f"http://{args.host}:{args.port}"
        asyncio.run(run_shell_async(server_url))
    except KeyboardInterrupt:
        print("\n\nShutting down HITL system...")


if __name__ == "__main__":
    main()