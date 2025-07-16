"""Agent implementations for the agentic research system."""

from agents import Agent, WebSearchTool, CodeInterpreterTool, ModelSettings
from agents.mcp import MCPServerSse
from openai.types.shared_params.reasoning import Reasoning
from openai.types.responses.tool_param import CodeInterpreter
from typing import List
from config import MODEL_RESEARCH, MODEL_CRITIQUE, MODEL_FINAL_REPORT
from tools import verify_url

class ResearchAgents:
    """Factory class for creating research agents and prompt templates."""
    
    @staticmethod
    def _create_base_model_settings() -> ModelSettings:
        """Create standardized model settings for all agents."""
        return ModelSettings(reasoning=Reasoning(summary="auto"))
    
    @staticmethod
    def create_research_agent() -> Agent:
        """Create the main research agent."""
        
        research_instructions = """
You are a professional researcher preparing a structured, data-driven report according to user query. 

CONTEXT AWARENESS:
- If this is your first time researching this query, conduct comprehensive initial research
- If you are being called back after a critique, review the critique feedback and address the specific gaps or issues identified
- Always build upon previous research rather than starting from scratch

RESEARCH METHODOLOGY:
- Focus on grounded data: include specific figures, trends, statistics, and measurable outcomes with special focus on original data sources. 
- When appropriate, summarize data in a way that could be turned into charts or tables, and call this out in the response (e.g., "this would work well as a bar chart comparing per-patient costs across regions").
- Prioritize reliable, up-to-date sources: peer-reviewed research, vendor data, certified testing labs and organizations.
- Include inline citations and return all source metadata.
- For GitHub repositories, break out their names, e.g. "GitHub repositories: facebook/react, openai/openai-python" in a separate section.

Be analytical, avoid generalities, and ensure that each section supports data-backed reasoning that could inform user query.
Even if the claim comes directly from vendor website, cross-check it with other sources and verify if it looks too general or too good to be true.

TOOL USAGE:
- Use web search tool for current information and general research
- Use code interpreter tool to analyze data or verify calculations

Provide a comprehensive research report that directly addresses the user's query.
"""
        
        return Agent(
            name="ResearchAgent",
            instructions=research_instructions,
            model=MODEL_RESEARCH,
            model_settings=ResearchAgents._create_base_model_settings(),
            tools=[
                WebSearchTool(),
                CodeInterpreterTool(tool_config=CodeInterpreter(
                    type="code_interpreter",
                    container={"type": "auto", "file_ids": []}
                )),
            ],
            handoffs=[]
        )
    
    
    @staticmethod
    def create_critique_agent(research_agent=None) -> Agent:
        """Create the critique agent with optional handoff to research agent for refinement."""
        
        critique_instructions = """
You are an expert fact checker with a focus on finding the factual discrepancies and nuances.
Be very careful in finding the distinctions between claims, supporting links, and info sources.
Pay special attention to claims addressing products unrelated to user query and incomplete compliance coverage.

IMPORTANT: You MUST use the verify_url tool to test every API endpoint mentioned in the research report. This is critical for validating source accessibility and API claims.

CRITICAL: For ANY GitHub repository mentioned in the research (even just the name like "facebook/react" or URLs like "https://github.com/user/repo"), you MUST immediately use the DeepWiki MCP tools to gather additional information:
1. First use ask_question to get basic information about the repository
2. Use ask_question again for specific technical details relevant to the research topic
3. If MCP tools timeout or fail, note this in your critique and continue with other verification methods

Tool Usage Guidelines:
- Use web search tool to verify claims when necessary

- Use DeepWiki MCP tools to ask in-depth questions about GitHub repositories mentioned in the research report. 
MANDATORY: If the research mentions ANY of these patterns, use MCP tools immediately:
    - Repository names like "openai/openai-python", "facebook/react", "microsoft/typescript"
    - GitHub URLs like "https://github.com/user/repo"
    - Any reference to "GitHub repository" or "repo" or "source code"

Examples of DeepWiki MCP use:
    - ask_question(repoName="openai/openai-python", question="What is this repository about?")
    - ask_question(repoName="openai/openai-python", question="How does authentication work?")
    - ask_question(repoName="vercel/next.js", question="What are the main API components?")
    - ask_question(repoName="tensorflow/tensorflow", question="How to implement custom models?")

- Use verify_url tool to check select API endpoints to verify if they actually exist
Examples of when to use verify_url:
- Testing API endpoint: verify_url("https://api.openai.com/v1/models")
- Checking API documentation: verify_url("https://docs.example.com/api")  

RESEARCH QUALITY ASSESSMENT:
After completing your critique, evaluate the research quality:

1. Factual accuracy of claims
2. Quality and reliability of sources  
3. Completeness relative to the original query
4. Any potential biases or gaps in coverage
5. Verification of quantitative data
6. Accessibility and validity of cited URLs and endpoints (TEST EVERY URL!)

DECISION POINT:
If the research has SIGNIFICANT gaps, missing critical information, or quality issues that were not addressed in the critique:
• Call transfer_to_research_agent to request additional web research with specific guidance on what needs improvement.

If the research plus critique is adequate to form a final report:
• Provide your critique and complete the task.

Be thorough but concise in your assessment, highlighting both strengths and areas for improvement.
"""
        
        handoffs = []
        if research_agent:
            handoffs.append(research_agent)
        
        return Agent(
            name="CritiqueAgent", 
            instructions=critique_instructions,
            model=MODEL_CRITIQUE,
            model_settings=ResearchAgents._create_base_model_settings(),
            tools=[
                WebSearchTool(),
                verify_url
            ],
            handoffs=handoffs
        )
    
    @staticmethod
    async def create_critique_agent_with_mcp(research_agent=None) -> tuple[Agent, MCPServerSse]:
        """Create critique agent with connected MCP server. Returns (agent, mcp_server) tuple."""
        
        # Create and connect DeepWiki MCP server with robust timeout settings
        deepwiki_server = MCPServerSse(
            params={
                "url": "https://mcp.deepwiki.com/sse",
                "timeout": 30,  # Connection timeout: 30 seconds
                "sse_read_timeout": 600,  # SSE read timeout: 10 minutes  
            },
            client_session_timeout_seconds=60.0,  # ClientSession read timeout: 60 seconds
            cache_tools_list=True,
            name="DeepWiki"
        )
        
        # Connect the server
        await deepwiki_server.connect()
        
        # Create base agent
        agent = ResearchAgents.create_critique_agent(research_agent)
        
        # Add MCP server to agent with strict schema configuration and timeout settings
        agent.mcp_servers = [deepwiki_server]
        agent.mcp_config = {
            "convert_schemas_to_strict": True,
            "timeout": 30,  # Tool call timeout in seconds
            "request_timeout": 60  # Request timeout in seconds
        }
        
        return agent, deepwiki_server
    
    @staticmethod
    def create_final_report_agent() -> Agent:
        """Create the final report agent."""
        
        final_report_instructions = """
You are a professional report writer specializing in creating comprehensive, well-formatted markdown reports.
Your role is to synthesize research findings and critique feedback into a polished final document.
The goal is not to mention changes and critique points, but synthesize a high-quality new report with relevant links supporting the claims.

You will receive:
1. Original research content with findings and sources
2. Detailed critique analysis highlighting strengths and weaknesses
3. Token usage statistics for cost calculation

Your task is to create a unified, professional markdown report that:

MAIN CONTENT REQUIREMENTS:
- Integrates the best research findings with critique insights
- Addresses and fixes any factual errors or gaps identified in the critique
- Maintains high-quality sourcing and citations
- Provides balanced, evidence-based conclusions


SOURCE CITATION REQUIREMENTS:
-  It is imperative that references are followed by source citations.
-  Pay special attention not to separate references and their matching urls. 

COST CALCULATION REQUIREMENTS:
- MANDATORY: Find the current OpenAI pricing for all models in use using a fetch tool for website https://platform.openai.com/docs/pricing 
- DO NOT map model names, do separate searches for all models in use, such as "o4-mini-deep-research pricing site:openai.com", or "o3-pro pricing site:openai.com", etc.
- Note different pricing tiers: input tokens, output tokens, cached input tokens, and reasoning tokens (free because they are part of output)
- Remember that cached tokens are part of the total input tokens. So do not double-count them.
- MANDATORY: write code and call code_interpreter tool to calculate accurate total costs based on prices for ALL models found in the token usage statistics (o4-mini-deep-research, o4-mini, etc.)
- Create a detailed cost breakdown table showing:
  * Each model used (o4-mini-deep-research, o4-mini, o3-pro, o3, etc.)
  * Token counts by type (input, output, cached, reasoning)
  * Cost per token type for each model from site:https://platform.openai.com/docs/pricing
  * Total cost per model, rounded to cents (1/100th of a dollar)
  * Grand total cost for entire workflow, rounded to cents (1/100th of a dollar)
  * IMPORTANT: the table should include results of cost calculation program run in the code_interpreter tool. DO NOT assume or approximate total costs without running a program!
- Present costs in a clear, professional format with tables showing cost breakdown by model and operation
- Include actual total cost estimation for the workflow of research + critique. Do not simulate estimates, you must write code to compute the costs.

MARKDOWN FORMATTING REQUIREMENTS:
- Use proper markdown headers (# ## ###)
- Include bullet points and numbered lists where appropriate
- Format code blocks and API endpoints with backticks
- Create tables for comparative data when relevant
- Use **bold** and *italic* formatting for emphasis
- Include proper link formatting [text](url)
- Add horizontal rules (---) to separate major sections

STRUCTURE TEMPLATE:
```markdown
# [Report Title]

## Executive Summary
[2-3 paragraph overview of key findings]

## Research Methodology
[Brief description of approach and sources]

## Key Findings
### [Major Finding 1]
[Details with evidence and sources]

### [Major Finding 2]
[Details with evidence and sources]

...

### [Major Finding N]

## Critical Analysis
[Addressing any remaining gaps or concerns, do not mention resolved issues]

## Conclusions and Recommendations
[Evidence-based conclusions and actionable recommendations]

## Sources and References
[Comprehensive list of all sources with accessibility status]

## Limitations and Considerations
[Honest assessment of research limitations and areas for future investigation]

## Cost Analysis
[Detailed table breakdown of token usage and costs by model/operation]

```

Create a comprehensive, professional report that combines the research depth with critical analysis and accurate cost calculations to provide maximum value to the reader.
"""
        
        return Agent(
            name="FinalReportAgent",
            instructions=final_report_instructions,
            model=MODEL_FINAL_REPORT,
            model_settings=ResearchAgents._create_base_model_settings(),
            tools=[
                CodeInterpreterTool(tool_config=CodeInterpreter(
                    type="code_interpreter",
                    container={"type": "auto", "file_ids": []}
                )),
                WebSearchTool()
            ]
        )
    
    
    # ============================================================================
    # PROMPT TEMPLATES - Centralized dynamic message creation for workflows
    # ============================================================================
    
    @staticmethod
    def create_critique_message(query: str, research_content: str) -> str:
        """
        Create a dynamic critique message with research content.
        
        Args:
            query: The original research query
            research_content: The research report to critique
            
        Returns:
            Formatted message for the critique agent
        """
        return f"""Please critique the following research report for the original query: '{query}'

Research Content:
{research_content}

Provide a comprehensive critique analyzing factual accuracy, source quality, completeness, and any gaps or biases."""
    
    @staticmethod
    def create_final_report_message(query: str, research_content: str, critique_content: str) -> str:
        """
        Create a dynamic final report message integrating the research and critique content.
        
        Args:
            query: The original research query
            research_content: The research findings
            critique_content: The critique analysis
            
        Returns:
            Formatted message for the final report agent
        """
        return f"""Start creating a comprehensive final markdown report that synthesizes the research findings and critique analysis.
        Include all sections and model cost lookups and calculations outlined in the system prompt.

Original Research Query: '{query}'

RESEARCH CONTENT:
{research_content}

CRITIQUE ANALYSIS:
{critique_content}

"""
    
    
