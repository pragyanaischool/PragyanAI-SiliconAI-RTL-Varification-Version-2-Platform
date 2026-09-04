"""LangGraph orchestration for the complete RTL verification pipeline."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from core.state import VerificationState
from agents.rtl_analyzer import RTLAnalyzerAgent
from agents.verification_planner import VerificationPlannerAgent
from agents.test_generator import TestGeneratorAgent
from agents.testbench_generator import TestbenchGeneratorAgent
from agents.simulator_agent import SimulatorAgent
from agents.failure_analyzer import FailureAnalyzerAgent
from agents.coverage_agent import CoverageAgent
from agents.red_team_agent import RedTeamAgent
from agents.mutation_agent import MutationAgent
from agents.formal_agent import FormalAgent
from agents.verification_judge import VerificationJudgeAgent
from graph.router import (
    route_after_simulation, route_after_failure, route_after_coverage,
    route_after_red_team, route_after_mutation, route_after_formal,
    route_after_judge,
)

AGENTS = {
    "rtl_analysis": RTLAnalyzerAgent(),
    "planning": VerificationPlannerAgent(),
    "test_generation": TestGeneratorAgent(),
    "testbench_generation": TestbenchGeneratorAgent(),
    "simulation": SimulatorAgent(),
    "failure_analysis": FailureAnalyzerAgent(),
    "coverage": CoverageAgent(),
    "red_team": RedTeamAgent(),
    "mutation": MutationAgent(),
    "formal": FormalAgent(),
    "judge": VerificationJudgeAgent(),
}

def _node(name):
    def run(state):
        result = AGENTS[name].execute(state)
        logger = state.get("_activity_logger")
        if logger:
            _dump_artifacts(logger, name, state, result)
        return result
    return run

def _dump_artifacts(logger, name, state, result):
    step = AGENTS[name].step
    merged = dict(state)
    merged.update(result)

    if name == "rtl_analysis":
        logger.write_code("rtl_analysis", "input_rtl.v", merged.get("current_rtl", ""), step)
        logger.write_json("rtl_analysis", "rtl_analysis.json", merged.get("rtl_analysis", {}), step)
    elif name == "planning":
        logger.write_json("planning", "verification_plan.json", merged.get("verification_plan", {}), step)
    elif name == "test_generation":
        tests = merged.get("generated_tests", [])
        logger.write_json("test_generation", "tests.json", tests, step)
        for i, test in enumerate(tests, 1):
            logger.write_text("test_generation", f"test_{i:03d}.json", test, step)
    elif name == "testbench_generation":
        logger.write_code("testbench", "testbench.v", merged.get("testbench", ""), step)
    elif name == "simulation":
        logger.write_code("simulation", "design.v", merged.get("current_rtl", ""), step)
        logger.write_code("simulation", "testbench.v", merged.get("testbench", ""), step)
        logger.write_text("simulation", "compile.log", merged.get("compile_output", ""), step)
        logger.write_text("simulation", "simulation.log", merged.get("simulation_output", ""), step)
        logger.write_json("simulation", "simulation_result.json", merged.get("simulation_result", {}), step)
    elif name == "failure_analysis":
        logger.write_json("failure_analysis", "failure_analysis.json", merged.get("failure_analysis", {}), step)
    elif name == "coverage":
        logger.write_json("coverage", "coverage.json", merged.get("coverage", {}), step)
    elif name == "red_team":
        logger.write_json("red_team", "red_team.json", merged.get("red_team_results", []), step)
    elif name == "mutation":
        mutations = merged.get("mutation_results", [])
        logger.write_json("mutation", "mutations.json", mutations, step)
        for i, m in enumerate(mutations, 1):
            logger.write_code("mutation", f"mutation_{i:03d}.v", m.get("mutated_rtl", ""), step)
    elif name == "formal":
        logger.write_json("formal", "formal.json", merged.get("formal_result", {}), step)
    elif name == "judge":
        logger.write_json("judge", "judge.json", merged.get("judge_result", {}), step)

def build_workflow():
    graph = StateGraph(VerificationState)
    for name in AGENTS:
        graph.add_node(name, _node(name))

    graph.add_edge(START, "rtl_analysis")
    graph.add_edge("rtl_analysis", "planning")
    graph.add_edge("planning", "test_generation")
    graph.add_edge("test_generation", "testbench_generation")
    graph.add_edge("testbench_generation", "simulation")

    graph.add_conditional_edges("simulation", route_after_simulation, {
        "coverage": "coverage",
        "failure_analysis": "failure_analysis",
    })
    graph.add_conditional_edges("failure_analysis", route_after_failure, {
        "test_generation": "test_generation",
        "end": END,
    })
    graph.add_conditional_edges("coverage", route_after_coverage, {
        "red_team": "red_team",
        "test_generation": "test_generation",
    })
    graph.add_conditional_edges("red_team", route_after_red_team, {
        "mutation": "mutation",
        "formal": "formal",
        "judge": "judge",
    })
    graph.add_conditional_edges("mutation", route_after_mutation, {
        "formal": "formal",
        "judge": "judge",
    })
    graph.add_edge("formal", "judge")
    graph.add_conditional_edges("judge", route_after_judge, {
        "test_generation": "test_generation",
        "end": END,
    })
    return graph.compile()

workflow = build_workflow()

def run_workflow(state: VerificationState):
    from observability.run_manager import create_verification_run
    if not state.get("run_id"):
        run_id, run_dir, logger = create_verification_run({
            "project": "PragyanAI SiliconAI",
            "workflow": "agentic_rtl_verification",
        })
        state["run_id"] = run_id
        state["run_dir"] = str(run_dir)
        state["_activity_logger"] = logger

    logger = state.get("_activity_logger")
    result = workflow.invoke(state)

    if logger:
        logger.write_json("judge", "verification_summary.json", {
            "run_id": result.get("run_id"),
            "verdict": result.get("final_verdict"),
            "verification_score": result.get("verification_score"),
            "coverage": result.get("coverage"),
            "mutation_score": result.get("mutation_score"),
        }, 11)
    return result
