"""Complete Linear LangGraph Workflow Orchestration with Formal SVA Assertion Generation."""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from agents.rtl_analyzer import RTLAnalyzerAgent
from agents.verification_planner import VerificationPlannerAgent
from agents.test_generator import TestGeneratorAgent
from agents.testbench_generator import TestbenchGeneratorAgent
from agents.simulator_agent import SimulatorAgent
from agents.failure_analyzer import FailureAnalyzerAgent
from agents.rtl_repair_agent import RTLRepairAgent
from agents.coverage_agent import CoverageAgent
from agents.red_team_agent import RedTeamAgent
from agents.mutation_agent import MutationAgent
from agents.assertion_agent import AssertionAgent
from agents.verification_judge import VerificationJudgeAgent


def run_node(agent_instance):
    """Wrapper function to execute an agent instance within a LangGraph node."""
    def node_func(state):
        return agent_instance.execute(state)
    return node_func


def create_verification_workflow():
    """Constructs the full 12-stage sequential agentic verification pipeline including formal SVA."""
    workflow = StateGraph(dict)

    # 1. Instantiate All Agents
    rtl_analyzer = RTLAnalyzerAgent()
    planner = VerificationPlannerAgent()
    test_gen = TestGeneratorAgent()
    tb_gen = TestbenchGeneratorAgent()
    simulator = SimulatorAgent()
    failure_analyzer = FailureAnalyzerAgent()
    rtl_repair = RTLRepairAgent()
    coverage = CoverageAgent()
    red_team = RedTeamAgent()
    mutation = MutationAgent()
    assertion_agent = AssertionAgent()
    judge = VerificationJudgeAgent()

    # 2. Register Nodes in the Graph
    workflow.add_node("rtl_analyzer", run_node(rtl_analyzer))
    workflow.add_node("verification_planner", run_node(planner))
    workflow.add_node("test_generator", run_node(test_gen))
    workflow.add_node("testbench_generator", run_node(tb_gen))
    workflow.add_node("simulator_agent", run_node(simulator))
    workflow.add_node("failure_analyzer", run_node(failure_analyzer))
    workflow.add_node("rtl_repair", run_node(rtl_repair))
    workflow.add_node("coverage_agent", run_node(coverage))
    workflow.add_node("red_team_agent", run_node(red_team))
    workflow.add_node("mutation_agent", run_node(mutation))
    workflow.add_node("assertion_agent", run_node(assertion_agent))
    workflow.add_node("verification_judge", run_node(judge))

    # 3. Define Guaranteed Linear Execution Flow (Zero Skipped Nodes)
    workflow.set_entry_point("rtl_analyzer")
    workflow.add_edge("rtl_analyzer", "verification_planner")
    workflow.add_edge("verification_planner", "test_generator")
    workflow.add_edge("test_generator", "testbench_generator")
    workflow.add_edge("testbench_generator", "simulator_agent")
    workflow.add_edge("simulator_agent", "failure_analyzer")
    workflow.add_edge("failure_analyzer", "rtl_repair")
    workflow.add_edge("rtl_repair", "coverage_agent")
    workflow.add_edge("coverage_agent", "red_team_agent")
    workflow.add_edge("red_team_agent", "mutation_agent")
    workflow.add_edge("mutation_agent", "assertion_agent")
    workflow.add_edge("assertion_agent", "verification_judge")
    workflow.add_edge("verification_judge", END)

    return workflow.compile()


def run_workflow(*args, **kwargs) -> dict:
    """
    Execute the full agentic verification workflow.
    Supports both dictionary state invocation and keyword argument unpacking.
    """
    if args and isinstance(args[0], dict):
        state = args[0]
    else:
        state = dict(kwargs)

    compiled_app = create_verification_workflow()
    return compiled_app.invoke(state)


__all__ = ["create_verification_workflow", "run_workflow"]
