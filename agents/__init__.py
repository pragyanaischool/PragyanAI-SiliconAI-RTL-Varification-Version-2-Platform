"""Lazy agent package."""

from importlib import import_module

_EXPORTS = {
    "RTLAnalyzerAgent": ".rtl_analyzer",
    "VerificationPlannerAgent": ".verification_planner",
    "TestGeneratorAgent": ".test_generator",
    "TestbenchGeneratorAgent": ".testbench_generator",
    "SimulatorAgent": ".simulator_agent",
    "FailureAnalyzerAgent": ".failure_analyzer",
    "CoverageAgent": ".coverage_agent",
    "RedTeamAgent": ".red_team_agent",
    "MutationAgent": ".mutation_agent",
    "FormalAgent": ".formal_agent",
    "VerificationJudgeAgent": ".verification_judge",
}

__all__ = list(_EXPORTS)

def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if not module_name:
        raise AttributeError(name)
    module = import_module(module_name, __name__)
    return getattr(module, name)
