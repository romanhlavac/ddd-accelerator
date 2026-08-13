import json
import re
import subprocess

REPO='romanhlavac/ddd-accelerator'

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
    d=issue(n); body=(d.get('body') or '').replace('\r\n','\n').replace('\r','\n')
    body=body.replace('parent #20 is updated','parent #61 is updated').replace('parent #20.','parent #61.')
    body,count=re.subn(r'(?ms)^## Dependencies\s*$.*?(?=^## (?:Risks|Definition of Done)\s*$)',newsec.rstrip()+"\n\n",body)
    if count!=1:
        raise RuntimeError(f'#{n} Dependencies replacement count={count}')
    patch(n,body)

# Remove repeated split notes from #46 and append exactly one canonical note.
d=issue(46); body=(d.get('body') or '').replace('\r\n','\n').replace('\r','\n')
body=re.sub(r'\n*## Backlog split note \(2026-08-13\)\n\nWP-13/#36–#41 is optional multi-agent evolution and is not a final-closure dependency of this WP-11 first-user guide\. EventStorming E2E closure is owned by #62\.\n*','\n',body)
body=body.rstrip()+"\n\n## Backlog split note (2026-08-13)\n\nWP-13/#36–#41 is optional multi-agent evolution and is not a final-closure dependency of this WP-11 first-user guide. EventStorming E2E closure is owned by #62.\n"
patch(46,body)

# Defensive parent wording normalization for moved Miro CRs without changing PR8 baseline references.
for n in (53,54,55,56,57):
    d=issue(n); body=d.get('body') or ''
    body=body.replace('WP-08 — #17','WP-12 — #60').replace('parent WP-08 #17','parent WP-12 #60').replace('Parent WP-08 #17','Parent WP-12 #60')
    patch(n,body)

# Read-back assertions.
for n in (36,37,38,39,40):
    body=issue(n).get('body') or ''
    if 'parent #20' in body or 'and parent #20' in body:
        raise RuntimeError(f'stale parent text remains in #{n}')
body=issue(46).get('body') or ''
if body.count('## Backlog split note (2026-08-13)') != 1:
    raise RuntimeError('duplicate #46 split note remains')
print('ISSUE_SEMANTICS_NORMALIZED')
