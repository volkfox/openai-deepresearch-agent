"""Custom tools for the agentic research system."""

from agents import function_tool
from typing import Dict, Any
import requests
from urllib.parse import urlparse

@function_tool
def verify_url(url: str) -> Dict[str, Any]:
    """
    Verify if a URL or HTTP/HTTPS API endpoint exists and is accessible.
    
    Args:
        url: The URL to verify (must be properly formatted with http:// or https://)
        
    Returns:
        Dictionary containing verification results with status code, success flag, and details
    """
    if not url or not isinstance(url, str):
        return {
            "success": False,
            "status_code": None,
            "error": "Invalid URL provided - must be a non-empty string",
            "accessible": False,
            "response_time_ms": None
        }
    
    # Basic URL validation
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {
                "success": False,
                "status_code": None,
                "error": "Invalid URL format - must include scheme (http/https) and domain",
                "accessible": False,
                "response_time_ms": None
            }
        
        if parsed.scheme not in ['http', 'https']:
            return {
                "success": False,
                "status_code": None,
                "error": f"Unsupported URL scheme '{parsed.scheme}' - only http and https are supported",
                "accessible": False,
                "response_time_ms": None
            }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "error": f"URL parsing failed: {str(e)}",
            "accessible": False,
            "response_time_ms": None
        }
    
    # Attempt to verify the URL
    try:
        import time
        start_time = time.time()
        
        # Use HEAD request first (faster, less bandwidth)
        response = requests.head(
            url, 
            timeout=10,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (Research Bot) URL Verification Tool'}
        )
        
        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000, 2)
        
        # If HEAD fails, try GET (some servers don't support HEAD)
        if response.status_code == 405:  # Method Not Allowed
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=10,
                allow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (Research Bot) URL Verification Tool'},
                stream=True  # Don't download full content
            )
            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000, 2)
            response.close()  # Close the stream
        
        # Determine if URL is accessible (2xx or 3xx status codes)
        accessible = 200 <= response.status_code < 400
        
        return {
            "success": True,
            "status_code": response.status_code,
            "error": None,
            "accessible": accessible,
            "response_time_ms": response_time_ms,
            "final_url": response.url if response.url != url else None,  # Show redirect target
            "status_description": f"{response.status_code} {response.reason}" if hasattr(response, 'reason') else str(response.status_code)
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": None,
            "error": "Request timeout - URL took longer than 10 seconds to respond",
            "accessible": False,
            "response_time_ms": None
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "status_code": None,
            "error": "Connection error - unable to reach the URL (DNS resolution failed or server unreachable)",
            "accessible": False,
            "response_time_ms": None
        }
    except requests.exceptions.TooManyRedirects:
        return {
            "success": False,
            "status_code": None,
            "error": "Too many redirects - URL redirect chain exceeded maximum limit",
            "accessible": False,
            "response_time_ms": None
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status_code": None,
            "error": f"Request failed: {str(e)}",
            "accessible": False,
            "response_time_ms": None
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "error": f"Unexpected error during URL verification: {str(e)}",
            "accessible": False,
            "response_time_ms": None
        }