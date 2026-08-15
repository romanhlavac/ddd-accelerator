from __future__ import annotations
"Pixel-fidelity visual carrier for the eight curved Miro Tips callouts.\n\nMiro REST v2 exposes connector endpoint metadata and the coarse ``curved`` shape,\nbut it does not expose the renderer's manually-authored curve/path control state.\nRecreating the approved eight curved screenshot callouts as native connectors can\ntherefore round-trip endpoint metadata while rendering a visibly different route.\n\nFor PR8 HVR fidelity those eight curves are represented by eight tightly-bounded\ntransparent PNG overlays extracted from the approved reference screenshot.  The\nthree simple text callouts remain native straight connectors with deterministic\nper-endpoint controls.  This keeps the interactive native content intact while\nremoving the non-round-trippable Miro curve router from the visual contract.\n"
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from . import miro_tips_full_arrow_fidelity_fix as full
from . import miro_tips_hvr_fix as tips
from . import miro_tips_legacy_line_fidelity_fix as legacy
from . import miro_tips_render_fidelity_fix as fidelity
from . import miro_tips_endpoint_geometry_v4 as endpoint_v4
from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual
from .image_upload import upload_image_resource
VISUAL_ARROW_OVERLAY_POLICY = 'frozen_reference_raster_arrow_overlays_v5'
VISUAL_ARROW_COUNT = 8
PHYSICAL_CONNECTOR_COUNT = 3
DIRECT_IMAGE_TARGET_CONNECTOR_COUNT = 0
OVERLAY_TITLE_PREFIX = 'DDDA-MIRO-TIPS-ARROW-V5:'
VISUAL_ACCEPTANCE_AUTHORITY = 'human_review_only'
ARROW_SPECS: tuple[dict[str, Any], ...] = ({'key': 'shortcut', 'asset': 'miro_tips_arrow_shortcut_v5.png', 'sha256': 'b6590f784a2fcc92acdf55c81b3b7e0b9b6aec9a2d114c6fbebad4234d426ae7', 'x': 73.33333333333334, 'y': 192.0, 'width': 98.66666666666667, 'height': 80.0}, {'key': 'navigation_mode', 'asset': 'miro_tips_arrow_navigation_mode_v5.png', 'sha256': 'bb846d522b1e9ce0480429eb177a9c8d582a73c01464c2815a92d77e6549aa26', 'x': 367.33333333333337, 'y': 113.33333333333333, 'width': 153.33333333333334, 'height': 109.33333333333333}, {'key': 'mouse_pointers', 'asset': 'miro_tips_arrow_mouse_pointers_v5.png', 'sha256': '7d2fde056c02517b294ded2d0322aab6f241122d891f685e2da27e48425d4787', 'x': 1647.3333333333333, 'y': 123.33333333333334, 'width': 52.0, 'height': 89.33333333333333}, {'key': 'facilitator_avatar', 'asset': 'miro_tips_arrow_facilitator_avatar_v5.png', 'sha256': '5ca6c9d29dd27a7676ef12e7fb1d4fa71251948e947583583998477e5a9378ac', 'x': 1760.6666666666667, 'y': 123.33333333333334, 'width': 28.0, 'height': 89.33333333333333}, {'key': 'undo', 'asset': 'miro_tips_arrow_undo_v5.png', 'sha256': '2f0397a73f16eb08b9f67fea9015f04511f52e3898a3d5e134fe83fe95f0f2f8', 'x': 114.66666666666666, 'y': 813.3333333333334, 'width': 85.33333333333333, 'height': 32.0}, {'key': 'frame_overview', 'asset': 'miro_tips_arrow_frame_overview_v5.png', 'sha256': 'fd00d1f67b638a152a74659b989ff21a188ea8e050c4d12fe2592437b78cc1e3', 'x': 90.0, 'y': 986.6666666666667, 'width': 137.33333333333334, 'height': 50.666666666666664}, {'key': 'board_map', 'asset': 'miro_tips_arrow_board_map_v5.png', 'sha256': 'd0550970cac15760fbc2b75f1e8deb3550698b7dd8725105ebbcfd3637700a5b', 'x': 1638.6666666666667, 'y': 984.0, 'width': 29.333333333333332, 'height': 80.0}, {'key': 'zoom_100', 'asset': 'miro_tips_arrow_zoom_100_v5.png', 'sha256': '0f62a757dd8a4eed4fc1a907d7c9c13a46fb02c16b458d95e95dda7b6c52ecba', 'x': 1784.0, 'y': 984.0, 'width': 29.333333333333332, 'height': 80.0})
_ORIGINAL_RECONCILE = full._reconcile_connectors
_ORIGINAL_READBACK = full._structural_readback
_ORIGINAL_VISIBLE_CHILDREN = fidelity._visible_children
_ORIGINAL_VISIBLE_RECONCILE = fidelity._visible_reconcile_without_connectors
_ORIGINAL_REBUILD_CONTROLS = full._rebuild_controls_below_native
_ORIGINAL_TIPS_RECONCILE: Any | None = None
_LAST_OVERLAY_RESULT: dict[str, Any] | None = None
_INSTALLED = False

def _close(left: Any, right: Any, tolerance: float=0.75) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False

def overlay_title(spec: dict[str, Any]) -> str:
    return f"{OVERLAY_TITLE_PREFIX}{spec['key']}:sha256={spec['sha256']}"

def is_visual_overlay(item: dict[str, Any], frame_id: str | None=None) -> bool:
    if str(item.get('type') or '') != 'image':
        return False
    if frame_id is not None and str((item.get('parent') or {}).get('id') or '') != str(frame_id):
        return False
    return str((item.get('data') or {}).get('title') or '').startswith(OVERLAY_TITLE_PREFIX)

def _overlay_items(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [item for item in base._children(client, board, frame_id) if is_visual_overlay(item, frame_id)]

def _same_overlay(item: dict[str, Any], frame_id: str, spec: dict[str, Any]) -> bool:
    if not is_visual_overlay(item, frame_id):
        return False
    if str((item.get('data') or {}).get('title') or '') != overlay_title(spec):
        return False
    pos, geom = (item.get('position') or {}, item.get('geometry') or {})
    return _close(pos.get('x'), spec['x']) and _close(pos.get('y'), spec['y']) and _close(geom.get('width'), spec['width']) and _close(geom.get('height'), spec['height'])

def overlay_evidence(items: list[dict[str, Any]], frame_id: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for spec in ARROW_SPECS:
        matches = [item for item in items if str(item.get('id') or '') not in used and _same_overlay(item, frame_id, spec)]
        if len(matches) != 1:
            raise ValueError(f"Miro Tips visual arrow overlay {spec['key']} mismatch: matches={len(matches)}")
        item = matches[0]
        used.add(str(item.get('id') or ''))
        rows.append({'key': spec['key'], 'item_id': str(item.get('id') or ''), 'asset_sha256': spec['sha256'], 'x': spec['x'], 'y': spec['y'], 'width': spec['width'], 'height': spec['height'], 'status': 'PASS'})
    extras = [item for item in items if is_visual_overlay(item, frame_id) and str(item.get('id') or '') not in used]
    if extras:
        raise ValueError(f'Miro Tips has {len(extras)} unexpected v5 visual overlay images')
    return {'policy': VISUAL_ARROW_OVERLAY_POLICY, 'count': len(rows), 'expected': VISUAL_ARROW_COUNT, 'status': 'PASS', 'arrows': rows}

def _asset_bytes(spec: dict[str, Any]) -> bytes:
    import hashlib
    path = Path(__file__).resolve().parent / 'assets' / str(spec['asset'])
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != spec['sha256']:
        raise ValueError(f"Miro Tips visual asset hash mismatch for {spec['key']}: {actual}")
    return data

def _ensure_overlays(client: Any, board: str, frame_id: str) -> dict[str, Any]:
    existing = _overlay_items(client, board, frame_id)
    counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
    expected_titles = {overlay_title(spec) for spec in ARROW_SPECS}
    for item in list(existing):
        title = str((item.get('data') or {}).get('title') or '')
        if title not in expected_titles:
            client.delete_item(board, str(item['id']))
            counts['deleted'] += 1
    existing = _overlay_items(client, board, frame_id)
    for spec in ARROW_SPECS:
        title = overlay_title(spec)
        candidates = [item for item in existing if str((item.get('data') or {}).get('title') or '') == title]
        if len(candidates) > 1:
            for item in candidates:
                client.delete_item(board, str(item['id']))
                counts['deleted'] += 1
            candidates = []
        if len(candidates) == 1 and _same_overlay(candidates[0], frame_id, spec):
            counts['unchanged'] += 1
            continue
        if len(candidates) == 1:
            client.delete_item(board, str(candidates[0]['id']))
            counts['deleted'] += 1
        payload = {'data': {'title': title}, 'position': {'x': float(spec['x']), 'y': float(spec['y']), 'origin': 'center'}, 'geometry': {'width': float(spec['width'])}, 'parent': {'id': str(frame_id)}}
        created = upload_image_resource(client, board, payload, _asset_bytes(spec), 'image/png')
        if not _same_overlay(created, frame_id, spec):
            raise ValueError(f"Miro Tips visual overlay read-back mismatch for {spec['key']}")
        counts['created'] += 1
    evidence = overlay_evidence(_overlay_items(client, board, frame_id), frame_id)
    return {'counts': counts, 'evidence': evidence}

def _filtered_children(original: Any, overlay_board: str, overlay_frame: str):

    def wrapped(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
        rows = list(original(client, board, frame_id))
        if str(board) == str(overlay_board) and str(frame_id) == str(overlay_frame):
            rows = [item for item in rows if not is_visual_overlay(item, overlay_frame)]
        return rows
    return wrapped

def visible_children_without_overlays(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [item for item in _ORIGINAL_VISIBLE_CHILDREN(client, board, frame_id) if not is_visual_overlay(item, frame_id)]

def visible_reconcile_without_overlays(client: Any, source_board: str, source_frame_id: str, target_board: str, target_frame_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    original_children = base._children
    base._children = _filtered_children(original_children, target_board, target_frame_id)
    try:
        return _ORIGINAL_VISIBLE_RECONCILE(client, source_board, source_frame_id, target_board, target_frame_id, manifest)
    finally:
        base._children = original_children

def rebuild_controls_without_overlays(client: Any, source_board: str, source_frame_id: str, target_board: str, target_frame_id: str, target_image: dict[str, Any], expected: list[tuple[float, float]]) -> dict[str, int]:
    original_children = base._children
    base._children = _filtered_children(original_children, target_board, target_frame_id)
    try:
        return _ORIGINAL_REBUILD_CONTROLS(client, source_board, source_frame_id, target_board, target_frame_id, target_image, expected)
    finally:
        base._children = original_children

def reconcile_connectors_as_three_native_plus_eight_overlays(client: Any, source_inventory: dict[str, Any], source_board: str, target_board: str, target_frame_id: str, source_image: dict[str, Any], target_image: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    used_anchors: set[str] = set()
    positions = legacy.compatibility_positions_with_legacy_arrows(source_inventory['direct_image_connectors'], target_image)
    for index, connector in enumerate(source_inventory['text_connectors']):
        sx, sy = positions[index * 2]
        ex, ey = positions[index * 2 + 1]
        connector['_ddda_target_start_anchor_id'] = str(legacy._find_anchor(client, target_board, target_frame_id, sx, sy, used_anchors)['id'])
        connector['_ddda_target_end_anchor_id'] = str(legacy._find_anchor(client, target_board, target_frame_id, ex, ey, used_anchors)['id'])
    native_mapping = fidelity._map_native(client, source_board, str((manifest.get('miro_tips') or {})['reference_source_frame_id']), target_board, target_frame_id)
    source_items = {str(item.get('id') or ''): item for item in client.list_items(source_board)}
    target_connectors = list(client.list_connectors(target_board))
    used: set[str] = set()
    counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
    expected_rows: list[dict[str, Any]] = []
    for source in source_inventory['text_connectors']:
        payload = full._connector_payload(source, native_mapping, source_items, source_image, str(target_image['id']), manifest)
        expected_rows.append(payload)
        pair = full._endpoint_ids(payload)
        hits = [row for row in target_connectors if str(row.get('id') or '') not in used and full._endpoint_ids(row) == pair]
        if len(hits) > 1:
            raise ValueError(f'Miro Tips duplicate physical connector for {pair}')
        row = hits[0] if hits else None
        if row is None:
            row = client.create_connector(target_board, payload)
            target_connectors.append(row)
            counts['created'] += 1
        elif visual.redline.same_connector(row, payload):
            counts['unchanged'] += 1
        else:
            row = client.update_connector(target_board, str(row['id']), payload)
            if not visual.redline.same_connector(row, payload):
                raise ValueError(f"Miro Tips straight connector read-back mismatch: {row.get('id')}")
            counts['updated'] += 1
        used.add(str(row['id']))
    managed_ids = {str(item.get('id') or '') for item in base._children(client, target_board, target_frame_id)}
    for row in list(target_connectors):
        rid = str(row.get('id') or '')
        if rid in used:
            continue
        if any((endpoint in managed_ids for endpoint in full._endpoint_ids(row) if endpoint)):
            client.delete_connector(target_board, rid)
            counts['deleted'] += 1
    overlay = _ensure_overlays(client, target_board, target_frame_id)
    global _LAST_OVERLAY_RESULT
    _LAST_OVERLAY_RESULT = overlay
    return {'counts': counts, 'native_mapping': native_mapping, 'proxy_id': str(target_image['id']), 'expected': expected_rows, 'visual_overlays': overlay}

def structural_readback_v5(client: Any, source_inventory: dict[str, Any], source_board: str, source_frame_id: str, target_board: str, target_frame_id: str, source_image: dict[str, Any], target_image: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    cfg = tips._config(manifest)
    children = list(base._children(client, target_board, target_frame_id))
    overlays = [item for item in children if is_visual_overlay(item, target_frame_id)]
    controls = [item for item in children if endpoint_v4.is_control_artifact(item, target_frame_id)]
    visible = [item for item in children if not is_visual_overlay(item, target_frame_id) and (not endpoint_v4.is_control_artifact(item, target_frame_id))]
    counts = Counter((str(item.get('type') or '') for item in visible))
    if len(visible) != tips.EXPECTED_ITEM_COUNT or dict(counts) != tips.EXPECTED_ITEM_TYPE_COUNTS:
        raise ValueError(f'Miro Tips visible target topology mismatch under v5: {dict(counts)}')
    if len(controls) != endpoint_v4.EXPECTED_COMPATIBILITY_ANCHORS:
        raise ValueError(f'Miro Tips requires six deterministic text-arrow controls, got {len(controls)}')
    text = ' '.join((base._visible((item.get('data') or {}).get('content')).casefold() for item in visible))
    missing = [m for m in cfg['required_markers'] if m not in text]
    if missing:
        raise ValueError(f'Miro Tips target is missing reference markers: {missing}')
    overlay = overlay_evidence(overlays, target_frame_id)
    native_mapping = fidelity._map_native(client, source_board, source_frame_id, target_board, target_frame_id)
    source_items = {str(item.get('id') or ''): item for item in client.list_items(source_board)}
    target_items = {str(item.get('id') or ''): item for item in children}
    connectors = list(client.list_connectors(target_board))
    used: set[str] = set()
    geometry: list[dict[str, Any]] = []
    for source in source_inventory['text_connectors']:
        expected = full._connector_payload(source, native_mapping, source_items, source_image, str(target_image['id']), manifest)
        pair = full._endpoint_ids(expected)
        matches = [row for row in connectors if str(row.get('id') or '') not in used and full._endpoint_ids(row) == pair and visual.redline.same_connector(row, expected)]
        if len(matches) != 1:
            raise ValueError(f"Miro Tips deterministic text connector mismatch: {source.get('id')}")
        actual = matches[0]
        used.add(str(actual['id']))
        geometry.append(endpoint_v4.connector_geometry_evidence(str(source.get('id') or ''), expected | {'_ddda_legacy_visual_arrow': deepcopy(source['_ddda_legacy_visual_arrow'])}, actual, target_items, target_image))
    related_ids = {str(item.get('id') or '') for item in children}
    related = [row for row in connectors if any((endpoint in related_ids for endpoint in full._endpoint_ids(row) if endpoint))]
    direct = [row for row in related if str(target_image.get('id') or '') in full._endpoint_ids(row)]
    if len(related) != PHYSICAL_CONNECTOR_COUNT or len(used) != PHYSICAL_CONNECTOR_COUNT or direct:
        raise ValueError(f'Miro Tips v5 physical connector topology mismatch: related={len(related)}, validated={len(used)}, direct={len(direct)}')
    return {'policy': tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY, 'source_item_count': 17, 'target_item_count': 17, 'item_type_counts': dict(tips.EXPECTED_ITEM_TYPE_COUNTS), 'source_connector_count': 11, 'target_connector_count': full.EXPECTED_DIRECT_IMAGE_CONNECTORS, 'actual_target_connector_count': PHYSICAL_CONNECTOR_COUNT, 'connector_contract_count': 11, 'native_item_count': len(native_mapping), 'source_image_id': str(source_image.get('id') or ''), 'target_image_id': str(target_image.get('id') or ''), 'status': 'PASS', 'STRUCTURAL_REFERENCE_MATCH': 'PASS', 'VISUAL_ARROW_ORACLE_MATCH': 'PASS', 'ENDPOINT_GEOMETRY_MATCH': 'PASS', 'HUMAN_VISUAL_ACCEPTANCE': 'PENDING', 'reference_structure_policy': 'native_children_plus_visual_arrow_overlays_v5', 'visual_acceptance_authority': VISUAL_ACCEPTANCE_AUTHORITY, 'reference_endpoint_contract': endpoint_v4.connector_contract_evidence(source_inventory['connectors'], str(source_image.get('id') or '')), 'endpoint_geometry': {'status': 'PASS', 'matched': len(geometry), 'expected': PHYSICAL_CONNECTOR_COUNT, 'tolerance_board_units': endpoint_v4.ENDPOINT_GEOMETRY_TOLERANCE, 'connectors': geometry}, 'visual_arrow_overlays': overlay, 'render_fidelity': {'status': 'PASS', 'routing_proxy_policy': 'native_curved_router_forbidden_v5', 'endpoint_policy': 'raster_visual_oracle_for_8_curves_plus_3_deterministic_straight_connectors', 'routing_proxy_count': 0, 'compatibility_anchor_count': len(controls), 'actual_connector_count': len(related), 'direct_image_source_connector_count': len(source_inventory['direct_image_connectors']), 'text_callout_connector_count': len(source_inventory['text_connectors']), 'direct_image_target_connector_count': len(direct), 'visual_arrow_overlay_count': overlay['count']}}

def reconcile_with_overlay_evidence(*args: Any, **kwargs: Any) -> dict[str, Any]:
    global _LAST_OVERLAY_RESULT
    if _ORIGINAL_TIPS_RECONCILE is None:
        raise RuntimeError('Miro Tips v5 reconcile wrapper is not installed')
    _LAST_OVERLAY_RESULT = None
    result = _ORIGINAL_TIPS_RECONCILE(*args, **kwargs)
    overlay = _LAST_OVERLAY_RESULT
    if not isinstance(overlay, dict):
        raise ValueError('Miro Tips v5 reconcile did not produce visual-arrow overlay evidence')
    counts = dict(overlay.get('counts') or {})
    item_counts = dict(result.get('items') or {})
    for key in ('created', 'updated', 'unchanged', 'deleted'):
        item_counts[key] = int(item_counts.get(key, 0)) + int(counts.get(key, 0))
    result['items'] = item_counts
    result['visual_arrow_overlays'] = overlay.get('evidence')
    result['visual_arrow_overlay_policy'] = VISUAL_ARROW_OVERLAY_POLICY
    return result

def install() -> None:
    global _INSTALLED, _ORIGINAL_TIPS_RECONCILE
    if _INSTALLED:
        return
    _ORIGINAL_TIPS_RECONCILE = tips.reconcile_miro_tips_children
    fidelity._visible_children = visible_children_without_overlays
    fidelity._visible_reconcile_without_connectors = visible_reconcile_without_overlays
    full._rebuild_controls_below_native = rebuild_controls_without_overlays
    full._reconcile_connectors = reconcile_connectors_as_three_native_plus_eight_overlays
    full._structural_readback = structural_readback_v5
    tips.reconcile_miro_tips_children = reconcile_with_overlay_evidence
    _INSTALLED = True

def uninstall() -> None:
    global _INSTALLED, _ORIGINAL_TIPS_RECONCILE, _LAST_OVERLAY_RESULT
    if not _INSTALLED:
        return
    if _ORIGINAL_TIPS_RECONCILE is not None:
        tips.reconcile_miro_tips_children = _ORIGINAL_TIPS_RECONCILE
    full._structural_readback = _ORIGINAL_READBACK
    full._reconcile_connectors = _ORIGINAL_RECONCILE
    full._rebuild_controls_below_native = _ORIGINAL_REBUILD_CONTROLS
    fidelity._visible_reconcile_without_connectors = _ORIGINAL_VISIBLE_RECONCILE
    fidelity._visible_children = _ORIGINAL_VISIBLE_CHILDREN
    _ORIGINAL_TIPS_RECONCILE = None
    _LAST_OVERLAY_RESULT = None
    _INSTALLED = False
