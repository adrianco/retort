#!/usr/bin/env python3
"""
Integration test for the Brazilian Soccer MCP Server tools.
"""

import sys
import os

# Add current directory to path to import the server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_find_matches_between_teams():
    """Test the find_matches_between_teams tool."""
    try:
        # Import the server module to register tools
        import brazilian_soccer_mcp_server
        
        # Import the specific tool function
        from brazilian_soccer_mcp_server import find_matches_between_teams
        
        # Run a simple test - this will check if the tool can be called
        result = find_matches_between_teams("Flamengo", "Fluminense")
        
        print("✓ find_matches_between_teams tool executed successfully")
        print(f"  Result type: {type(result)}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to test find_matches_between_teams: {e}")
        return False

def test_get_team_statistics():
    """Test the get_team_statistics tool."""
    try:
        # Import the server module to register tools
        import brazilian_soccer_mcp_server
        
        # Import the specific tool function
        from brazilian_soccer_mcp_server import get_team_statistics
        
        # Run a simple test
        result = get_team_statistics("Flamengo")
        
        print("✓ get_team_statistics tool executed successfully")
        print(f"  Result type: {type(result)}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to test get_team_statistics: {e}")
        return False

if __name__ == "__main__":
    print("Running integration tests for Brazilian Soccer MCP Server tools...")
    print("=" * 60)
    
    tests = [
        test_find_matches_between_teams,
        test_get_team_statistics
    ]
    
    results = []
    for test in tests:
        print(f"\n{test.__name__}:")
        result = test()
        results.append(result)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ All integration tests passed!")
        sys.exit(0)
    else:
        print("✗ Some integration tests failed!")
        sys.exit(1)