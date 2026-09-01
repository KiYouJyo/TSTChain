#!/usr/bin/env python3
"""TST Chain v0.5 Workflow conformance and ReferenceCity protocol mappings."""
from __future__ import annotations
import copy,json,sys
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from v0_2_conformance import canonical_bytes
ROOT=Path(__file__).resolve().parents[1]; SD=ROOT/'schemas/v0.5'; ED=ROOT/'examples/v0.5'
ERRORS={
 'UNAUTHORIZED':('TST-WF-001','UNAUTHORIZED'),'INVALID_STATE_TRANSITION':('TST-WF-002','INVALID_STATE_TRANSITION'),'MISSING_DOCUMENT':('TST-WF-003','MISSING_DOCUMENT'),'MISSING_SIGNATURE':('TST-WF-004','MISSING_SIGNATURE'),'RULE_CONFLICT':('TST-WF-005','RULE_CONFLICT'),'VERSION_CONFLICT':('TST-WF-006','VERSION_CONFLICT'),'REQUEST_ID_REUSE':('TST-WF-007','REQUEST_ID_REUSE')}
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def validate(sn,v):
 s=load(SD/sn); Draft202012Validator.check_schema(s); Draft202012Validator(s,format_checker=FormatChecker()).validate(v)
def intent_key(req):
 return canonical_bytes({'workflow_id':req['workflow_id'],'instance_id':req['instance_id'],'subject_ref':req['subject_ref'],'actor_ref':req['actor_ref'],'action':req['action'],'expected_version':req['expected_version'],'payload_digest':req['payload_digest']})
class Engine:
 def __init__(self,definition,instances=None):
  self.definition=definition; self.instances={i['instance_id']:copy.deepcopy(i) for i in (instances or [])}; self.requests={}
 def transition(self,req,processed_at):
  rid=req['request_id']; key=intent_key(req)
  if rid in self.requests:
   old_key,old_result=self.requests[rid]
   if old_key==key:
    replay=copy.deepcopy(old_result); replay['idempotent_replay']=True; return replay
   return self._failure(req,'REQUEST_ID_REUSE',self.instances.get(req['instance_id']),processed_at)
  inst=self.instances.get(req['instance_id'])
  create=inst is None
  if not create:
   if req['expected_version']!=inst['current_version']:
    result=self._failure(req,'VERSION_CONFLICT',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  elif req['expected_version'] is not None:
   result=self._failure(req,'VERSION_CONFLICT',None,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  transition=next((t for t in self.definition['transitions'] if t['action']==req['action'] and t['from_state']==(None if create else inst['current_state'])),None)
  # authorization happens before transition validity, but required permission is transition-specific;
  # deny decisions are unconditionally rejected, then allow decisions are checked against matched transition.
  if req['authorization']['decision']!='allow':
   result=self._failure(req,'UNAUTHORIZED',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  if transition is None:
   result=self._failure(req,'INVALID_STATE_TRANSITION',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  granted=set(req['authorization']['granted_permissions'])
  if not set(transition['required_permissions']).issubset(granted):
   result=self._failure(req,'UNAUTHORIZED',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  if transition['document_requirement']=='at_least_one' and not req['document_refs']:
   result=self._failure(req,'MISSING_DOCUMENT',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  if transition['signature_required'] and not req['signature_refs']:
   result=self._failure(req,'MISSING_SIGNATURE',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  if transition['rule_gate']=='pass_required' and (not req['rule_evaluations'] or any(x['outcome']!='pass' for x in req['rule_evaluations'])):
   result=self._failure(req,'RULE_CONFLICT',inst,processed_at); self.requests[rid]=(key,copy.deepcopy(result)); return result
  old_state=None if create else inst['current_state']; old_version=None if create else inst['current_version']
  if transition['version_effect']=='create': new_version='1'
  elif transition['version_effect']=='increment': new_version=str(int(inst['current_version'])+1)
  else: new_version=inst['current_version']
  new_inst={'instance_id':req['instance_id'],'workflow_id':req['workflow_id'],'subject_ref':req['subject_ref'],'current_state':transition['to_state'],'current_version':new_version,'updated_at':req['occurred_at'],'schema_version':'0.5'}
  self.instances[req['instance_id']]=new_inst
  result={'result_id':'tst:wf-result:'+rid.split(':')[-1],'request_id':rid,'accepted':True,'state_changed':True,'previous_state':old_state,'current_state':new_inst['current_state'],'previous_version':old_version,'current_version':new_version,'error_code':'TST-WF-000','semantic_code':'OK','audit_event':transition['audit_event'],'idempotent_replay':False,'processed_at':processed_at,'schema_version':'0.5'}
  self.requests[rid]=(key,copy.deepcopy(result)); return result
 def _failure(self,req,kind,inst,processed_at):
  code,semantic=ERRORS[kind]; state=None if inst is None else inst['current_state']; version=None if inst is None else inst['current_version']
  return {'result_id':'tst:wf-result:'+req['request_id'].split(':')[-1],'request_id':req['request_id'],'accepted':False,'state_changed':False,'previous_state':state,'current_state':state,'previous_version':version,'current_version':version,'error_code':code,'semantic_code':semantic,'audit_event':'verify' if kind!='UNAUTHORIZED' else 'attempt_unauthorized_change','idempotent_replay':False,'processed_at':processed_at,'schema_version':'0.5'}
def req(name,action,instance,subject,expected,permission='plan.amend',decision='allow',docs=None,sigs=None,rules=None,digest='a'*64):
 return {'request_id':'tst:wf-request:'+name,'workflow_id':'tst:workflow:referencecity-plan-lifecycle','instance_id':instance,'subject_ref':subject,'actor_ref':'RC:ACTOR:001','action':action,'expected_version':expected,'occurred_at':'2030-04-01T00:00:00Z','payload_digest':{'algorithm':'sha256','digest':digest,'canonicalization':'RFC8785-JCS'},'authorization':{'decision_ref':'tst:authz:'+name,'decision':decision,'granted_permissions':[permission] if permission else []},'document_refs':docs or [],'signature_refs':sigs or [],'rule_evaluations':rules or [],'schema_version':'0.5'}
def check_scenarios(defn):
 # S001 create
 e=Engine(defn); r=e.transition(req('s001','create_plan','tst:wf-instance:s001','RC:PLAN:0003',None,'plan.create'), '2030-04-01T00:00:01Z'); assert (r['accepted'],r['current_state'],r['current_version'])==(True,'draft','1')
 # idempotent replay and request-id reuse
 replay=e.transition(req('s001','create_plan','tst:wf-instance:s001','RC:PLAN:0003',None,'plan.create'), '2030-04-01T00:00:02Z'); assert replay['idempotent_replay'] is True
 changed=req('s001','create_plan','tst:wf-instance:s001','RC:PLAN:0003',None,'plan.create',digest='b'*64); reuse=e.transition(changed,'2030-04-01T00:00:03Z'); assert reuse['semantic_code']=='REQUEST_ID_REUSE'
 # S002 authorized amendment increments version
 inst={'instance_id':'tst:wf-instance:s002','workflow_id':defn['workflow_id'],'subject_ref':'RC:PLAN:0001','current_state':'effective','current_version':'1','updated_at':'2030-03-01T00:00:00Z','schema_version':'0.5'}; e=Engine(defn,[inst]); r=e.transition(req('s002','open_amendment',inst['instance_id'],inst['subject_ref'],'1','plan.amend',rules=[{'evaluation_ref':'tst:rule-evaluation:s002','outcome':'pass'}]),'2030-04-01T00:00:01Z'); assert (r['current_state'],r['current_version'])==('amendment','2')
 # S003 review -> approve -> activate
 inst={'instance_id':'tst:wf-instance:s003','workflow_id':defn['workflow_id'],'subject_ref':'RC:PLAN:0002','current_state':'submitted','current_version':'1','updated_at':'2030-03-01T00:00:00Z','schema_version':'0.5'}; e=Engine(defn,[inst])
 for name,action,perm,state in [('s003a','review_pass','plan.review','reviewed'),('s003b','approve_plan','plan.approve','approved'),('s003c','activate_plan','plan.activate','effective')]:
  r=e.transition(req(name,action,inst['instance_id'],inst['subject_ref'],'1',perm,docs=['RC:DOC:000001'],sigs=['tst:signature:'+name]),'2030-04-01T00:00:01Z'); assert r['current_state']==state
 # S004 denied authorization
 inst={'instance_id':'tst:wf-instance:s004','workflow_id':defn['workflow_id'],'subject_ref':'RC:PLAN:0001','current_state':'effective','current_version':'1','updated_at':'2030-03-01T00:00:00Z','schema_version':'0.5'}; e=Engine(defn,[inst]); r=e.transition(req('s004','open_amendment',inst['instance_id'],inst['subject_ref'],'1','plan.amend',decision='deny',rules=[{'evaluation_ref':'x','outcome':'pass'}]),'2030-04-01T00:00:01Z'); assert r['semantic_code']=='UNAUTHORIZED' and not r['state_changed']
 # S006 rule conflict
 e=Engine(defn,[inst]); r=e.transition(req('s006','open_amendment',inst['instance_id'],inst['subject_ref'],'1','plan.amend',rules=[{'evaluation_ref':'tst:rule-evaluation:referencecity-s006','outcome':'fail'}]),'2030-04-01T00:00:01Z'); assert r['semantic_code']=='RULE_CONFLICT'
 # S008 missing signature on activate
 inst8={'instance_id':'tst:wf-instance:s008','workflow_id':defn['workflow_id'],'subject_ref':'RC:PLAN:0002','current_state':'approved','current_version':'1','updated_at':'2030-03-01T00:00:00Z','schema_version':'0.5'}; e=Engine(defn,[inst8]); r=e.transition(req('s008','activate_plan',inst8['instance_id'],inst8['subject_ref'],'1','plan.activate',docs=['RC:DOC:000001'],sigs=[]),'2030-04-01T00:00:01Z'); assert r['semantic_code']=='MISSING_SIGNATURE'
 # S010 stale expected version is rejected before later gates
 inst10={'instance_id':'tst:wf-instance:s010','workflow_id':defn['workflow_id'],'subject_ref':'RC:PLAN:0001','current_state':'effective','current_version':'2','updated_at':'2030-03-01T00:00:00Z','schema_version':'0.5'}; e=Engine(defn,[inst10]); r=e.transition(req('s010','open_amendment',inst10['instance_id'],inst10['subject_ref'],'1','plan.amend',rules=[{'evaluation_ref':'x','outcome':'pass'}]),'2030-04-01T00:00:01Z'); assert r['semantic_code']=='VERSION_CONFLICT' and r['current_version']=='2'
def main():
 defn=load(ED/'workflow-referencecity.json'); inst=load(ED/'instance-effective-v1.json'); rq=load(ED/'request-s010.json'); rs=load(ED/'result-s010.json')
 validate('workflow-definition.schema.json',defn); validate('workflow-instance.schema.json',inst); validate('transition-request.schema.json',rq); validate('transition-result.schema.json',rs)
 assert defn['initial_state'] in defn['states']
 for t in defn['transitions']:
  assert t['to_state'] in defn['states']; assert t['from_state'] is None or t['from_state'] in defn['states']
 check_scenarios(defn)
 # Explicit vector for S010 from fixture with authoritative version 2
 inst10=copy.deepcopy(inst); inst10['current_version']='2'; e=Engine(defn,[inst10]); actual=e.transition(rq,'2030-03-10T01:00:01Z'); assert actual==rs
 print('TST Chain v0.5 Workflow conformance: PASS'); print('  ReferenceCity S001/S002/S003/S004/S006/S008/S010 protocol verdicts available'); print('  idempotency + optimistic concurrency: PASS'); print('  persistence/finality: intentionally absent until v0.7'); return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as exc: print(f'TST Chain v0.5 conformance: FAIL: {exc}',file=sys.stderr); raise
