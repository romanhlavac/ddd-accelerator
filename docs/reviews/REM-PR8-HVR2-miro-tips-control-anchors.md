# REM-PR8 HVR-2 — Miro Tips explicit control anchors

Status: Corrective implementation for HVR-2 re-review

## Human finding

HVR-2 remained `CHANGES_REQUIRED` because the generated Miro Tips arrows were attached to the screenshot image as one object. Miro normalized the image-side connector endpoint, so an authored `endItem.position` could not reliably guarantee that an arrowhead landed on the intended UI control. The Miro Tips block also had to stay at the accepted lower placement with **+600 Miro units** vertical offset from the reference-derived position.

## Corrective design

The target tutorial now uses **explicit control anchors** derived from the **reference arrowhead positions**:

1. Keep the reference Miro UI screenshot as the visual background.
2. Keep the authored native sticky/text callouts above the screenshot.
3. For every black captionless reference callout, convert its normalized screenshot-side arrowhead coordinate into a parent-relative point in the target screenshot.
4. Create one tiny transparent child shape at that exact UI-control point.
5. Terminate the generated connector on that anchor item rather than on the whole screenshot image.
6. Remove legacy black tutorial connectors that still terminate on the screenshot image.
7. Preserve the active Miro Tips frame identity `3458764680476608045` when its accepted geometry and placement are already stable.

This makes the UI control itself an explicit managed endpoint and removes dependence on Miro's normalization of connector-to-image positions.

## Mechanical acceptance

For the target Miro Tips frame the exact-SHA remediation must prove:

- at least one reference screenshot image;
- eight source reference callouts with authored screenshot arrowhead positions;
- at least eight explicit transparent control anchors;
- at least eight black captionless tutorial connectors terminating on those anchors;
- zero tutorial connectors terminating directly on the screenshot image;
- accepted reference geometry and the +600 Miro-units placement;
- unchanged protected frames;
- a **zero-mutation second reconcile** for items, anchors and connectors.

A technical PASS leaves `human_review_status=PENDING` and `overall_status=READY_FOR_HUMAN_REVIEW`. It does not approve HVR-2 by itself.

## Governance

HVR-2 remains pending until the generated target board is visually reviewed by a human. **HVR-3 remains blocked** until HVR-2 receives the required human verdict. This corrective change does not authorize merge, promotion, release, tag creation or gate approval.
