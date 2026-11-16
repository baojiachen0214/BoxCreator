import copy
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as E
from pathlib import Path

from PIL import Image, ImageChops
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from shapely.geometry import Polygon

from boxcreator.audit import findings
from boxcreator.demo import make_demo
from boxcreator.geometry import geometry_hash, prepare_scene, validate
from boxcreator.pdf import assemble, inspect_pdf, vector_only
from boxcreator.svg import export_svg
from boxcreator.verify import compare_layers, render_page


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        make_demo(self.root)
        self.data = json.loads((self.root/"net.json").read_text())

    def test_real_hole_survives_triangulation(self):
        scene = prepare_scene(self.data, self.root/"artwork.png")
        p = next(p for p in scene["panels"] if p["id"] == "front")
        shape = Polygon(p["outline"], p["holes"])
        triangles = [Polygon(t) for t in p["triangles"]]
        self.assertAlmostEqual(sum(t.area for t in triangles), shape.area, places=6)
        hole = Polygon(p["holes"][0])
        self.assertTrue(all(t.intersection(hole).area < 1e-7 for t in triangles))
        self.assertEqual(validate(self.data)["material_components"], 1)

    def test_wrong_hinge_and_disconnected_piece_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["panels"][1]["hinge"] = [[60,109],[130,109]]
        with self.assertRaisesRegex(ValueError, "shared panel boundary"): validate(bad)
        bad = copy.deepcopy(self.data)
        # A second independent paper piece must not become an implicit floating panel.
        bad["panels"].append({"id":"loose","outline":[[1,1],[5,1],[5,5],[1,5]]})
        with self.assertRaisesRegex(ValueError, "one root"): validate(bad)

    def test_geometry_digest_tracks_structure_not_timing(self):
        other = copy.deepcopy(self.data)
        other["texture"] = "a-different-print.png"
        other["panels"][1]["stage"] = [.2,.65]
        other["panels"].reverse()
        self.assertEqual(geometry_hash(self.data), geometry_hash(other))
        other["panels"][0]["angle_deg"] = -80
        self.assertNotEqual(geometry_hash(self.data), geometry_hash(other))

    def test_layered_pdf_is_vector_and_dimensionally_identical(self):
        report = vector_only(self.root/"layered.pdf")
        self.assertEqual(report["layers"], ["01_Artwork", "02_Dieline"])
        self.assertAlmostEqual(report["pages"][0]["size_mm"][0],200, places=4)
        self.assertEqual(report["pages"][0]["unembedded_fonts"],0)
        root = PdfReader(self.root/"layered.pdf").trailer["/Root"]
        groups = root["/OCProperties"]["/OCGs"]
        self.assertEqual(groups[1].get_object()["/Usage"]["/Print"]["/PrintState"], "/OFF")

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler not installed")
    def test_actual_layer_toggles_render_like_pure_sources(self):
        report = compare_layers(*(self.root/n for n in ("artwork.pdf","dieline.pdf","layered.pdf")))
        self.assertEqual(len(report["layer_comparisons"]),2)
        self.assertTrue(all(p["pixels_equal_to_source"] for p in report["layer_comparisons"]))

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler not installed")
    def test_all_pages_of_a_variant_book_have_independent_layers(self):
        for name in ("artwork","dieline"):
            reader = PdfReader(self.root/f"{name}.pdf"); writer = PdfWriter()
            writer.add_page(reader.pages[0]); writer.add_page(reader.pages[0])
            writer.write(self.root/f"{name}-book.pdf")
        assemble(self.root/"artwork-book.pdf",self.root/"dieline-book.pdf",self.root/"book.pdf")
        report = compare_layers(self.root/"artwork-book.pdf",self.root/"dieline-book.pdf",self.root/"book.pdf")
        self.assertEqual({p["page"] for p in report["layer_comparisons"]},{1,2})
        self.assertEqual(len(report["layer_comparisons"]),4)

    def test_raster_nested_in_form_is_rejected(self):
        path = self.root/"raster.pdf"
        c = canvas.Canvas(str(path))
        c.beginForm("nested")
        c.drawImage(ImageReader(Image.new("RGB", (4,4), "red")),0,0,10,10)
        c.endForm(); c.doForm("nested"); c.showPage(); c.save()
        self.assertEqual(inspect_pdf(path)["pages"][0]["image_xobjects"],1)
        with self.assertRaisesRegex(ValueError, "Raster"): vector_only(path)

    def test_inline_image_is_rejected(self):
        w = PdfWriter(); p = w.add_blank_page(100,100)
        s = DecodedStreamObject()
        s.set_data(b"q BI /W 1 /H 1 /BPC 8 /CS /RGB ID \xff\x00\x00 EI Q")
        p[NameObject("/Contents")] = w._add_object(s)
        p[NameObject("/Resources")] = DictionaryObject()
        path = self.root/"inline.pdf"; w.write(path)
        self.assertEqual(inspect_pdf(path)["pages"][0]["inline_images"],1)
        with self.assertRaises(ValueError): vector_only(path)

    def test_never_rescales_mismatched_pdf(self):
        path = self.root/"wrong.pdf"
        c = canvas.Canvas(str(path),pagesize=(100,100));c.line(0,0,100,100);c.showPage();c.save()
        with self.assertRaisesRegex(ValueError,"never scale"):
            assemble(self.root/"artwork.pdf",path,self.root/"bad.pdf")

    def test_existing_layers_need_explicit_vector_resolution(self):
        with self.assertRaisesRegex(ValueError,"pure, annotation-free"):
            assemble(self.root/"layered.pdf",self.root/"dieline.pdf",self.root/"bad.pdf")

    @unittest.skipUnless(shutil.which("pdftocairo"), "Poppler not installed")
    def test_svg_editable_layers_and_no_duplicate_ids(self):
        path = self.root/"layered.svg"
        export_svg(self.root/"artwork.pdf",self.root/"dieline.pdf",path)
        tree = E.parse(path); ns = "{http://www.w3.org/2000/svg}"
        self.assertFalse(list(tree.iter(ns+"image")))
        self.assertEqual([n.get("id") for n in tree.getroot()], ["01_Artwork","02_Dieline"])
        ids = [n.get("id") for n in tree.iter() if n.get("id")]
        self.assertEqual(len(ids),len(set(ids)))

    @unittest.skipUnless(shutil.which("rsvg-convert") and shutil.which("pdftoppm") and shutil.which("pdftocairo"), "SVG renderer and Poppler required")
    def test_svg_render_keeps_the_complete_net_at_the_pdf_scale(self):
        path = self.root/"layered.svg"
        export_svg(self.root/"artwork.pdf",self.root/"dieline.pdf",path)
        render_page(self.root/"layered.pdf",self.root/"pdf.png",dpi=101.6)
        with Image.open(self.root/"pdf.png") as pdf:
            w,h = pdf.size
            subprocess.run(["rsvg-convert","-w",str(w),"-h",str(h),"-b","white","-o",str(self.root/"svg.png"),str(path)],check=True)
            with Image.open(self.root/"svg.png") as svg:
                delta = ImageChops.difference(pdf.convert("RGB"),svg.convert("RGB"))
                # Permit renderer antialiasing; clipping or a 4/3 scale error affects large areas.
                r,g,b = delta.split()
                histogram = ImageChops.lighter(ImageChops.lighter(r,g),b).histogram()
                errors = sum(histogram[31:])
                self.assertLess(errors/(w*h),.02)

    def test_publication_scan_reports_rules_without_values(self):
        token = "gh" + "p_" + "A"*30
        path = "/" + "Users" + "/private-person/project/file"
        self.assertIn("provider-token",findings(token))
        self.assertIn("private-machine-path",findings(path))
        self.assertFalse(findings("Never commit credentials. Use a secure store."))


if __name__ == "__main__": unittest.main()
