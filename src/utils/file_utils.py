"""
File management utilities with intelligent token budgeting.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
import mimetypes


logger = logging.getLogger(__name__)


# Common code file extensions
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
    '.sql', '.sh', '.bash', '.yml', '.yaml', '.json', '.xml', '.toml',
    '.md', '.rst', '.html', '.css', '.scss'
}

# Directories to ignore
IGNORED_DIRS = {
    'node_modules', '__pycache__', 'venv', 'env', '.git', 
    'build', 'dist', 'target', '.pytest_cache'
}


class FileManager:
    """
    Intelligent file management with token budgeting.
    
    Features:
    - Recursive directory reading
    - File type filtering
    - Token budget management
    - Large file handling
    """
    
    def __init__(self, max_tokens: int = 1_000_000):
        """Initialize with token limit."""
        self.max_tokens = max_tokens
        self.token_reserve = 50_000  # Reserve for prompt/response
    
    async def read_files(self, paths: List[str], 
                        extensions: Optional[Set[str]] = None) -> Dict[str, str]:
        """
        Read files from paths with intelligent filtering.
        
        Args:
            paths: List of file or directory paths
            extensions: Optional set of extensions to include
            
        Returns:
            Dictionary mapping file paths to contents
        """
        if extensions is None:
            extensions = CODE_EXTENSIONS
        
        file_contents = {}
        total_tokens = 0
        available_tokens = self.max_tokens - self.token_reserve
        
        # Expand directories to individual files
        all_files = self._expand_paths(paths, extensions)
        
        for filepath in all_files:
            try:
                # Estimate tokens for this file
                file_size = os.path.getsize(filepath)
                estimated_tokens = file_size // 4  # Rough estimate
                
                if total_tokens + estimated_tokens > available_tokens:
                    logger.warning(f"Skipping {filepath} - token limit reached")
                    continue
                
                # Read file content
                content = await self._read_file(filepath)
                if content:
                    file_contents[filepath] = content
                    total_tokens += estimated_tokens
                    
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
                continue
        
        logger.info(f"Read {len(file_contents)} files, ~{total_tokens:,} tokens")
        return file_contents
    
    def _expand_paths(self, paths: List[str], 
                     extensions: Set[str]) -> List[str]:
        """Expand directories to individual files."""
        expanded = []
        
        for path in paths:
            path_obj = Path(path)
            
            if not path_obj.exists():
                logger.warning(f"Path does not exist: {path}")
                continue
            
            if path_obj.is_file():
                if path_obj.suffix.lower() in extensions:
                    expanded.append(str(path_obj))
            elif path_obj.is_dir():
                # Walk directory
                for root, dirs, files in os.walk(path_obj):
                    # Filter out ignored directories
                    dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                    
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in extensions:
                            expanded.append(str(file_path))
        
        return sorted(expanded)
    
    async def _read_file(self, filepath: str, 
                        max_size: int = 1_000_000) -> Optional[str]:
        """Read a single file with size limits."""
        try:
            path = Path(filepath)
            
            # Check file size
            if path.stat().st_size > max_size:
                logger.warning(f"File too large: {filepath}")
                return None
            
            # Read with UTF-8, handle encoding errors
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return None
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Simple approximation: 1 token ≈ 4 characters
        return len(text) // 4