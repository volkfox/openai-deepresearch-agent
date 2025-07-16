#!/usr/bin/env python3
"""
Test script to validate the agentic research setup.
"""

import sys
import os
import importlib.util

def test_imports():
    """Test that all required modules can be imported."""
    
    print("Testing imports...")
    
    # Test agents import
    try:
        import agents
        print("✅ agents package imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import agents: {e}")
        return False
    
    # Test specific agents components
    try:
        from agents import Agent, Runner, WebSearchTool, CodeInterpreterTool, function_tool
        print("✅ Core agents components imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import agents components: {e}")
        return False
    
    # Test local modules
    try:
        import config
        print("✅ Config module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import config: {e}")
        return False
    
    try:
        from context import ResearchContext
        print("✅ Context module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import context: {e}")
        return False
    
    try:
        from research_agents import ResearchAgents
        print("✅ ResearchAgents imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ResearchAgents: {e}")
        return False
    
    return True

def test_config():
    """Test configuration setup."""
    
    print("\nTesting configuration...")
    
    try:
        import config
        
        # Test basic config attributes
        assert hasattr(config, 'MODEL_RESEARCH')
        assert hasattr(config, 'MODEL_CRITIQUE')
        assert hasattr(config, 'RESULTS_DIR')
        
        print("✅ Configuration structure is valid")
        
        # Test results directory creation
        if os.path.exists(config.RESULTS_DIR):
            print("✅ Results directory exists")
        else:
            print("❌ Results directory not created")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    return True

def test_agent_creation():
    """Test agent creation without API calls."""
    
    print("\nTesting agent creation...")
    
    try:
        from research_agents import ResearchAgents
        
        # Test research agent creation
        research_agent = ResearchAgents.create_research_agent()
        print("✅ ResearchAgent created successfully")
        
        # Test critique agent creation
        critique_agent = ResearchAgents.create_critique_agent()
        print("✅ CritiqueAgent created successfully")
        
        
        # Test standalone agents (using existing methods)
        standalone_research = ResearchAgents.create_research_agent()
        print("✅ ResearchAgent created successfully")
        
        standalone_critique = ResearchAgents.create_critique_agent()
        print("✅ CritiqueAgent created successfully")
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False
    
    return True

def test_cli_parsing():
    """Test CLI argument parsing."""
    
    print("\nTesting CLI parsing...")
    
    try:
        from cli import create_parser, validate_args
        
        # Test parser creation
        parser = create_parser()
        print("✅ CLI parser created successfully")
        
        # Test basic argument parsing
        args = parser.parse_args(["-q", "test query", "-v"])
        assert args.query == "test query"
        assert args.verbose == True
        print("✅ Basic argument parsing works")
        
        # Test critique-only parsing
        args = parser.parse_args(["--critique-only", "--input-file", "test.txt", "-q", "test"])
        assert args.critique_only == True
        assert args.input_file == "test.txt"
        print("✅ Critique-only argument parsing works")
        
    except Exception as e:
        print(f"❌ CLI parsing failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    
    print("🔍 Agentic Research Tool - Setup Validation")
    print("=" * 50)
    
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(__file__))
    
    tests = [
        test_imports,
        test_config,
        test_agent_creation,
        test_cli_parsing
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed! The agentic research tool is ready to use.")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)