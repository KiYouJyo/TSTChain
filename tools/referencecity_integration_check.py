#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/'integrations/referencecity/v0.1'
def load(n): return json.loads((BASE/n).read_text(encoding='utf-8'))
def main():
 p=load('profile.json'); g=load('capability-gap.json')
 assert p['referencecity_protocol_version']=='0.1' and p['referencecity_core_dataset_version']=='0.1.0'
 assert p['canonicalization_boundary']['tst_core_profile']=='TST-C14N-JSON/0.1'; assert p['canonicalization_boundary']['referencecity_external_content_profile']=='RFC8785-JCS'
 assert p['ground_truth_policy']['adapter_input_contains_ground_truth'] is False and p['ground_truth_policy']['adapter_must_not_read_expected_directory'] is True
 ss=g['scenarios']; assert [x['scenario'] for x in ss]==[f'S{i:03d}' for i in range(1,11)]
 counts={'full':0,'partial':0,'unsupported':0}
 for x in ss: assert x['status'] in counts; counts[x['status']]+=1; assert x['missing'] and x['target_versions']
 assert counts==g['summary']; assert g['end_to_end_ready'] is False
 print('TST × ReferenceCity integration profile: PASS'); print(f"  as-of={g['as_of_tstchain_version']} full={counts['full']} partial={counts['partial']} unsupported={counts['unsupported']}"); return 0
if __name__=='__main__': raise SystemExit(main())
