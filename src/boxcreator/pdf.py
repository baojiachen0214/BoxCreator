"""Vector-preserving assembly. No image tracing or guessed process-line semantics."""
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject as A, DecodedStreamObject as S,
                          DictionaryObject as D, FloatObject as F, NameObject as N,
                          TextStringObject as T)

PT_PER_MM = 72 / 25.4


def normalized(page):
    if page.rotation or float(page.get("/UserUnit", 1)) != 1 or tuple(page.mediabox.lower_left) != (0, 0):
        raise ValueError("Normalize page rotation, UserUnit and page origin before assembly; re-check dimensions")


def inspect_pdf(path):
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        counts = {"image_xobjects": 0, "inline_images": 0, "rgb_operations": 0,
                  "cmyk_operations": 0, "unembedded_fonts": 0}
        seen = set()

        def obj(value):
            return value.get_object() if hasattr(value, "get_object") else value

        def scan(stream, resources):
            from pypdf.generic import ContentStream
            resources = obj(resources)
            used_fonts = set()
            current_font = None
            for operands, op in ContentStream(stream, reader).operations:
                if op == b"INLINE IMAGE": counts["inline_images"] += 1
                if op in (b"rg", b"RG"): counts["rgb_operations"] += 1
                if op in (b"k", b"K"): counts["cmyk_operations"] += 1
                if op == b"Tf": current_font = operands[0]
                if op in (b"Tj", b"TJ", b"'", b'"') and current_font: used_fonts.add(current_font)
            fonts = obj(resources.get("/Font", {}))
            for name in used_fonts:
                font = obj(fonts[name])
                descendant = obj(font.get("/DescendantFonts", [font]))[0]
                desc = obj(obj(descendant).get("/FontDescriptor", {}))
                if not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                    counts["unembedded_fonts"] += 1
            for ref in obj(resources.get("/XObject", {})).values():
                xobj = obj(ref)
                if id(xobj) in seen: continue
                seen.add(id(xobj))
                if xobj.get("/Subtype") == "/Image": counts["image_xobjects"] += 1
                if xobj.get("/Subtype") == "/Form": scan(xobj, xobj.get("/Resources", resources))
            # Soft-mask transparency can hide an image in an ExtGState Form.
            for ref in obj(resources.get("/ExtGState", {})).values():
                state = obj(ref); mask = obj(state.get("/SMask", {}))
                if isinstance(mask, dict) and "/G" in mask:
                    group = obj(mask["/G"])
                    if id(group) not in seen:
                        seen.add(id(group)); scan(group, group.get("/Resources", resources))
            for ref in obj(resources.get("/Pattern", {})).values():
                pattern = obj(ref)
                if pattern.get("/PatternType") == 1 and id(pattern) not in seen:
                    seen.add(id(pattern)); scan(pattern, pattern.get("/Resources", resources))

        contents = page.get_contents()
        if contents is not None: scan(contents, page.get("/Resources", {}))
        unit = float(page.get("/UserUnit", 1))
        pages.append(dict(size_mm=[float(page.mediabox.width) * unit / PT_PER_MM,
                                   float(page.mediabox.height) * unit / PT_PER_MM],
                          rotation=page.rotation, user_unit=unit,
                          origin=list(map(float, page.mediabox.lower_left)), **counts))
    oc = reader.trailer["/Root"].get("/OCProperties", {})
    oc = oc.get_object() if hasattr(oc, "get_object") else oc
    groups = oc.get("/OCGs", [])
    return {"pages": pages, "layers": [str(g.get_object()["/Name"]) for g in groups],
            "has_output_intent": bool(reader.trailer["/Root"].get("/OutputIntents"))}


def vector_only(path):
    report = inspect_pdf(path)
    if any(p["image_xobjects"] or p["inline_images"] for p in report["pages"]):
        raise ValueError(f"Raster content remains in {Path(path).name}; converting a container is not vectorization")
    return report


def assemble(artwork, dieline, output):
    vector_only(artwork)
    vector_only(dieline)
    art, die = PdfReader(artwork), PdfReader(dieline)
    if len(art.pages) != len(die.pages): raise ValueError("Artwork and dieline page counts differ")
    for reader in (art, die):
        if reader.trailer["/Root"].get("/OCProperties") or any(p.get("/Annots") for p in reader.pages):
            raise ValueError("Use pure, annotation-free source PDFs; resolve existing layers as vectors first")
    writer = PdfWriter()
    layers = []
    for label, printable in [("01_Artwork", True), ("02_Dieline", False)]:
        obj = D({N("/Type"): N("/OCG"), N("/Name"): T(label),
                 N("/Usage"): D({N("/Print"): D({N("/PrintState"): N("/ON" if printable else "/OFF")})})})
        layers.append(writer._add_object(obj))
    writer._root_object[N("/OCProperties")] = D({N("/OCGs"): A(layers), N("/D"): D({
        N("/BaseState"): N("/ON"), N("/Order"): A(layers), N("/ON"): A(layers),
        N("/AS"): A([D({N("/Event"): N("/Print"), N("/Category"): A([N("/Print")]), N("/OCGs"): A(layers)})])})})
    writer._root_object[N("/PageMode")] = N("/UseOC")
    for ap, dp in zip(art.pages, die.pages):
        normalized(ap); normalized(dp)
        for key in ("/MediaBox", "/CropBox", "/TrimBox", "/BleedBox"):
            av = ap.get(key, ap.mediabox); dv = dp.get(key, dp.mediabox)
            if any(abs(float(x) - float(y)) > .01 for x, y in zip(av, dv)):
                raise ValueError(f"Mismatched {key}; never scale a dieline to fit artwork")
        p = writer.add_blank_page(float(ap.mediabox.width), float(ap.mediabox.height))
        forms = D()
        for name, source, oc in [("/Artwork", ap, layers[0]), ("/Dieline", dp, layers[1])]:
            contents = source.get_contents()
            f = S(); f.set_data(contents.get_data() if contents is not None else b"")
            f.update({N("/Type"): N("/XObject"), N("/Subtype"): N("/Form"),
                      N("/BBox"): A([F(x) for x in source.mediabox]),
                      N("/Resources"): source.get("/Resources", D()).clone(writer), N("/OC"): oc})
            if "/Group" in source: f[N("/Group")] = source["/Group"].clone(writer)
            forms[N(name)] = writer._add_object(f)
        p[N("/Resources")] = D({N("/XObject"): forms})
        stream = S(); stream.set_data(b"q /Artwork Do Q\nq /Dieline Do Q")
        p[N("/Contents")] = writer._add_object(stream)
        for key in ("/TrimBox", "/BleedBox", "/CropBox"):
            if key in ap: p[N(key)] = ap[key].clone(writer)
    if "/OutputIntents" in art.trailer["/Root"]:
        writer._root_object[N("/OutputIntents")] = art.trailer["/Root"]["/OutputIntents"].clone(writer)
    writer.add_metadata({"/Title": "BoxCreator - layered vector dieline", "/Creator": "BoxCreator"})
    writer.compress_identical_objects()
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    writer.write(output)


def isolate_layer(source, output, index):
    writer = PdfWriter(clone_from=source)
    groups = writer._root_object["/OCProperties"]["/OCGs"]
    d = writer._root_object["/OCProperties"]["/D"]
    d[N("/BaseState")] = N("/OFF")
    d[N("/ON")] = A([groups[index]])
    d[N("/OFF")] = A([g for i, g in enumerate(groups) if i != index])
    writer.write(output)
