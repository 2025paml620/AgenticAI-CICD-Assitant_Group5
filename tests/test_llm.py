"""Member 3 unit tests; live acceptance is explicitly opt-in."""
import os
import unittest
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage
from agents.llm_agent import Diagnosis, GroundingReview, LLMAgent, contains_json_fragment
from agents.base_agent import validate_result
from scenario_loader import agent_input
from tools.pipeline_tools import PIPELINE_TOOLS


def fake_model(sid='A', category='unit_test'):
    calls = [{'id': str(i), 'name': t.name, 'args': {'scenario_id': sid}}
             for i, t in enumerate(PIPELINE_TOOLS)]
    model = Mock()
    model.bind_tools.return_value.invoke.side_effect = [AIMessage(content='', tool_calls=calls),
                                                       AIMessage(content='Ready')]
    model.with_structured_output.return_value.invoke.return_value = Diagnosis(
        failure_category=category,
        supporting_evidence=[{'tool_call_id': '1', 'quote': '[build]'},
                             {'tool_call_id': '3', 'quote': agent_input(sid)['recent_changes'][0]}],
        likely_cause='Likely regression in the recently changed code.',
        recommended_step='Review the failed tests and the recent code changes.',
        reasoning='The returned logs and recent changes support further investigation.',
        verification_checklist=['Run affected tests after review.', 'Check the full pipeline status.'])
    diagnosis = model.with_structured_output.return_value.invoke.return_value
    model.with_structured_output.return_value.invoke.side_effect = [
        diagnosis, GroundingReview(supported=True, explanation='Supported by the returned evidence.')]
    return model


class LLMTests(unittest.TestCase):
    def test_json_projection_checks_values(self):
        output = {'test_results': {'failed': 2, 'passed': 18}}
        self.assertTrue(contains_json_fragment({'failed': 2}, output))
        self.assertFalse(contains_json_fragment({'failed': 99}, output))
        self.assertFalse(contains_json_fragment({'invented': 2}, output))
        self.assertFalse(contains_json_fragment({}, output))

    def test_tools_do_not_leak_answer_keys_or_mutate_fixtures(self):
        before = agent_input('A')
        for tool in PIPELINE_TOOLS:
            result = tool.invoke({'scenario_id': 'A'})
            self.assertNotIn('expected', result)
            self.assertNotIn('failure_type', result)
            result.clear()
        self.assertEqual(before, agent_input('A'))

    def test_real_dispatch_and_round_trip(self):
        model = fake_model()
        result = LLMAgent(model=model).decide({'id': 'A'})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(result['tool_calls']), 4)
        self.assertEqual(validate_result(result), [])
        messages = model.bind_tools.return_value.invoke.call_args_list[0].args[0]
        self.assertEqual(sum(m.type == 'tool' for m in messages), 4)

    def test_unsupported_quote_is_rejected(self):
        model = fake_model()
        model.with_structured_output.return_value.invoke.return_value.supporting_evidence[0].quote = 'invented evidence'
        self.assertEqual(LLMAgent(model=model).decide({'id': 'A'})['status'], 'error')

    def test_category_contradiction_is_rejected(self):
        self.assertEqual(LLMAgent(model=fake_model(category='deployment')).decide({'id': 'A'})['status'], 'error')
        self.assertEqual(LLMAgent(model=fake_model(category='unknown')).decide({'id': 'A'})['status'], 'error')

    def test_unavailable_or_timeout(self):
        for exc in (ConnectionError('offline'), TimeoutError('timed out')):
            model = Mock()
            model.bind_tools.return_value.invoke.side_effect = exc
            result = LLMAgent(model=model).decide({'id': 'A'})
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['tools_used'], [])

    def test_no_calls_fails_compatibility(self):
        model = Mock()
        model.bind_tools.return_value.invoke.return_value = AIMessage(content='I know the answer')
        self.assertEqual(LLMAgent(model=model, max_rounds=2).decide({'id': 'A'})['status'], 'error')

    def test_empty_evidence_is_recorded_as_error(self):
        empty_tool = Mock(name='empty')
        empty_tool.name = 'get_pipeline_status'
        empty_tool.invoke.return_value = {}
        model = Mock()
        model.bind_tools.return_value.invoke.return_value = AIMessage(content='', tool_calls=[
            {'id': 'empty', 'name': empty_tool.name, 'args': {'scenario_id': 'A'}}])
        with patch('agents.llm_agent.PIPELINE_TOOLS', [empty_tool]):
            result = LLMAgent(model=model, max_rounds=1).decide({'id': 'A'})
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['tool_calls'][0]['error'], 'Empty evidence')

    def test_malformed_tool_response(self):
        model = Mock()
        model.bind_tools.return_value.invoke.return_value = AIMessage(content='', invalid_tool_calls=[
            {'id': 'bad', 'name': 'get_pipeline_status', 'args': '{', 'error': 'invalid JSON'}])
        self.assertIn('Malformed', LLMAgent(model=model).decide({'id': 'A'})['reasoning'])

    def test_wrong_scenario_and_write_tool_rejected(self):
        for name, args in [('deploy', {'scenario_id': 'A'}),
                           ('get_pipeline_status', {'scenario_id': 'B'})]:
            model = Mock()
            model.bind_tools.return_value.invoke.return_value = AIMessage(content='', tool_calls=[
                {'id': 'bad', 'name': name, 'args': args}])
            result = LLMAgent(model=model, max_rounds=1).decide({'id': 'A'})
            self.assertEqual(result['tools_used'], [])
            self.assertIn('error', result['tool_calls'][0])

    def test_malformed_final(self):
        model = fake_model()
        model.with_structured_output.return_value.invoke.side_effect = [{'failure_category': 'unit_test'}]
        self.assertEqual(LLMAgent(model=model).decide({'id': 'A'})['status'], 'error')

    def test_unsupported_recommendation_review_rejected(self):
        model = fake_model()
        diagnosis = model.with_structured_output.return_value.invoke.return_value
        model.with_structured_output.return_value.invoke.side_effect = [
            diagnosis, GroundingReview(supported=False, explanation='Unsupported recommendation')]
        self.assertEqual(LLMAgent(model=model).decide({'id': 'A'})['status'], 'error')

    def test_bad_citation_can_be_corrected(self):
        model = fake_model()
        good = model.with_structured_output.return_value.invoke.return_value
        bad = good.model_copy(deep=True)
        bad.supporting_evidence[0].quote = 'fabricated quote'
        model.with_structured_output.return_value.invoke.side_effect = [
            bad, good, GroundingReview(supported=True, explanation='Corrected citations are supported.')]
        result = LLMAgent(model=model).decide({'id': 'A'})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(result['tool_calls']), 4)

    @unittest.skipUnless(os.getenv('RUN_OLLAMA_TESTS') == '1', 'Set RUN_OLLAMA_TESTS=1 for local model acceptance')
    def test_live_primary_scenarios(self):
        for sid, category in [('A', 'unit_test'), ('B', 'dependency'), ('C', 'deployment')]:
            with self.subTest(scenario=sid):
                result = LLMAgent().decide({'id': sid})
                self.assertEqual(result['status'], 'ok', result['reasoning'])
                self.assertEqual(result['failure_category'], category)
                self.assertGreaterEqual(len(set(result['tools_used'])), 2)


if __name__ == '__main__':
    unittest.main()
