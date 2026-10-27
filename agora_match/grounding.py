"""LLMs select immutable facts; application code renders their values and labels."""
import json
import re


WRITER_CONTRACT = (' Return strict JSON only: {"lead":"one short qualitative explanation without digits",'
                   '"fact_ids":["FA"]}. Select one to three supplied fact_ids. Never write numerical '
                   'statistics (including number words) in lead; the application inserts the selected facts verbatim. '
                   'Write a single sentence of at most 180 characters. Use "player matchups" instead of numerical football phrases. '
                   'Do not diagnose fatigue, infer marking assignments, predict results, or invent causes. '
                   'Use the requested output language for lead. Preserve the audience response_goal.')


def normalize_facts(facts):
    return [dict(f, fact_id=f.get("fact_id","F"+chr(65+i)),
                 label=f.get("label",f.get("metric","Evidence"))) for i,f in enumerate(facts)]


def output_schema(role, facts):
    ids = [f['fact_id'] for f in facts]
    selection = {'type':'array', 'items':{'type':'string', 'enum':ids},
                 'minItems':1, 'maxItems':min(3,len(ids))}
    properties = ({'fact_ids':selection} if role == 'match_analyst' else
                  {'approved':{'type':'boolean'}} if role == 'evidence_reviewer' else
                  {'lead':{'type':'string'}, 'fact_ids':selection})
    return {'type':'object', 'properties':properties, 'required':list(properties), 'additionalProperties':False}


def select_facts(raw, evidence):
    """A reader may rank supplied facts, but cannot introduce a new claim or ID."""
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {'fact_ids'}:
            raise ValueError()
        ids = data['fact_ids']
        if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or not all(isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError()
        facts = {f['fact_id']: f for f in evidence['facts']}
        return [facts[i] for i in ids]
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError('analyst_evidence_bounds') from None


def assemble_draft(raw, evidence, limit):
    try:
        data = json.loads(raw)
        if set(data) != {"lead","fact_ids"}:
            raise ValueError()
        lead, ids = data["lead"],data["fact_ids"]
        if not isinstance(lead,str) or not 1 <= len(lead.strip()) <= min(550,limit):
            raise ValueError()
        if re.search(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|zero|τρεις|τρία|επτά|πέντε|δύο)\b",lead,re.IGNORECASE):
            raise ValueError()
        if not isinstance(ids,list) or not 1 <= len(ids) <= 3 or not all(isinstance(i,str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError()
        facts = {f["fact_id"]:f for f in evidence["facts"]}
        selected = [facts[i] for i in ids]
        # Reject a known participant used outside the retrieved evidence context.
        verified = json.dumps({k:evidence.get(k) for k in ("verified_summary","summary","facts","caveat")},ensure_ascii=False).casefold()
        for entity in evidence.get("entities",[]):
            if entity.casefold() in lead.casefold() and entity.casefold() not in verified:
                raise ValueError()
        sentence = lead.strip()
        if sentence[-1] not in '.!?;;':
            sentence += '.'
        rendered = sentence + " " + " · ".join(str(f["label"])+": "+str(f["value"]) for f in selected)
        if len(rendered) > limit:
            raise ValueError()
        return rendered, ids
    except (ValueError,KeyError,TypeError,AttributeError):
        raise ValueError("narrator_evidence_bounds") from None
