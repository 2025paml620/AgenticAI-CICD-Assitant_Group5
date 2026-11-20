"""Fixture access only: no shell, network, writes, or evaluator answer keys."""
from langchain_core.tools import tool
from scenario_loader import agent_input


@tool
def get_pipeline_status(scenario_id: str) -> dict:
    """Read pipeline stage status, readiness checks and deployment logs."""
    s = agent_input(scenario_id)
    return {key: s.get(key) for key in ('pipeline_status', 'health_checks', 'deployment_logs')}


@tool
def read_build_logs(scenario_id: str) -> dict:
    """Read build/test/deployment logs and dependency resolution evidence."""
    s = agent_input(scenario_id)
    return {key: s.get(key) for key in ('build_logs', 'dependencies')}


@tool
def get_test_results(scenario_id: str) -> dict:
    """Read test counts, failed tests and test report availability."""
    return {'test_results': agent_input(scenario_id).get('test_results')}


@tool
def get_recent_change_summary(scenario_id: str) -> dict:
    """Read recent commit summaries; an empty list means unavailable evidence."""
    changes = agent_input(scenario_id).get('recent_changes') or []
    if changes:
        return {'recent_changes': changes}
    # State the absence explicitly so "no data" is reported as citable evidence
    # rather than an empty payload that the agent rejects as a failed call.
    return {'recent_changes': [], 'notes': 'No recent-change information available for this run.'}


PIPELINE_TOOLS = [get_pipeline_status, read_build_logs, get_test_results, get_recent_change_summary]
