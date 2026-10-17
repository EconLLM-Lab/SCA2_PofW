# NOT A BINDING

This page explains one choice. The science views in this folder do not use the generative style from the algorithmic-art skill. That includes particle fields, flow fields, noise "neurons" and a glowing brain. This page is the only place where that style may appear, and no sketch ships here either (see the last section).

## What the algorithmic-art skill asks for

The skill asks for a "living algorithm": seeded noise, particles and emergent marks, with "90% algorithmic generation, 10% essential parameters". In that style the beauty is in the process, and a mark is good when it looks good. The seed picks the marks. No measurement does.

## Why the workbench refuses it

The workbench rests on one rule from the source brief: zero fake geometry. A mark on screen must map one-to-one to a real tensor slice, an attention entry, an adapter delta or a SwiGLU pole from a real forward pass. Generative marks break that rule in three ways.

1. **The mark has no referent.** A particle at (x, y) stands for no tensor element. If a reader asks "what is this dot?", there is no answer except "the seed put it there". Each mark in index.html carries a `data-tensor` name and a `<title>`, and the legend gives the tensor or module it will bind to (`BIND` in `model.mjs`).
2. **The motion can't be checked.** Noise moves because time moves. The parts in the anatomy figures move only when the forward pass changes, for example after a clamp or a steer. The conservation bar then checks that same pass: the residual inf-norm must be below 1e-3 and the DLA abs gap below 1e-2. A particle field has nothing to conserve, so it can never fail a check, and so it can never be trusted.
3. **It makes the brain metaphor look confirmed.** A cloud of glowing dots shaped like a brain tells the reader that the model is a brain and that we can see it think. Neither claim is true. Cammarata's point is that native neurons are legible as poles of SwiGLU products. A picture that hides the poles inside a pretty cloud works against that point.

## What we use instead

The anatomy skill gives each view a small instrument whose working is the concept: a plate of tensor blocks, a plotting plate with a quadrant III pocket, a contour gauge between two label plates, and a selector wired to a margin gauge. Every height, dot position, pin and needle angle comes from `forward()` in `model.mjs`. Today that function is a seeded toy (d=16, 2 heads, d_ffn=32, 4 layers). It is not Llama and it is not an adapter, and the page says so. When `workbench/src/sca2_workbench/hooks.py` exists, each array is swapped for the named tensor, and the drawing code stays the same.

## Where generative work is allowed

Only on this page, as a sketch titled "NOT A BINDING", and only as a mood study for colour or texture. It must never reach a view that a reader could mistake for a reading of the model. No p5 sketch was made for this study: none was needed, and leaving it out keeps the folder free of a CDN dependency and of marks that bind to nothing.
