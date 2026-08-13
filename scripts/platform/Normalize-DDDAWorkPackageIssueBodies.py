import json
import re
import subprocess

REPO='romanhlavac/ddd-accelerator'
OWNER='romanhlavac'
PROJECT='2'

def run(*args):
    p=subprocess.run(['gh',*args],text=True,capture_output=True)
    if p.returncode:
        raise RuntimeError(f"gh {' '.join(args)}: {p.stderr or p.stdout}")
    return p.stdout

def issue(n):
    return json.loads(run('api',f'repos/{REPO}/issues/{n}'))

def patch(n,body):
    payload=json.dumps({'body':body},ensure_ascii=False)
    p=subprocess.run(['gh','api','--method','PATCH',f'repos/{REPO}/issues/{n}','--input','-'],input=payload,text=True,capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)

sections={
36:"""## Dependencies

### Direct blocked-by

No native Issue blocker is required in the current WP-13 graph. #36 is the foundational WP-13 contract slice.

### Consumed baselines

- PR #8 preliminary agent/capability schemas and compatibility contract;
- WP-08 human-only decision safety boundaries;
- WP-10 evidence/provenance contracts when capabilities consume registered evidence.

### Downstream consumers

- #37 orchestrator;
- #39 authorization/safety;
- #41 multi-agent package-first acceptance;
- WP-11 may consume analytical outputs only through an optional integration adapter, not as a mandatory #36 dependency.
""",
37:"""## Dependencies

### Direct blocked-by

- #36 — versioned capability/agent contracts.

### Consumed baselines

- WP-08 human-only decision and validation safety contracts.

EventStorming #34/#35 and WP-11 are not mandatory prerequisites for the WP-13 orchestrator core.
""",
38:"""## Dependencies

### Direct blocked-by

- #37 — bounded fan-out/orchestrator.

### Consumed contracts

- #36 capability/result contracts are consumed transitively through #37.

EventStorming #34/#35 and WP-11 are not mandatory prerequisites for the WP-13 fan-in core.
""",
39:"""## Dependencies

### Direct blocked-by

- #36 — capability permissions/contracts;
- #37 — orchestrator;
- #38 — fan-in/conflict records.

### Consumed baseline

WP-08 human-only decision/HRDR contracts remain the authority for production human approval semantics, but are not modeled as an additional native blocker here.
""",
40:"""## Dependencies

### Direct blocked-by

- #37 — orchestrator;
- #38 — fan-in/conflicts;
- #39 — human checkpoints and authorization safety.

WP-11 EventStorming is not a mandatory prerequisite for the WP-13 recovery/observability core.
"""
}
for n,newsec in sections.items():
    d=issue(n); body=d.get('body') or ''
    body=body.replace('parent #20 is updated','parent #61 is updated').replace('parent #20.','parent #61.')
    body,count=re.subn(r'## Dependencies\n.*?(?=\n## Risks)',newsec.rstrip()+"\n",body,flags=re.S)
    if count!=1:
        raise RuntimeError(f'#{n} Dependencies replacement count={count}')
    patch(n,body)

# Remove repeated split notes from #46 and append exactly one canonical note.
d=issue(46); body=d.get('body') or ''
body=re.sub(r'\n*## Backlog split note \(2026-08-13\)\n\nWP-13/#36–#41 is optional multi-agent evolution and is not a final-closure dependency of this WP-11 first-user guide\. EventStorming E2E closure is owned by #62\.\n*','\n',body)
body=body.rstrip()+"\n\n## Backlog split note (2026-08-13)\n\nWP-13/#36–#41 is optional multi-agent evolution and is not a final-closure dependency of this WP-11 first-user guide. EventStorming E2E closure is owned by #62.\n"
patch(46,body)

# Defensive parent wording normalization for moved Miro CRs without changing PR8 baseline references.
for n in (53,54,55,56,57):
    d=issue(n); body=d.get('body') or ''
    body=body.replace('WP-08 — #17','WP-12 — #60').replace('parent WP-08 #17','parent WP-12 #60').replace('Parent WP-08 #17','Parent WP-12 #60')
    patch(n,body)

# Align Project planning summaries and verify priority order.
projects=json.loads(run('project','list','--owner',OWNER,'--limit','100','--format','json'))
project=next(x for x in projects['projects'] if x['title']=='DDDA Platform Backlog' and not x.get('closed'))
fields=json.loads(run('project','field-list',PROJECT,'--owner',OWNER,'--format','json'))
outcome=next(x for x in fields['fields'] if x['name']=='Outcome summary')
items=json.loads(run('project','item-list',PROJECT,'--owner',OWNER,'--limit','200','--format','json'))
by_number={int((x.get('content') or {}).get('number')):x for x in items['items'] if (x.get('content') or {}).get('number')}
summaries={
17:'Close the already implemented DDDA 0.1.0 / PR8 platform foundation without adding new feature scope.',
20:'EventStorming methodology, executable workshop runtime, governed Miro round-trip and package-first acceptance independent of multi-agent runtime.',
60:'Generic Miro Platform Lab/CI/HVR/Example/Project lifecycle, environment rebinding and explicit profile credential isolation.',
61:'Bounded multi-agent capability contracts, fan-out/fan-in, explicit human checkpoints, recovery and package-first acceptance.'}
priorities={17:'P0',20:'P1',60:'P2',61:'P3'}
for n,text in summaries.items():
    item=by_number[n]
    run('project','item-edit','--id',item['id'],'--project-id',project['id'],'--field-id',outcome['id'],'--text',text)
items=json.loads(run('project','item-list',PROJECT,'--owner',OWNER,'--limit','200','--format','json'))
by_number={int((x.get('content') or {}).get('number')):x for x in items['items'] if (x.get('content') or {}).get('number')}
final={}
for n,text in summaries.items():
    item=by_number[n]
    if item.get('priority')!=priorities[n]: raise RuntimeError(f'priority mismatch #{n}')
    if item.get('outcome summary')!=text: raise RuntimeError(f'outcome mismatch #{n}')
    final[n]={'priority':item.get('priority'),'work_package':item.get('work Package'),'dependency':item.get('dependency'),'outcome_summary':item.get('outcome summary')}
open('wp-planning-normalization.json','w',encoding='utf-8').write(json.dumps(final,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(final,ensure_ascii=False))
