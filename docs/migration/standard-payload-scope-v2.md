# Migration: STANDARD payload scope v2

Owner: CR #171. Impact: HIGH; a prospective gate-semantics change.

STANDARD 0.1.2 and later require the exact candidate ZIP path in addition to its
SHA-256. The governed promotion wrapper passes the already restored canonical
package through `--package-path`; the collector never builds a replacement.
Runner Git history must include the annotated previous tag and complete
first-parent source chain. Missing objects fail closed.

Physical evidence schema v2 contains repository/version/source identity,
baseline and candidate payload manifests, full history transitions and explicit
cancellation references. The kernel verifies every changed path by replay.
Candidate Context schema v1 remains readable and gains `contentScopeReference`:
status, evidence_id, contract_version=2, source_sha and package_sha256. A
STANDARD release context needs these exact bound fields; Project reference
semantics remain unchanged.

Historical 0.1.1 snapshots continue through their legacy contract. Explicit
emergency compatibility keeps its own evaluator; STANDARD does not read its
ledger or call its transformation engine. Rolling back the new implementation
does not authorize release from already collected v2 evidence; revalidate under
the selected versioned contract and obtain fresh human authorization.

To collect diagnostics in standard PR CI, add exactly one explicit request:
`<!-- ddda:standard-scope-inventory:v2 version=0.1.2 -->`.
The optional job reuses the run's canonical candidate and fetches the previous
published asset read-only. Collection PASS means successful acquisition;
`kernel_preview` can be FAIL and the actual Release Scope Gate remains NOT_RUN.
This request grants no merge, recovery, promotion, tag or publication authority.

No Milestone, Issue membership, Git history, tag, asset, package inclusion rule,
client workspace or Cursor runtime behavior changes in this migration. Current
out-of-scope/shared contributions can remain blocked after the migration.
