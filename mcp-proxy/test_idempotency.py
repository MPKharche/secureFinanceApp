#!/usr/bin/env python3
"""Test script for idempotency handler."""
import sys
import time
import asyncio
from pathlib import Path

# Add mcp-proxy to path
sys.path.insert(0, str(Path(__file__).parent))

from idempotency import generate_idempotency_key, is_duplicate, get_cached_response
from database import db

def test_key_generation():
    """Test idempotency key generation."""
    print("Testing idempotency key generation...")
    
    # Same message, same user, same time bucket
    key1 = generate_idempotency_key("Paid 100 for coffee", "user123")
    time.sleep(1)
    key2 = generate_idempotency_key("Paid 100 for coffee", "user123")
    
    assert key1 == key2, "Same message should generate same key"
    print("  ✓ Same message generates same key")
    
    # Different message
    key3 = generate_idempotency_key("Paid 200 for coffee", "user123")
    assert key1 != key3, "Different message should generate different key"
    print("  ✓ Different message generates different key")
    
    # Different user
    key4 = generate_idempotency_key("Paid 100 for coffee", "user456")
    assert key1 != key4, "Different user should generate different key"
    print("  ✓ Different user generates different key")
    
    # With telegram message ID
    key5 = generate_idempotency_key("Paid 100 for coffee", "user123", telegram_message_id="msg123")
    key6 = generate_idempotency_key("Paid 100 for coffee", "user123", telegram_message_id="msg123")
    assert key5 == key6, "Same telegram message ID should generate same key"
    print("  ✓ Same telegram message ID generates same key")
    
    key7 = generate_idempotency_key("Paid 100 for coffee", "user123", telegram_message_id="msg456")
    assert key5 != key7, "Different telegram message ID should generate different key"
    print("  ✓ Different telegram message ID generates different key")
    
    print("✓ All key generation tests passed\n")

async def test_duplicate_detection():
    """Test duplicate detection with database."""
    print("Testing duplicate detection...")
    
    try:
        await db.connect()
        
        # Generate unique test key
        key = f"test_duplicate_key_{int(time.time())}"
        
        # Should be unique first time
        is_dup = await is_duplicate(key)
        assert not is_dup, "Should be unique on first check"
        print("  ✓ First check returns unique")
        
        # Insert into mcp_call_log
        await db.execute(
            """
            INSERT INTO mcp_call_log (tool_name, params, source, success, idempotency_key)
            VALUES ($1, $2, $3, $4, $5)
            """,
            "test_tool", {}, "test", True, key
        )
        print("  ✓ Inserted test record")
        
        # Should be duplicate now
        is_dup = await is_duplicate(key)
        assert is_dup, "Should be duplicate after insert"
        print("  ✓ Second check returns duplicate")
        
        print("✓ Duplicate detection test passed\n")
        
    finally:
        await db.close()

async def test_cached_response():
    """Test cached response retrieval."""
    print("Testing cached response retrieval...")
    
    try:
        await db.connect()
        
        # Generate unique test key
        key = f"test_cache_key_{int(time.time())}"
        
        # Should be None initially
        response = await get_cached_response(key)
        assert response is None, "Should return None for non-existent key"
        print("  ✓ Returns None for non-existent key")
        
        # Insert with response
        test_response = {"result": "success", "transaction_id": "test123"}
        await db.execute(
            """
            INSERT INTO mcp_call_log (
                tool_name, params, source, success, 
                idempotency_key, response
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            "test_tool", {}, "test", True, key, test_response
        )
        print("  ✓ Inserted test record with response")
        
        # Should return cached response
        cached = await get_cached_response(key)
        assert cached == test_response, "Should return cached response"
        print("  ✓ Returns cached response correctly")
        
        print("✓ Cached response test passed\n")
        
    finally:
        await db.close()

def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Proxy - Idempotency Handler Tests")
    print("=" * 60 + "\n")
    
    # Test 1: Key generation (no database)
    test_key_generation()
    
    # Test 2: Duplicate detection (requires database)
    asyncio.run(test_duplicate_detection())
    
    # Test 3: Cached response (requires database)
    asyncio.run(test_cached_response())
    
    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)

if __name__ == "__main__":
    main()
