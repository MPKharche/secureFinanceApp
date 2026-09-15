"""Test checkpoint handler functionality."""
import asyncio
import sys
from pathlib import Path

# Add mcp-proxy to path
sys.path.insert(0, str(Path(__file__).parent))

from database import db
from checkpoint_handler import save_checkpoint, recover_unprocessed_checkpoints
from models import CheckpointRequest


async def test_checkpoint():
    """Test checkpoint save and recovery."""
    print("Starting checkpoint tests...")
    
    await db.connect()
    
    try:
        # Test 1: Save checkpoint
        print("\n1. Testing checkpoint save...")
        checkpoint = CheckpointRequest(
            session_id="test_session_123",
            telegram_chat_id="613463569",
            conversation_state={
                "messages": [],
                "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001"
            },
            pending_mcp_call={
                "tool": "propose_create_transaction",
                "params": {
                    "description": "test transaction",
                    "amount": 100.00,
                    "date": "2026-09-16"
                }
            }
        )
        
        result = await save_checkpoint(checkpoint)
        assert result['status'] == 'saved', "Checkpoint save failed"
        print("   ✓ Checkpoint saved")
        
        # Test 2: Verify saved to database
        print("\n2. Verifying checkpoint in database...")
        row = await db.fetchrow(
            "SELECT * FROM hermes_checkpoints WHERE session_id = $1",
            "test_session_123"
        )
        assert row is not None, "Checkpoint not found in database"
        assert row['processed'] == False, "Checkpoint should not be processed yet"
        assert row['telegram_chat_id'] == "613463569", "Chat ID mismatch"
        assert row['pending_mcp_call'] is not None, "Pending call should exist"
        print("   ✓ Checkpoint verified in database")
        
        # Test 3: Test upsert (save same checkpoint again)
        print("\n3. Testing checkpoint upsert...")
        checkpoint.conversation_state['messages'] = ["updated"]
        result = await save_checkpoint(checkpoint)
        assert result['status'] == 'saved', "Checkpoint upsert failed"
        
        # Verify only one row exists
        count = await db.fetchval(
            "SELECT COUNT(*) FROM hermes_checkpoints WHERE session_id = $1",
            "test_session_123"
        )
        assert count == 1, f"Expected 1 checkpoint, found {count}"
        print("   ✓ Checkpoint upsert works (no duplicates)")
        
        # Test 4: Test recovery
        print("\n4. Testing checkpoint recovery...")
        count = await recover_unprocessed_checkpoints()
        print(f"   ✓ Recovered {count} checkpoint(s)")
        
        # Verify checkpoint marked as processed
        row = await db.fetchrow(
            "SELECT * FROM hermes_checkpoints WHERE session_id = $1",
            "test_session_123"
        )
        assert row['processed'] == True, "Checkpoint should be marked as processed"
        print("   ✓ Checkpoint marked as processed")
        
        # Test 5: Cleanup
        print("\n5. Cleaning up test data...")
        await db.execute(
            "DELETE FROM hermes_checkpoints WHERE session_id = $1",
            "test_session_123"
        )
        await db.execute(
            "DELETE FROM pending_transactions WHERE raw_message = $1",
            "Recovered from checkpoint"
        )
        print("   ✓ Cleanup complete")
        
        print("\n" + "="*50)
        print("✓ All checkpoint tests passed!")
        print("="*50)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_checkpoint())
    sys.exit(0 if success else 1)
