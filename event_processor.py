"""Centralized event processing for streaming workflows."""

import json
import os
from typing import Dict, Any, Optional
from config import RESULTS_DIR, MODEL_RESEARCH, MODEL_CRITIQUE, MODEL_FINAL_REPORT
from context import ResearchContext
from token_tracker import get_global_tracker, track_usage


class StreamEventProcessor:
    """Centralized processor for handling streaming events from agents."""
    
    # Class-level mappings for better performance
    WORKFLOW_TO_MODEL = {
        "research": MODEL_RESEARCH,
        "critique": MODEL_CRITIQUE,
        "critique_only": MODEL_CRITIQUE,
        "research_critique_iterative": MODEL_CRITIQUE,
        "final_report": MODEL_FINAL_REPORT,
        "final_report_only": MODEL_FINAL_REPORT,
    }
    
    WORKFLOW_TO_FILENAME = {
        "research": "raw_events_research.json", 
        "critique": "raw_events_critique_after_research.json",
        "critique_only": "raw_events_critique.json",
        "final_report": "raw_events_final_report.json",
        "final_report_only": "raw_events_final_report_only.json",
        "research_critique_iterative": "raw_events_iterative.json"
    }
    
    def __init__(self, context: ResearchContext, workflow_type: str):
        self.context = context
        self.workflow_type = workflow_type
        self.raw_events = []
    
    async def process_stream(self, result_stream, display_prefix: str = ""):
        """
        Process entire event stream and return final output.
        
        Args:
            result_stream: The streaming result from Runner.run_streamed()
            display_prefix: Prefix for displayed events (e.g., "Research", "Critique")
            
        Returns:
            Final output from the stream
        """
        if self.context.verbose and display_prefix:
            print(f"\n{display_prefix} streaming events:")
        
        async for ev in result_stream.stream_events():
            self._save_raw_event(ev)
            self._display_event(ev)
        
        final_output = result_stream.final_output
        self._display_token_usage(result_stream)
        self._save_raw_events_file()
        
        return final_output
    
    def _is_ping_event(self, ev) -> bool:
        """Check if event is a ping event that should be filtered out."""
        return (hasattr(ev, 'type') and ev.type == 'ping') or 'ping' in str(ev).lower()
    
    def _save_raw_event(self, ev):
        """Save raw event for debugging."""
        if self._is_ping_event(ev):
            return
            
        try:
            if hasattr(ev, 'model_dump'):
                self.raw_events.append(ev.model_dump())
            else:
                self.raw_events.append({
                    "type": str(type(ev).__name__),
                    "str_repr": str(ev),
                    "event_type": getattr(ev, 'type', 'unknown')
                })
        except Exception as e:
            self.raw_events.append({
                "error": f"Failed to serialize event: {e}", 
                "type": str(type(ev).__name__)
            })
    
    def _display_event(self, ev):
        """Display event based on type and verbose settings."""
        if not self.context.verbose or self._is_ping_event(ev):
            return
            
        if ev.type == "agent_updated_stream_event":
            print(f"\n🔄 Handoff to: {ev.new_agent.name}")
        elif ev.type == "raw_response_event":
            self._display_response_event(ev)
        elif ev.type == "tool_call_delta_event":
            self._display_tool_progress(ev)
    
    def _get_item_type(self, ev) -> str:
        """Safely get the item type from an event."""
        if not hasattr(ev.data, "item") or not hasattr(ev.data.item, "type"):
            return ""
        return ev.data.item.type
    
    def _is_search_event(self, ev) -> bool:
        """Check if event is a web search event."""
        return (hasattr(ev.data, "item") and 
                hasattr(ev.data.item, "action") and 
                hasattr(ev.data.item.action, "type") and 
                ev.data.item.action.type == "search")
    
    def _display_response_event(self, ev):
        """Handle response events (web search, reasoning, tool calls)."""
        item_type = self._get_item_type(ev)
        event_type = getattr(ev.data, "type", "")
        
        if self._is_search_event(ev):
            query = getattr(ev.data.item.action, 'query', 'Unknown query')
            if query is not None:
                context_label = "Fact-checking" if self.workflow_type == "critique" else "Web search"
                print(f"🔍 [{context_label}] {query}")
        
        elif item_type == "reasoning":
            if event_type == "response.output_item.added":
                print("💭 [REASONING] ", end="", flush=True)
            elif event_type == "response.output_item.done":
                print("✓ ", end="", flush=True)
                self._display_reasoning_summary(ev.data.item)
        
        elif item_type == "code_interpreter_call" and event_type == "response.output_item.done":
            self._display_code_interpreter_call(ev.data.item)
        
        elif item_type == "function_call" and event_type == "response.output_item.done":
            self._display_tool_call(ev.data.item)
    
    def _display_reasoning_summary(self, reasoning_item):
        """Display reasoning summary if available."""
        if hasattr(reasoning_item, 'summary') and reasoning_item.summary:
            print(f"\n💭 [REASONING SUMMARY]")
            for summary in reasoning_item.summary:
                if hasattr(summary, 'text') and summary.text:
                    print(summary.text)
    
    def _display_code_interpreter_call(self, code_item):
        """Display completed code interpreter calls."""
        if hasattr(code_item, 'code') and code_item.code:
            # Extract the first line of code to show what it's doing
            code_lines = code_item.code.strip().split('\n')
            first_line = code_lines[0] if code_lines else 'Unknown code'
            
            # Show more context for short code blocks
            if len(code_lines) <= 3:
                code_preview = ' | '.join(code_lines)
            else:
                code_preview = f"{first_line}... ({len(code_lines)} lines)"
            
            print(f"\n⚙️ [Code Interpreter] {code_preview}")
    
    def _display_tool_call(self, tool_item):
        """Display completed tool calls."""
        if hasattr(tool_item, 'name') and hasattr(tool_item, 'arguments'):
            args_text = tool_item.arguments
            
            # Special handling for different tool types
            if tool_item.name == "verify_url":
                try:
                    args_dict = json.loads(args_text)
                    url = args_dict.get('url', 'unknown URL')
                    print(f"\n🔧 [Tool] {tool_item.name}({url})")
                except Exception:
                    print(f"\n🔧 [Tool] {tool_item.name}({args_text})")
            elif tool_item.name in ["read_wiki_structure", "read_wiki_contents", "ask_question"]:
                # MCP DeepWiki tools
                try:
                    args_dict = json.loads(args_text)
                    repo = args_dict.get('repoName', 'unknown repo')
                    if tool_item.name == "ask_question":
                        question = args_dict.get('question', 'unknown question')
                        print(f"\n📚 [MCP] {tool_item.name}({repo}: '{question}')")
                    else:
                        print(f"\n📚 [MCP] {tool_item.name}({repo})")
                except Exception:
                    print(f"\n📚 [MCP] {tool_item.name}({args_text})")
            else:
                print(f"\n🔧 [Tool] {tool_item.name}({args_text})")
    
    def _display_tool_progress(self, ev):
        """Show tool usage progress indicators."""
        if hasattr(ev, 'tool_call') and hasattr(ev.tool_call, 'function'):
            if ev.tool_call.function.name == "web_search":
                print(".", end="", flush=True)
            elif ev.tool_call.function.name == "verify_url":
                print("🔧", end="", flush=True)
    
    def _display_token_usage(self, result_stream):
        """Display token usage information and track it."""
        # Access usage from the context wrapper
        if hasattr(result_stream, 'context_wrapper') and hasattr(result_stream.context_wrapper, 'usage'):
            usage = result_stream.context_wrapper.usage
            
            # Determine the model based on workflow type
            model = self._get_model_for_workflow()
            
            # Track token usage
            track_usage(model, usage, self.workflow_type)
            
            # Display reasoning tokens if available
            if hasattr(usage, 'output_tokens_details') and hasattr(usage.output_tokens_details, 'reasoning_tokens'):
                reasoning_tokens = usage.output_tokens_details.reasoning_tokens
                if reasoning_tokens and reasoning_tokens > 0:
                    print(f"\n💭 Generated {reasoning_tokens:,} reasoning tokens")
            
            # Display total token usage with cached tokens if available
            if hasattr(usage, 'total_tokens') and usage.total_tokens > 0:
                usage_parts = [f"{usage.input_tokens:,} input", f"{usage.output_tokens:,} output"]
                
                # Add cached tokens if available
                if hasattr(usage, 'input_tokens_details') and hasattr(usage.input_tokens_details, 'cached_tokens'):
                    cached_tokens = usage.input_tokens_details.cached_tokens
                    if cached_tokens and cached_tokens > 0:
                        usage_parts.append(f"{cached_tokens:,} cached")
                
                print(f"🎯 Total tokens: {usage.total_tokens:,} ({', '.join(usage_parts)})")
        else:
            # Fallback: look for usage in the final_output or other attributes
            if hasattr(result_stream, 'final_output') and hasattr(result_stream.final_output, 'usage'):
                usage = result_stream.final_output.usage
                model = self._get_model_for_workflow()
                track_usage(model, usage, self.workflow_type)
                
                if hasattr(usage, 'total_tokens') and usage.total_tokens > 0:
                    print(f"🎯 Total tokens: {usage.total_tokens:,} ({usage.input_tokens:,} input, {usage.output_tokens:,} output)")
    
    def _get_model_for_workflow(self) -> str:
        """Get the model name based on workflow type."""
        return self.WORKFLOW_TO_MODEL.get(self.workflow_type, "unknown")
    
    def _save_raw_events_file(self):
        """Save raw events to workflow-specific file."""
        filename = self.WORKFLOW_TO_FILENAME.get(self.workflow_type, f"raw_events_{self.workflow_type}.json")
        raw_events_path = os.path.join(RESULTS_DIR, filename)
        
        with open(raw_events_path, 'w', encoding='utf-8') as f:
            json.dump(self.raw_events, f, indent=2, ensure_ascii=False)
        
        if self.context.verbose:
            print(f"Raw {self.workflow_type} events saved to {raw_events_path}")


def create_event_processor(context: ResearchContext, workflow_type: str) -> StreamEventProcessor:
    """Factory function to create event processor."""
    return StreamEventProcessor(context, workflow_type)