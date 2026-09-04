from graph.router import route_after_simulation, route_after_coverage

def test_simulation_route():
    assert route_after_simulation({"simulation_passed": True}) == "coverage"
    assert route_after_simulation({"simulation_passed": False}) == "failure_analysis"

def test_coverage_route():
    assert route_after_coverage({"coverage": {"score": 96, "target": 95}}) == "red_team"
