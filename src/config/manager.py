"""
Configuration management for the MCP Orchestrator.

This module handles loading, validating, and managing configuration including
API keys, model parameters, and orchestration settings.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import platform
from cryptography.fernet import Fernet
import keyring


logger = logging.getLogger(__name__)


class SecureKeyStore:
    """Base class for secure key storage."""
    
    def get_key(self, service: str, key_name: str) -> Optional[str]:
        """Retrieve a key from secure storage."""
        raise NotImplementedError
    
    def set_key(self, service: str, key_name: str, value: str):
        """Store a key in secure storage."""
        raise NotImplementedError
    
    def delete_key(self, service: str, key_name: str):
        """Delete a key from secure storage."""
        raise NotImplementedError


class SystemKeyringStore(SecureKeyStore):
    """Use system keyring for secure storage."""
    
    def get_key(self, service: str, key_name: str) -> Optional[str]:
        """Retrieve from system keyring."""
        try:
            return keyring.get_password(service, key_name)
        except Exception as e:
            logger.error(f"Failed to retrieve key from keyring: {e}")
            return None
    
    def set_key(self, service: str, key_name: str, value: str):
        """Store in system keyring."""
        try:
            keyring.set_password(service, key_name, value)
        except Exception as e:
            logger.error(f"Failed to store key in keyring: {e}")
            raise
    
    def delete_key(self, service: str, key_name: str):
        """Delete from system keyring."""
        try:
            keyring.delete_password(service, key_name)
        except Exception as e:
            logger.error(f"Failed to delete key from keyring: {e}")


class EncryptedFileStore(SecureKeyStore):
    """Fallback encrypted file storage for API keys."""
    
    def __init__(self, storage_path: Path):
        """Initialize with storage path."""
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self):
        """Ensure we have an encryption key."""
        key_file = self.storage_path / ".key"
        if not key_file.exists():
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            # Restrict permissions
            if platform.system() != "Windows":
                os.chmod(key_file, 0o600)
        
        self.cipher = Fernet(key_file.read_bytes())
    
    def _get_store_file(self, service: str) -> Path:
        """Get the store file for a service."""
        return self.storage_path / f"{service}.enc"
    
    def get_key(self, service: str, key_name: str) -> Optional[str]:
        """Retrieve from encrypted file."""
        store_file = self._get_store_file(service)
        if not store_file.exists():
            return None
        
        try:
            encrypted_data = store_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            store = json.loads(decrypted_data.decode())
            return store.get(key_name)
        except Exception as e:
            logger.error(f"Failed to retrieve key from encrypted store: {e}")
            return None
    
    def set_key(self, service: str, key_name: str, value: str):
        """Store in encrypted file."""
        store_file = self._get_store_file(service)
        
        # Load existing store or create new
        if store_file.exists():
            try:
                encrypted_data = store_file.read_bytes()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                store = json.loads(decrypted_data.decode())
            except:
                store = {}
        else:
            store = {}
        
        # Update store
        store[key_name] = value
        
        # Encrypt and save
        encrypted_data = self.cipher.encrypt(json.dumps(store).encode())
        store_file.write_bytes(encrypted_data)
        
        # Restrict permissions
        if platform.system() != "Windows":
            os.chmod(store_file, 0o600)
    
    def delete_key(self, service: str, key_name: str):
        """Delete from encrypted file."""
        store_file = self._get_store_file(service)
        if not store_file.exists():
            return
        
        try:
            encrypted_data = store_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            store = json.loads(decrypted_data.decode())
            
            if key_name in store:
                del store[key_name]
                
                if store:
                    # Re-encrypt and save
                    encrypted_data = self.cipher.encrypt(json.dumps(store).encode())
                    store_file.write_bytes(encrypted_data)
                else:
                    # Delete file if empty
                    store_file.unlink()
        except Exception as e:
            logger.error(f"Failed to delete key from encrypted store: {e}")


class ConfigManager:
    """
    Manages configuration for the MCP Orchestrator.
    
    Configuration priority:
    1. Environment variables
    2. User config file
    3. Default config file
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Optional custom configuration directory
        """
        if config_dir:
            self.config_dir = config_dir
        else:
            # Default to user config directory
            if platform.system() == "Windows":
                self.config_dir = Path(os.environ.get("APPDATA", "")) / "mcp_orchestrator"
            else:
                self.config_dir = Path.home() / ".config" / "mcp_orchestrator"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize secure key store
        self._init_key_store()
        
        # Configuration cache
        self._config_cache = None
    
    def _init_key_store(self):
        """Initialize the appropriate secure key store."""
        try:
            # Try system keyring first
            self.key_store = SystemKeyringStore()
            # Test if it works
            self.key_store.set_key("mcp_orchestrator_test", "test", "test")
            self.key_store.delete_key("mcp_orchestrator_test", "test")
            logger.info("Using system keyring for secure key storage")
        except:
            # Fall back to encrypted file storage
            logger.info("System keyring unavailable, using encrypted file storage")
            self.key_store = EncryptedFileStore(self.config_dir / "keys")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from all sources.
        
        Returns:
            Merged configuration dictionary
        """
        if self._config_cache:
            return self._config_cache
        
        # Start with default config
        config = self._load_default_config()
        
        # Merge user config if exists
        user_config_file = self.config_dir / "config.yaml"
        if user_config_file.exists():
            try:
                with open(user_config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                    config = self._deep_merge(config, user_config)
            except Exception as e:
                logger.error(f"Failed to load user config: {e}")
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        # Load API keys
        config["api_keys"] = self._load_api_keys()
        
        self._config_cache = config
        return config
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "mcp": {
                "version": "1.0.0",
                "server_name": "mcp-orchestrator"
            },
            "orchestration": {
                "default_strategy": "progressive_deep_dive",
                "strategies": {
                    "max_quality_council": {
                        "activation_threshold": 0.8,
                        "parallel_timeout": 60,
                        "synthesis_method": "weighted_consensus"
                    },
                    "progressive_deep_dive": {
                        "initial_model": "claude_sonnet",
                        "escalation_threshold": 0.6
                    }
                }
            },
            "models": {
                "claude": {
                    "opus": {
                        "max_tokens": 8192,
                        "thinking_mode": "deep"
                    },
                    "sonnet": {
                        "max_tokens": 4096,
                        "mode": "fast"
                    }
                },
                "gemini_polyglot": {
                    "api_endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model_id": "google/gemini-2.5-pro-preview-06-05",
                    "max_thinking_tokens": 32000,
                    "default_thinking_tokens": 16000
                },
                "o3_architect": {
                    "api_endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model_id": "openai/o3-high",
                    "reasoning_depths": ["low", "medium", "high", "maximum"],
                    "default_reasoning": "high"
                }
            },
            "cost_management": {
                "max_cost_per_request": 5.0,
                "daily_limit": 100.0,
                "warning_threshold": 0.8
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # Cost limits
        if "MCP_MAX_COST_PER_REQUEST" in os.environ:
            config["cost_management"]["max_cost_per_request"] = float(
                os.environ["MCP_MAX_COST_PER_REQUEST"]
            )
        
        if "MCP_DAILY_LIMIT" in os.environ:
            config["cost_management"]["daily_limit"] = float(
                os.environ["MCP_DAILY_LIMIT"]
            )
        
        # Default strategy
        if "MCP_DEFAULT_STRATEGY" in os.environ:
            config["orchestration"]["default_strategy"] = os.environ["MCP_DEFAULT_STRATEGY"]
        
        # Logging level
        if "MCP_LOG_LEVEL" in os.environ:
            config["logging"]["level"] = os.environ["MCP_LOG_LEVEL"]
        
        return config
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment or secure storage."""
        keys = {}
        
        # OpenRouter API key
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            openrouter_key = self.key_store.get_key("mcp_orchestrator", "openrouter_api_key")
        
        if openrouter_key:
            keys["openrouter"] = openrouter_key
        else:
            logger.warning("OpenRouter API key not found. External models will be unavailable.")
        
        return keys
    
    def save_api_key(self, service: str, key: str):
        """
        Save an API key to secure storage.
        
        Args:
            service: Service name (e.g., "openrouter")
            key: API key value
        """
        self.key_store.set_key("mcp_orchestrator", f"{service}_api_key", key)
        # Clear cache to reload
        self._config_cache = None
        logger.info(f"API key for {service} saved successfully")
    
    def update_config(self, updates: Dict[str, Any]):
        """
        Update configuration values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        # Load current config
        config = self.load_config()
        
        # Apply updates
        for key, value in updates.items():
            if "." in key:
                # Handle nested keys like "orchestration.default_strategy"
                parts = key.split(".")
                current = config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                config[key] = value
        
        # Save to user config file
        user_config_file = self.config_dir / "config.yaml"
        with open(user_config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        # Clear cache
        self._config_cache = None
        logger.info("Configuration updated successfully")
    
    def create_example_config(self):
        """Create an example configuration file."""
        example_config = {
            "orchestration": {
                "default_strategy": "progressive_deep_dive",
                "quality_mode": "balanced"  # "maximum", "balanced", "efficient"
            },
            "cost_management": {
                "max_cost_per_request": 5.0,
                "daily_limit": 100.0
            },
            "models": {
                "preferences": {
                    "code_editing": "gemini_polyglot",
                    "architecture": "o3_architect",
                    "general": "claude_opus"
                }
            }
        }
        
        example_file = self.config_dir / "config.example.yaml"
        with open(example_file, 'w') as f:
            yaml.dump(example_config, f, default_flow_style=False)
            f.write("\n# To use this configuration, rename to config.yaml\n")
            f.write("# API keys should be set via environment variables or the save_api_key method\n")
        
        logger.info(f"Example configuration created at: {example_file}")