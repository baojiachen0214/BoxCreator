"""Observable output checks; deliberately not a print-shop or physical-fit certificate."""
import hashlib
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

from .pdf import inspect_pdf, isolate_layer, normalized


def render_page(source, output, page=1, dpi=144):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp)/"page"
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi),
                        "-singlefile", "-png", str(source), str(prefix)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        output.write_bytes(prefix.with_suffix(".png").read_bytes())


def compare_layers(artwork, dieline, layered, dpi=96):
    from pypdf import PdfReader
    inputs = [Path(p) for p in (artwork, dieline, layered)]
    reports = [inspect_pdf(p) for p in inputs]
    if reports[2]["layers"] != ["01_Artwork", "02_Dieline"]:
        raise ValueError("Expected exactly the two named delivery layers")
    if len({len(r["pages"]) for r in reports}) != 1:
        raise ValueError("Page counts differ")
    if any(p["image_xobjects"] or p["inline_images"] for r in reports for p in r["pages"]):
        raise ValueError("Raster content remains")
    for path in inputs:
        for p in PdfReader(path).pages: normalized(p)
    comparisons = []
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        for i, label in enumerate(("artwork", "dieline")):
            isolated = tmp/f"{label}.pdf"
            isolate_layer(layered, isolated, i)
            for page in range(1, len(reports[0]["pages"])+1):
                for p in range(3):
                    if any(abs(a-b) > .004 for a,b in zip(reports[0]["pages"][page-1]["size_mm"],
                                                         reports[p]["pages"][page-1]["size_mm"])):
                        raise ValueError("Page dimensions changed")
                render_page(inputs[i], tmp/"source.png", page, dpi)
                render_page(isolated, tmp/"isolated.png", page, dpi)
                with Image.open(tmp/"source.png") as a, Image.open(tmp/"isolated.png") as b:
                    equal = a.size == b.size and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None
                comparisons.append({"page": page, "layer": label, "pixels_equal_to_source": equal})
                if not equal: raise ValueError(f"Layer toggling changes source appearance: {label}, page {page}")
    return {"raster_content": False, "dimensions_unchanged": True, "layer_comparisons": comparisons,
            "manual_review_required": ["Visual design and panel orientation", "Cut/fold semantics and source fidelity",
                "Printer color profile, spot separations, fonts and bleed", "Physical paper sample and closure fit"]}


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()
