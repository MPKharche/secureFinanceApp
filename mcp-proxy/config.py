"""Configuration management for MCP Proxy."""
import os
from pathlib import Path
from typing import Optional

class Config:
    """MCP Proxy configuration from environment variables."""
    
    # Server
    MCP_PROXY_PORT: int = int(os.getenv('MCP_PROXY_PORT', '8766'))
    HOST: str = os.getenv('HOST', '127.0.0.1')
    
    # Securo MCP
    SECURO_MCP_URL: str = os.getenv('SECURO_MCP_URL', 'http://127.0.0.1:8765/mcp')
    SECURO_MCP_TOKEN: str = os.getenv('SECURO_MCP_TOKEN', '')
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/securo')
    DATABASE_POOL_MIN: int = int(os.getenv('DATABASE_POOL_MIN', '2'))
    DATABASE_POOL_MAX: int = int(os.getenv('DATABASE_POOL_MAX', '10'))
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ALERT_CHAT_ID: str = os.getenv('TELEGRAM_ALERT_CHAT_ID', '')
    
    # Retry
    RETRY_INTERVAL_1: int = int(os.getenv('RETRY_INTERVAL_1', '15'))
    RETRY_INTERVAL_2: int = int(os.getenv('RETRY_INTERVAL_2', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '2'))
    
    # Circuit Breaker
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5'))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '60'))
    
    # Write-Ahead Log
    WAL_DIR: Path = Path(os.getenv('WAL_DIR', '/root/apps/secureFinanceApp/mcp-proxy/wal'))
    WAL_RETENTION_DAYS: int = int(os.getenv('WAL_RETENTION_DAYS', '7'))
    
    # Idempotency
    IDEMPOTENCY_WINDOW_SECONDS: int = int(os.getenv('IDEMPOTENCY_WINDOW_SECONDS', '300'))
    
    # Monitoring
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        errors = []
        
        # Only SECURO_MCP_TOKEN and Telegram settings optional for development
        # (alerter handles missing Telegram gracefully)
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        # Ensure WAL directory exists
        cls.WAL_DIR.mkdir(parents=True, exist_ok=True)

config = Config()
