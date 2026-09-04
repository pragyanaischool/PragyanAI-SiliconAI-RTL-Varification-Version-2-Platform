from config.settings import MAX_TEST_SCENARIOS, MAX_TEST_CASES, MAX_TESTBENCH_LINES
from core.state import create_initial_state

def test_settings():
    assert MAX_TEST_SCENARIOS >= 1
    assert MAX_TEST_CASES >= MAX_TEST_SCENARIOS
    assert MAX_TESTBENCH_LINES >= 1

def test_initial_state():
    state = create_initial_state("module dut; endmodule")
    assert state["original_rtl"]
    assert state["current_rtl"] == state["original_rtl"]
