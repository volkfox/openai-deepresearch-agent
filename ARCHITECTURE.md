# Agentic Research Tool - Architecture Documentation

## System Overview

The agentic research tool implements a function-based workflow orchestration system built on OpenAI's Agents framework. The architecture centers on streaming event processing, global token tracking, and agent factory patterns.

## Directory Structure

```
agentic_research/
├── agentic_research.py         # Main executable entry point
├── main.py                     # Workflow orchestration functions
├── research_agents.py          # Agent factory methods and prompt templates
├── tools.py                    # Custom function tools
├── config.py                   # Configuration constants and exit codes
├── context.py                  # State management and file I/O
├── cli.py                      # Command line interface
├── event_processor.py          # Centralized streaming event processing
├── token_tracker.py            # Global token usage tracking
├── test_setup.py               # System validation
├── test_mcp_connection.py      # MCP connectivity testing
├── requirements.txt            # Dependencies
├── env.example                 # Environment template
└── results/                    # Auto-created output directory
    ├── research_results.txt    # Human-readable research reports
    ├── research_results.json   # Structured research data
    ├── critique_results.txt    # Human-readable critique analysis
    ├── final_report.md         # Markdown synthesis reports
    ├── token_usage.json        # Token usage statistics
    └── raw_events_*.json       # Debug event streams
```

## Core Architecture Components

### 1. Entry Point and Workflow Orchestration

**Entry Point:**
```python
# agentic_research.py
from main import main

if __name__ == "__main__":
    asyncio.run(main())
```

**Workflow Orchestration (main.py):**
```python
async def run_research_workflow(args) -> dict:
    failed_agent = None
    
    if args.iterative and args.critique:
        failed_agent = await run_iterative_workflow(context, args, results)
    else:
        failed_agent = await run_standalone_workflow(context, args, results)
    
    # Return results with failed_agent for exit code determination
    if failed_agent:
        results["failed_agent"] = failed_agent
    
    return results
```

**Workflow Functions:**
- `run_standalone_workflow()` - Sequential agent execution
- `run_iterative_workflow()` - Hybrid approach with agent handoffs
- `run_research()`, `run_critique()`, `run_final_report()` - Individual agent runners

### 2. Agent Factory System

**ResearchAgents Factory Class:**
```python
class ResearchAgents:
    @staticmethod
    def create_research_agent() -> Agent:
        return Agent(
            name="ResearchAgent",
            instructions="...",
            model=MODEL_RESEARCH,
            tools=[WebSearchTool(), CodeInterpreterTool()]
        )
    
    @staticmethod
    def create_critique_agent(research_agent=None) -> Agent:
        handoffs = [research_agent] if research_agent else []
        return Agent(
            name="CritiqueAgent",
            instructions="...",
            model=MODEL_CRITIQUE,
            tools=[WebSearchTool(), verify_url],
            handoffs=handoffs
        )
    
    @staticmethod
    async def create_critique_agent_with_mcp(research_agent=None) -> tuple[Agent, MCPServerSse]:
        # MCP server lifecycle management
        deepwiki_server = MCPServerSse(...)
        await deepwiki_server.connect()
        
        agent = ResearchAgents.create_critique_agent(research_agent)
        agent.mcp_servers = [deepwiki_server]
        agent.mcp_config = {"convert_schemas_to_strict": True, "timeout": 30}
        
        return agent, deepwiki_server
```

**Agent Execution Pattern:**
```python
result_stream = Runner.run_streamed(agent, message, context=context, max_turns=MAX_TURNS)
processor = create_event_processor(context, workflow_type)
output = await processor.process_stream(result_stream)
```

### 3. Event Processing System

**StreamEventProcessor Class:**
```python
class StreamEventProcessor:
    def __init__(self, context: ResearchContext, workflow_type: str):
        self.context = context
        self.workflow_type = workflow_type
        self.raw_events = []
    
    async def process_stream(self, result_stream, display_prefix=""):
        async for ev in result_stream.stream_events():
            self._save_raw_event(ev)
            self._display_event(ev)
        
        final_output = result_stream.final_output
        self._display_token_usage(result_stream)
        self._save_raw_events_file()
        return final_output
```

**Event Types:**
- `agent_updated_stream_event` - Agent handoffs and transitions
- `raw_response_event` - Web search, reasoning, tool calls
- `tool_call_delta_event` - Tool execution progress
- Ping events (filtered out)

**Workflow-Specific Processing:**
- Model attribution for token tracking via `WORKFLOW_TO_MODEL` mapping
- File naming for raw events (e.g., `raw_events_research.json`)
- Display context labeling (e.g., "Fact-checking" vs "Web search")

### 4. Token Tracking Architecture

**Global Token Tracker:**
```python
_global_tracker = TokenTracker()

def get_global_tracker() -> TokenTracker:
    return _global_tracker

def track_usage(model: str, usage: Any, operation_type: str):
    token_usage = TokenUsage.from_openai_usage(model, usage, operation_type)
    _global_tracker.add_usage(token_usage)
```

**TokenUsage Data Structure:**
```python
@dataclass
class TokenUsage:
    model: str
    timestamp: float
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_tokens_cached: int = 0
    output_tokens_reasoning: int = 0
    operation_type: str = "unknown"
```

**Token Integration Points:**
1. **Event Processing** - Automatic tracking during stream processing
2. **Context Saving** - Token stats appended to all saved results
3. **Workflow Completion** - Token usage report saved to JSON
4. **Real-time Display** - Live token usage feedback during execution

### 5. Context Management System

**ResearchContext as State Container:**
```python
@dataclass
class ResearchContext:
    query: str
    verbose: bool = False
    critique_requested: bool = False
    critique_only: bool = False
    input_file: Optional[str] = None
    output_data: Dict[str, Any] = None
    
    def save_research_results(self, content: str):
        tracker = get_global_tracker()
        token_stats = tracker.format_markdown_section()
        content_with_stats = f"{content}\n\n{token_stats}"
        
        # Save both TXT and JSON formats
        self._save_to_files(content_with_stats, "research_results")
```

**Context Flow:**
1. Created in `main.py` from CLI arguments
2. Passed to all agents via `Runner.run_streamed()`
3. Used by event processor for workflow-specific handling
4. Updated with results after each agent completion
5. Persisted to files with embedded token usage statistics

### 6. Error Handling and Exit Codes

**Exit Code System:**
```python
# config.py
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_RESEARCH_AGENT_ERROR = 2
EXIT_CRITIQUE_AGENT_ERROR = 3
EXIT_FINAL_REPORT_AGENT_ERROR = 4
EXIT_GENERAL_ERROR = 5
```

**Error Handling Strategy:**
```python
# main.py
async def run_standalone_workflow(context, args, results):
    failed_agent = None
    
    try:
        await run_research(context, results)
    except Exception as e:
        failed_agent = "research"
        raise e
    
    try:
        await run_critique(context, results)
    except Exception as e:
        failed_agent = "critique"
        raise e
    
    return failed_agent
```

**Exit Code Determination:**
```python
# main.py main()
failed_agent = results.get("failed_agent", "general")
if failed_agent == "research":
    return EXIT_RESEARCH_AGENT_ERROR
elif failed_agent == "critique":
    return EXIT_CRITIQUE_AGENT_ERROR
elif failed_agent == "final_report":
    return EXIT_FINAL_REPORT_AGENT_ERROR
else:
    return EXIT_GENERAL_ERROR
```

### 7. MCP Integration Patterns

**MCP Server Lifecycle:**
```python
async def create_critique_agent_with_mcp(research_agent=None) -> tuple[Agent, MCPServerSse]:
    deepwiki_server = MCPServerSse(
        params={
            "url": "https://mcp.deepwiki.com/sse",
            "timeout": 30,
            "sse_read_timeout": 600,
        },
        client_session_timeout_seconds=60.0,
        cache_tools_list=True,
        name="DeepWiki"
    )
    
    await deepwiki_server.connect()
    
    agent = ResearchAgents.create_critique_agent(research_agent)
    agent.mcp_servers = [deepwiki_server]
    agent.mcp_config = {
        "convert_schemas_to_strict": True,
        "timeout": 30,
        "request_timeout": 60
    }
    
    return agent, deepwiki_server
```

**MCP Usage Pattern:**
1. **Server Creation** - Configure with timeouts and connection parameters
2. **Agent Association** - Attach server to agent with config
3. **Automatic Tool Discovery** - Tools automatically available to agent
4. **Cleanup Management** - Server cleanup in finally blocks

### 8. File I/O and Results System

**File Organization:**
- `results/` directory auto-created in `config.py`
- Workflow-specific file naming (e.g., `raw_events_research.json`)
- Token usage statistics embedded in all output files
- JSON and TXT formats for different consumption needs

**File Save Pattern:**
```python
# context.py
def save_research_results(self, content: str):
    tracker = get_global_tracker()
    token_stats = tracker.format_markdown_section()
    content_with_stats = f"{content}\n\n{token_stats}"
    
    # TXT: Human-readable with header
    txt_path = os.path.join(RESULTS_DIR, "research_results.txt")
    with open(txt_path, 'w') as f:
        f.write(_create_file_header("Research Query", self.query))
        f.write(content_with_stats)
    
    # JSON: Structured data with metadata
    json_data = {
        "query": self.query,
        "timestamp": datetime.now().isoformat(),
        "content": content_with_stats,
        "token_usage": tracker.get_usage_report()
    }
    
    json_path = os.path.join(RESULTS_DIR, "research_results.json")
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
```

## Workflow Execution Patterns

### Standalone Workflow
```
CLI Args → ResearchContext → run_standalone_workflow()
  ↓
  research_mode → run_research() → ResearchAgent → WebSearch/CodeInterpreter
  ↓
  critique_mode → run_critique() → CritiqueAgent + MCP → DeepWiki/URLVerify
  ↓
  final_report_mode → run_final_report() → FinalReportAgent → CodeInterpreter/WebSearch
  ↓
  Results + Token Stats → Files (TXT/JSON/MD)
```

### Iterative Workflow (Hybrid)
```
CLI Args → ResearchContext → run_iterative_workflow()
  ↓
  Programmatic: run_research() → ResearchAgent → Results
  ↓
  Agent Handoff: CritiqueAgent with handoff to ResearchAgent
  ↓
  OpenAI manages: critique ←→ research (if needed)
  ↓
  Results + Token Stats → Files
```

### Event Processing Flow
```
Agent Execution → Runner.run_streamed() → Event Stream
  ↓
  StreamEventProcessor → _display_event() + _save_raw_event()
  ↓
  Token Extraction → global_tracker.track_usage()
  ↓
  Final Output + Token Stats → Context → File Save
```

### Token Tracking Flow
```
Event Processing → extract_usage() → TokenUsage objects
  ↓
  Global TokenTracker → aggregate by model/operation
  ↓
  format_markdown_section() → appended to all outputs
  ↓
  get_usage_report() → saved to token_usage.json
```

## Configuration System

**Model Configuration:**
```python
# config.py
MODEL_RESEARCH = "o4-mini-deep-research"
MODEL_CRITIQUE = "o3-pro"
MODEL_FINAL_REPORT = "o4-mini"

# Agent turn limits
MAX_TURNS_RESEARCH = 15
MAX_TURNS_CRITIQUE = 25
MAX_TURNS_FINAL_REPORT = 15
```

**Path Configuration:**
```python
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)  # Auto-create on import
```

**Environment Integration:**
```python
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def validate_config() -> bool:
    return bool(OPENAI_API_KEY)
```

## Tool System

**Custom Tools:**
```python
# tools.py
@function_tool
def verify_url(url: str) -> str:
    """Verify URL accessibility for source validation."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return f"✅ URL accessible: {response.status_code}"
    except Exception as e:
        return f"❌ URL inaccessible: {str(e)}"
```

**Tool Integration:**
- Research Agent: `WebSearchTool()`, `CodeInterpreterTool()`
- Critique Agent: `WebSearchTool()`, `verify_url`, MCP tools (automatic)
- Final Report Agent: `CodeInterpreterTool()`, `WebSearchTool()`

## Data Structures

**Core Data Types:**
```python
# context.py
@dataclass
class ResearchContext:
    query: str
    verbose: bool = False
    critique_requested: bool = False
    critique_only: bool = False
    input_file: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)

# token_tracker.py
@dataclass
class TokenUsage:
    model: str
    timestamp: float
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_tokens_cached: int = 0
    output_tokens_reasoning: int = 0
    operation_type: str = "unknown"
```

**Event Processing Types:**
```python
# event_processor.py
WORKFLOW_TO_MODEL = {
    "research": MODEL_RESEARCH,
    "critique": MODEL_CRITIQUE,
    "critique_only": MODEL_CRITIQUE,
    "research_critique_iterative": MODEL_CRITIQUE,
    "final_report": MODEL_FINAL_REPORT,
    "final_report_only": MODEL_FINAL_REPORT,
}
```

## CLI Interface

**Command Line Architecture:**
```python
# cli.py
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI-powered research tool")
    parser.add_argument("-q", "--query", required=True)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-c", "--critique", action="store_true")
    parser.add_argument("-r", "--final-report", action="store_true")
    parser.add_argument("-i", "--iterative", action="store_true")
    parser.add_argument("--critique-only", action="store_true")
    parser.add_argument("--final-report-only", action="store_true")
    parser.add_argument("--input-file", type=str)
    return parser
```

**Argument Validation:**
```python
def validate_args(args) -> tuple[bool, str]:
    # Validation logic for argument combinations
    # Returns (is_valid, error_message)
```

## Key Implementation Details

1. **No Central Orchestrator** - Workflow orchestration is handled by Python functions in `main.py`, not by an AI agent

2. **Hybrid Handoff Strategy** - Iterative mode uses programmatic handoffs (research→critique) and OpenAI agent handoffs (critique→research)

3. **Global Token Tracking** - Single `TokenTracker` instance tracks usage across all agents and workflows

4. **Event-Driven Architecture** - All agent interactions flow through streaming event processing

5. **Factory Pattern Dominance** - Agent creation, event processing, and prompt generation all use factory methods

6. **Automatic Resource Management** - MCP servers, file handles, and token tracking are automatically managed

7. **Comprehensive Error Handling** - Agent-specific error tracking with unique exit codes for different failure modes

8. **Integrated File I/O** - Token usage statistics are embedded in all output files, not separate

This architecture implements a sophisticated multi-agent research system with comprehensive observability and error handling while maintaining clear separation of concerns and efficient resource utilization.