"""Command line interface for the agentic research tool."""

import argparse
import os
import sys
from typing import Optional
from config import OPENAI_API_KEY, DEFAULT_QUERY, RESULTS_DIR

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    
    parser = argparse.ArgumentParser(
        description="Agentic Research Tool - AI-powered research with critique capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -q "Research AI safety regulations in Brazil"
  %(prog)s -q "Find all capabilities for agentic product X" -v -c
  %(prog)s -q "Market analysis query" -c -r -v
  %(prog)s --critique-only --input-file results/research_results.txt -q "Original query"
  %(prog)s --final-report-only -q "Original query"
  %(prog)s -q "Simple market analysis query" --critique-model gpt-4o
  %(prog)s -q "Some complex research query that may require multiple iterations" -vcri
        """
    )
    
    # Main arguments
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Research query to process"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    
    parser.add_argument(
        "-c", "--critique",
        action="store_true",
        help="Run critique after research"
    )
    
    parser.add_argument(
        "--critique-only",
        action="store_true",
        help="Only run critique on existing research"
    )
    
    parser.add_argument(
        "-r", "--final-report",
        action="store_true",
        help="Generate final report after research and critique"
    )
    
    parser.add_argument(
        "--final-report-only",
        action="store_true",
        help="Only generate final report from existing research and critique results"
    )
    
    parser.add_argument(
        "--input-file",
        type=str,
        help="Input file for critique-only mode"
    )
    
    parser.add_argument(
        "--critique-model",
        type=str,
        help="Specific model to use for critique"
    )
    
    parser.add_argument(
        "--research-model",
        type=str,
        help="Specific model to use for research"
    )
    
    parser.add_argument(
        "-i", "--iterative",
        action="store_true",
        help="Enable iterative research-critique loop (critique can request more research)"
    )
    
    return parser

def validate_args(args: argparse.Namespace) -> tuple[bool, Optional[str]]:
    """
    Validate command line arguments.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # Check API key
    if not OPENAI_API_KEY:
        return False, "OPENAI_API_KEY environment variable is required"
    
    # Check critique-only mode requirements
    if args.critique_only:
        if not args.input_file:
            # Use default input file location
            default_input = os.path.join(RESULTS_DIR, "research_results.txt")
            if os.path.exists(default_input):
                args.input_file = default_input
                print(f"Using default input file: {args.input_file}")
            else:
                return False, f"Critique-only mode requires --input-file (default {default_input} not found)"
        if not args.query:
            return False, "Critique-only mode requires --query (original query)"
    
    # Check final-report-only mode requirements
    if args.final_report_only:
        default_research = os.path.join(RESULTS_DIR, "research_results.txt")
        default_critique = os.path.join(RESULTS_DIR, "critique_results.txt")
        
        if not os.path.exists(default_research):
            return False, f"Final-report-only mode requires existing research results at {default_research}"
        if not os.path.exists(default_critique):
            return False, f"Final-report-only mode requires existing critique results at {default_critique}"
        if not args.query:
            return False, "Final-report-only mode requires --query (original query)"
        
        print(f"Using research file: {default_research}")
        print(f"Using critique file: {default_critique}")
    
    # Check query requirement for non-critique-only modes
    if not args.critique_only and not args.query:
        # Use default query if none provided
        args.query = DEFAULT_QUERY
        print(f"Using default query: {args.query}")
    
    return True, None

def get_effective_query(args: argparse.Namespace) -> str:
    """Get the effective query to use."""
    if args.query:
        return args.query
    return DEFAULT_QUERY

def display_welcome():
    """Display welcome message."""
    print("🔍 Agentic Research Tool")
    print("=" * 40)

def display_error(message: str):
    """Display error message and exit."""
    print(f"❌ Error: {message}", file=sys.stderr)
    sys.exit(1)

def display_success(message: str):
    """Display success message."""
    print(f"✅ {message}")

def display_info(message: str):
    """Display info message."""
    print(f"ℹ️  {message}")

def display_warning(message: str):
    """Display warning message."""
    print(f"⚠️  {message}")

def display_processing(message: str):
    """Display processing message."""
    print(f"🔄 {message}")

def display_critique_mode():
    """Display critique mode header."""
    print("\n📝 Critique Mode")
    print("-" * 20)

def display_research_mode():
    """Display research mode header."""
    print("\n🔍 Research Mode")
    print("-" * 20)

