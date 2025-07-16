"""Token usage tracking system for the agentic research tool."""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class TokenUsage:
    """Token usage information for a single model response."""
    model: str
    timestamp: float
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_tokens_cached: int = 0
    output_tokens_reasoning: int = 0
    operation_type: str = "unknown"  # research, critique, final_report
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_openai_usage(cls, model: str, usage: Any, operation_type: str = "unknown") -> "TokenUsage":
        """Create TokenUsage from OpenAI usage object."""
        return cls(
            model=model,
            timestamp=time.time(),
            requests=getattr(usage, 'requests', 1),
            input_tokens=getattr(usage, 'input_tokens', 0),
            output_tokens=getattr(usage, 'output_tokens', 0),
            total_tokens=getattr(usage, 'total_tokens', 0),
            input_tokens_cached=getattr(getattr(usage, 'input_tokens_details', None), 'cached_tokens', 0) or 0,
            output_tokens_reasoning=getattr(getattr(usage, 'output_tokens_details', None), 'reasoning_tokens', 0) or 0,
            operation_type=operation_type
        )


class TokenTracker:
    """Tracks token usage across multiple model calls."""
    
    def __init__(self):
        self.usage_history: List[TokenUsage] = []
        self.totals_by_model: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'requests': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'input_tokens_cached': 0,
            'output_tokens_reasoning': 0
        })
        self.totals_by_operation: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'requests': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'input_tokens_cached': 0,
            'output_tokens_reasoning': 0
        })
    
    def add_usage(self, usage: TokenUsage):
        """Add a token usage record."""
        self.usage_history.append(usage)
        
        # Update model totals
        model_totals = self.totals_by_model[usage.model]
        model_totals['requests'] += usage.requests
        model_totals['input_tokens'] += usage.input_tokens
        model_totals['output_tokens'] += usage.output_tokens
        model_totals['total_tokens'] += usage.total_tokens
        model_totals['input_tokens_cached'] += usage.input_tokens_cached
        model_totals['output_tokens_reasoning'] += usage.output_tokens_reasoning
        
        # Update operation totals
        op_totals = self.totals_by_operation[usage.operation_type]
        op_totals['requests'] += usage.requests
        op_totals['input_tokens'] += usage.input_tokens
        op_totals['output_tokens'] += usage.output_tokens
        op_totals['total_tokens'] += usage.total_tokens
        op_totals['input_tokens_cached'] += usage.input_tokens_cached
        op_totals['output_tokens_reasoning'] += usage.output_tokens_reasoning
    
    def get_model_summary(self) -> Dict[str, Dict[str, int]]:
        """Get token usage summary by model."""
        return dict(self.totals_by_model)
    
    def get_operation_summary(self) -> Dict[str, Dict[str, int]]:
        """Get token usage summary by operation type."""
        return dict(self.totals_by_operation)
    
    def get_total_usage(self) -> Dict[str, int]:
        """Get overall token usage totals."""
        totals = {
            'requests': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'input_tokens_cached': 0,
            'output_tokens_reasoning': 0
        }
        
        for usage in self.usage_history:
            totals['requests'] += usage.requests
            totals['input_tokens'] += usage.input_tokens
            totals['output_tokens'] += usage.output_tokens
            totals['total_tokens'] += usage.total_tokens
            totals['input_tokens_cached'] += usage.input_tokens_cached
            totals['output_tokens_reasoning'] += usage.output_tokens_reasoning
        
        return totals
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get comprehensive usage report."""
        return {
            'total_usage': self.get_total_usage(),
            'by_model': self.get_model_summary(),
            'by_operation': self.get_operation_summary(),
            'detailed_history': [usage.to_dict() for usage in self.usage_history]
        }
    
    def save_to_file(self, filepath: str):
        """Save token usage report to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.get_usage_report(), f, indent=2)
    
    def format_markdown_section(self, final_report: bool = False) -> str:
        """Format token usage statistics as markdown section for reports."""
        total_usage = self.get_total_usage()
        model_usage = self.get_model_summary()
        operation_usage = self.get_operation_summary()
        
        # Use different header for final reports to clarify these tokens are not included in cost estimates
        header = "## Token Usage Statistics (not included in cost estimates)" if final_report else "## Token Usage Statistics"
        
        lines = [
            header,
            "",
            f"**Total Usage:** {total_usage['total_tokens']:,} tokens ({total_usage['input_tokens']:,} input, {total_usage['output_tokens']:,} output)",
        ]
        
        if total_usage['input_tokens_cached'] > 0:
            lines.append(f"**Cached Tokens:** {total_usage['input_tokens_cached']:,}")
        
        if total_usage['output_tokens_reasoning'] > 0:
            lines.append(f"**Reasoning Tokens:** {total_usage['output_tokens_reasoning']:,}")
        
        lines.extend([
            f"**Total Requests:** {total_usage['requests']:,}",
            "",
            "### By Model:"
        ])
        
        for model, usage in model_usage.items():
            cost_breakdown = []
            if usage['input_tokens_cached'] > 0:
                cost_breakdown.append(f"{usage['input_tokens_cached']:,} cached")
            if usage['output_tokens_reasoning'] > 0:
                cost_breakdown.append(f"{usage['output_tokens_reasoning']:,} reasoning")
            
            cost_info = f" ({', '.join(cost_breakdown)})" if cost_breakdown else ""
            lines.append(f"- **{model}:** {usage['total_tokens']:,} tokens ({usage['requests']:,} requests{cost_info})")
        
        lines.extend([
            "",
            "### By Operation:"
        ])
        
        for operation, usage in operation_usage.items():
            cost_breakdown = []
            if usage['input_tokens_cached'] > 0:
                cost_breakdown.append(f"{usage['input_tokens_cached']:,} cached")
            if usage['output_tokens_reasoning'] > 0:
                cost_breakdown.append(f"{usage['output_tokens_reasoning']:,} reasoning")
            
            cost_info = f" ({', '.join(cost_breakdown)})" if cost_breakdown else ""
            lines.append(f"- **{operation}:** {usage['total_tokens']:,} tokens ({usage['requests']:,} requests{cost_info})")
        
        return "\n".join(lines)

    def print_summary(self):
        """Print a human-readable summary of token usage."""
        print("\n📊 Token Usage Summary")
        print("=" * 50)
        
        total = self.get_total_usage()
        print(f"Overall: {total['total_tokens']:,} tokens ({total['input_tokens']:,} input, {total['output_tokens']:,} output)")
        
        # Always show cached and reasoning tokens for debugging
        print(f"Cached tokens: {total['input_tokens_cached']:,}")
        print(f"Reasoning tokens: {total['output_tokens_reasoning']:,}")
        
        print(f"Total requests: {total['requests']:,}")
        
        print("\nBy Model:")
        for model, usage in self.totals_by_model.items():
            cached_info = f", {usage['input_tokens_cached']:,} cached" if usage['input_tokens_cached'] > 0 else ""
            reasoning_info = f", {usage['output_tokens_reasoning']:,} reasoning" if usage['output_tokens_reasoning'] > 0 else ""
            print(f"  {model}: {usage['total_tokens']:,} tokens ({usage['requests']:,} requests{cached_info}{reasoning_info})")
        
        print("\nBy Operation:")
        for operation, usage in self.totals_by_operation.items():
            cached_info = f", {usage['input_tokens_cached']:,} cached" if usage['input_tokens_cached'] > 0 else ""
            reasoning_info = f", {usage['output_tokens_reasoning']:,} reasoning" if usage['output_tokens_reasoning'] > 0 else ""
            print(f"  {operation}: {usage['total_tokens']:,} tokens ({usage['requests']:,} requests{cached_info}{reasoning_info})")


# Global token tracker instance
_global_tracker = TokenTracker()

def get_global_tracker() -> TokenTracker:
    """Get the global token tracker instance."""
    return _global_tracker

def reset_global_tracker():
    """Reset the global token tracker."""
    global _global_tracker
    _global_tracker = TokenTracker()

def track_usage(model: str, usage: Any, operation_type: str = "unknown"):
    """Convenience function to track usage with global tracker."""
    token_usage = TokenUsage.from_openai_usage(model, usage, operation_type)
    _global_tracker.add_usage(token_usage)
    return token_usage