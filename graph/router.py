"""Pure routing policy for the verification graph."""

from core.state import VerificationState

END = "end"

def route_after_simulation(state):
    return "coverage" if state.get("simulation_passed") else "failure_analysis"

def route_after_failure(state):
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return END
    return "test_generation"

def route_after_coverage(state):
    target = state.get("coverage", {}).get("target", 95)
    score = state.get("coverage", {}).get("score", 0)
    return "red_team" if score >= target else "test_generation"

def route_after_red_team(state):
    return "mutation" if state.get("run_mutation", False) else ("formal" if state.get("run_formal", False) else "judge")

def route_after_mutation(state):
    return "formal" if state.get("run_formal", False) else "judge"

def route_after_formal(state):
    return "judge"

def route_after_judge(state):
    verdict = state.get("final_verdict", "UNKNOWN")
    if verdict == "PASS":
        return END
    if state.get("iteration", 0) < state.get("max_iterations", 3):
        return "test_generation"
    return END
