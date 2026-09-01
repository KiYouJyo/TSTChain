#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'integrations/referencecity/v0.1'

def load(name):
    return json.loads((BASE/name).read_text(encoding='utf-8'))

def main():
    p=load('profile.json')
    g=load('capability-gap.json')
    assert p['referencecity_protocol_version']=='0.1'
    assert p['referencecity_core_dataset_version']=='0.1.0'
    assert p['referencecity_pin']==g['referencecity_pin']
    assert p['tstchain_current_protocol']==g['as_of_tstchain_version']=='0.7'
    assert p['canonicalization_boundary']['tst_core_profile']=='TST-C14N-JSON/0.1'
    assert p['canonicalization_boundary']['referencecity_external_content_profile']=='RFC8785-JCS'
    policy=p['ground_truth_policy']
    assert policy['adapter_input_contains_ground_truth'] is False
    assert policy['adapter_must_not_read_expected_directory'] is True
    assert policy['scoring_is_separate_process'] is True
    ss=g['scenarios']
    assert [x['scenario'] for x in ss]==[f'S{i:03d}' for i in range(1,11)]
    counts={'full':0,'partial':0,'unsupported':0}
    for item in ss:
        assert item['status'] in counts
        counts[item['status']]+=1
        if item['status']=='full':
            assert item['missing']==[] and item['target_versions']==[]
        else:
            assert item['missing'] and item['target_versions']
    assert counts==g['summary']=={'full':10,'partial':0,'unsupported':0}
    assert g['end_to_end_ready'] is True
    assert g['production_ready'] is False
    validation=g['validation']
    assert validation['adapter_ground_truth_read'] is False
    assert validation['python_versions']==['3.11','3.12','3.13']
    assert validation['passed']==validation['total']==10 and validation['all_passed'] is True
    print('TST × ReferenceCity integration profile: PASS')
    print('  as-of=0.7 full=10 partial=0 unsupported=0')
    print('  independent benchmark score=10/10; production_ready=false')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
