"""Write-ahead log for disaster recovery."""
import json
import os
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any

from config import config

logger = logging.getLogger(__name__)

async def append_to_wal(
    request_data: Dict[str, Any],
    idempotency_key: str
) -> None:
    """
    Append MCP request to write-ahead log.
    
    Writes to daily log file in JSONL format. Each line is a complete JSON object.
    Forces fsync to ensure data is on disk.
    
    Args:
        request_data: The MCP request dictionary
        idempotency_key: The idempotency key for this request
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "idempotency_key": idempotency_key,
        "request": request_data
    }
    
    # Get today's log file
    log_file = config.WAL_DIR / f"{date.today()}.jsonl"
    
    try:
        # Append to file with fsync
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        logger.debug(f"Appended to WAL: {idempotency_key}")
        
    except Exception as e:
        logger.error(f"Failed to write to WAL: {e}")
        # Don't fail the request if WAL write fails
        # WAL is for disaster recovery only

async def rotate_old_wal_files() -> None:
    """
    Delete WAL files older than retention period.
    
    Keeps files within WAL_RETENTION_DAYS, deletes older ones.
    """
    cutoff_date = date.today() - timedelta(days=config.WAL_RETENTION_DAYS)
    deleted_count = 0
    
    try:
        for wal_file in config.WAL_DIR.glob("*.jsonl"):
            # Parse date from filename: YYYY-MM-DD.jsonl
            try:
                file_date = date.fromisoformat(wal_file.stem)
                
                if file_date < cutoff_date:
                    wal_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old WAL file: {wal_file.name}")
                    
            except ValueError:
                # Not a date-formatted file, skip
                continue
        
        if deleted_count > 0:
            logger.info(f"Rotated {deleted_count} old WAL files")
            
    except Exception as e:
        logger.error(f"Error rotating WAL files: {e}")

def get_wal_size_mb() -> float:
    """Get total size of WAL directory in MB."""
    total_bytes = sum(
        f.stat().st_size 
        for f in config.WAL_DIR.glob("*.jsonl")
    )
    return total_bytes / (1024 * 1024)
