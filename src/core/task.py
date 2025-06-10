"""
Task definition and analysis module for MCP.

This module provides the core task representation and analysis capabilities
for determining appropriate LLM selection and orchestration strategies.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import re
from datetime import datetime


class TaskType(Enum):
    """Enumeration of different coding task types."""
    CODE_GENERATION = auto()
    BUG_FIX = auto()
    REFACTORING = auto()
    ARCHITECTURE = auto()
    DOCUMENTATION = auto()
    CODE_REVIEW = auto()
    TEST_GENERATION = auto()
    OPTIMIZATION = auto()
    COMPLEX_EDIT = auto()
    EXPLANATION = auto()
    CRITICAL_BUG = auto()
    DESIGN = auto()


class ComplexityLevel(Enum):
    """Task complexity levels."""
    TRIVIAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class ImpactLevel(Enum):
    """Potential impact level of the task."""
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    MAJOR = 4
    CRITICAL = 5


@dataclass
class TaskAnalysis:
    """Results of task analysis."""
    task_type: TaskType
    complexity: ComplexityLevel
    estimated_impact: ImpactLevel
    requires_multiple_perspectives: bool
    languages_detected: List[str]
    frameworks_detected: List[str]
    estimated_lines_affected: int
    has_architectural_implications: bool
    requires_deep_reasoning: bool
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """
    Represents a coding task to be processed by the MCP.
    
    Attributes:
        description: Natural language description of the task
        code_context: Relevant code snippets or file contents
        file_paths: List of file paths involved in the task
        user_preferences: User-specified preferences for handling
        timestamp: When the task was created
        session_context: Additional context from the coding session
    """
    description: str
    code_context: Optional[str] = None
    file_paths: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate task after initialization."""
        if not self.description.strip():
            raise ValueError("Task description cannot be empty")


class TaskAnalyzer:
    """
    Analyzes tasks to determine their type, complexity, and optimal handling strategy.
    """
    
    def __init__(self):
        self.type_patterns = self._initialize_type_patterns()
        self.complexity_indicators = self._initialize_complexity_indicators()
        
    def analyze(self, task: Task) -> TaskAnalysis:
        """
        Perform comprehensive analysis of a task.
        
        Args:
            task: The task to analyze
            
        Returns:
            TaskAnalysis object containing analysis results
        """
        task_type = self._detect_task_type(task)
        complexity = self._assess_complexity(task, task_type)
        impact = self._estimate_impact(task, task_type)
        languages = self._detect_languages(task)
        frameworks = self._detect_frameworks(task)
        
        return TaskAnalysis(
            task_type=task_type,
            complexity=complexity,
            estimated_impact=impact,
            requires_multiple_perspectives=self._needs_multiple_perspectives(task, complexity),
            languages_detected=languages,
            frameworks_detected=frameworks,
            estimated_lines_affected=self._estimate_affected_lines(task),
            has_architectural_implications=self._has_architectural_implications(task, task_type),
            requires_deep_reasoning=self._requires_deep_reasoning(task, complexity, task_type),
            confidence_score=self._calculate_confidence(task, task_type)
        )
    
    def _initialize_type_patterns(self) -> Dict[TaskType, List[re.Pattern]]:
        """Initialize regex patterns for task type detection."""
        return {
            TaskType.BUG_FIX: [
                re.compile(r'\b(fix|bug|error|issue|problem|broken|crash|fail)\b', re.I),
                re.compile(r'\b(not working|doesn\'t work|exception|traceback)\b', re.I)
            ],
            TaskType.REFACTORING: [
                re.compile(r'\b(refactor|restructure|reorganize|clean up|improve|optimize)\b', re.I),
                re.compile(r'\b(technical debt|code smell|duplicate|DRY)\b', re.I)
            ],
            TaskType.ARCHITECTURE: [
                re.compile(r'\b(architect|design|structure|pattern|system|module)\b', re.I),
                re.compile(r'\b(microservice|monolith|layer|component|interface)\b', re.I)
            ],
            TaskType.CODE_GENERATION: [
                re.compile(r'\b(create|implement|add|build|generate|write)\b', re.I),
                re.compile(r'\b(feature|function|class|method|component)\b', re.I)
            ],
            TaskType.TEST_GENERATION: [
                re.compile(r'\b(test|unit test|integration test|e2e|coverage)\b', re.I),
                re.compile(r'\b(pytest|jest|mocha|junit|testing)\b', re.I)
            ],
            TaskType.DOCUMENTATION: [
                re.compile(r'\b(document|docs|readme|comment|explain|describe)\b', re.I),
                re.compile(r'\b(api doc|docstring|jsdoc|javadoc)\b', re.I)
            ],
            TaskType.OPTIMIZATION: [
                re.compile(r'\b(optimize|performance|speed up|faster|efficient)\b', re.I),
                re.compile(r'\b(memory|cpu|latency|throughput|bottleneck)\b', re.I)
            ]
        }
    
    def _initialize_complexity_indicators(self) -> Dict[str, int]:
        """Initialize complexity scoring indicators."""
        return {
            "multi_file": 3,
            "architectural_terms": 4,
            "complex_algorithms": 4,
            "concurrent_processing": 5,
            "distributed_systems": 5,
            "security_concerns": 4,
            "performance_critical": 4,
            "large_codebase": 3,
            "multiple_languages": 3,
            "framework_specific": 2
        }
    
    def _detect_task_type(self, task: Task) -> TaskType:
        """Detect the primary type of the task."""
        description_lower = task.description.lower()
        
        # Check for explicit type indicators
        type_scores = {}
        for task_type, patterns in self.type_patterns.items():
            score = sum(1 for pattern in patterns if pattern.search(description_lower))
            if score > 0:
                type_scores[task_type] = score
        
        # Return the type with highest score, or default to CODE_GENERATION
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        
        return TaskType.CODE_GENERATION
    
    def _assess_complexity(self, task: Task, task_type: TaskType) -> ComplexityLevel:
        """Assess the complexity level of the task."""
        complexity_score = 0
        
        # Base complexity by task type
        type_base_complexity = {
            TaskType.ARCHITECTURE: 3,
            TaskType.REFACTORING: 2,
            TaskType.OPTIMIZATION: 3,
            TaskType.CRITICAL_BUG: 3,
            TaskType.COMPLEX_EDIT: 3,
            TaskType.BUG_FIX: 2,
            TaskType.CODE_GENERATION: 2,
            TaskType.TEST_GENERATION: 1,
            TaskType.DOCUMENTATION: 1,
            TaskType.EXPLANATION: 1
        }
        
        complexity_score += type_base_complexity.get(task_type, 2)
        
        # Adjust based on file count
        if len(task.file_paths) > 5:
            complexity_score += 2
        elif len(task.file_paths) > 2:
            complexity_score += 1
        
        # Check for complexity indicators in description
        description_lower = task.description.lower()
        for indicator, weight in self.complexity_indicators.items():
            if indicator.replace("_", " ") in description_lower:
                complexity_score += weight * 0.5
        
        # Consider code context size
        if task.code_context and len(task.code_context) > 5000:
            complexity_score += 1
        
        # Map score to complexity level
        if complexity_score <= 2:
            return ComplexityLevel.LOW
        elif complexity_score <= 4:
            return ComplexityLevel.MEDIUM
        elif complexity_score <= 6:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.VERY_HIGH
    
    def _estimate_impact(self, task: Task, task_type: TaskType) -> ImpactLevel:
        """Estimate the potential impact of the task."""
        if task_type == TaskType.CRITICAL_BUG:
            return ImpactLevel.CRITICAL
        
        if task_type in [TaskType.ARCHITECTURE, TaskType.DESIGN]:
            return ImpactLevel.MAJOR
        
        if len(task.file_paths) > 10:
            return ImpactLevel.MAJOR
        elif len(task.file_paths) > 5:
            return ImpactLevel.MODERATE
        
        # Check for impact keywords
        impact_keywords = {
            "critical": ImpactLevel.CRITICAL,
            "major": ImpactLevel.MAJOR,
            "breaking": ImpactLevel.MAJOR,
            "security": ImpactLevel.MAJOR,
            "performance": ImpactLevel.MODERATE,
            "minor": ImpactLevel.LOW
        }
        
        description_lower = task.description.lower()
        for keyword, level in impact_keywords.items():
            if keyword in description_lower:
                return level
        
        return ImpactLevel.MODERATE
    
    def _detect_languages(self, task: Task) -> List[str]:
        """Detect programming languages involved in the task."""
        languages = set()
        
        # Check file extensions
        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP'
        }
        
        for file_path in task.file_paths:
            for ext, lang in extension_map.items():
                if file_path.endswith(ext):
                    languages.add(lang)
        
        # Check description for language mentions
        desc_lower = task.description.lower()
        for lang in ['python', 'javascript', 'typescript', 'java', 'c++', 'go', 'rust']:
            if lang in desc_lower:
                languages.add(lang.title())
        
        return list(languages)
    
    def _detect_frameworks(self, task: Task) -> List[str]:
        """Detect frameworks mentioned or implied in the task."""
        frameworks = set()
        
        # Common framework indicators
        framework_patterns = {
            'react': re.compile(r'\b(react|jsx|component|hooks?)\b', re.I),
            'django': re.compile(r'\b(django|models?|views?|urls?)\b', re.I),
            'flask': re.compile(r'\b(flask|route|blueprint)\b', re.I),
            'express': re.compile(r'\b(express|router|middleware)\b', re.I),
            'spring': re.compile(r'\b(spring|boot|bean|autowired)\b', re.I),
            'vue': re.compile(r'\b(vue|vuex|composition api)\b', re.I),
            'angular': re.compile(r'\b(angular|ng-|directive|service)\b', re.I)
        }
        
        desc_and_context = task.description
        if task.code_context:
            desc_and_context += " " + task.code_context
        
        for framework, pattern in framework_patterns.items():
            if pattern.search(desc_and_context):
                frameworks.add(framework)
        
        return list(frameworks)
    
    def _estimate_affected_lines(self, task: Task) -> int:
        """Estimate the number of lines that might be affected."""
        base_estimate = 50  # Default estimate
        
        # Adjust based on task type
        type_multipliers = {
            TaskType.ARCHITECTURE: 10,
            TaskType.REFACTORING: 5,
            TaskType.BUG_FIX: 0.5,
            TaskType.DOCUMENTATION: 0.3,
            TaskType.OPTIMIZATION: 2
        }
        
        task_type = self._detect_task_type(task)
        multiplier = type_multipliers.get(task_type, 1)
        
        # Adjust based on file count
        file_multiplier = max(1, len(task.file_paths))
        
        return int(base_estimate * multiplier * file_multiplier)
    
    def _has_architectural_implications(self, task: Task, task_type: TaskType) -> bool:
        """Determine if the task has architectural implications."""
        if task_type in [TaskType.ARCHITECTURE, TaskType.DESIGN]:
            return True
        
        arch_keywords = ['architecture', 'design pattern', 'structure', 'refactor', 
                        'module', 'component', 'interface', 'api design']
        
        desc_lower = task.description.lower()
        return any(keyword in desc_lower for keyword in arch_keywords)
    
    def _requires_deep_reasoning(self, task: Task, complexity: ComplexityLevel, 
                               task_type: TaskType) -> bool:
        """Determine if the task requires deep reasoning capabilities."""
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            return True
        
        if task_type in [TaskType.ARCHITECTURE, TaskType.OPTIMIZATION, 
                         TaskType.CRITICAL_BUG, TaskType.COMPLEX_EDIT]:
            return True
        
        deep_reasoning_keywords = ['complex', 'intricate', 'sophisticated', 
                                  'algorithm', 'optimize', 'design', 'architect']
        
        desc_lower = task.description.lower()
        return any(keyword in desc_lower for keyword in deep_reasoning_keywords)
    
    def _needs_multiple_perspectives(self, task: Task, complexity: ComplexityLevel) -> bool:
        """Determine if the task would benefit from multiple LLM perspectives."""
        if complexity.value >= ComplexityLevel.HIGH.value:
            return True
        
        perspective_keywords = ['best approach', 'alternatives', 'trade-offs', 
                               'pros and cons', 'compare', 'evaluate']
        
        desc_lower = task.description.lower()
        return any(keyword in desc_lower for keyword in perspective_keywords)
    
    def _calculate_confidence(self, task: Task, task_type: TaskType) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.7  # Base confidence
        
        # Increase confidence if we have more context
        if task.code_context:
            confidence += 0.1
        
        if task.file_paths:
            confidence += 0.05 * min(len(task.file_paths), 2)
        
        # Decrease confidence for ambiguous task types
        if task_type in [TaskType.CODE_GENERATION, TaskType.EXPLANATION]:
            confidence -= 0.1
        
        return min(confidence, 1.0)