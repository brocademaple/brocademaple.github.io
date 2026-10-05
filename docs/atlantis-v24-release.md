# Atlantis Gallery V2.4 public preview

This release exposes the existing V2.4 crescent campus at `/gallery-v2/` and the original Blender renders at `/gallery-v2/renders.html`. The previous `/gallery/` remains intact.

The Blender source and both exported GLBs contain 607,242 evaluated triangles. The 42 artwork JPEGs remain byte-identical, their aspect ratios and UVs are verified, and all eight navigation markers match the master. Five critical round-trip routes and six walking spawns pass the local navigation regressions.

The release fixes a missing `build-version.json`, versions the runtime JavaScript, aligns the viewer with AgX tone mapping, adjusts glass and fill lighting, adds an original-render viewer and provides a small-screen entry that does not eagerly load the 55.8 MiB GLB. Mobile users may opt into 3D. This is a public preview; glass transmission, soft indirect lighting, full-campus human navigation and physical-device performance remain review items.

Validation: Hugo 0.164.0 production build; browser UI navigation, artwork details, WASD and distinct quality profiles; 390×844 screenshot with no overflow; source/export geometry audit; original image bytes and decoded PBR pixels; beginner lab `.blend` and `.glb` generation. Evidence is in `docs/evidence/atlantis-v24/`.

Personal tutorial: https://my.feishu.cn/docx/RxIsdvxU2ovh9txxYcPc2ZjynLf

The editable master is 121 MiB and remains at `/Users/eee/Desktop/works/atlantis-v24/atlantis-gallery-master-v2-polish.blend`; it is above GitHub's ordinary-file limit. This commit contains the web GLB and implementation scripts. A clone alone cannot reconstruct all original Blender source assets; the local master and texture/reference archive remain the source of truth.

Local viewing: `python3 -m http.server 8033 --bind 127.0.0.1 --directory /Users/eee/Desktop/works/atlantis-v24/output`.
