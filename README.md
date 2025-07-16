# Agentic Research Tool

AI-powered research tool with critique and reporting capabilities, built with the OpenAI Agents framework.

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp env.example .env
# Edit .env and set OPENAI_API_KEY=your_key_here

# Test setup
python test_setup.py
```
## Full workflow (research to critique to final report, with a possible repeated research loop)

```bash
python agentic_research.py -q "Your research query" -cvri

```

## Usage of separate stages. 

The tool supports several workflow modes. Each mode can include verbose output (`-v`) to show streaming events.

### 1. Research Only
Conducts deep research stage only and saves results to `results/research_results.txt`
```bash
python agentic_research.py -q "Your research query" -v
```

### 2. Research + Final Report  
Conducts research, then generates a final markdown report with cost analysis
```bash
python agentic_research.py -q "Your research query" -r -v
```

### 3. Research + Critique
Conducts research, then critiques the findings for accuracy and completeness
```bash
python agentic_research.py -q "Your research query" -c -v
```

### 4. Research + Critique + Final Report (Full Pipeline without loop)
Conducts research, critiques it, then generates a comprehensive final report
```bash
python agentic_research.py -q "Your research query" -c -r -v
```

### 5. Critique Existing Research
Uses existing research results to generate critique 
```bash
python agentic_research.py --critique-only --input-file results/research_results.txt -q "Original query" -v
```
**Note:** Requires existing `results/research_results.txt`

### 6. Final Report Only 
Uses existing research and critique results to generate final report with streaming output
```bash
python agentic_research.py --final-report-only -q "Original query" -v
```
**Note:** Requires existing `results/research_results.txt` and `results/critique_results.txt` from previous runs

### 7. Using File Content as Query
Read query from a text file using shell command substitution
```bash
python agentic_research.py -q "$(cat temp_query.txt)" -v
```

## Command Line Options

### Core Flags
- `-q, --query`: Research query (required for all modes)
- `-v, --verbose`: Show detailed streaming output (web searches, reasoning, tool calls)

### Workflow Modes  
- `-r, --final-report`: Generate final markdown report after research
- `-c, --critique`: Run critique analysis after research
- `-i, --iterative`: Allow critique agent to return control to research agent for another run
- `--critique-only`: Only critique existing research (skips research phase)
- `--final-report-only`: Only generate final report (skips research and critique phases)

### Advanced Options
- `--input-file`: Input file path for critique-only mode (defaults to `results/research_results.txt`)

### Flag Combinations
- No flags: Research only
- `-r`: Research → Final Report  
- `-c`: Research → Critique
- `-cr`: Research → Critique → Final Report
- `--critique-only`: Critique existing research
- `--final-report-only`: Final report from existing research + critique

## Output

Results are saved to `results/`:
- `research_results.txt` - Research report with token usage stats
- `research_results.json` - Structured data
- `critique_results.txt` - Critique analysis with token usage stats
- `final_report.md` - Final markdown report with cost analysis
- `raw_events_*.json` - Debug event streams (verbose mode)

## Models

Default models:
- Research: `o4-mini-deep-research`
- Critique: `o4-mini`
- Final Report: `o4-mini`

## Architecture

The tool uses specialized AI agents:
- **ResearchAgent**: Conducts web search and analysis with token tracking
- **CritiqueAgent**: Fact-checks with MCP DeepWiki integration and URL verification
- **FinalReportAgent**: Creates markdown reports with cost calculations

Features token usage tracking, cost analysis, and automatic results directory creation.

## Development

See `ARCHITECTURE.md` for technical details.

## Requirements

- Python 3.8+
- OpenAI API key
- Internet connection for web search