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
    kind = values.get('foundryKind','OpenAI')
    if kind not in {'OpenAI','AIServices'}:
        raise ValueError('foundryKind must be OpenAI or AIServices')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{1,63}',values.get('foundryProjectName','agora-match')):
        raise ValueError('Invalid Foundry project name')
    models = values.get('modelDeployments',[])
    names = [m['name'] for m in models]
    if not names or len(names) != len(set(names)):
        raise ValueError('Provide at least one model deployment with unique names')
    for model in models:
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',model['name']) or not 1 <= model['capacity'] <= 100:
            raise ValueError('Invalid model deployment name or capacity')
        if not model.get('modelName') or not model.get('modelVersion'):
            raise ValueError('Pin model name and version')
        if model.get('modelFormat','OpenAI') not in {'OpenAI','OpenAI-OSS'}:
            raise ValueError('Unsupported model format')
        if model.get('modelFormat') == 'OpenAI-OSS' and kind != 'AIServices':
            raise ValueError('OpenAI-OSS requires an AIServices Foundry project')
    for role in ('readerDeployment','writerDeployment','reviewerDeployment'):
        if values.get(role,'agora-chat') not in names:
            raise ValueError(f'{role} does not name a provisioned model deployment')
    reasoning = {x.strip() for x in values.get('reasoningDeployments','agora-chat').split(',') if x.strip()}
    if not reasoning.issubset(names):
        raise ValueError('Reasoning model profile references an unknown deployment')
    minimum, maximum = values.get('minReplicas',0), values.get('maxReplicas',2)
    if not 0 <= minimum <= 1 or not 1 <= maximum <= 3 or minimum > maximum:
        raise ValueError('Invalid replica bounds')
    if not 1 <= values.get('modelTimeoutSeconds',15) <= 60 or not 3 <= values.get('answerBudgetSeconds',45) <= 120:
        raise ValueError('Invalid model time budgets')
    return {'valid':True,'deployments':len(models),'roles':3,'max_replicas':maximum}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parameters',default='infra/parameters.example.json')
    args = parser.parse_args()
    print(json.dumps(validate(args.parameters)))
