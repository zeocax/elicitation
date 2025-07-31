#!/usr/bin/env python3
"""Simple test for reasoning content extraction"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.llm import LLMClient


async def main():
    client = LLMClient()
    
    # Test message with thinking tags
    messages = [
        {"role": "user", "content": "Explain to me how AI works"}
    ]
    
    print("Testing reasoning extraction...")
    print(f"Input: {messages[0]['content']}")
    print("\n--- Output ---")
    
    result = await client.call(messages)
    print(f"\nFinal content returned: {result}")


if __name__ == "__main__":
    asyncio.run(main())