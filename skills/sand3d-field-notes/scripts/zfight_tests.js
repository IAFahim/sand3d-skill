// Two tests of a model as a GPU draws it, for a page that has three.js (r150 or later), a
// renderer, a scene and a camera. Serve this file beside the page and, from its console:
//
//   const { drawOrderTest, crackTest } = await import('./zfight_tests.js');
//   drawOrderTest(THREE, renderer, scene, camera);      // pixels whose surface depends on the order of drawing
//   crackTest(THREE, renderer, scene, camera);          // pixels left empty though drawn all round
//
// `pick` (the fifth argument, default: every mesh) says which objects are the model's: a sky
// dome, a ground plane or writing on the page would else be counted as surfaces and as cover.
// Both put everything back as it was, and return their numbers with two pictures (canvases:
// `ids` and `flips` for the first, `holes` for the second). Neither is a proof: one camera, one
// size. Ask of the views where a player goes, and of the places a camera can get into.

// Which pixels change their surface when the draw order is turned about? That is what
// z-fighting is to a GPU: two faces at one depth, and which of them the pixel shows depends on
// which was drawn first. Every mesh is drawn in a colour of its own (no lights, no tone
// mapping), the picture is read back, and all is drawn again with every order turned about:
// meshes last to first, and the triangles of each mesh last to first. The count and the picture
// of changed pixels come from the one pass over the pixels, so that they cannot disagree.
export function drawOrderTest(THREE, renderer, scene, camera, pick = (o) => o.isMesh) {
  const meshes = [];
  scene.traverse((o) => { if (pick(o)) meshes.push(o); });
  const W = renderer.domElement.width, H = renderer.domElement.height, N = meshes.length;
  if (N > 65535) throw new Error('zfight_tests: more meshes than colours (65,535)');
  const keep = { out: renderer.outputColorSpace, tone: renderer.toneMapping, sort: renderer.sortObjects,
                 auto: renderer.shadowMap.autoUpdate, clear: renderer.getClearColor(new THREE.Color()),
                 alpha: renderer.getClearAlpha() };
  const old = meshes.map((m) => m.material), ids = meshes.map((m, i) => new THREE.MeshBasicMaterial({
    color: new THREE.Color().setRGB(((i + 1) & 255) / 255, (((i + 1) >> 8) & 255) / 255, 0, THREE.LinearSRGBColorSpace),
    fog: false, toneMapped: false, side: m.material.side }));
  const rt = new THREE.WebGLRenderTarget(W, H, { depthBuffer: true, stencilBuffer: false });
  const turn = () => {                                   // every mesh's triangles, last to first
    meshes.forEach((m) => { const g = m.geometry; if (!g.index) return; const a = g.index.array, n = a.length / 3;
      for (let t = 0; t < n / 2; t++) for (let c = 0; c < 3; c++) { const k = 3 * (n - 1 - t) + c, x = a[3 * t + c]; a[3 * t + c] = a[k]; a[k] = x; }
      g.index.needsUpdate = true; });
  };
  function pass(reversed) {
    meshes.forEach((m, i) => { m.material = ids[i]; m.renderOrder = reversed ? N - i : i; });
    if (reversed) turn();
    renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 1); renderer.clear(); renderer.render(scene, camera);
    const buf = new Uint8Array(W * H * 4);
    renderer.readRenderTargetPixels(rt, 0, 0, W, H, buf);
    if (reversed) turn();
    return buf;
  }
  let bufA, bufB;
  try {
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
    renderer.sortObjects = true; renderer.shadowMap.autoUpdate = false;
    bufA = pass(false); bufB = pass(true);
  } finally {
    meshes.forEach((m, i) => { m.material = old[i]; m.renderOrder = 0; });
    ids.forEach((m) => m.dispose()); rt.dispose();
    renderer.outputColorSpace = keep.out; renderer.toneMapping = keep.tone; renderer.sortObjects = keep.sort;
    renderer.shadowMap.autoUpdate = keep.auto; renderer.setClearColor(keep.clear, keep.alpha);
    renderer.setRenderTarget(null);
  }
  // readRenderTargetPixels gives the rows from the bottom up: row 0 is the foot of the picture
  const id = (buf, x, y) => buf[4 * ((H - 1 - y) * W + x)] + 256 * buf[4 * ((H - 1 - y) * W + x) + 1];
  const drawn = new Uint32Array(N + 1), pairs = {};
  let changed = 0, toNothing = 0;
  const box = [W, H, -1, -1];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const a = id(bufA, x, y), b = id(bufB, x, y);
    drawn[a]++;
    if (a === b) continue;
    changed++; if (!a || !b) toNothing++;
    box[0] = Math.min(box[0], x); box[1] = Math.min(box[1], y); box[2] = Math.max(box[2], x); box[3] = Math.max(box[3], y);
    const key = [a, b].sort((p, q) => p - q).map((i) => name(meshes[i - 1])).join(' + ');
    pairs[key] = (pairs[key] || 0) + 1;
  }
  const flips = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) flips[y * W + x] = id(bufA, x, y) !== id(bufB, x, y);
  return { size: [W, H], pixels: W * H, meshes: N, meshesDrawn: drawn.filter((n, i) => n && i).length, changed, toNothing,
           share: changed / (W * H), box: changed ? box : null,
           pairs: Object.entries(pairs).sort((p, q) => q[1] - p[1]).slice(0, 8),
           ids: picture(W, H, (x, y) => { const i = id(bufA, x, y); return i ? [37 * i % 200 + 40, 61 * i % 200 + 40, 89 * i % 200 + 40] : [0, 0, 0]; }),
           flips: picture(W, H, (x, y) => flips[y * W + x] ? [255, 255, 255] : [0, 0, 0]) };
}

// Holes: pixels where nothing of the model is drawn though it is drawn all round them. The
// model alone is drawn in a colour per mesh, so that a pixel left empty is a crack: two faces
// that do not meet, a T-junction. Counted are the empty pixels with all four neighbours drawn
// and those with three (the second can be the corner of an outline, so look at the picture).
export function crackTest(THREE, renderer, scene, camera, pick = (o) => o.isMesh) {
  const meshes = [], hidden = [];
  scene.traverse((o) => { if (o.isMesh) { if (pick(o)) meshes.push(o); else { hidden.push([o, o.visible]); o.visible = false; } } });
  const W = renderer.domElement.width, H = renderer.domElement.height;
  const keep = { auto: renderer.shadowMap.autoUpdate, clear: renderer.getClearColor(new THREE.Color()), alpha: renderer.getClearAlpha() };
  const old = meshes.map((m) => m.material), ids = meshes.map((m, i) => new THREE.MeshBasicMaterial({
    color: new THREE.Color().setRGB(((i + 1) & 255) / 255, (((i + 1) >> 8) & 255) / 255, 0, THREE.LinearSRGBColorSpace),
    fog: false, toneMapped: false, side: m.material.side }));
  const rt = new THREE.WebGLRenderTarget(W, H, { depthBuffer: true, stencilBuffer: false });
  const buf = new Uint8Array(W * H * 4);
  try {
    meshes.forEach((m, i) => { m.material = ids[i]; });
    renderer.shadowMap.autoUpdate = false; renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 1);
    renderer.clear(); renderer.render(scene, camera); renderer.readRenderTargetPixels(rt, 0, 0, W, H, buf);
  } finally {
    meshes.forEach((m, i) => { m.material = old[i]; ids[i].dispose(); });
    renderer.shadowMap.autoUpdate = keep.auto; renderer.setClearColor(keep.clear, keep.alpha); renderer.setRenderTarget(null);
    rt.dispose(); hidden.forEach(([o, v]) => { o.visible = v; });
  }
  const id = (x, y) => buf[4 * ((H - 1 - y) * W + x)] + 256 * buf[4 * ((H - 1 - y) * W + x) + 1];
  const cells = new Uint8Array(W * H), box = [W, H, -1, -1];
  let empty = 0, enclosed = 0, narrow = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (id(x, y)) continue;
    empty++;
    const round = [[1, 0], [-1, 0], [0, 1], [0, -1]].filter(([dx, dy]) => x + dx >= 0 && x + dx < W && y + dy >= 0 && y + dy < H && id(x + dx, y + dy)).length;
    if (round < 3) continue;
    enclosed += round === 4; narrow += round === 3; cells[y * W + x] = 1;
    box[0] = Math.min(box[0], x); box[1] = Math.min(box[1], y); box[2] = Math.max(box[2], x); box[3] = Math.max(box[3], y);
  }
  return { size: [W, H], pixels: W * H, empty, enclosed, narrow, box: enclosed + narrow ? box : null,
           holes: picture(W, H, (x, y) => (cells[y * W + x] ? [255, 0, 0] : id(x, y) ? [60, 60, 60] : [0, 0, 0])) };
}

function name(o) {
  return (o.name || (o.parent && o.parent.name) || '?').replace(/_?\d+$/, '') + '/' + ((o.material && o.material.name) || '').replace(/^kenney_/, '');
}

function picture(W, H, colour) {
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'), im = g.createImageData(W, H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const rgb = colour(x, y), d = 4 * (y * W + x);
    im.data[d] = rgb[0]; im.data[d + 1] = rgb[1]; im.data[d + 2] = rgb[2]; im.data[d + 3] = 255;
  }
  g.putImageData(im, 0, 0);
  return c;
}
