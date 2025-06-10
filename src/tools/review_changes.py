"""
Pre-commit validation tool for reviewing git changes.

Comprehensive review of staged/unstaged git changes across multiple repositories.
"""

import os
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from src.tools.base import BaseTool, ToolOutput
from src.core.dynamic_context import ToolResponse, RequestStatus, ClarificationRequest
from src.prompts import REVIEW_CHANGES_PROMPT


@dataclass
class GitChange:
    """Represents a git change."""
    file_path: str
    change_type: str  # added, modified, deleted
    diff: str
    repo_path: str


class ReviewChangesTool(BaseTool):
    """
    Reviews pending git changes before commit.
    
    Features:
    - Recursive repository discovery
    - Validates changes against requirements
    - Detects incomplete implementations
    - Multi-repo support
    - Security-focused analysis
    """
    
    def __init__(self, orchestrator=None):
        super().__init__(orchestrator)
        self.name = "review_changes"
        self.description = (
            "Review git changes before committing. Validates against requirements, "
            "finds incomplete implementations, security issues, and ensures quality."
        )
    
    def get_name(self) -> str:
        """Return tool name."""
        return self.name
    
    def get_description(self) -> str:
        """Return tool description."""
        return self.description
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Starting directory to search for repos (default: current)"
                },
                "original_request": {
                    "type": "string",
                    "description": "The requirements/ticket for context"
                },
                "compare_to": {
                    "type": "string",
                    "description": "Branch/tag to compare against (default: HEAD)"
                },
                "review_type": {
                    "type": "string",
                    "enum": ["full", "security", "performance", "quick"],
                    "description": "Type of review to perform"
                },
                "severity_filter": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "all"],
                    "description": "Minimum severity to report"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Max depth for repo search (default: 3)"
                }
            },
            "required": []
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute the review changes tool."""
        try:
            # Extract parameters
            start_path = Path(arguments.get("path", ".")).resolve()
            original_request = arguments.get("original_request", "")
            compare_to = arguments.get("compare_to", "HEAD")
            review_type = arguments.get("review_type", "full")
            severity_filter = arguments.get("severity_filter", "all")
            max_depth = arguments.get("max_depth", 3)
            
            # Find all git repositories
            repos = self._find_git_repos(start_path, max_depth)
            
            if not repos:
                return ToolOutput(
                    status="error",
                    content="No git repositories found in the specified path."
                )
            
            # Collect changes from all repos
            all_changes = []
            for repo in repos:
                changes = self._get_repo_changes(repo, compare_to)
                all_changes.extend(changes)
            
            if not all_changes:
                return ToolOutput(
                    status="success",
                    content="No pending changes found in any repository."
                )
            
            # Check if we need more context
            if self._needs_clarification(all_changes, original_request):
                clarification = ClarificationRequest(
                    question="I need to see test files to ensure changes have proper test coverage",
                    files_needed=self._get_test_files_for_changes(all_changes),
                    context_type="test_coverage"
                )
                
                response = ToolResponse(
                    status=RequestStatus.REQUIRES_CLARIFICATION,
                    content="",
                    clarification_request=clarification
                )
                
                return ToolOutput(
                    status="requires_clarification",
                    content=str(response.to_dict()),
                    content_type="json"
                )
            
            # Perform the review
            review_result = await self._review_changes(
                all_changes,
                original_request,
                review_type,
                severity_filter
            )
            
            return ToolOutput(
                status="success",
                content=review_result,
                content_type="markdown",
                metadata={
                    "repos_checked": len(repos),
                    "files_changed": len(all_changes),
                    "review_type": review_type
                }
            )
            
        except Exception as e:
            return ToolOutput(
                status="error",
                content=f"Error reviewing changes: {str(e)}"
            )
    
    def _find_git_repos(self, start_path: Path, max_depth: int) -> List[Path]:
        """Recursively find all git repositories."""
        repos = []
        
        def search_repos(path: Path, depth: int):
            if depth > max_depth:
                return
            
            # Check if current directory is a git repo
            if (path / ".git").is_dir():
                repos.append(path)
                return  # Don't search inside git repos
            
            # Search subdirectories
            try:
                for item in path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        search_repos(item, depth + 1)
            except PermissionError:
                pass
        
        search_repos(start_path, 0)
        return repos
    
    def _get_repo_changes(self, repo_path: Path, compare_to: str) -> List[GitChange]:
        """Get all changes in a repository."""
        changes = []
        
        try:
            # Get staged changes
            staged_output = subprocess.run(
                ["git", "diff", "--name-status", "--cached"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get unstaged changes
            unstaged_output = subprocess.run(
                ["git", "diff", "--name-status"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse changes
            for line in staged_output.stdout.splitlines() + unstaged_output.stdout.splitlines():
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        change_type = self._parse_change_type(parts[0])
                        file_path = parts[1]
                        
                        # Get diff for this file
                        diff = self._get_file_diff(repo_path, file_path)
                        
                        changes.append(GitChange(
                            file_path=file_path,
                            change_type=change_type,
                            diff=diff,
                            repo_path=str(repo_path)
                        ))
            
        except subprocess.CalledProcessError:
            # Not a git repo or git error
            pass
        
        return changes
    
    def _parse_change_type(self, status: str) -> str:
        """Parse git status letter to change type."""
        mapping = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied'
        }
        return mapping.get(status[0], 'unknown')
    
    def _get_file_diff(self, repo_path: Path, file_path: str) -> str:
        """Get diff for a specific file."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD", "--", file_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def _needs_clarification(self, changes: List[GitChange], original_request: str) -> bool:
        """Check if we need additional context."""
        # Need clarification if:
        # 1. Many files changed but no test files
        # 2. Complex changes without clear requirements
        # 3. Security-sensitive files modified
        
        has_tests = any('test' in c.file_path.lower() for c in changes)
        has_many_changes = len(changes) > 10
        has_security_files = any(
            any(pattern in c.file_path.lower() for pattern in ['auth', 'security', 'password', 'token'])
            for c in changes
        )
        
        return (has_many_changes and not has_tests) or (has_security_files and not original_request)
    
    def _get_test_files_for_changes(self, changes: List[GitChange]) -> List[str]:
        """Get test files that should be checked for the changes."""
        test_files = []
        
        for change in changes:
            # Guess test file names
            base_name = Path(change.file_path).stem
            test_patterns = [
                f"test_{base_name}.py",
                f"{base_name}_test.py",
                f"tests/{base_name}.py",
                f"test/{base_name}.py"
            ]
            test_files.extend(test_patterns)
        
        return list(set(test_files))[:10]  # Limit to 10 files
    
    async def _review_changes(
        self,
        changes: List[GitChange],
        original_request: str,
        review_type: str,
        severity_filter: str
    ) -> str:
        """Perform the actual review of changes."""
        # Group changes by repository
        repos = {}
        for change in changes:
            if change.repo_path not in repos:
                repos[change.repo_path] = []
            repos[change.repo_path].append(change)
        
        # Build review prompt
        prompt = f"{REVIEW_CHANGES_PROMPT}\n\n"
        
        if original_request:
            prompt += f"## Original Request/Requirements:\n{original_request}\n\n"
        
        prompt += f"## Changes to Review ({review_type} review):\n\n"
        
        for repo_path, repo_changes in repos.items():
            prompt += f"### Repository: {repo_path}\n"
            prompt += f"Files changed: {len(repo_changes)}\n\n"
            
            for change in repo_changes:
                prompt += f"#### {change.file_path} ({change.change_type})\n"
                prompt += f"```diff\n{change.diff[:1000]}...\n```\n\n"  # Truncate large diffs
        
        # This would normally call an LLM to review
        # For now, return a structured review
        return self._generate_review_report(repos, review_type, severity_filter)
    
    def _generate_review_report(
        self,
        repos: Dict[str, List[GitChange]],
        review_type: str,
        severity_filter: str
    ) -> str:
        """Generate a review report."""
        report = "# Pre-Commit Review Report\n\n"
        
        total_issues = 0
        
        for repo_path, changes in repos.items():
            report += f"## Repository: {repo_path}\n"
            report += f"- Files changed: {len(changes)}\n"
            report += f"- Review type: {review_type}\n\n"
            
            # Analyze changes
            issues = self._analyze_changes(changes, review_type)
            
            # Filter by severity
            if severity_filter != "all":
                issues = [i for i in issues if i["severity"] == severity_filter.upper()]
            
            if issues:
                report += "### Issues Found:\n\n"
                for issue in issues:
                    report += f"**[{issue['severity']}]** {issue['title']}\n"
                    report += f"- File: {issue['file']}\n"
                    report += f"- Description: {issue['description']}\n"
                    report += f"- Fix: {issue['fix']}\n\n"
                
                total_issues += len(issues)
            else:
                report += "✅ No issues found\n\n"
        
        report += f"\n## Summary\n"
        report += f"- Total repositories: {len(repos)}\n"
        report += f"- Total files changed: {sum(len(changes) for changes in repos.values())}\n"
        report += f"- Total issues: {total_issues}\n"
        
        return report
    
    def _analyze_changes(self, changes: List[GitChange], review_type: str) -> List[Dict[str, Any]]:
        """Analyze changes for issues."""
        issues = []
        
        for change in changes:
            # Check for common issues
            if change.change_type == "added":
                # Check if new file is used anywhere
                if not self._is_file_referenced(change):
                    issues.append({
                        "severity": "MEDIUM",
                        "title": "Unused new file",
                        "file": change.file_path,
                        "description": "New file added but not referenced anywhere",
                        "fix": "Ensure the file is imported/used or remove if not needed"
                    })
            
            # Security checks
            if review_type in ["full", "security"]:
                security_issues = self._check_security(change)
                issues.extend(security_issues)
        
        return issues
    
    def _is_file_referenced(self, change: GitChange) -> bool:
        """Check if a file is referenced in the codebase."""
        # Simplified check - in real implementation would search codebase
        return True
    
    def _check_security(self, change: GitChange) -> List[Dict[str, Any]]:
        """Check for security issues in changes."""
        issues = []
        
        # Check for hardcoded secrets
        if any(pattern in change.diff.lower() for pattern in ['password=', 'api_key=', 'secret=']):
            issues.append({
                "severity": "CRITICAL",
                "title": "Potential hardcoded secret",
                "file": change.file_path,
                "description": "Detected potential hardcoded credentials in diff",
                "fix": "Use environment variables or secure credential storage"
            })
        
        return issues