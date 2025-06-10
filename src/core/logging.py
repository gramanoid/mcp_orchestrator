"""
Logging configuration and utilities for MCP Orchestrator.

This module sets up structured logging with appropriate formatters,
handlers, and log levels for different components.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured log records.
    
    Supports both human-readable and JSON output formats.
    """
    
    def __init__(self, format_type: str = "human", include_extras: bool = True):
        """
        Initialize structured formatter.
        
        Args:
            format_type: "human" for readable format, "json" for JSON format
            include_extras: Whether to include extra fields in output
        """
        self.format_type = format_type
        self.include_extras = include_extras
        
        if format_type == "human":
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            fmt = None  # JSON format doesn't use a format string
            
        super().__init__(fmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        if self.format_type == "json":
            return self._format_json(record)
        else:
            return self._format_human(record)
    
    def _format_human(self, record: logging.LogRecord) -> str:
        """Format record for human readability."""
        # Start with basic formatting
        message = super().format(record)
        
        # Add extras if present and requested
        if self.include_extras and hasattr(record, "__dict__"):
            extras = {}
            for key, value in record.__dict__.items():
                if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                    extras[key] = value
            
            if extras:
                message += f" | extras: {extras}"
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extras
        if self.include_extras:
            for key, value in record.__dict__.items():
                if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                    # Ensure value is JSON serializable
                    try:
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)


class MCPLogFilter(logging.Filter):
    """
    Custom log filter for MCP-specific filtering.
    
    Can filter based on component, severity, or custom criteria.
    """
    
    def __init__(self, min_level: Optional[int] = None, 
                 components: Optional[list] = None,
                 exclude_components: Optional[list] = None):
        """
        Initialize log filter.
        
        Args:
            min_level: Minimum log level to pass through
            components: List of component names to include
            exclude_components: List of component names to exclude
        """
        super().__init__()
        self.min_level = min_level
        self.components = components
        self.exclude_components = exclude_components or []
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record."""
        # Check minimum level
        if self.min_level and record.levelno < self.min_level:
            return False
        
        # Check component inclusion
        if self.components:
            component_match = any(comp in record.name for comp in self.components)
            if not component_match:
                return False
        
        # Check component exclusion
        for comp in self.exclude_components:
            if comp in record.name:
                return False
        
        return True


class CostLogger:
    """Specialized logger for tracking API costs."""
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize cost logger.
        
        Args:
            log_file: Optional file path for cost logs
        """
        self.logger = logging.getLogger("mcp.costs")
        self.total_cost = 0.0
        
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(StructuredFormatter(format_type="json"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_cost(self, model: str, operation: str, cost: float, 
                 tokens: Dict[str, int], metadata: Optional[Dict[str, Any]] = None):
        """
        Log an API cost event.
        
        Args:
            model: Model that incurred the cost
            operation: Operation performed
            cost: Cost in USD
            tokens: Token counts by type
            metadata: Additional metadata
        """
        self.total_cost += cost
        
        self.logger.info(
            f"API cost: ${cost:.4f} for {model}",
            extra={
                "model": model,
                "operation": operation,
                "cost_usd": cost,
                "tokens": tokens,
                "total_cost": self.total_cost,
                "metadata": metadata or {}
            }
        )


def setup_logging(config: Dict[str, Any], log_dir: Optional[Path] = None):
    """
    Set up logging configuration for MCP.
    
    Args:
        config: Logging configuration dictionary
        log_dir: Optional directory for log files
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Set base level
    log_level = getattr(logging, config.get("level", "INFO"))
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        StructuredFormatter(
            format_type=config.get("console_format", "human"),
            include_extras=config.get("include_extras", True)
        )
    )
    root_logger.addHandler(console_handler)
    
    # File handler if log directory provided
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file with rotation
        main_log = log_dir / "mcp_orchestrator.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            StructuredFormatter(
                format_type=config.get("file_format", "json"),
                include_extras=True
            )
        )
        root_logger.addHandler(file_handler)
        
        # Error log file
        error_log = log_dir / "errors.log"
        error_handler = logging.FileHandler(error_log)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            StructuredFormatter(format_type="json", include_extras=True)
        )
        root_logger.addHandler(error_handler)
    
    # Set up component-specific loggers
    setup_component_loggers(config.get("components", {}))
    
    # Set up cost logger
    if log_dir:
        cost_log = log_dir / "costs.log"
        cost_logger = CostLogger(cost_log)
    
    # Log startup
    logger = logging.getLogger("mcp.logging")
    logger.info(
        "Logging initialized",
        extra={
            "log_level": log_level,
            "log_dir": str(log_dir) if log_dir else None,
            "handlers": len(root_logger.handlers)
        }
    )


def setup_component_loggers(component_config: Dict[str, Any]):
    """
    Set up loggers for specific components.
    
    Args:
        component_config: Component-specific logging configuration
    """
    # Default component configurations
    default_components = {
        "mcp.adapters": {"level": "INFO"},
        "mcp.orchestrator": {"level": "INFO"},
        "mcp.strategies": {"level": "INFO"},
        "mcp.api": {"level": "WARNING"},
        "mcp.costs": {"level": "INFO"}
    }
    
    # Merge with provided config
    components = {**default_components, **component_config}
    
    for component, config in components.items():
        logger = logging.getLogger(component)
        
        # Set level if specified
        if "level" in config:
            level = getattr(logging, config["level"])
            logger.setLevel(level)
        
        # Add filters if specified
        if "filters" in config:
            for filter_config in config["filters"]:
                filter_obj = MCPLogFilter(**filter_config)
                logger.addFilter(filter_obj)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with MCP naming convention.
    
    Args:
        name: Logger name (will be prefixed with 'mcp.')
        
    Returns:
        Logger instance
    """
    if not name.startswith("mcp."):
        name = f"mcp.{name}"
    
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding temporary log context."""
    
    def __init__(self, logger: logging.Logger, **kwargs):
        """
        Initialize log context.
        
        Args:
            logger: Logger to add context to
            **kwargs: Context key-value pairs
        """
        self.logger = logger
        self.context = kwargs
        self.old_adapter = None
    
    def __enter__(self):
        """Enter context and add context to logger."""
        # Store old adapter
        self.old_adapter = self.logger.adapter if hasattr(self.logger, "adapter") else None
        
        # Create new adapter with context
        self.logger.adapter = logging.LoggerAdapter(self.logger, self.context)
        
        return self.logger.adapter
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore logger."""
        # Restore old adapter
        if self.old_adapter:
            self.logger.adapter = self.old_adapter
        elif hasattr(self.logger, "adapter"):
            delattr(self.logger, "adapter")


# Convenience function for structured logging
def log_structured(logger: logging.Logger, level: int, message: str, **kwargs):
    """
    Log a structured message with extra fields.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **kwargs: Extra fields to include
    """
    logger.log(level, message, extra=kwargs)