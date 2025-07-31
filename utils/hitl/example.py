"""Example usage of simplified HITL system"""

import asyncio
from utils.hitl import HITLClient


async def main():
    # Initialize HITL client
    client = HITLClient()
    
    # Example 1: Request feedback from user
    feedback = await client.request_feedback(
        prompt="Please provide your feedback on the generated code:",
        tool_name="CodeGenerator",
        context={"file": "main.py", "lines": 100}
    )
    
    if feedback:
        print(f"User feedback: {feedback}")
    else:
        print("No feedback received")
    
    # Example 2: Send notification without requiring feedback
    success = await client.notify(
        message="Code generation completed successfully! 5 files were created.",
        tool_name="CodeGenerator",
        context={"files_created": 5, "total_lines": 500}
    )
    
    if success:
        print("Notification sent successfully")
    else:
        print("Failed to send notification")


if __name__ == "__main__":
    asyncio.run(main())