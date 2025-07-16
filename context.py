"""Context management for the agentic research tool."""

from dataclasses import dataclass
from typing import Optional, Any, Dict
import json
import os
from datetime import datetime
from config import RESULTS_DIR
from token_tracker import get_global_tracker


def _create_file_header(title: str, query: str) -> str:
    """Create standardized file header."""
    return f"{title}: {query}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'=' * 50}\n\n"

@dataclass
class ResearchContext:
    """Context object passed to all agents and tools."""
    
    query: str
    verbose: bool = False
    critique_requested: bool = False
    critique_only: bool = False
    input_file: Optional[str] = None
    output_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.output_data is None:
            self.output_data = {}
    
    def save_research_results(self, content: str, reasoning: str = "", 
                            tools_used: list = None, web_searches: list = None):
        """Save research results to files with token usage statistics."""
        if tools_used is None:
            tools_used = []
        if web_searches is None:
            web_searches = []
            
        # Get token usage statistics
        tracker = get_global_tracker()
        token_stats = tracker.format_markdown_section()
        
        # Combine research content with token usage statistics
        content_with_stats = f"{content}\n\n{token_stats}"
            
        # Save text results
        txt_path = os.path.join(RESULTS_DIR, "research_results.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(_create_file_header("Research Query", self.query))
            f.write(content_with_stats)
            
        # Save JSON results
        json_data = {
            "query": self.query,
            "timestamp": datetime.now().isoformat(),
            "content": content_with_stats,
            "reasoning": reasoning,
            "tools_used": tools_used,
            "web_searches": web_searches,
            "token_usage": tracker.get_usage_report()
        }
        
        json_path = os.path.join(RESULTS_DIR, "research_results.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            
        self.output_data.update(json_data)
        
        if self.verbose:
            print(f"Results saved to {txt_path} and {json_path}")
    
    def save_critique_results(self, critique: str):
        """Save critique results to file with token usage statistics."""
        # Get token usage statistics
        tracker = get_global_tracker()
        token_stats = tracker.format_markdown_section()
        
        # Combine critique with token usage statistics
        critique_with_stats = f"{critique}\n\n{token_stats}"
        
        critique_path = os.path.join(RESULTS_DIR, "critique_results.txt")
        with open(critique_path, 'w', encoding='utf-8') as f:
            f.write(_create_file_header("Critique for Query", self.query))
            f.write(critique_with_stats)
            
        # Update JSON with critique (including token stats)
        json_path = os.path.join(RESULTS_DIR, "research_results.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["critique"] = critique_with_stats
            data["critique_timestamp"] = datetime.now().isoformat()
            data["token_usage"] = tracker.get_usage_report()
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        self.output_data["critique"] = critique_with_stats
        self.output_data["token_usage"] = tracker.get_usage_report()
        
        if self.verbose:
            print(f"Critique saved to {critique_path}")
    
    def save_final_report_results(self, final_report: str):
        """Save final report results to file with token usage statistics."""
        # Get token usage statistics
        tracker = get_global_tracker()
        token_stats = tracker.format_markdown_section(final_report=True)
        
        # Combine final report with token usage statistics
        final_report_with_stats = f"{final_report}\n\n{token_stats}"
        
        final_report_path = os.path.join(RESULTS_DIR, "final_report.md")
        with open(final_report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Final Research Report\n\n")
            f.write(f"**Original Query:** {self.query}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(final_report_with_stats)
            
        # Update JSON with final report (including token stats)
        json_path = os.path.join(RESULTS_DIR, "research_results.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["final_report"] = final_report_with_stats
            data["final_report_timestamp"] = datetime.now().isoformat()
            data["token_usage"] = tracker.get_usage_report()  # Update with latest stats
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        self.output_data["final_report"] = final_report_with_stats
        self.output_data["token_usage"] = tracker.get_usage_report()
        
        if self.verbose:
            print(f"Final report saved to {final_report_path}")
    
    def load_research_content(self, file_path: str) -> str:
        """Load research content from file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # If it's a JSON file, extract the content field
        if file_path.endswith('.json'):
            try:
                data = json.loads(content)
                return data.get('content', content)
            except json.JSONDecodeError:
                pass
                
        return content
    
