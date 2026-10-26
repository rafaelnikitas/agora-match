"""Validate model wiring before any paid Azure resources are provisioned."""
import argparse
import json
import re
from pathlib import Path


def validate(path):
    values = {k:v['value'] for k,v in json.loads(Path(path).read_text())['parameters'].items()}
    name = values.get('environmentName','demo')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,15}',name):
        raise ValueError('environmentName must be a lowercase slug of 1–16 characters')
    models = values.get('modelDeployments',[])
    names = [m['name'] for m in models]
    if not names or len(names) != len(set(names)):
        raise ValueError('Provide at least one model deployment with unique names')
    for model in models:
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',model['name']) or not 1 <= model['capacity'] <= 100:
            raise ValueError('Invalid model deployment name or capacity')
        if not model.get('modelName') or not model.get('modelVersion'):
            raise ValueError('Pin model name and version')
    for role in ('readerDeployment','writerDeployment','reviewerDeployment'):
        if values.get(role,'agora-chat') not in names:
            raise ValueError(f'{role} does not name a provisioned model deployment')
    reasoning = {x.strip() for x in values.get('reasoningDeployments','agora-chat').split(',') if x.strip()}
    if not reasoning.issubset(names):
        raise ValueError('Reasoning model profile references an unknown deployment')
    minimum, maximum = values.get('minReplicas',0), values.get('maxReplicas',2)
    if not 0 <= minimum <= 1 or not 1 <= maximum <= 3 or minimum > maximum:
        raise ValueError('Invalid replica bounds')
    return {'valid':True,'deployments':len(models),'roles':3,'max_replicas':maximum}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parameters',default='infra/parameters.example.json')
    args = parser.parse_args()
    print(json.dumps(validate(args.parameters)))
