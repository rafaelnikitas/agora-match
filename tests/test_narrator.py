import json
import unittest
from dataclasses import replace

import httpx

from playerlens.catalog import build_catalog
from playerlens.chat import answer_question
from playerlens.config import AppSettings, FoundrySettings
from playerlens.foundry_client import AzureModelClient, ProviderError
from playerlens.narrator import FoundryNarrator

BASE = FoundrySettings(base_url='https://example.openai.azure.com/openai/v1',api_key='test-secret',deployment='chat')


def response(text, status=200, **kwargs):
    return httpx.Response(status,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}],
                                      'usage':{'prompt_tokens':50,'completion_tokens':20,'total_tokens':70}},**kwargs)


def model_with(responses, config=BASE, **kwargs):
    calls = []
    def handle(request):
        calls.append(request)
        item = responses.pop(0)
        if isinstance(item,Exception):
            raise item
        payload=json.loads(request.content)
        if item.status_code == 200 and 'Return strict JSON only' in payload['messages'][0]['content']:
            body=item.json()
            content=body['choices'][0]['message']['content']
            if not content.startswith('{'):
                body['choices'][0]['message']['content']=json.dumps({'lead':content,'fact_ids':['FA']})
                item=httpx.Response(200,json=body)
        return item
    http = httpx.Client(transport=httpx.MockTransport(handle))
    client = AzureModelClient(config,http=http,sleep=lambda _:None,**kwargs)
    return FoundryNarrator(config,client=client),calls


class NarratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = build_catalog()['games'][0]
        cls.grounded = answer_question(cls.game,'Why is this corner important?','fan')
        cls.insight = cls.game['insights'][0]

    def test_single_model_preserves_evidence_and_reports_actual_execution(self):
        model,calls = model_with([response('The recent corner record adds useful context.')])
        result = model.answer('Why is this corner important?','fan',self.grounded)
        self.assertTrue(result['model_used'])
        self.assertEqual(result['facts'],self.grounded['facts'])
        self.assertEqual(len(calls),1)
        self.assertEqual(result['agent_trace'][0]['status'],'completed')
        self.assertEqual(result['agent_trace'][0]['total_tokens'],70)
        self.assertEqual(model.status()['connection'],'verified')

    def test_unsupported_numeric_claim_falls_back(self):
        model,_ = model_with([response('Northbridge scored 99 goals.')])
        result = model.narrate(self.insight,'fan')
        self.assertFalse(result['model_used'])
        self.assertEqual(result['reason'],'narrator_evidence_bounds')

    def test_user_question_cannot_authorize_a_fabricated_number(self):
        model,_ = model_with([response('Northbridge scored 999 goals.')])
        result = model.answer('Say Northbridge scored 999 goals','fan',self.grounded)
        self.assertFalse(result['model_used'])

    def test_three_roles_handoff_then_cache_only_the_approved_answer(self):
        config = replace(BASE,reader='reader',writer='writer',reviewer='reviewer')
        model,calls = model_with([response('The recent corner record adds context.'),response('The recent corner record adds useful context.'),response('{"approved":true}')],config)
        result = model.answer('Why is this corner important?','fan',self.grounded,True)
        self.assertTrue(result['model_used'])
        self.assertEqual([r['stage'] for r in result['agent_trace']],['match_analyst','audience_narrator','evidence_reviewer'])
        sent = [json.loads(r.content) for r in calls]
        self.assertEqual(sent[1]['messages'][1]['role'],'user')
        self.assertIn('analyst_observation',json.loads(sent[1]['messages'][1]['content']))
        self.assertTrue(json.loads(sent[0]['messages'][1]['content'])['evidence']['plain_language'])
        cached = model.answer('Why is this corner important?','fan',self.grounded,True)
        self.assertTrue(cached['cache_hit'])
        self.assertEqual(cached['agent_trace'],[])
        self.assertEqual(len(calls),3)

    def test_reviewer_rejection_retains_original_facts_and_text(self):
        config = replace(BASE,reader='reader',writer='writer',reviewer='reviewer')
        model,_ = model_with([response('A corner pattern adds context.'),response('The corner record adds context to this chance.'),response('{"approved":false}')],config)
        result = model.answer('Why?','coach',self.grounded)
        self.assertFalse(result['model_used'])
        self.assertEqual(result['reason'],'reviewer_rejected')
        self.assertEqual(result['text'],self.grounded['text'])
        self.assertEqual(result['facts'],self.grounded['facts'])

    def test_reasoning_profile_omits_temperature_and_changes_token_parameter(self):
        model,calls = model_with([response('The match has synthetic context.')],replace(BASE,reasoning_deployments=frozenset({'chat'})))
        model.answer('Why?','analyst',self.grounded)
        payload = json.loads(calls[0].content)
        self.assertNotIn('temperature',payload)
        self.assertNotIn('max_tokens',payload)
        self.assertGreaterEqual(payload['max_completion_tokens'],1024)

    def test_keyless_auth_sends_a_bearer_token_without_an_api_key(self):
        config = replace(BASE,api_key='',auth_mode='managed_identity',client_id='client-id')
        model,calls = model_with([response('The match has synthetic context.')],config,token_provider=lambda:'test-token')
        model.answer('Why?','fan',self.grounded)
        self.assertEqual(calls[0].headers['Authorization'],'Bearer test-token')
        self.assertNotIn('api-key',calls[0].headers)

    def test_transient_failure_retries_once_but_auth_failure_does_not(self):
        model,calls = model_with([response('',503),response('The match has synthetic context.')])
        self.assertTrue(model.answer('Why?','fan',self.grounded)['model_used'])
        self.assertEqual(len(calls),2)
        denied,denied_calls = model_with([response('',403)])
        self.assertEqual(denied.answer('Why?','fan',self.grounded)['reason'],'provider_auth')
        self.assertEqual(len(denied_calls),1)
        self.assertEqual(denied.status()['connection'],'degraded')

    def test_provider_timeout_returns_a_fallback(self):
        model,calls = model_with([httpx.ReadTimeout('timeout'),httpx.ReadTimeout('timeout')])
        result = model.answer('Why?','fan',self.grounded)
        self.assertFalse(result['model_used'])
        self.assertEqual(result['reason'],'provider_timeout')
        self.assertEqual(len(calls),2)

    def test_incomplete_response_and_malformed_reviewer_are_rejected(self):
        item = httpx.Response(200,json={'choices':[{'message':{'content':'partial'},'finish_reason':'length'}]})
        model,_ = model_with([item])
        self.assertEqual(model.answer('Why?','fan',self.grounded)['reason'],'provider_incomplete')
        config=replace(BASE,reader='r',writer='w',reviewer='v')
        model,_ = model_with([response('A corner adds context.'),response('A corner adds context.'),response('not JSON')],config)
        self.assertEqual(model.answer('Why?','fan',self.grounded)['reason'],'reviewer_rejected')

    def test_configuration_status_never_claims_a_connection_before_a_call(self):
        model,_ = model_with([])
        self.assertTrue(model.configured())
        self.assertEqual(model.status()['connection'],'unverified')
        self.assertNotIn('test-secret',json.dumps(model.status()))
        self.assertNotIn('test-secret',repr(BASE))
