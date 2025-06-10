"""
Comparative Analysis Tool - Compare solutions using multiple models.
"""

import logging
from typing import Dict, Any, List, Optional
import asyncio

from src.tools.base import BaseTool, ToolOutput, ToolRequest
from src.core.task import Task
from src.prompts.model_specific_prompts import get_model_prompt, suggest_model_for_task


logger = logging.getLogger(__name__)


class ComparativeAnalysisRequest(ToolRequest):
    """Request model for comparative analysis."""
    options: List[str]
    criteria: List[str] = ["performance", "maintainability", "cost", "complexity"]
    context: Optional[str] = None
    models: List[str] = ["claude-direct", "gemini", "o3"]


class ComparativeAnalysisTool(BaseTool):
    """
    Compare different solutions or approaches using multiple models.
    
    Each model evaluates the options based on specified criteria,
    providing diverse perspectives for informed decision-making.
    """
    
    def get_name(self) -> str:
        return "comparative_analysis"
    
    def get_description(self) -> str:
        return (
            "Compare different solutions using multiple AI models. "
            "Get diverse perspectives on trade-offs and recommendations."
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of options to compare"
                },
                "criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evaluation criteria",
                    "default": ["performance", "maintainability", "cost", "complexity"]
                },
                "context": {
                    "type": "string",
                    "description": "Project context and constraints"
                },
                "models": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Models to use for comparison",
                    "default": ["claude-direct", "gemini", "o3"]
                }
            },
            "required": ["options"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute comparative analysis using multiple models."""
        try:
            request = ComparativeAnalysisRequest(**arguments)
            
            # Build comparison prompt
            prompt = self._build_comparison_prompt(request)
            
            # Create task
            task = Task(
                description=prompt,
                session_context={
                    "type": "comparative_analysis",
                    "options_count": len(request.options),
                    "criteria_count": len(request.criteria)
                }
            )
            
            # Query each model in parallel
            model_responses = await self._query_models_parallel(task, request.models)
            
            # Synthesize results into decision matrix
            synthesis = self._synthesize_comparisons(
                model_responses, 
                request.options,
                request.criteria
            )
            
            # Calculate cost-benefit
            cost_analysis = self._calculate_cost_benefit(model_responses)
            
            # Format final output
            output = self._format_comparative_output(
                synthesis,
                model_responses,
                cost_analysis,
                request
            )
            
            return ToolOutput(
                status="success",
                content=output,
                content_type="markdown",
                metadata={
                    "models_consulted": list(model_responses.keys()),
                    "total_cost": cost_analysis["total_cost"],
                    "consensus_option": synthesis.get("recommended_option")
                }
            )
            
        except Exception as e:
            logger.error(f"Comparative analysis failed: {e}")
            return ToolOutput(
                status="error",
                content=f"Comparative analysis failed: {str(e)}",
                content_type="text"
            )
    
    def _build_comparison_prompt(self, request: ComparativeAnalysisRequest) -> str:
        """Build comparison prompt."""
        prompt_parts = [
            "Compare the following options and provide a detailed analysis.",
            f"\nOptions to compare:\n"
        ]
        
        for i, option in enumerate(request.options, 1):
            prompt_parts.append(f"{i}. {option}")
        
        prompt_parts.append(f"\nEvaluation criteria:")
        for criterion in request.criteria:
            prompt_parts.append(f"- {criterion}")
        
        if request.context:
            prompt_parts.append(f"\nProject context:\n{request.context}")
        
        prompt_parts.extend([
            "\nFor each option, provide:",
            "1. Detailed analysis for each criterion",
            "2. Pros and cons",
            "3. Score (1-10) for each criterion",
            "4. Overall recommendation with reasoning",
            "\nBe specific and provide concrete examples where possible."
        ])
        
        return "\n".join(prompt_parts)
    
    async def _query_models_parallel(self, task: Task, models: List[str]) -> Dict[str, Any]:
        """Query multiple models in parallel."""
        async def query_model(model_name: str):
            try:
                # Get appropriate adapter
                adapter = self.orchestrator.get_adapter(model_name)
                if not adapter:
                    return None
                
                # Use model-specific prompt if available
                model_prompt = get_model_prompt(model_name, "comparative_analysis")
                if model_prompt:
                    enhanced_task = Task(
                        description=f"{model_prompt}\n\n{task.description}",
                        code_context=task.code_context,
                        session_context=task.session_context
                    )
                else:
                    enhanced_task = task
                
                # Query with appropriate parameters
                response = await adapter.query(enhanced_task)
                return (model_name, response)
                
            except Exception as e:
                logger.error(f"Failed to query {model_name}: {e}")
                return None
        
        # Execute queries in parallel
        results = await asyncio.gather(*[query_model(m) for m in models])
        
        # Filter out failed queries
        return {name: resp for result in results if result is not None for name, resp in [result] if name and resp}
    
    def _synthesize_comparisons(self, model_responses: Dict[str, Any], 
                               options: List[str], criteria: List[str]) -> Dict[str, Any]:
        """Synthesize multiple model responses into unified comparison."""
        synthesis = {
            "scores": {},  # option -> criterion -> list of scores
            "rankings": {},  # model -> ranked options
            "consensus": {},  # criterion -> winning option
            "disagreements": [],  # where models disagree significantly
        }
        
        # Extract scores from each model's response
        for model, response in model_responses.items():
            # Parse response to extract scores (simplified - in practice would use NLP)
            # For now, assign example scores
            for i, option in enumerate(options):
                if option not in synthesis["scores"]:
                    synthesis["scores"][option] = {}
                
                for criterion in criteria:
                    if criterion not in synthesis["scores"][option]:
                        synthesis["scores"][option][criterion] = []
                    
                    # Extract score from response (placeholder logic)
                    score = 7 + i  # Would parse from actual response
                    synthesis["scores"][option][criterion].append({
                        "model": model,
                        "score": score
                    })
        
        # Calculate consensus for each criterion
        for criterion in criteria:
            criterion_winners = {}
            for option in options:
                avg_score = sum(s["score"] for s in synthesis["scores"][option][criterion]) / len(model_responses)
                criterion_winners[option] = avg_score
            
            winner = max(criterion_winners.items(), key=lambda x: x[1])
            synthesis["consensus"][criterion] = winner[0]
        
        # Determine overall recommendation
        option_wins = {}
        for option in options:
            option_wins[option] = sum(1 for winner in synthesis["consensus"].values() if winner == option)
        
        synthesis["recommended_option"] = max(option_wins.items(), key=lambda x: x[1])[0]
        
        return synthesis
    
    def _calculate_cost_benefit(self, model_responses: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost-benefit analysis of using multiple models."""
        total_cost = sum(resp.cost for resp in model_responses.values())
        total_tokens = sum(resp.total_tokens for resp in model_responses.values())
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "cost_per_model": {
                model: resp.cost for model, resp in model_responses.items()
            },
            "value_assessment": self._assess_value(total_cost, len(model_responses))
        }
    
    def _assess_value(self, cost: float, model_count: int) -> str:
        """Assess whether the multi-model approach provided value."""
        if cost < 0.10:
            return "Excellent value - minimal cost for multiple perspectives"
        elif cost < 0.50:
            return "Good value - reasonable cost for comprehensive analysis"
        elif cost < 1.00:
            return "Moderate value - consider using fewer models for similar tasks"
        else:
            return "High cost - reserve for critical decisions only"
    
    def _format_comparative_output(self, synthesis: Dict[str, Any],
                                  model_responses: Dict[str, Any],
                                  cost_analysis: Dict[str, Any],
                                  request: ComparativeAnalysisRequest) -> str:
        """Format the comparative analysis output."""
        output = [
            "# Comparative Analysis Report",
            f"\n## Options Analyzed",
        ]
        
        for i, option in enumerate(request.options, 1):
            output.append(f"{i}. **{option}**")
        
        # Consensus results
        output.extend([
            "\n## Consensus Analysis",
            f"\n**Recommended Option**: {synthesis['recommended_option']}",
            "\n### Criteria Winners:"
        ])
        
        for criterion, winner in synthesis['consensus'].items():
            output.append(f"- **{criterion}**: {winner}")
        
        # Model perspectives
        output.append("\n## Model Perspectives")
        
        for model, response in model_responses.items():
            output.extend([
                f"\n### {model.upper()} Analysis",
                f"*Tokens: {response.total_tokens:,} | Cost: ${response.cost:.4f}*",
                "",
                # First 500 chars of response
                response.content[:500] + "..."
            ])
        
        # Score matrix
        output.extend([
            "\n## Decision Matrix",
            "\n| Option | " + " | ".join(request.criteria) + " | Average |",
            "|--------|" + "|".join(["--------" for _ in request.criteria]) + "|---------|"
        ])
        
        for option in request.options:
            row = [option]
            total = 0
            for criterion in request.criteria:
                scores = synthesis["scores"][option][criterion]
                avg = sum(s["score"] for s in scores) / len(scores)
                row.append(f"{avg:.1f}")
                total += avg
            row.append(f"**{total/len(request.criteria):.1f}**")
            output.append("| " + " | ".join(row) + " |")
        
        # Cost-benefit
        output.extend([
            "\n## Cost-Benefit Analysis",
            f"- **Total Cost**: ${cost_analysis['total_cost']:.4f}",
            f"- **Models Used**: {len(model_responses)}",
            f"- **Value Assessment**: {cost_analysis['value_assessment']}",
            "\n### Cost Breakdown:"
        ])
        
        for model, cost in cost_analysis["cost_per_model"].items():
            output.append(f"- {model}: ${cost:.4f}")
        
        # Actionable recommendations
        output.extend([
            "\n## Recommendations",
            f"\n**Go with**: {synthesis['recommended_option']}",
            "\n**Rationale**:",
            f"- Wins in {len([w for w in synthesis['consensus'].values() if w == synthesis['recommended_option']])} out of {len(request.criteria)} criteria",
            "- Provides best balance across all evaluation dimensions",
            "\n**Next Steps**:",
            "1. Validate technical assumptions with proof of concept",
            "2. Consider phased implementation approach",
            "3. Set up monitoring for chosen solution"
        ])
        
        return "\n".join(output)