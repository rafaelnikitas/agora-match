import json
import unittest
from fastapi.testclient import TestClient
from agora_match.acceptance import run_checks
from agora_match.api import create_app
from agora_match.catalog import build_catalog
from agora_match.narrator import FoundryNarrator
from agora_match.config import FoundrySettings
from agora_match.projection import project_game


class AccuracyTests(unittest.TestCase):
    def test_independent_acceptance_examples(self):
        report=run_checks()
        self.assertEqual([r for r in report['checks'] if not r['passed']],[])

    def test_api_and_model_boundary_receive_the_selected_time(self):
        catalog=build_catalog()
        class RecordingNarrator(FoundryNarrator):
            def answer(self,q,role,grounded,simplify=False):
                self.observed=grounded
                return grounded
        model=RecordingNarrator(FoundrySettings())
        with TestClient(create_app(narrator=model,catalog=catalog)) as c:
            body={'question':'How is Luca Gray playing?','game_id':'northbridge-eastport','analysis_time_seconds':1200,'language':'el'}
            r=c.post('/api/ask',json=body)
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json()['analysis_context']['seconds'],1200)
            self.assertEqual(model.observed['language'],'el')
            self.assertEqual(model.observed['facts'][0]['value'],0)
            self.assertEqual(c.post('/api/ask',json=body|{'analysis_time_seconds':9999}).status_code,422)
            self.assertEqual(c.get('/api/analysis?analysis_time_seconds=-1').status_code,400)
            self.assertEqual(c.post('/api/ask',json=body|{'language':'invalid'}).status_code,422)

    def test_empty_prefixes_and_partial_windows_are_usable(self):
        g=build_catalog()['games'][0]
        for t in (0,1,1200,3299,3300,4199,4200):
            view=project_game(g,t)
            self.assertTrue(view['insights'])
            self.assertEqual(len(view['player_profiles']),22)
            self.assertEqual(view['analysis_context']['seconds'],t)

    def test_tied_zero_metrics_share_rank_one(self):
        g=project_game(build_catalog()['games'][0],0)
        self.assertEqual({p['ranks']['goals'] for p in g['player_profiles']},{1})

    def test_missing_sensor_sample_is_not_a_zero_effort_window(self):
        from copy import deepcopy
        g=deepcopy(build_catalog()['games'][0])
        g['tracking_snapshots']=[s for s in g['tracking_snapshots'] if s['minute']!=65]
        board=project_game(g)['match_intelligence']['coach_board']['players']
        self.assertTrue(all(r['high_speed_sample_change_pct'] is None for r in board))
        self.assertFalse(any(i['id']=='load-output-drop' for i in project_game(g)['insights']))

    def test_missing_paired_frame_is_not_filled_with_another_minute(self):
        from copy import deepcopy
        g=deepcopy(build_catalog()['games'][0])
        g['tracking_snapshots']=[s for s in g['tracking_snapshots'] if s['minute']!=55]
        self.assertTrue(all(r['paired_spacing'] is None for r in project_game(g)['match_intelligence']['coach_board']['players']))
