import json
import logging
import unittest
from dataclasses import replace
from pathlib import Path
import httpx

from fastapi.testclient import TestClient
from agora_match.api import create_app
from agora_match.catalog import build_catalog
from agora_match.config import AppSettings, FoundrySettings
from agora_match.foundry_client import Admission, ProviderError
from agora_match.narrator import FoundryNarrator
from agora_match.telemetry import OperationFormatter
from scripts.preflight import validate
from tests.test_narrator import BASE, model_with, response


class AzureRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=build_catalog()

    def client(self,**kwargs):
        narrator=FoundryNarrator(FoundrySettings())
        return TestClient(create_app(narrator=narrator,catalog=self.catalog,**kwargs))

    def test_existing_ui_and_both_games_work_with_production_api(self):
        with self.client() as c:
            self.assertEqual(c.get('/').status_code,200)
            self.assertEqual(c.get('/api/games').json()['games'][1]['game_id'],'harbor-redvale')
            r=c.get('/api/state?game_id=harbor-redvale&view=coach')
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json()['foundry_status']['connection'],'unconfigured')
            self.assertIn('X-Request-ID',r.headers)
            self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])

    def test_public_demo_answer_is_explicitly_marked_as_fallback(self):
        with self.client() as c:
            r=c.post('/api/ask',json={'question':'Why is this corner important?','persona':'fan'})
            self.assertEqual(r.status_code,200)
            self.assertFalse(r.json()['model_used'])
            self.assertEqual(r.json()['reason'],'foundry_not_configured')
            self.assertTrue(r.json()['facts'])

    def test_require_ai_fails_readiness_without_affecting_liveness(self):
        with self.client(settings=AppSettings(require_ai=True)) as c:
            self.assertEqual(c.get('/health/live').status_code,200)
            self.assertEqual(c.get('/health/ready').status_code,503)

    def test_api_exposes_real_role_handoffs_and_verifies_connection_after_use(self):
        config=replace(BASE,reader='reader',writer='writer',reviewer='reviewer')
        narrator,_=model_with([response('{"fact_ids":["FA"]}'),
            response('The recent attacks ended in crosses. This is a short synthetic sample.'),response('{"approved":true}')],config)
        with TestClient(create_app(narrator=narrator,catalog=self.catalog)) as c:
            self.assertEqual(c.get('/api/state').json()['foundry_status']['connection'],'unverified')
            result=c.post('/api/ask',json={'question':'How many attacks ended in crosses?','persona':'analyst'}).json()
            self.assertTrue(result['model_used'])
            self.assertEqual(len(result['agent_trace']),3)
            self.assertEqual(result['foundry_status']['connection'],'verified')

    def test_validation_guards_missing_ids_large_bodies_and_unknown_fields(self):
        with self.client() as c:
            self.assertEqual(c.post('/api/ask',json={'question':'x','persona':'referee'}).status_code,422)
            self.assertEqual(c.post('/api/ask',json={'question':'x','game_id':'missing'}).status_code,404)
            self.assertEqual(c.post('/api/ask',json={'question':'x','player_id':'missing'}).status_code,404)
            self.assertEqual(c.post('/api/ask',json={'question':'x','deployment':'arbitrary'}).status_code,422)
            self.assertEqual(c.post('/api/ask',content=b'x'*16001,headers={'Content-Type':'application/json'}).status_code,413)
            self.assertEqual(c.post('/api/ask',content='not JSON',headers={'Content-Type':'application/json'}).status_code,422)

    def test_cross_origin_rejected_but_tls_termination_same_host_allowed(self):
        with self.client() as c:
            body={'question':'Why?'}
            self.assertEqual(c.post('/api/ask',json=body,headers={'Origin':'https://evil.example'}).status_code,403)
            self.assertEqual(c.post('/api/ask',json=body,headers={'Origin':'https://testserver'}).status_code,200)
            self.assertEqual(c.get('/',headers={'Host':'evil.example'}).status_code,400)

    def test_replica_request_limit_is_enforced(self):
        with self.client(settings=AppSettings(api_requests_per_minute=1)) as c:
            self.assertEqual(c.post('/api/ask',json={'question':'Why?'}).status_code,200)
            self.assertEqual(c.post('/api/ask',json={'question':'Why?'}).status_code,429)
            self.assertEqual(c.get('/health/live').status_code,200)

    def test_sse_can_resume_at_end_without_replaying_old_events(self):
        last=len(self.catalog['games'][0]['events'])-1
        with self.client() as c:
            r=c.get('/api/events/northbridge-eastport',headers={'Last-Event-ID':str(last)})
            self.assertEqual(r.status_code,200)
            self.assertIn('event: complete',r.text)
            self.assertNotIn('event: match_event',r.text)
            self.assertEqual(c.get('/api/events/northbridge-eastport?after=-2').status_code,400)
            self.assertEqual(c.get('/api/events/northbridge-eastport',headers={'Last-Event-ID':'invalid'}).status_code,400)
            self.assertEqual(c.get(f'/api/events/northbridge-eastport?after={last}&speed=4').status_code,200)
            self.assertEqual(c.get(f'/api/events/northbridge-eastport?after={last}&speed=3').status_code,400)

    def test_azure_template_parameters_reference_real_deployments(self):
        p=Path(__file__).resolve().parents[1]/'infra/parameters.example.json'
        self.assertTrue(validate(p)['valid'])
        self.assertEqual(validate(p.with_name('parameters.trial.json'))['max_replicas'],1)

    def test_operation_logs_exclude_unapproved_fields(self):
        row=logging.LogRecord('agora',logging.INFO,'',0,'model_stage',(),None)
        row.operation={'stage':'reader','api_key':'secret','question':'private question','duration_ms':20}
        output=OperationFormatter().format(row)
        self.assertNotIn('secret',output)
        self.assertNotIn('private question',output)
        self.assertEqual(json.loads(output)['duration_ms'],20)


class LimitsAndConfigurationTests(unittest.TestCase):
    def test_foundry_project_endpoint_keeps_strict_path_and_host_boundaries(self):
        base='https://agora.services.ai.azure.com'
        good=base+'/api/projects/agora-match/openai/v1'
        self.assertNotIn('invalid_azure_v1_endpoint',FoundrySettings(base_url=good).errors())
        for endpoint in [base+'/api/projects/../openai/v1',base+'/api/projects/a%2Fb/openai/v1',
                         base+'/api/projects/agora/openai/v1?key=secret',good+'#fragment',
                         good.replace('.services.ai.azure.com','.openai.azure.com'),
                         good.replace('.services.ai.azure.com','.services.ai.azure.com.evil.example')]:
            with self.subTest(endpoint=endpoint):
                self.assertIn('invalid_azure_v1_endpoint',FoundrySettings(base_url=endpoint).errors())

    def test_only_azure_https_v1_endpoints_are_allowed(self):
        for endpoint in ['http://localhost/openai/v1','https://evil.example/openai/v1','https://x.openai.azure.com:bad/openai/v1','https://user:secret@x.openai.azure.com/openai/v1']:
            self.assertIn('invalid_azure_v1_endpoint',FoundrySettings(base_url=endpoint).errors())

    def test_partial_pipeline_configuration_is_rejected(self):
        self.assertIn('incomplete_role_deployments',FoundrySettings(reader='reader').errors())

    def test_circuit_opens_then_allows_one_recovery_probe(self):
        now=[0]
        policy=Admission(FoundrySettings(circuit_failures=2,circuit_cooldown=10),clock=lambda:now[0])
        for _ in range(2):
            policy.enter();policy.leave(False)
        with self.assertRaisesRegex(ProviderError,'circuit_open'):policy.enter()
        now[0]=11
        policy.enter()
        with self.assertRaisesRegex(ProviderError,'circuit_open'):policy.enter()
        policy.leave(True)
        policy.enter();policy.leave(True)

    def test_model_rate_and_concurrency_limits_reject_extra_work(self):
        now=[0]
        policy=Admission(FoundrySettings(requests_per_minute=1,max_concurrency=1),clock=lambda:now[0])
        policy.enter()
        with self.assertRaisesRegex(ProviderError,'model_busy'):policy.enter()
        policy.leave(True)
        with self.assertRaisesRegex(ProviderError,'model_rate_limit'):policy.enter()
        now[0]=61
        policy.enter();policy.leave(True)
