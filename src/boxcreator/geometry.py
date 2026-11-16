"""Reviewed manufacturing coordinates: millimetres, origin at lower left."""
import hashlib
import json
import math
from pathlib import Path

from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def geometry_hash(data):
    # Artwork, file paths, stage timing and notes cannot alter this geometry digest.
    fields = ("id", "outline", "holes", "parent", "hinge", "angle_deg")
    payload = {"canvas_mm": data["canvas_mm"], "panels": [
        {k: p[k] for k in fields if k in p} for p in sorted(data["panels"], key=lambda p: p["id"])]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(data):
    w, h = data["canvas_mm"]
    if not all(math.isfinite(v) and v > 0 for v in (w, h)):
        raise ValueError("canvas_mm must contain positive finite dimensions")
    panels = data["panels"]
    if not panels or any(not isinstance(p.get("id"), str) or not p["id"] for p in panels) or len({p["id"] for p in panels}) != len(panels):
        raise ValueError("Panel IDs must be unique and nonempty")
    lookup = {p["id"]: p for p in panels}
    shapes, solids = {}, {}
    roots = []
    for p in panels:
        coords = p["outline"] + [xy for ring in p.get("holes", []) for xy in ring]
        if not all(len(xy) == 2 and all(math.isfinite(v) for v in xy) for xy in coords):
            raise ValueError(f"Invalid coordinates: {p['id']}")
        outer = Polygon(p["outline"])
        solid = Polygon(p["outline"], p.get("holes", []))
        if not outer.is_valid or not solid.is_valid or solid.area <= 0:
            raise ValueError(f"Invalid polygon or hole: {p['id']}")
        if not box(0, 0, w, h).buffer(1e-6).covers(outer):
            raise ValueError(f"Panel outside canvas: {p['id']}")
        if any(not outer.contains(Polygon(r)) for r in p.get("holes", [])):
            raise ValueError(f"Hole must lie strictly inside panel: {p['id']}")
        if not p.get("parent"):
            roots.append(p["id"])
        shapes[p["id"]], solids[p["id"]] = outer, solid
    if len(roots) != 1:
        raise ValueError("Use one root panel per net; separate variants into separate manifests")
    for i, a in enumerate(panels):
        for b in panels[i + 1:]:
            if shapes[a["id"]].intersection(shapes[b["id"]]).area > 1e-5:
                raise ValueError(f"Overlapping flat panels: {a['id']}, {b['id']}")
        parent = a.get("parent")
        if not parent:
            continue
        if parent not in lookup or parent == a["id"]:
            raise ValueError(f"Unknown or self parent: {a['id']}")
        points = a["hinge"]
        if len(points) != 2 or not all(len(xy) == 2 and all(math.isfinite(v) for v in xy) for xy in points):
            raise ValueError(f"Hinge needs two finite 2D endpoints: {a['id']}")
        hinge = LineString(points)
        if hinge.length < 1e-6:
            raise ValueError(f"Hinge needs two distinct endpoints: {a['id']}")
        for pid in (a["id"], parent):
            if not solids[pid].boundary.buffer(.01).covers(hinge):
                raise ValueError(f"Hinge is not on shared panel boundary: {a['id']}")
        angle = a["angle_deg"]
        if not math.isfinite(angle) or abs(angle) > 180:
            raise ValueError(f"Invalid fold angle: {a['id']}")
        start, end = a.get("stage", [.1, .6])
        if not 0 <= start < end <= .8:
            raise ValueError("Fold stages must be within 0..0.8; leave time for the orbit")
        seen = {a["id"]}
        nxt = parent
        while nxt:
            if nxt in seen:
                raise ValueError("Fold graph contains a cycle")
            seen.add(nxt)
            if nxt not in lookup:
                raise ValueError(f"Unknown parent: {nxt}")
            nxt = lookup[nxt].get("parent")
    net = unary_union(list(solids.values()))
    if net.geom_type != "Polygon":
        raise ValueError("Flat net must be one physically connected piece")
    return {"geometry_sha256": geometry_hash(data), "panel_count": len(panels),
            "material_components": 1, "window_count": sum(len(p.get("holes", [])) for p in panels)}


def prepare_scene(data, texture):
    report = validate(data)
    result = dict(data, texture=str(Path(texture).resolve()), geometry_report=report)
    result["panels"] = []
    for panel in data["panels"]:
        shape = Polygon(panel["outline"], panel.get("holes", []))
        triangles = constrained_delaunay_triangles(shape)
        coords = [list(t.exterior.coords)[:3] for t in triangles.geoms if shape.covers(t)]
        if abs(sum(Polygon(t).area for t in coords) - shape.area) > 1e-5:
            raise ValueError(f"Triangulation lost material: {panel['id']}")
        result["panels"].append(dict(panel, triangles=coords))
    return result
