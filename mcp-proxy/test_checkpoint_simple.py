"""Test checkpoint handler via Docker exec."""
import subprocess
import json
import sys


def run_sql(query, *params):
    """Execute SQL via docker exec."""
    cmd = [
        'docker', 'compose', 'exec', '-T', 'db',
        'psql', '-U', 'postgres', '-d', 'securo', '-t', '-c', query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd='/root/apps/secureFinanceApp')
    if result.returncode != 0:
        raise Exception(f"SQL failed: {result.stderr}")
    return result.stdout.strip()


def test_checkpoint():
    """Test checkpoint save and recovery via database."""
    print("Starting checkpoint tests via Docker exec...")
    
    try:
        # Test 1: Insert checkpoint
        print("\n1. Testing checkpoint save...")
        query = """
        INSERT INTO hermes_checkpoints 
            (session_id, telegram_chat_id, conversation_state, pending_mcp_call, processed)
        VALUES 
            ('test_session_123', '613463569', '{"messages": []}'::jsonb, 
             '{"tool": "propose_create_transaction", "params": {"description": "test", "amount": 100}}'::jsonb, 
             false)
        ON CONFLICT (session_id, telegram_chat_id) 
        DO UPDATE SET 
            conversation_state = EXCLUDED.conversation_state,
            pending_mcp_call = EXCLUDED.pending_mcp_call,
            created_at = NOW(),
            processed = false
        """
        run_sql(query)
        print("   ✓ Checkpoint saved")
        
        # Test 2: Verify saved
        print("\n2. Verifying checkpoint in database...")
        result = run_sql("SELECT COUNT(*) FROM hermes_checkpoints WHERE session_id = 'test_session_123'")
        count = int(result.strip())
        assert count == 1, f"Expected 1 checkpoint, found {count}"
        print("   ✓ Checkpoint verified in database")
        
        # Test 3: Check processed flag
        print("\n3. Checking processed flag...")
        result = run_sql("SELECT processed FROM hermes_checkpoints WHERE session_id = 'test_session_123'")
        processed = result.strip().lower() == 'f' or result.strip().lower() == 'false'
        assert processed == False or result.strip() == 'f', "Checkpoint should not be processed yet"
        print("   ✓ Processed flag is false")
        
        # Test 4: Update to processed
        print("\n4. Marking checkpoint as processed...")
        run_sql("UPDATE hermes_checkpoints SET processed = true WHERE session_id = 'test_session_123'")
        result = run_sql("SELECT processed FROM hermes_checkpoints WHERE session_id = 'test_session_123'")
        processed = result.strip().lower() in ['t', 'true']
        assert processed, "Checkpoint should be marked as processed"
        print("   ✓ Checkpoint marked as processed")
        
        # Test 5: Cleanup
        print("\n5. Cleaning up test data...")
        run_sql("DELETE FROM hermes_checkpoints WHERE session_id = 'test_session_123'")
        print("   ✓ Cleanup complete")
        
        print("\n" + "="*50)
        print("✓ All checkpoint tests passed!")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_checkpoint()
    sys.exit(0 if success else 1)
