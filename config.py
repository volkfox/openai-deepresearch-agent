"""Configuration for the agentic research tool."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)

# API Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Model Configuration
MODEL_RESEARCH = "o4-mini-deep-research"
MODEL_CRITIQUE = "o3-pro"
MODEL_FINAL_REPORT = "o4-mini"

# Agent Configuration
MAX_TURNS_RESEARCH = 15
MAX_TURNS_CRITIQUE = 25
MAX_TURNS_FINAL_REPORT = 15

# File Configuration
RESULTS_DIR = "results"
DEFAULT_QUERY = (
    "Find if Microsoft 365 Copilot has SOC2 and HIPAA compliance. "
    "Do not be distracted with other products under Copilot brand. "
    "Ground your answers in official data from Microsoft."
)

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

# Exit codes for different failure types
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_RESEARCH_AGENT_ERROR = 2
EXIT_CRITIQUE_AGENT_ERROR = 3
EXIT_FINAL_REPORT_AGENT_ERROR = 4
EXIT_GENERAL_ERROR = 5

# Configuration validation utility
def validate_config() -> bool:
    """Validate essential configuration."""
    return bool(OPENAI_API_KEY)
