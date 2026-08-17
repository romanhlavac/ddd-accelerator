# Synthetic claims domain notes

These notes are intentionally synthetic and contain no client data.

## Business observations

- A claim is registered before assessment starts.
- A claim cannot be approved before liability and coverage are checked.
- The legacy system mixes claim intake, assessment and payment concerns.
- The first modernization slice should preserve the legacy audit trail and operational continuity.

## Open questions

- Which legacy events can be exported reliably?
- Who owns the authoritative claim status?
- Which rules belong to claim assessment and which belong to policy coverage?
