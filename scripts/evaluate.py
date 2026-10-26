"""Measure evidence routing, real-model/fallback rate and latency; never invent a quality score."""
import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


def evaluate(url, cases, pause=0):
    u=urlsplit(url)
    if u.scheme!='https' and u.hostname not in {'localhost','127.0.0.1'}:
        raise ValueError('Use HTTPS for a deployed app')
    rows=[]
    for case in cases:
        for role in ('fan','analyst','coach'):
            body={'question':case['question'],'game_id':case['game_id'],'persona':role,'player_id':'N8','simplify':True}
            request=urllib.request.Request(url.rstrip('/')+'/api/ask',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
            start=time.monotonic()
            try:
                with urllib.request.urlopen(request,timeout=90) as response:
                    answer=json.load(response)
            except urllib.error.URLError:
                answer={'reason':'http_or_network_failure'}
            values=[f.get('value') for f in answer.get('facts',[])]
            evidence_ok=answer.get('topic')==case['topic'] and bool(values) and all(v in values for v in case.get('expected_values',[]))
            rows.append({'persona':role,'expected_topic':case['topic'],'actual_topic':answer.get('topic'),'evidence_ok':evidence_ok,'model_used':answer.get('model_used',False),'cache_hit':answer.get('cache_hit',False),'reason':answer.get('reason'),'latency_ms':round((time.monotonic()-start)*1000)})
            if pause: time.sleep(pause)
    times=sorted(row['latency_ms'] for row in rows)
    return {'questions':len(rows),'evidence_routing_rate':sum(r['evidence_ok'] for r in rows)/len(rows),
            'real_model_rate':sum(r['model_used'] for r in rows)/len(rows),'fallback_rate':sum(not r['model_used'] for r in rows)/len(rows),
            'p50_latency_ms':statistics.median(times),'p95_latency_ms':times[max(0,round(.95*len(times))-1)],
            'note':'Evidence routing checks known facts; it is not a semantic groundedness or coaching-quality score.','results':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True)
    p.add_argument('--cases',default=str(Path(__file__).with_name('evaluation-cases.json')))
    p.add_argument('--pause-seconds',type=float,default=0)
    p.add_argument('--require-ai',action='store_true')
    p.add_argument('--output',default='build/evaluation.json')
    args=p.parse_args()
    report=evaluate(args.url,json.loads(Path(args.cases).read_text()),args.pause_seconds)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
    raise SystemExit(0 if report['evidence_routing_rate']==1 and (not args.require_ai or report['real_model_rate']==1) else 1)
