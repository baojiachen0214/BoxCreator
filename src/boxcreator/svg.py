"""Export each pure PDF, then put all process paths in one SVG layer."""
import re
import subprocess
import tempfile
import xml.etree.ElementTree as E
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
INK = "http://www.inkscape.org/namespaces/inkscape"
E.register_namespace("", SVG)
E.register_namespace("inkscape", INK)


def export_svg(artwork, dieline, output):
    from pypdf import PdfReader
    from .pdf import normalized, vector_only
    for p in (artwork, dieline):
        if len(vector_only(p)["pages"]) != 1:
            raise ValueError("SVG export takes one variant/page at a time")
        normalized(PdfReader(p).pages[0])
    with tempfile.TemporaryDirectory() as tmp:
        sources = []
        for i, pdf in enumerate((artwork, dieline)):
            dest = Path(tmp) / f"layer{i}.svg"
            subprocess.run(["pdftocairo", "-svg", str(pdf), str(dest)], check=True)
            src = E.parse(dest).getroot()
            if list(src.iter(f"{{{SVG}}}image")):
                raise ValueError("SVG export contains raster images")
            ids = {n.get("id"): f"L{i}_{n.get('id')}" for n in src.iter() if n.get("id")}
            for n in src.iter():
                for k, v in list(n.attrib.items()):
                    if k == "id": v = ids[v]
                    else:
                        v = re.sub(r"url\(#([^)]*)\)", lambda m: f"url(#{ids.get(m[1], m[1])})", v)
                        if v.startswith("#"): v = "#" + ids.get(v[1:], v[1:])
                    n.set(k, v)
            sources.append(src)
        if sources[0].get("viewBox") != sources[1].get("viewBox"):
            raise ValueError("SVG layer coordinate systems differ")
        root = E.Element(f"{{{SVG}}}svg", {k: sources[0].get(k) for k in ("width", "height", "viewBox")})
        for label, source in zip(("01_Artwork", "02_Dieline"), sources):
            group = E.SubElement(root, f"{{{SVG}}}g", {"id": label,
                f"{{{INK}}}groupmode": "layer", f"{{{INK}}}label": label})
            # PDF exports use pt; nested pt dimensions would be reinterpreted in CSS px
            # and enlarge the content by 4/3. Use the shared parent viewport instead.
            source.set("width", "100%"); source.set("height", "100%")
            group.append(source)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        E.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
