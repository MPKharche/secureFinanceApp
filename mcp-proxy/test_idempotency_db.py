#!/usr/bin/env python3
"""Test idempotency with database via docker exec."""
import sys
import time
import json
import subprocess
from pathlib import Path

# Add mcp-proxy to path
sys.path.insert(0, str(Path(__file__).parent))

from idempotency import generate_idempotency_key

def docker_exec_sql(sql):
    """Execute SQL via docker exec using stdin."""
    result = subprocess.run(
        ["docker", "exec", "-i", "securo-db-1", "psql", "-U", "postgres", "-d", "securo", "-t", "-A"],
        input=sql,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"SQL Error: {result.stderr}")
        return None
    
    return result.stdout.strip()

def test_duplicate_detection():
    """Test duplicate detection via docker."""
    print("Testing duplicate detection via docker exec...")
    
    # Generate unique test key
    test_key = f"test_duplicate_key_{int(time.time())}"
    print(f"  Test key: {test_key}")
    
    # Check if duplicate (should be False)
    sql = f"""
        SELECT COUNT(*) FROM mcp_call_log 
        WHERE idempotency_key = '{test_key}' 
        AND called_at > NOW() - INTERVAL '1 hour'
    """
    count = docker_exec_sql(sql)
    assert count == "0", f"Expected 0, got {count}"
    print("  ✓ First check returns unique (count=0)")
    
    # Insert test record
    sql = f"""
        INSERT INTO mcp_call_log (
            tool_name, params, source, success, idempotency_key
        ) VALUES (
            'test_tool', '{{}}'::jsonb, 'test', true, '{test_key}'
        )
    """
    docker_exec_sql(sql)
    print("  ✓ Inserted test record")
    
    # Check again (should be duplicate now)
    sql = f"""
        SELECT COUNT(*) FROM mcp_call_log 
        WHERE idempotency_key = '{test_key}' 
        AND called_at > NOW() - INTERVAL '1 hour'
    """
    count = docker_exec_sql(sql)
    assert count == "1", f"Expected 1, got {count}"
    print("  ✓ Second check returns duplicate (count=1)")
    
    print("✓ Duplicate detection test passed\n")

def test_cached_response():
    """Test cached response retrieval."""
    print("Testing cached response retrieval...")
    
    # Generate unique test key
    test_key = f"test_cache_key_{int(time.time())}"
    print(f"  Test key: {test_key}")
    
    # Check no response initially
    sql = f"""
        SELECT response FROM mcp_call_log 
        WHERE idempotency_key = '{test_key}' 
        AND success = true
        AND called_at > NOW() - INTERVAL '1 hour'
        ORDER BY called_at DESC
        LIMIT 1
    """
    result = docker_exec_sql(sql)
    assert result == "", "Expected no response initially"
    print("  ✓ No cached response initially")
    
    # Insert with response using stdin
    sql = f"""
INSERT INTO mcp_call_log (
    tool_name, params, source, success, 
    idempotency_key, response
) VALUES (
    'test_tool', '{{}}'::jsonb, 'test', true, 
    '{test_key}', 
    '{{"result": "success", "transaction_id": "test123"}}'::jsonb
);
    """
    docker_exec_sql(sql)
    print("  ✓ Inserted test record with response")
    
    # Check response exists
    sql = f"""
        SELECT response FROM mcp_call_log 
        WHERE idempotency_key = '{test_key}' 
        AND success = true
        AND called_at > NOW() - INTERVAL '1 hour'
        ORDER BY called_at DESC
        LIMIT 1
    """
    result = docker_exec_sql(sql)
    assert result != "", "Expected cached response"
    cached_data = json.loads(result)
    assert cached_data["result"] == "success", "Response content mismatch"
    print("  ✓ Returns cached response correctly")
    
    print("✓ Cached response test passed\n")

def main():
    """Run all database tests."""
    print("=" * 60)
    print("MCP Proxy - Idempotency Database Tests")
    print("=" * 60 + "\n")
    
    test_duplicate_detection()
    test_cached_response()
    
    print("=" * 60)
    print("ALL DATABASE TESTS PASSED ✓")
    print("=" * 60)

if __name__ == "__main__":
    main()
