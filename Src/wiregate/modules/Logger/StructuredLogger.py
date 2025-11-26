"""
Structured Logging Configuration Module
Provides JSON logging for production and human-readable logging for development
"""
import logging
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger

from ..Config import DASHBOARD_MODE


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add message (from message_dict or record.msg)
        if 'message' not in log_record:
            log_record['message'] = record.getMessage()
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Add any extra context from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_record[key] = value


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development mode"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='[%Y-%m-%d %H:%M:%S]'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with exception info if present"""
        formatted = super().format(record)
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)
        return formatted


def setup_structured_logging(log_level: str = 'INFO', force_json: Optional[bool] = None) -> None:
    """
    Set up structured logging based on DASHBOARD_MODE
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        force_json: Force JSON format if True, human-readable if False, None for auto-detect
    """
    # Determine format based on mode
    if force_json is None:
        use_json = DASHBOARD_MODE == 'production'
    else:
        use_json = force_json
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Set formatter based on mode
    if use_json:
        formatter = StructuredFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s',
            timestamp=True
        )
    else:
        formatter = HumanReadableFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Also configure uvicorn access logs if in JSON mode
    if use_json:
        # Configure uvicorn logger for JSON
        uvicorn_logger = logging.getLogger('uvicorn')
        uvicorn_logger.handlers.clear()
        uvicorn_handler = logging.StreamHandler(sys.stdout)
        uvicorn_handler.setFormatter(formatter)
        uvicorn_logger.addHandler(uvicorn_handler)
        uvicorn_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Configure uvicorn.access logger
        uvicorn_access_logger = logging.getLogger('uvicorn.access')
        uvicorn_access_logger.handlers.clear()
        uvicorn_access_handler = logging.StreamHandler(sys.stdout)
        uvicorn_access_handler.setFormatter(formatter)
        uvicorn_access_logger.addHandler(uvicorn_access_handler)
        uvicorn_access_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context: Any) -> None:
    """
    Log a message with additional context fields
    
    Args:
        logger: Logger instance
        level: Log level (logging.DEBUG, logging.INFO, etc.)
        message: Log message
        **context: Additional context fields to include in log
    """
    logger.log(level, message, extra=context)

