#!/usr/bin/env python3
"""
Agentic Research Tool

This is the main entry point for the agentic research tool built with OpenAI Agents framework.
It provides AI-powered research capabilities with critique functionality.
"""

import asyncio
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from main import main

if __name__ == "__main__":
    asyncio.run(main())