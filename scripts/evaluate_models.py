"""Live single/three-role comparison. Never labels local or mocked results AI accuracy."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agora_match.catalog import build_catalog
from agora_match.chat import answer_question
from agora_match.config import FoundrySettings, AppSettings
from agora_match.narrator import FoundryNarrator
from agora_match.projection import project_game

CASES=[
    {"id":"corner","question":"Why is this corner important?","seconds":4062,"role":"fan"},
    {"id":"attacks","question":"How many attacks ended in crosses?","seconds":4338,"role":"analyst"},
    {"id":"early-cases","question":"Show all fullback vs winger cases","seconds":1200,"role":"analyst"},
    {"id":"load","question":"Show Milo Vale's running output","seconds":4338,"role":"coach"},
    {"id":"player-history","question":"Compare Luca Gray's xG with his last five matches","seconds":4338,"role":"analyst"},
    {"id":"greek","question":"Why is this corner important?","seconds":4062,"role":"fan","language":"el"},
]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-live',action='store_true',help='Explicitly permit paid provider calls with configured identity')
    p.add_argument('--mode',choices=['single','three-role','compare'],default='compare')
    p.add_argument('--pause-seconds',type=float,default=8)
    p.add_argument('--output',default='build/live-model-evaluation.json')
    args=p.parse_args()
    config=FoundrySettings.from_env()
    report={'status':'not_run','source':'live_azure_only','qualitative_accuracy':'pending human review','results':[]}
    if not args.run_live or not config.configured:
        report['reason']='Explicit --run-live and valid Foundry configuration are required.'
    elif args.mode in {'three-role','compare'} and not config.reader:
        report['reason']='Configure reader, writer and reviewer deployment names.'
    else:
        game=build_catalog()['games'][0]
        modes=['single','three-role'] if args.mode=='compare' else [args.mode]
        for mode in modes:
            selected=replace(config,deployment=config.writer or config.deployment,reader='',writer='',reviewer='') if mode=='single' else config
            model=FoundryNarrator(selected,app_settings=AppSettings(cache_seconds=0))
            try:
                for case in CASES:
                    grounded=answer_question(project_game(game,case['seconds']),case['question'],case['role'],'N8',True)
                    grounded['language']=case.get('language','en')
                    start=time.monotonic()
                    answer=model.answer(case['question'],case['role'],grounded,True)
                    report['results'].append({'case':case['id'],'mode':mode,'language':grounded['language'],
                        'model_used':answer['model_used'],'latency_ms':round((time.monotonic()-start)*1000),
                        'token_usage':sum(s.get('total_tokens',0) for s in answer.get('agent_trace',[])),
                        'agent_trace':answer.get('agent_trace',[]),
                        'reason':answer.get('reason'),'output':answer['text'],'facts':grounded['facts'],
                        'claim_contract_passed':answer.get('validation',{}).get('fact_values')=='rendered_verbatim',
                        'reviewer_approved':answer.get('validation',{}).get('reviewer_approved',False),
                        'human_review':{'supported_qualitative_claims':None,'appropriate_uncertainty':None,'useful_for_role':None,'language_correct':None}})
                    if args.pause_seconds: time.sleep(args.pause_seconds)
            finally: model.close()
        report['status']='completed' if all(r['model_used'] for r in report['results']) else 'completed_with_fallbacks'
        report['summary']={mode:{'responses':len(rows:=[r for r in report['results'] if r['mode']==mode]),
            'real_model_responses':sum(r['model_used'] for r in rows),'median_latency_ms':statistics.median(r['latency_ms'] for r in rows),
            'total_tokens':sum(r['token_usage'] for r in rows)} for mode in modes}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False))
    return 0 if report['status']=='completed' else 2


if __name__=='__main__': raise SystemExit(main())
