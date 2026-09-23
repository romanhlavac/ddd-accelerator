from pathlib import Path
import json

R=Path.cwd(); B=R/'config/governance/github-bootstrap.json'; P=R/'config/governance/backlog-policy.yaml'; I=R/'docs/roadmap/backlog-index.md'; D=R/'docs/roadmap/README.md'; T=R/'runtime/platform/tests/test_project_backlog_delivery_governance.py'; W=R/'docs/roadmap/work-packages/WP-14-multi-model-workbench-git-sync.md'

def one(s,a,b):
    if s.count(a)!=1: raise RuntimeError(f'expected one match for {a[:50]!r}, got {s.count(a)}')
    return s.replace(a,b,1)

c=json.loads(B.read_text(encoding='utf-8-sig'))
assert not any(int(x.get('parent',-1))==148 for x in c['hierarchy'])
c['hierarchy'].append({'parent':148,'children':[149,150,151,152,153,154]}); c['hierarchy'].sort(key=lambda x:int(x['parent']))
for blocked,blockers in {150:[149],151:[149],152:[149],153:[149,150,151,152],154:[150,153]}.items():
    assert not any(int(x['blocked'])==blocked for x in c['dependencies'])
    c['dependencies'].append({'blocked':blocked,'blocked_by':blockers})
c['dependencies'].sort(key=lambda x:int(x['blocked']))
f=next(x for x in c['fields'] if x['name']=='Work Package'); names=[x['name'] for x in f['options']]; assert 'WP-14' not in names
f['options'].insert(names.index('Other'),{'name':'WP-14','color':'GREEN','description':'Multi-Model Workbench & Git-backed Model Synchronization.'})
M={
148:{'Status':'Backlog','Work Package':'WP-14','Item Type':'Work Package','Target Release':'0.2.0','Blocked':'No','Human Review':'Pending','Outcome summary':'Provider-neutral multi-model workbench and Git-backed synchronization across workshop, DDD and architecture providers.'},
149:{'Status':'Backlog','Work Package':'WP-14','Item Type':'Change Request','Platform Area':'ORCHESTRATION','Impact':'HIGH','Target Release':'0.2.0','Blocked':'No','Human Review':'Pending'},
150:{'Status':'Blocked','Work Package':'WP-14','Item Type':'Change Request','Platform Area':'ORCHESTRATION','Impact':'HIGH','Target Release':'0.2.0','Blocked':'Yes','Human Review':'Pending'},
151:{'Status':'Blocked','Work Package':'WP-14','Item Type':'Change Request','Platform Area':'ORCHESTRATION','Impact':'HIGH','Target Release':'0.2.0','Blocked':'Yes','Human Review':'Pending'},
152:{'Status':'Blocked','Work Package':'WP-14','Item Type':'Change Request','Platform Area':'ORCHESTRATION','Impact':'HIGH','Target Release':'0.2.0','Blocked':'Yes','Human Review':'Pending'},
153:{'Status':'Blocked','Work Package':'WP-14','Item Type':'Change Request','Platform Area':'ORCHESTRATION','Impact':'HIGH','Target Release':'0.2.0','Blocked':'Yes','Human Review':'Pending'},
154:{'Status':'Blocked','Work Package':'WP-14','Item Type':'Change Request','Platform Area':'SECURITY-GOVERNANCE','Impact':'BREAKING','Target Release':'0.2.0','Blocked':'Yes','Human Review':'Pending'},
155:{'Status':'In progress','Work Package':'Other','Item Type':'Change Request','Platform Area':'SECURITY-GOVERNANCE','Impact':'MEDIUM','Target Release':'0.1.2','Blocked':'No','Human Review':'Pending'} }
existing={int(n) for g in c['item_groups'] if g.get('kind')=='issue' for n in g.get('numbers',[])}; assert not(existing & set(M))
for n in sorted(M): c['item_groups'].append({'kind':'issue','numbers':[n],'metadata':M[n]})
m=next(x for x in c['milestones'] if x['title']=='DDDA 0.1.1'); assert m['state']=='open' and m['issues']==[9,12,67,68,70,96,98]
assert all(set(range(148,156)).isdisjoint(set(x.get('issues',[]))) for x in c['milestones'])
B.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

p=P.read_text(encoding='utf-8')
p=one(p,'values: [WP-08, WP-09, WP-10, WP-11, WP-12, WP-13, Other]','values: [WP-08, WP-09, WP-10, WP-11, WP-12, WP-13, WP-14, Other]')
p=one(p,'  Other:\n    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132]\n','  WP-14:\n    parent_issue: 148\n    children: [149, 150, 151, 152, 153, 154]\n  Other:\n    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132, 155]\n')
p=one(p,'  Other:\n    - blocking: 16\n      blocked: 49\n','  WP-14:\n    - blocking: 149\n      blocked: 150\n    - blocking: 149\n      blocked: 151\n    - blocking: 149\n      blocked: 152\n    - blocking: 149\n      blocked: 153\n    - blocking: 150\n      blocked: 153\n    - blocking: 151\n      blocked: 153\n    - blocking: 152\n      blocked: 153\n    - blocking: 150\n      blocked: 154\n    - blocking: 153\n      blocked: 154\n  Other:\n    - blocking: 16\n      blocked: 49\n')
assert '  WP-14:\n    title: Multi-Model Workbench' not in p
p += '\n  WP-14:\n    title: Multi-Model Workbench & Git-backed Model Synchronization\n    state: backlog\n    target_release: 0.2.0\n    outcome_summary: Provider-neutral workshop, DDD and architecture model providers coordinated through one Git-backed synchronization contract.\n'
P.write_text(p,encoding='utf-8')

i=I.read_text(encoding='utf-8'); sec='''## WP-14 — #148 Multi-Model Workbench & Git-backed Model Synchronization\n\nChildren: #149, #150, #151, #152, #153, #154.\n\n```text\n#149 → #150\n#149 → #151\n#149 → #152\n#149 + #150 + #151 + #152 → #153\n#150 + #153 → #154\n```\n\nProposed target 0.2.0 is planning metadata only; #148–#154 remain outside Milestones and Project priority/order remains unset until separate human decisions.\n\n'''
i=one(i,'## Cross-cutting\n',sec+'## Cross-cutting\n'); i=one(i,'## Boundary invariant\n','- #155 — WP-14 canonical backlog/Project governance enablement (`Other`, proposed 0.1.2); priority and Milestone membership remain unset.\n\n## Boundary invariant\n'); I.write_text(i,encoding='utf-8')

d=D.read_text(encoding='utf-8'); d=one(d,'| — | existing project priority | WP-10 | Enterprise ingestion | backlog | TBD |\n','| — | existing project priority | WP-10 | Enterprise ingestion | backlog | TBD |\n| — | unset — human decision pending | WP-14 | Multi-Model Workbench & Git-backed Model Synchronization | planned | proposed 0.2.0 |\n'); d=one(d,'- [GitHub backlog index](backlog-index.md)','- [WP-14 — Multi-Model Workbench & Git-backed Model Synchronization](work-packages/WP-14-multi-model-workbench-git-sync.md)\n- [GitHub backlog index](backlog-index.md)'); D.write_text(d,encoding='utf-8')

assert not W.exists(); W.write_text('''# WP-14 — Multi-Model Workbench & Git-backed Model Synchronization\n\n**Authority:** #148. **Children:** #149–#154. **Proposed target:** 0.2.0; no Milestone membership is authorized by #155. **Priority/order:** unset pending a human Project decision.\n\n## Outcome\nOne provider-neutral Git-backed synchronization contract across workshop, DDD and architecture providers. Git/DDDA owns cross-tool identity, lifecycle/provenance, traceability, sync state, conflicts/tombstones and decisions; provider-native semantics remain provider-owned.\n\n## Dependency topology\n```text\n#149 → #150\n#149 → #151\n#149 → #152\n#149 + #150 + #151 + #152 → #153\n#150 + #153 → #154\n```\n\n#155 materializes planning governance only. It does not authorize implementation of #149–#154, assign priority, or approve DDDA 0.2.0 release scope.\n''',encoding='utf-8')

t=T.read_text(encoding='utf-8'); assert 'test_wp14_governance_contract_is_canonical_and_milestone_neutral' not in t
t=one(t,'    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132]" in POLICY.read_text(encoding="utf-8")','    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132, 155]" in POLICY.read_text(encoding="utf-8")')
t += '''\n\ndef test_wp14_governance_contract_is_canonical_and_milestone_neutral():\n    cfg=json.loads(BOOTSTRAP.read_text(encoding="utf-8-sig"))\n    wp=next(x for x in cfg["fields"] if x["name"]=="Work Package")\n    assert [x["name"] for x in wp["options"]].count("WP-14")==1\n    h={int(x["parent"]):x["children"] for x in cfg["hierarchy"]}; assert h[148]==[149,150,151,152,153,154]\n    deps={int(x["blocked"]):x["blocked_by"] for x in cfg["dependencies"]}; assert deps[150]==[149] and deps[153]==[149,150,151,152] and deps[154]==[150,153]\n    meta={int(n):g.get("metadata",{}) for g in cfg["item_groups"] if g.get("kind")=="issue" for n in g.get("numbers",[])}\n    assert set(range(148,156)).issubset(meta) and all("Priority" not in meta[n] for n in range(148,156))\n    assert all(set(range(148,156)).isdisjoint(set(m.get("issues",[]))) for m in cfg["milestones"])\n    m=next(x for x in cfg["milestones"] if x["title"]=="DDDA 0.1.1"); assert m["issues"]==[9,12,67,68,70,96,98]\n    assert "WP-14-multi-model-workbench-git-sync.md" in (ROOT/"docs/roadmap/README.md").read_text(encoding="utf-8")\n'''; T.write_text(t,encoding='utf-8')
