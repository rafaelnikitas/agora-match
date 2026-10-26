"""A real live-Azure acceptance gate. Template fallback cannot pass --require-ai."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlsplit


def run(url, require_ai=False):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' and parsed.hostname not in {'localhost','127.0.0.1'}:
        raise ValueError('Use HTTPS for a deployed app')
    url = url.rstrip('/')
    with urllib.request.urlopen(url+'/health/ready',timeout=30) as response:
        health = json.load(response)
    if health.get('ready') is not True:
        raise RuntimeError('Application is not ready')
    # A unique reference prevents a previous cached answer from masquerading as a
    # fresh provider/identity check. It is not part of the football evidence.
    question = 'How many of the last attacks ended in crosses?'
    if require_ai:
        question += ' Acceptance reference: ' + uuid.uuid4().hex
    body = {'question':question,'persona':'analyst','game_id':'northbridge-eastport','player_id':'N8','simplify':True}
    start = time.monotonic()
    request = urllib.request.Request(url+'/api/ask',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=90) as response:
        answer = json.load(response)
    if not answer.get('facts'):
        raise RuntimeError('The answer did not preserve its evidence')
    if require_ai and not answer.get('model_used'):
        raise RuntimeError('Real AI gate failed: '+answer.get('reason','unknown'))
    stages = [row['stage'] for row in answer.get('agent_trace',[])]
    if require_ai and stages != ['match_analyst','audience_narrator','evidence_reviewer']:
        raise RuntimeError('Expected all three configured model roles to complete')
    return {'passed':True,'model_used':answer.get('model_used',False),'stages':stages,'evidence_count':len(answer['facts']),'latency_ms':round((time.monotonic()-start)*1000)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--require-ai',action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.url,args.require_ai)))
    except (ValueError,RuntimeError,urllib.error.URLError) as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
