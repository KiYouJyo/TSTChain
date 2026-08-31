#!/usr/bin/env python3
"""TST Chain v0.4 Provenance conformance checks."""
from __future__ import annotations
import json,sys
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from v0_2_conformance import canonical_bytes,sha256_hex
ROOT=Path(__file__).resolve().parents[1]; SD=ROOT/'schemas/v0.4'; ED=ROOT/'examples/v0.4'
M={
'plan-artifact-referencecity.json':'plan-artifact.schema.json','plan-version-v1.json':'plan-version.schema.json','plan-version-v2.json':'plan-version.schema.json','amendment-edge-v2-v1.json':'provenance-edge.schema.json','supersede-edge-v2-v1.json':'provenance-edge.schema.json','historical-verification-s009.json':'historical-verification.schema.json'}
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def validate(sn,v):
 s=load(SD/sn); Draft202012Validator.check_schema(s); Draft202012Validator(s,format_checker=FormatChecker()).validate(v)
def check_examples():
 for f,s in M.items(): validate(s,load(ED/f))
def check_version_graph():
 artifact=load(ED/'plan-artifact-referencecity.json'); versions=[load(ED/'plan-version-v1.json'),load(ED/'plan-version-v2.json')]; edges=[load(ED/'amendment-edge-v2-v1.json'),load(ED/'supersede-edge-v2-v1.json')]
 by={v['plan_version_id']:v for v in versions}; assert artifact['current_version_ref'] in by
 nums=sorted(int(v['version']) for v in versions); assert nums==[1,2]
 for v in versions:
  assert v['plan_artifact_id']==artifact['plan_artifact_id']
  prev=v['previous_version_ref']
  if prev is not None:
   assert prev in by; assert int(by[prev]['version'])<int(v['version'])
 for e in edges:
  assert e['from_ref'] in by and e['to_ref'] in by and e['from_ref']!=e['to_ref']
 # cycle detection on version provenance
 graph={k:[] for k in by}
 for e in edges: graph[e['from_ref']].append(e['to_ref'])
 def visit(node,stack,done):
  if node in stack: raise AssertionError('provenance cycle')
  if node in done: return
  stack.add(node)
  for nxt in graph[node]: visit(nxt,stack,done)
  stack.remove(node); done.add(node)
 done=set()
 for node in graph: visit(node,set(),done)
 assert versions[0]['content_digest']['canonicalization']=='RFC8785-JCS'
 assert len(sha256_hex(artifact))==64 and canonical_bytes(artifact)==canonical_bytes(json.loads(json.dumps(artifact)))
def check_history():
 verification=load(ED/'historical-verification-s009.json'); v1=load(ED/'plan-version-v1.json'); edges={load(ED/'amendment-edge-v2-v1.json')['edge_id'],load(ED/'supersede-edge-v2-v1.json')['edge_id']}
 assert verification['exists'] is True and verification['provenance_intact'] is True
 assert verification['expected_content_digest']==v1['content_digest']; assert verification['content_digest_match'] is True
 assert set(verification['proof_edge_refs'])==edges
 assert verification['status']==v1['status']
def main():
 check_examples(); check_version_graph(); check_history(); print('TST Chain v0.4 Provenance conformance: PASS'); print('  ReferenceCity S001/S002: PlanArtifact + version/amendment model available'); print('  ReferenceCity S009: historical digest/provenance verification available'); return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as exc: print(f'TST Chain v0.4 conformance: FAIL: {exc}',file=sys.stderr); raise
