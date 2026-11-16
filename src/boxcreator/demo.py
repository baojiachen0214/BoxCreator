"""Synthetic six-face net: no customer artwork, transcripts or brand assets."""
import json
import math
from pathlib import Path

from reportlab.lib.colors import CMYKColor, CMYKColorSep
from reportlab.pdfgen import canvas

from .geometry import validate
from .pdf import PT_PER_MM as MM, assemble


def make_demo(output):
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    def rect(x, y, w, h): return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]
    hole = [[95+14*math.cos(i*math.pi/24),85+9*math.sin(i*math.pi/24)] for i in range(48)]
    data = {"canvas_mm": [200,230], "panels": [
        {"id":"base", "outline":rect(60,110,70,50)},
        {"id":"front", "outline":rect(60,60,70,50), "holes":[hole], "parent":"base", "hinge":[[60,110],[130,110]], "angle_deg":-90, "stage":[.15,.5]},
        {"id":"back", "outline":rect(60,160,70,50), "parent":"base", "hinge":[[60,160],[130,160]], "angle_deg":90, "stage":[.1,.45]},
        {"id":"left", "outline":rect(10,110,50,50), "parent":"base", "hinge":[[60,110],[60,160]], "angle_deg":90, "stage":[.2,.55]},
        {"id":"right", "outline":rect(130,110,50,50), "parent":"base", "hinge":[[130,110],[130,160]], "angle_deg":-90, "stage":[.25,.6]},
        {"id":"lid", "outline":rect(60,10,70,50), "parent":"front", "hinge":[[60,60],[130,60]], "angle_deg":-90, "stage":[.55,.75]}
    ]}
    validate(data)
    (out/"net.json").write_text(json.dumps(data, indent=2))
    art = canvas.Canvas(str(out/"artwork.pdf"), pagesize=(200*MM,230*MM))
    art.scale(MM,MM)
    colors = [(.75,.1,.1,0),(.05,.6,.25,0),(.05,.35,.75,0),(.4,.05,.55,0),(.15,.1,.6,0),(.25,.65,.05,0)]
    for i,p in enumerate(data["panels"]):
        art.saveState(); path=art.beginPath(); path.moveTo(*p["outline"][0])
        for xy in p["outline"][1:]: path.lineTo(*xy)
        path.close()
        for ring in p.get("holes",[]):
            path.moveTo(*ring[0])
            for xy in ring[1:]: path.lineTo(*xy)
            path.close()
        art.clipPath(path,stroke=0,fill=0,fillMode=0)
        art.setFillColor(CMYKColor(*colors[i])); art.rect(0,0,200,230,stroke=0,fill=1)
        art.setStrokeColor(CMYKColor(0,0,0,0)); art.setLineWidth(.7)
        x0,y0=p["outline"][0]
        for k in range(6): art.circle(x0+7+k*9,y0+8+(k%3)*8,3,stroke=1,fill=0)
        art.restoreState()
    art.showPage(); art.save()
    die=canvas.Canvas(str(out/"dieline.pdf"),pagesize=(200*MM,230*MM));die.scale(MM,MM)
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    net=unary_union([Polygon(p["outline"],p.get("holes",[])) for p in data["panels"]])
    die.setStrokeColor(CMYKColorSep(0,1,0,0,spotName="CutContour"));die.setStrokeOverprint(True);die.setLineWidth(.12)
    for ring in [net.exterior,*net.interiors]:
        q=die.beginPath();q.moveTo(*ring.coords[0])
        for xy in list(ring.coords)[1:]:q.lineTo(*xy)
        q.close();die.drawPath(q)
    die.setStrokeColor(CMYKColorSep(1,0,0,0,spotName="Crease"));die.setDash(1.2,.7)
    for p in data["panels"]:
        if p.get("parent"):die.line(*p["hinge"][0],*p["hinge"][1])
    die.showPage();die.save()
    assemble(out/"artwork.pdf",out/"dieline.pdf",out/"layered.pdf")
    return out
