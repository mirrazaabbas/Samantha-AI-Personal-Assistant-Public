"""Learning primitive -- router policies, reward functions, learning."""

from __future__ import annotations

from samantha.learning._stubs import (
    QueryAnalyzer,
    RewardFunction,
    RouterPolicy,
    RoutingContext,
)
from samantha.learning.agents.agent_evolver import AgentConfigEvolver
from samantha.learning.learning_orchestrator import LearningOrchestrator
from samantha.learning.optimize.llm_optimizer import LLMOptimizer
from samantha.learning.optimize.optimizer import OptimizationEngine
from samantha.learning.optimize.store import OptimizationStore
from samantha.learning.routing.complexity import (
    ComplexityQueryAnalyzer,
    score_complexity,
)
from samantha.learning.routing.heuristic_reward import HeuristicRewardFunction
from samantha.learning.routing.router import (
    HeuristicRouter,
    build_routing_context,
)
from samantha.learning.training.data import TrainingDataMiner
from samantha.learning.training.lora import HAS_TORCH, LoRATrainer, LoRATrainingConfig


def ensure_registered() -> None:
    """Ensure all learning policies are registered in RouterPolicyRegistry."""
    from samantha.learning.routing.heuristic_policy import (
        ensure_registered as _reg_heuristic,
    )

    _reg_heuristic()

    from samantha.learning.routing.learned_router import (
        ensure_registered as _reg_learned,
    )

    _reg_learned()

    # Intelligence training (optional deps)
    try:
        import samantha.learning.intelligence  # noqa: F401
    except ImportError:
        pass

    # Orchestrator-specific training (optional deps)
    try:
        import samantha.learning.intelligence.orchestrator  # noqa: F401
    except ImportError:
        pass

    # Agent optimizers (optional deps)
    try:
        import samantha.learning.agents.dspy_optimizer  # noqa: F401
    except ImportError:
        pass
    try:
        import samantha.learning.agents.gepa_optimizer  # noqa: F401
    except ImportError:
        pass
    try:
        import samantha.learning.agents.ace_optimizer  # noqa: F401
    except ImportError:
        pass


__all__ = [
    "AgentConfigEvolver",
    "ComplexityQueryAnalyzer",
    "HAS_TORCH",
    "HeuristicRewardFunction",
    "HeuristicRouter",
    "LLMOptimizer",
    "LearningOrchestrator",
    "LoRATrainer",
    "LoRATrainingConfig",
    "OptimizationEngine",
    "OptimizationStore",
    "QueryAnalyzer",
    "RewardFunction",
    "RouterPolicy",
    "RoutingContext",
    "TrainingDataMiner",
    "build_routing_context",
    "ensure_registered",
    "score_complexity",
]
