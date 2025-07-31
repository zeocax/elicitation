"""Interactive shell for handling HITL requests"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime
import json
import sys
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from .models import HITLRequest, HITLResponse, RequestType


class HITLShell:
    """Interactive shell for responding to HITL requests"""
    
    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url
        self.console = Console()
        self.running = False
    
    async def get_next_request(self, timeout: float = 30.0) -> Optional[HITLRequest]:
        """Poll server for next request"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.server_url}/next",
                    params={"timeout": timeout}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data:
                            return HITLRequest.from_dict(data)
            except Exception as e:
                self.console.print(f"[red]Error polling server: {e}[/red]")
        return None
    
    async def send_response(self, response: HITLResponse) -> bool:
        """Send response back to server"""
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.server_url}/response/{response.request_id}"
                response_dict = response.to_dict()
                
                self.console.print(f"[dim]DEBUG: Sending response to {url}[/dim]")
                self.console.print(f"[dim]DEBUG: Response data: {response_dict}[/dim]")
                
                async with session.post(url, json=response_dict) as resp:
                    if resp.status == 200:
                        self.console.print(f"[dim]DEBUG: Response sent successfully (status: {resp.status})[/dim]")
                        return True
                    else:
                        # Read error details
                        error_text = await resp.text()
                        self.console.print(f"[red]ERROR: Server returned status {resp.status}[/red]")
                        self.console.print(f"[red]ERROR: Response body: {error_text}[/red]")
                        return False
            except aiohttp.ClientError as e:
                self.console.print(f"[red]ERROR: Network error sending response: {type(e).__name__}: {e}[/red]")
                return False
            except Exception as e:
                self.console.print(f"[red]ERROR: Unexpected error sending response: {type(e).__name__}: {e}[/red]")
                import traceback
                self.console.print(f"[red]{traceback.format_exc()}[/red]")
                return False
    
    def display_request(self, request: HITLRequest):
        """Display request in a formatted way"""
        # Create header
        header = f"[bold cyan]HITL Request from {request.tool_name or 'Unknown Tool'}[/bold cyan]"
        
        # Create content based on request type
        if request.type == RequestType.FEEDBACK:
            content = f"[yellow]{request.prompt}[/yellow]"
        elif request.type == RequestType.NOTIFY:
            content = f"[green]{request.prompt}[/green]"
        
        # Display panel
        panel = Panel(
            content,
            title=header,
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
        
        # Show context if available
        if request.context:
            self.console.print("\n[dim]Context:[/dim]")
            for key, value in request.context.items():
                self.console.print(f"  {key}: {value}")
    
    async def handle_request(self, request: HITLRequest):
        """Handle a single request"""
        self.console.clear()
        self.console.print(f"\n[bold green]New Request Received[/bold green] (ID: {request.id[:8]}...)")
        self.console.print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.display_request(request)
        
        try:
            # Handle based on request type
            if request.type == RequestType.FEEDBACK:
                self.console.print("\n[bold cyan]Your feedback:[/bold cyan]")
                self.console.print(Text("• Press Enter for new line", style="dim"))
                self.console.print(Text("• Press Enter twice (empty line) to submit", style="dim"))
                self.console.print(Text("• Or press Ctrl+D to submit\n", style="dim"))
                
                lines = []
                line_num = 1
                empty_line_count = 0
                try:
                    while True:
                        # Show line number for better UX
                        line = input(f"[{line_num}] ")
                        
                        # Check for double Enter (empty line)
                        if line == "":
                            empty_line_count += 1
                            if empty_line_count >= 1 and len(lines) > 0:
                                # Remove the last empty line from lines if it was added
                                break
                            elif len(lines) == 0:
                                # If no content yet, reset counter and continue
                                empty_line_count = 0
                                continue
                        else:
                            empty_line_count = 0
                        
                        # Clean up any Unicode surrogates in the line
                        line = line.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                        
                        lines.append(line)
                        line_num += 1
                except EOFError:
                    # Ctrl+D pressed
                    pass
                
                value = "\n".join(lines)
                
                # Clean up any Unicode surrogates that might be present
                # This can happen when inputting and deleting Chinese characters
                
                    
                value = value.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                
                if value.strip():
                    self.console.print(f"\n[green]Received {len(lines)} lines of feedback[/green]")
                else:
                    self.console.print("\n[yellow]No feedback provided[/yellow]")
                    
                response = HITLResponse(request_id=request.id, value=value)
                
            elif request.type == RequestType.NOTIFY:
                # Just display notification, no response needed
                self.console.print("\n[dim]Press Enter to acknowledge...[/dim]")
                input()
                # response = HITLResponse(request_id=request.id, value=True)
                response = None
            
            else:
                # response = HITLResponse(
                #     request_id=request.id,
                #     success=False,
                #     error=f"Unknown request type: {request.type}"
                # )
                response = None
            
            # Send response
            if response is not None:
                success = await self.send_response(response)
            else:
                success = True
            if success:
                self.console.print("\n[green]✓ Response sent successfully[/green]")
            else:
                self.console.print("\n[red]✗ Failed to send response[/red]")
                
        except KeyboardInterrupt:
            # User cancelled
            response = HITLResponse(
                request_id=request.id,
                success=False,
                error="User cancelled"
            )
            await self.send_response(response)
            self.console.print("\n[yellow]Request cancelled[/yellow]")
        except Exception as e:
            # Error occurred
            response = HITLResponse(
                request_id=request.id,
                success=False,
                error=str(e)
            )
            await self.send_response(response)
            self.console.print(f"\n[red]Error: {e}[/red]")
    
    async def run(self):
        """Main loop for the shell"""
        self.running = True
        
        # Display welcome message
        self.console.print(Panel.fit(
            "[bold green]HITL Shell Started[/bold green]\n"
            f"Connected to: {self.server_url}\n"
            "Waiting for requests...",
            border_style="green"
        ))
        
        while self.running:
            try:
                # Poll for next request
                request = await self.get_next_request(timeout=30.0)
                if request:
                    await self.handle_request(request)
                    self.console.print("\n[dim]Waiting for next request...[/dim]")
                else:
                    # No request, just continue polling
                    self.console.print(".", end="", style="dim")
                    
            except KeyboardInterrupt:
                self.console.print("\n\n[yellow]Shutting down...[/yellow]")
                self.running = False
                break
            except Exception as e:
                self.console.print(f"\n[red]Unexpected error: {e}[/red]")
                await asyncio.sleep(5)  # Wait before retrying


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HITL Interactive Shell")
    parser.add_argument(
        "--server",
        default="http://localhost:8765",
        help="HITL server URL (default: http://localhost:8765)"
    )
    
    args = parser.parse_args()
    
    shell = HITLShell(server_url=args.server)
    
    try:
        await shell.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())