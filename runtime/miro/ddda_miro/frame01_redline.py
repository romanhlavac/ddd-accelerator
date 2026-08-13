from __future__ import annotations

import argparse, hashlib, html, json, os, re, sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from .anchor_contract import _close, _get_frame, _protected_snapshot, canonical_miro_text
from .client import MiroClient, normalize_miro_font_size, normalize_miro_percentage
from .yamlio import load_yaml

RID = "REM-PR8-HVA-CC-012.5"
NATIVE = {"shape", "text", "sticky_note"}
EP = {"shape": "shapes", "text": "texts", "sticky_note": "sticky_notes"}


def load_manifest(path: Path) -> dict[str, Any]:
    m = load_yaml(path.resolve())
    if not isinstance(m, dict) or m.get("remediation_id") != RID:
        raise ValueError("invalid REM-012.5 manifest")
    required = {"board_id", "frame_id", "source_board_id", "source_frame_id", "source_frame_title", "protected_frames", "source_sentinels"}
    missing = sorted(required - set(m))
    if missing or len(m["protected_frames"]) != 17:
        raise ValueError(f"invalid REM-012.5 manifest fields/protected frames: {missing}")
    if str(m["frame_id"]) in {str(x) for x in m["protected_frames"]}:
        raise ValueError("Frame 01 cannot protect itself")
    return m


def children(c: MiroClient, board: str, frame: str) -> list[dict[str, Any]]:
    return [x for x in c.list_items(board) if str((x.get("parent") or {}).get("id") or "") == frame]


def frame_connectors(c: MiroClient, board: str, ids: set[str]) -> list[dict[str, Any]]:
    return [x for x in c.list_connectors(board) if str((x.get("startItem") or {}).get("id") or "") in ids and str((x.get("endItem") or {}).get("id") or "") in ids]


def visible(item: dict[str, Any]) -> str:
    raw = canonical_miro_text((item.get("data") or {}).get("content"))
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", raw)).split())


def identity(item: dict[str, Any]) -> str:
    text = visible(item)
    hit = re.search(r"\bG([1-8])\s*·", text)
    if hit: return f"stage:G{hit.group(1)}"
    hit = re.fullmatch(r"G([1-8])\s*[◉⛔△✕✓•]?", text)
    if hit: return f"marker:G{hit.group(1)}"
    return f"{item.get('type')}:{text.casefold()}" if text else ""


def item_payload(src: dict[str, Any], frame: str) -> dict[str, Any]:
    t = str(src.get("type") or "")
    if t not in NATIVE: raise ValueError(f"unsupported redline item type: {t}")
    data = {k: deepcopy(v) for k, v in (src.get("data") or {}).items() if k in {"content", "shape"}}
    p, g, s = src.get("position") or {}, src.get("geometry") or {}, src.get("style") or {}
    allowed = {
        "shape": {"fillColor","fillOpacity","fontFamily","fontSize","textAlign","textAlignVertical","color","borderColor","borderOpacity","borderStyle","borderWidth"},
        "text": {"fillColor","fillOpacity","fontFamily","fontSize","textAlign","color"},
        "sticky_note": {"fillColor","textAlign","textAlignVertical"},
    }[t]
    style = {k: deepcopy(v) for k, v in s.items() if k in allowed}
    if t in {"shape","text"} and style.get("fontSize") is not None: style["fontSize"] = normalize_miro_font_size(style["fontSize"])
    out: dict[str, Any] = {"data": data, "position": {"x": float(p.get("x") or 0), "y": float(p.get("y") or 0), "origin": "center"}, "parent": {"id": frame}}
    if style: out["style"] = style
    out["geometry"] = ({"width": float(g["width"]), "height": float(g["height"])} if t == "shape" else {"width": float(g["width"])})
    return out


def same_item(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    for k, v in (expected.get("data") or {}).items():
        a = (remote.get("data") or {}).get(k)
        if canonical_miro_text(a) != canonical_miro_text(v) if k == "content" else a != v: return False
    if str((remote.get("parent") or {}).get("id") or "") != str((expected.get("parent") or {}).get("id") or ""): return False
    for sec in ("position","geometry"):
        for k, v in (expected.get(sec) or {}).items():
            if k != "origin" and not _close((remote.get(sec) or {}).get(k), v): return False
    for k, v in (expected.get("style") or {}).items():
        a = (remote.get("style") or {}).get(k)
        if isinstance(v, str) and v.startswith("#"):
            if str(a or "").casefold() != v.casefold(): return False
        elif k == "fontSize":
            if not _close(a, v): return False
        elif a != v: return False
    return True


def match(src: dict[str, Any], targets: list[dict[str, Any]], used: set[str]) -> dict[str, Any] | None:
    pool = [x for x in targets if x.get("type") == src.get("type") and str(x.get("id") or "") not in used]
    key = identity(src); exact = [x for x in pool if key and identity(x) == key]
    if len(exact) == 1: return exact[0]
    sp = src.get("position") or {}; sx, sy = float(sp.get("x") or 0), float(sp.get("y") or 0)
    near = sorted((abs(sx-float((x.get("position") or {}).get("x") or 0))+abs(sy-float((x.get("position") or {}).get("y") or 0)), x) for x in pool)
    return near[0][1] if near and near[0][0] <= 25 and (len(near)==1 or near[0][0] < near[1][0]) else None


def connector_payload(src: dict[str, Any], start: str, end: str) -> dict[str, Any]:
    out: dict[str, Any] = {"startItem": {"id": start}, "endItem": {"id": end}}
    for name in ("startItem","endItem"):
        snap = (src.get(name) or {}).get("snapTo")
        if snap: out[name]["snapTo"] = snap
    if src.get("shape"): out["shape"] = src["shape"]
    style = {k: deepcopy(v) for k,v in (src.get("style") or {}).items() if k in {"startStrokeCap","endStrokeCap","strokeColor","strokeStyle","strokeWidth"}}
    if style: out["style"] = style
    caps=[]
    for c in src.get("captions") or []:
        row={k:deepcopy(v) for k,v in c.items() if k in {"content","position"}}
        if "position" in row: row["position"] = normalize_miro_percentage(row["position"])
        if row: caps.append(row)
    if caps: out["captions"] = caps
    return out


def same_connector(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    for name in ("startItem","endItem"):
        if str((remote.get(name) or {}).get("id") or "") != str((expected.get(name) or {}).get("id") or ""): return False
    if expected.get("shape") and remote.get("shape") != expected["shape"]: return False
    for k,v in (expected.get("style") or {}).items():
        a=(remote.get("style") or {}).get(k)
        if isinstance(v,str) and v.startswith("#"):
            if str(a or "").casefold()!=v.casefold(): return False
        elif a!=v: return False
    ac, ec = remote.get("captions") or [], expected.get("captions") or []
    if len(ac)!=len(ec): return False
    return all(canonical_miro_text(a.get("content"))==canonical_miro_text(e.get("content")) and str(a.get("position"))==str(e.get("position")) for a,e in zip(ac,ec))


def reconcile(c: MiroClient, m: dict[str, Any]) -> dict[str, Any]:
    sb,tb,sf,tf = map(str,(m["source_board_id"],m["board_id"],m["source_frame_id"],m["frame_id"]))
    source_frame, target_frame = _get_frame(c,sb,sf), _get_frame(c,tb,tf)
    if str((source_frame.get("data") or {}).get("title") or "") != str(m["source_frame_title"]): raise ValueError("source frame title mismatch")
    for k in ("width","height"):
        if not _close((source_frame.get("geometry") or {}).get(k),(target_frame.get("geometry") or {}).get(k)): raise ValueError(f"source/target frame {k} mismatch")
    src = children(c,sb,sf)
    bad=sorted({str(x.get("type") or "") for x in src if str(x.get("type") or "") not in NATIVE})
    if bad: raise ValueError(f"source contains unsupported items: {bad}")
    src_ids={str(x["id"]) for x in src}; sc=frame_connectors(c,sb,src_ids)
    if len(src)<50 or len(sc)<20: raise ValueError(f"source inventory too small: {len(src)}/{len(sc)}")
    text=" ".join(visible(x) for x in src)
    for phrase in m["source_sentinels"]:
        if str(phrase) not in text: raise ValueError(f"source missing sentinel: {phrase}")
    for phrase in m.get("source_forbidden_sentinels") or []:
        if str(phrase) in text: raise ValueError(f"source contains forbidden sentinel: {phrase}")
    digest=hashlib.sha256(json.dumps([(x.get("type"),identity(x),x.get("position"),x.get("geometry")) for x in src],sort_keys=True,default=str).encode()).hexdigest()
    tgt=children(c,tb,tf); used:set[str]=set(); mapping:dict[str,str]={}; counts={"created":0,"updated":0,"unchanged":0,"deleted":0}
    for s in sorted(src,key=lambda x:(identity(x),str(x.get("id") or ""))):
        payload=item_payload(s,tf); t=match(s,tgt,used)
        if t is None:
            t=c._request("POST",f"boards/{tb}/{EP[str(s['type'])]}",body=payload); tgt.append(t); counts["created"]+=1
        elif same_item(t,payload): counts["unchanged"]+=1
        else:
            t=c._request("PATCH",f"boards/{tb}/{EP[str(s['type'])]}/{t['id']}",body=payload); counts["updated"]+=1
            if not same_item(t,payload): raise ValueError(f"item {t['id']} read-back mismatch")
        used.add(str(t["id"])); mapping[str(s["id"])]=str(t["id"])
    tc=frame_connectors(c,tb,{str(x["id"]) for x in tgt}); usedc:set[str]=set(); cc={"created":0,"updated":0,"unchanged":0,"deleted":0}
    for s in sc:
        start=mapping[str((s.get("startItem") or {})["id"])]; end=mapping[str((s.get("endItem") or {})["id"])]
        payload=connector_payload(s,start,end)
        hits=[x for x in tc if str(x.get("id") or "") not in usedc and str((x.get("startItem") or {}).get("id") or "")==start and str((x.get("endItem") or {}).get("id") or "")==end]
        t=hits[0] if hits else None
        if t is None: t=c.create_connector(tb,payload); tc.append(t); cc["created"]+=1
        elif same_connector(t,payload): cc["unchanged"]+=1
        else:
            t=c.update_connector(tb,str(t["id"]),payload); cc["updated"]+=1
            if not same_connector(t,payload): raise ValueError(f"connector {t['id']} read-back mismatch")
        usedc.add(str(t["id"]))
    extrasc=[x for x in tc if str(x.get("id") or "") not in usedc]; extrasi=[x for x in tgt if str(x.get("id") or "") not in used]
    for x in extrasc: c.delete_connector(tb,str(x["id"])); cc["deleted"]+=1
    for x in extrasi: c.delete_item(tb,str(x["id"])); counts["deleted"]+=1
    return {"source_digest":digest,"source_item_count":len(src),"source_connector_count":len(sc),"items":counts,"connectors":cc}


def apply(c: MiroClient, m: dict[str, Any], sha: str) -> dict[str, Any]:
    board=str(m["board_id"]); protected=[str(x) for x in m["protected_frames"]]
    before=_protected_snapshot(c,board,protected); first=reconcile(c,m)
    if _protected_snapshot(c,board,protected)["digest"]!=before["digest"]: raise ValueError("protected frames changed")
    second=reconcile(c,m)
    if any(second["items"][k] for k in ("created","updated","deleted")) or any(second["connectors"][k] for k in ("created","updated","deleted")): raise ValueError("second reconcile is not zero mutation")
    after=_protected_snapshot(c,board,protected)
    if after["digest"]!=before["digest"] or first["source_digest"]!=second["source_digest"]: raise ValueError("protected/source digest changed")
    return {"status":"PASS","remediation_id":RID,"source_sha":sha,"board_id":board,"frame_id":str(m["frame_id"]),"source_board_id":str(m["source_board_id"]),"source_frame_id":str(m["source_frame_id"]),"source_digest":first["source_digest"],"first_run":first,"second_run":second,"protected_frames":{"count":17,"before_digest":before["digest"],"after_digest":after["digest"],"unchanged":True},"technical_status":"PASS","human_review_status":"PENDING","overall_status":"READY_FOR_HUMAN_REVIEW","merge_allowed":False,"promotion_allowed":False,"release_allowed":False,"gate_approval_allowed":False}


def main(argv: list[str] | None=None) -> int:
    p=argparse.ArgumentParser(); p.add_argument("--manifest",required=True,type=Path); p.add_argument("--report",required=True,type=Path); p.add_argument("--source-sha",required=True); p.add_argument("--apply",action="store_true"); a=p.parse_args(argv)
    try:
        m=load_manifest(a.manifest); result={"status":"PASS","remediation_id":RID,"mode":"validate-only"} if not a.apply else apply(MiroClient(os.environ["MIRO_ACCESS_TOKEN"]),m,a.source_sha)
        code=0
    except Exception as exc:  # noqa: BLE001
        result={"status":"FAIL","remediation_id":RID,"source_sha":a.source_sha,"technical_status":"FAIL","human_review_status":"PENDING","overall_status":"CHANGES_REQUIRED","merge_allowed":False,"promotion_allowed":False,"release_allowed":False,"gate_approval_allowed":False,"error":str(exc)}; code=1
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2),file=sys.stdout if code==0 else sys.stderr); return code


if __name__ == "__main__": raise SystemExit(main())
