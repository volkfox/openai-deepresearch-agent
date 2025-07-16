"""Main entry point for the agentic research tool."""

import asyncio
import sys
import os
import json
import logging
from typing import Optional

# Configure logging to suppress SSE ping messages
logging.basicConfig(level=logging.WARNING)
# Suppress specific loggers that might be printing SSE ping messages
logging.getLogger('agents').setLevel(logging.ERROR)
logging.getLogger('agents.mcp').setLevel(logging.ERROR)
logging.getLogger('mcp.client.sse').setLevel(logging.ERROR)  # This suppresses the ping warnings
logging.getLogger('httpx').setLevel(logging.WARNING)


from agents import Runner
from cli import (
    create_parser, validate_args, get_effective_query,
    display_welcome, display_error, display_success, display_info, display_warning,
    display_critique_mode, display_research_mode
)
from config import (
    MODEL_RESEARCH, MODEL_CRITIQUE, RESULTS_DIR, MAX_TURNS_RESEARCH, MAX_TURNS_CRITIQUE, MAX_TURNS_FINAL_REPORT,
    EXIT_SUCCESS, EXIT_VALIDATION_ERROR, EXIT_RESEARCH_AGENT_ERROR, EXIT_CRITIQUE_AGENT_ERROR, 
    EXIT_FINAL_REPORT_AGENT_ERROR, EXIT_GENERAL_ERROR
)
from context import ResearchContext
from research_agents import ResearchAgents
from token_tracker import get_global_tracker, reset_global_tracker
from event_processor import create_event_processor

async def run_research_workflow(args) -> dict:
    """
    Run the research workflow based on arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Dictionary with results
    """
    
    # Update config with CLI arguments
    research_model = args.research_model if args.research_model else MODEL_RESEARCH
    critique_model = args.critique_model if args.critique_model else MODEL_CRITIQUE
    
    # Reset token tracker for new workflow
    reset_global_tracker()
    
    # Create research context
    query = get_effective_query(args)
    context = ResearchContext(
        query=query,
        verbose=args.verbose,
        critique_requested=args.critique,
        critique_only=args.critique_only,
        input_file=args.input_file
    )
    
    results = {}
    
    # Track which agent failed for specific error codes
    failed_agent = None
    
    try:
        if args.iterative and args.critique and not args.final_report_only and not args.critique_only:
            # Use iterative handoff workflow when explicitly enabled
            failed_agent = await run_iterative_workflow(context, args, results)
        else:
            # Use standalone workflow by default
            failed_agent = await run_standalone_workflow(context, args, results)
            
    except KeyboardInterrupt:
        display_error("Workflow interrupted by user (Ctrl+C)")
        results["error"] = "User interruption"
    except Exception as e:
        error_msg = str(e)
        if "stream" in error_msg.lower() or "connection" in error_msg.lower():
            display_error(f"Streaming connection failed: {error_msg}")
            results["error"] = f"Streaming failure: {error_msg}"
        else:
            display_error(f"Workflow execution failed: {error_msg}")
            results["error"] = error_msg
        failed_agent = "general"
    
    # Add token usage to results
    tracker = get_global_tracker()
    results["token_usage"] = tracker.get_usage_report()
    
    # Save token usage report
    token_usage_path = os.path.join(RESULTS_DIR, "token_usage.json")
    tracker.save_to_file(token_usage_path)
    
    # Display token usage summary
    if args.verbose:
        tracker.print_summary()
    
    # Add failed agent info to results for error code determination
    if failed_agent:
        results["failed_agent"] = failed_agent
    
    return results


async def run_iterative_workflow(context: ResearchContext, args, results: dict):
    """Run iterative research-critique workflow with hybrid handoffs."""
    failed_agent = None
    from agents import Runner
    
    display_info("🔄 Iterative Research-Critique Workflow (Hybrid)")
    print("--------------------")
    print("Using hybrid approach: programmatic research→critique, OpenAI critique→research")
    
    # Create regular research agent (no MCP)
    research_agent = ResearchAgents.create_research_agent()
    
    if context.verbose:
        display_info(f"Starting iterative workflow: {context.query}")
        print(f"\n🔍 Beginning research...")
    
    # Step 1: Run initial research programmatically
    try:
        result_stream = Runner.run_streamed(research_agent, context.query, context=context, max_turns=MAX_TURNS_RESEARCH)
        processor = create_event_processor(context, "research")
        research_content = await processor.process_stream(result_stream, "🔍 Research")
    except Exception as e:
        failed_agent = "research"
        raise e
    
    if context.verbose:
        print("\n")
        display_success("Initial research completed")
    
    # Save initial research results
    context.save_research_results(research_content)
    results.update(context.output_data)
    results["research_output"] = research_content
    
    if context.verbose:
        print(f"\n📝 Starting critique with handoff capability and MCP tools...")
    
    # Step 2: Create critique agent with MCP and handoff to research agent
    critique_agent, mcp_server = await ResearchAgents.create_critique_agent_with_mcp(research_agent)
    
    try:
        # Create critique message with research content
        critique_message = ResearchAgents.create_critique_message(context.query, research_content)
        
        # Run critique with potential handoff back to research
        try:
            result_stream = Runner.run_streamed(
                critique_agent, 
                critique_message, 
                context=context, 
                max_turns=MAX_TURNS_CRITIQUE
            )
            processor = create_event_processor(context, "research_critique_iterative")
            final_output = await processor.process_stream(result_stream, "📝 Critique")
        except Exception as e:
            failed_agent = "critique"
            raise e
        
        if context.verbose:
            print("\n")
            display_success("Iterative workflow completed")
        
        # Print final output to screen
        if final_output:
            print("\n" + "="*60)
            print("FINAL OUTPUT:")
            print("="*60)
            print(final_output)
            print("="*60 + "\n")
        
        # Save critique results to context for final report
        if final_output:
            context.save_critique_results(final_output)
        
        # Save final results
        results.update(context.output_data)
        results["iterative_output"] = final_output
        
        # If final report is also requested, generate it using standalone approach
        if args.final_report:
            print("\n" + "="*60)
            display_info("📊 Final Report Mode")
            print("="*60)
            try:
                await run_final_report(context, results)
            except Exception as e:
                failed_agent = "final_report"
                raise e
            
    finally:
        # Clean up MCP server
        await mcp_server.cleanup()
    
    return failed_agent

async def run_standalone_workflow(context: ResearchContext, args, results: dict):
    """Run workflow using standalone agents."""
    failed_agent = None
    
    if args.final_report_only:
        # Final-report-only mode
        display_info("📊 Final Report Only Mode")
        print("--------------------")
        try:
            await run_final_report(context, results, source_description="final-report-only")
        except Exception as e:
            failed_agent = "final_report"
            raise e
    elif args.critique_only:
        # Critique-only mode
        display_critique_mode()
        try:
            await run_critique(context, results)
        except Exception as e:
            failed_agent = "critique"
            raise e
    elif args.critique:
        # Research + critique mode  
        display_research_mode()
        try:
            await run_research(context, results)
        except Exception as e:
            failed_agent = "research"
            raise e
        
        display_critique_mode()
        # Get research content from context and pass it to critique
        research_content = context.output_data.get("content", "")
        if not research_content:
            display_warning("No research content found for critique")
        else:
            try:
                await run_critique(context, results, research_content, "previous research")
            except Exception as e:
                failed_agent = "critique"
                raise e
            
        # If final report is also requested, generate it
        if args.final_report:
            print("\n" + "="*60)
            display_info("📊 Final Report Mode")
            print("="*60)
            try:
                await run_final_report(context, results)
            except Exception as e:
                failed_agent = "final_report"
                raise e
    elif args.final_report:
        # Research + final report mode (without critique)
        display_research_mode()
        try:
            await run_research(context, results)
        except Exception as e:
            failed_agent = "research"
            raise e
        
        print("\n" + "="*60)
        display_info("📊 Final Report Mode")
        print("="*60)
        try:
            await run_final_report(context, results)
        except Exception as e:
            failed_agent = "final_report"
            raise e
    else:
        # Research-only mode
        display_research_mode()
        try:
            await run_research(context, results)
        except Exception as e:
            failed_agent = "research"
            raise e
    
    return failed_agent

async def run_research(context: ResearchContext, results: dict):
    """Run standalone research."""
    
    # Create regular research agent (no MCP)
    research_agent = ResearchAgents.create_research_agent()
    
    if context.verbose:
        display_info(f"Starting research: {context.query}")
        print(f"\n🔍 Researching: {context.query}")
    
    # Use streaming with centralized event processing
    result_stream = Runner.run_streamed(research_agent, context.query, context=context, max_turns=MAX_TURNS_RESEARCH)
    
    # Process events through centralized processor
    processor = create_event_processor(context, "research")
    research_content = await processor.process_stream(result_stream)
    
    if context.verbose:
        print("\n")
        display_success("Research completed")
    
    # Save research results
    context.save_research_results(research_content)
    
    results.update(context.output_data)
    results["research_output"] = research_content

async def run_critique(context: ResearchContext, results: dict, research_content: str = None, source_description: str = "research"):
    """Run critique workflow on research content."""
    
    # Create critique agent with MCP server
    critique_agent, mcp_server = await ResearchAgents.create_critique_agent_with_mcp()
    
    try:
        # Get research content - either from parameter or load from file
        if research_content is None:
            research_content = context.load_research_content(context.input_file)
            source_description = f"file: {context.input_file}"
        
        critique_message = ResearchAgents.create_critique_message(context.query, research_content)
        
        if context.verbose:
            display_info(f"Starting critique of {source_description}")
            print(f"\n📝 Critiquing research with MCP tools...")
        
        # Use streaming with centralized event processing
        result_stream = Runner.run_streamed(
            critique_agent, 
            critique_message, 
            context=context, 
            max_turns=MAX_TURNS_CRITIQUE
        )
        
        # Determine workflow type for event processor
        workflow_type = "critique_only" if "file:" in source_description else "critique"
        processor = create_event_processor(context, workflow_type)
        critique_content = await processor.process_stream(result_stream)
        
        if context.verbose:
            print("\n")
            display_success("Critique completed")
        
        # Save critique results
        context.save_critique_results(critique_content)
        
        results.update(context.output_data)
        results["critique_output"] = critique_content
        
    finally:
        # Clean up MCP server
        await mcp_server.cleanup()


async def run_final_report(context: ResearchContext, results: dict, research_content: str = None, critique_content: str = None, source_description: str = "workflow"):
    """Run final report generation using research and critique content."""
    
    final_report_agent = ResearchAgents.create_final_report_agent()
    
    # Get research and critique content - either from parameters or load from files/context
    if research_content is None or critique_content is None:
        if source_description == "workflow":
            # Get from context (after research and critique steps)
            research_content = context.output_data.get("content", "")
            critique_content = context.output_data.get("critique", "")
            source_description = "previous workflow steps"
        else:
            # Load from files (final-report-only mode)
            research_path = os.path.join(RESULTS_DIR, "research_results.txt")
            critique_path = os.path.join(RESULTS_DIR, "critique_results.txt")
            research_content = context.load_research_content(research_path)
            critique_content = context.load_research_content(critique_path)
            source_description = f"files: {research_path} and {critique_path}"
    
    if not research_content:
        display_warning("No research content found for final report")
        return
    
    if not critique_content:
        display_warning("No critique content found for final report")
        return
    
    final_report_message = ResearchAgents.create_final_report_message(context.query, research_content, critique_content)
    
    if context.verbose:
        display_info(f"Starting final report generation from {source_description}")
    
    print(f"\n📊 Generating comprehensive final report...")
    print("(Synthesizing research findings and critique into markdown format)")
    print()
    
    # Use streaming with centralized event processing
    result_stream = Runner.run_streamed(final_report_agent, final_report_message, context=context, max_turns=MAX_TURNS_FINAL_REPORT)
    
    # Determine workflow type for event processor
    workflow_type = "final_report_only" if "files:" in source_description else "final_report"
    processor = create_event_processor(context, workflow_type)
    final_report_content = await processor.process_stream(result_stream)
    
    # Print final report to screen
    if final_report_content:
        print("\n" + "="*60)
        print("FINAL REPORT:")
        print("="*60)
        print(final_report_content)
        print("="*60 + "\n")
    
    if context.verbose:
        print("\n")
        display_success("Final report completed")
    
    # Save final report results
    context.save_final_report_results(final_report_content)
    
    results.update(context.output_data)
    results["final_report_output"] = final_report_content


async def main():
    """Main entry point."""
    
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Display welcome
    display_welcome()
    
    # Validate arguments
    is_valid, error_msg = validate_args(args)
    if not is_valid:
        display_error(error_msg)
        return EXIT_VALIDATION_ERROR
    
    # Run workflow
    results = await run_research_workflow(args)
    
    # Display final results and return appropriate exit code
    if "error" not in results:
        display_success("Workflow completed successfully!")
        if args.verbose:
            display_info(f"Results saved to: {RESULTS_DIR}/")
        return EXIT_SUCCESS
    else:
        display_error(f"Workflow failed: {results['error']}")
        
        # Return specific error code based on which agent failed
        failed_agent = results.get("failed_agent", "general")
        if failed_agent == "research":
            return EXIT_RESEARCH_AGENT_ERROR
        elif failed_agent == "critique":
            return EXIT_CRITIQUE_AGENT_ERROR
        elif failed_agent == "final_report":
            return EXIT_FINAL_REPORT_AGENT_ERROR
        else:
            return EXIT_GENERAL_ERROR

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)