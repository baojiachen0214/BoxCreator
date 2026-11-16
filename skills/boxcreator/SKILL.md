---
name: boxcreator
description: Produce or revise complete vector carton dielines and Blender folding/product videos from a dieline PDF, a short style brief and optional references. Use for packaging design and its engineering handoff, including layer, vector and fold QA.
---

# BoxCreator

Use within the complete BoxCreator checkout. Resolve the document links relative to this file. The user supplies the PDF and design intent; create the internal geometry manifest yourself.

## Deliverable and decisions

Deliver all faces in a complete 1:1 vector net, editable artwork/process layers, pure artwork and dieline PDFs, editable SVG, packed Blender project, folding/full-orbit MP4 and a truthful acceptance report. Adjust the exact bundle to the user's scope; a concept image is not a finished net.

First inspect the actual PDF, measure dimensions, identify panels and process-line semantics, and check which tools can import and export the required files. A page of separate face references may not be a connected manufacturing net. Ask for missing engineering intent only when it affects the result.

For design, vectorization, print preparation and mechanical interpretation, read [workflow](../../docs/workflow.md). When creating a fold manifest or diagnosing geometry, read [geometry](../../docs/geometry.md). Use actual tools, reference views and small verified samples; avoid guessing a latch from an attractive rendering.

Preserve confirmed dimensions and frozen structure. For a requested full-panel redraw, recompose the artwork instead of patching a cutline. Generate illustrations at the exact panel ratio with clipping handled by geometry. Vectorize into real paths, restore fonts as paths or embedded text, and inspect the export. Cloud processing is an option, not a requirement; it needs authorization for the material being uploaded and must not assume historical account access.

Keep process lines in one named layer separate from artwork from the start. Map the final artwork and geometry to Blender; make windows actual mesh holes. Fold in a physically plausible order and show the complete object throughout the orbit. A kinematic preview does not prove lock engagement or paper strength.

For final checks read [acceptance](../../docs/acceptance.md). For an inherited or stalled task read [recovery](../../docs/recovery.md); use [lessons](../../docs/lessons.md) to diagnose recurrent failure without importing old customer preferences. Never publish raw conversations, keys, account screenshots or client assets as examples.

Use the `boxcreator` CLI described in [README](../../README.md) for repeatable checks. It is a helper, not an automatic PDF interpreter: adapt geometry/modeling when a structure needs curved scores, multiple hinges, locks, thickness or collisions. Keep such adaptations in the private task workspace unless they are intentionally generalized and tested.
