#!/usr/bin/env python3
"""
Standalone test script to verify MCP DeepWiki connection.
"""

import asyncio
import sys
import time
from agents.mcp import MCPServerSse

async def test_mcp_connection():
    """Test MCP connection to DeepWiki server."""
    print("🔍 Testing MCP DeepWiki connection...")
    
    # Create MCP server with various timeout configurations
    server = MCPServerSse(
        params={
            "url": "https://mcp.deepwiki.com/sse",
            "timeout": 30,
            "sse_read_timeout": 600,
            "connect_timeout": 30,
            "read_timeout": 60
        },
        cache_tools_list=True,
        name="DeepWiki"
    )
    
    try:
        # Test connection
        print("📡 Connecting to MCP server...")
        start_time = time.time()
        await server.connect()
        connect_time = time.time() - start_time
        print(f"✅ Connected successfully in {connect_time:.2f} seconds")
        
        # Test server attributes
        print("\n🔧 Testing server attributes...")
        print(f"📋 Server name: {server.name}")
        print(f"📋 Server URL: {server.params.get('url', 'unknown')}")
        
        # Test if server has tools attribute
        if hasattr(server, 'tools'):
            print(f"📋 Server has tools attribute: {len(server.tools)} tools")
            for tool in server.tools:
                print(f"  - {tool.name}: {tool.description}")
        else:
            print("📋 Server tools attribute not available")
        
        # Check if server is properly connected
        if hasattr(server, 'connected') and server.connected:
            print("✅ Server shows as connected")
        else:
            print("⚠️ Server connection status unknown")
        
        print("\n🧪 Basic MCP server connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        return False
    
    finally:
        # Cleanup
        try:
            await server.cleanup()
            print("\n🧹 Cleaned up MCP server")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
    
    return True

async def test_basic_connectivity():
    """Test basic connectivity to the MCP server URL."""
    print("\n🌐 Testing basic HTTP connectivity...")
    
    try:
        import urllib.request
        import urllib.error
        
        # Simple HTTP test with proper headers
        req = urllib.request.Request("https://mcp.deepwiki.com/sse")
        req.add_header('Accept', 'text/event-stream')
        req.add_header('Cache-Control', 'no-cache')
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; MCP-Client/1.0)')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"📡 HTTP Status: {response.status}")
            print(f"📋 Headers: {dict(response.headers)}")
            print("✅ Basic connectivity successful")
            
    except urllib.error.URLError as e:
        print(f"❌ HTTP connectivity error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

async def main():
    """Main test function."""
    print("🚀 MCP DeepWiki Connection Test")
    print("=" * 50)
    
    # Test basic connectivity first
    connectivity_ok = await test_basic_connectivity()
    
    if connectivity_ok:
        print("\n" + "=" * 50)
        # Test full MCP connection
        mcp_ok = await test_mcp_connection()
        
        if mcp_ok:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print("\n💥 MCP connection test failed!")
            return 1
    else:
        print("\n💥 Basic connectivity test failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)