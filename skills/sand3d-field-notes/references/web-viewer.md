# A model in a browser: three.js on GitHub Pages, and how to test it

What `index.html` in `IAFahim/liminal-arena` does, with what it took to get right. three.js r187 from the npm package, Chromium 155, Firefox 158, a GeForce RTX 3060.

## Serving it

- GitHub Pages, from a branch's root, with one call: `gh api --method POST repos/<owner>/<repo>/pages -f 'source[branch]=main' -f 'source[path]=/'`. It answers with `html_url`. Then `gh api repos/<owner>/<repo>/pages/builds/latest` until `status` is `built`: 31 s for the first build. `gh repo view` has no Pages field; ask `pages` (a 404 means none).
- An empty `.nojekyll` in the root: no Jekyll pass, so `vendor/` is served as it lies. A `.glb` comes back as `model/gltf-binary` and a module as `application/javascript`, which is what `import` needs.
- Every address in the page is relative (`./vendor/...`, `models/...`): the site lives under `https://<owner>.github.io/<repo>/`, a sub-path.
- three.js is kept whole in `vendor/three/`: `LICENSE`, `build/three.core.js`, `build/three.module.js`, and the four addons under `examples/jsm/` that the page and GLTFLoader import. 2.3 MB raw, about 460 KB gzipped; the npm package ships no `.min.js`. `three.module.js` imports `./three.core.js` and the addons import `three` by name, so the page carries an import map. Check the tarball's sha512 against the registry's before vendoring.

## What a GLB needs in a viewer

- The design plates (`Markers`) are hidden at load; the file itself is not touched.
- The file's 24 point lamps are photometric (271.757, see `dressing-and-export.md`), hundreds of times too dim for a daylit scene. The viewer takes each one out and hangs a spot light in its place, as bright as the lit ceiling tile above it. The file stays as it is; a viewer that wants other lights makes them.
- A browser has no bounce light. A room lit only by its tiles would be black but for them. The viewer adds a light from straight overhead that shines nothing, and its shadow map is read a second time by every material (`onBeforeCompile`): where a roof is in the way, a warm glow is added. The lamp cone is found by casting 16 rays from each lamp to the nearest wall, so a light without shadows stays in its own room.

## WebGL 2's limits, and how to count against them

- WebGL 2 promises every machine 15 varying vectors, 16 texture units, and 224 and 256 uniform vectors in the fragment and the vertex stage.
- Each shadow-casting light takes one texture unit and one varying. 24 shadow-casting spot lights and 4 directional ones did not link: `THREE.WebGLProgram: Shader Error ... Could not pack varying vMapUv`, then `useProgram: program not valid` on every draw, and a black slab where the arena was.
- Five shadow maps (a sun, three sky lights, the overhead one) leave the arena's programs at 10 of 15 varyings, 8 of 16 samplers, 194 of 224 fragment vectors and 70 of 256 vertex vectors.
- **The software renderer in headless Chromium is not the minimum.** It reports 31 varyings, 32 texture units and 4096 uniform vectors.
- Count what a program uses after it is compiled, per stage, because the limit is per stage: link its vertex shader with its fragment shader and count the active uniforms (each scalar or vector one, a matrix 2 to 4), then link the vertex shader alone with `#version 300 es` + `void main(){}` and count again: the difference is the fragment stage's. `getProgramParameter(program, gl.ACTIVE_VARYINGS)` is no use for varyings: it counts only those in a transform-feedback list, and reads 0.
- 323 draw calls on the aerial, 1.5 ms a frame at 1600 × 857 on the RTX 3060.

## three.js r187: what is not where it was

- `PCFSoftShadowMap` is removed: it warns and falls back to `PCFShadowMap`. Name `PCFShadowMap` yourself.
- `Object3D` has no `setVisible()`: set `.visible`.
- `LightShadow.intensity` exists, and `getShadow()` in the shader takes a shadow intensity.
- A spot light's `distance` is not a hard cutoff: it has a window, `pow2(saturate(1 - pow4(d / cutoff)))`, which left the floor right under a lamp at 11%. Pass `distance = 0` and shape the cone by geometry.
- `LinearToneMapping` is exposure times the colour, then clipped, the same as Blender's `Standard` view with its exposure in stops. So the numbers of a Cycles picture carry over: a directional light's intensity is irradiance flat-on (the sun's is its strength on level ground over the sun's height), and `Color.setRGB` takes linear values where a hex string is sRGB.
- A sky dome must be `toneMapped: false`, or the dusk exposure (8 here) turns it white.
- Fog is mixed in after tone mapping, in display colours: its colour is a colour as seen, not a light. Its start was moved with the camera (`max(base, distance from the arena - its radius)`), or the aerial, 180 m back, washed out.

## OrbitControls

- A fixed `maxPolarAngle = PI / 2 - 0.01` keeps a camera out of the floor, and quietly lifted three of eight preset cameras, those whose eye is below what they look at, by up to 0.8 m. Take the limit from a floor height, the target's height and the current distance instead: `acos((floor - target.y) / distance)`.
- `start` fires on a pointer down and on a wheel turn: cancel a camera glide there.
- After a drag the damping keeps dispatching `change` for two or three seconds while each frame still moves the camera by more than a millimetre. A page that draws only on `change` settles by itself.

## Framing

- A view that must hold the whole model is fitted to the window it is opened in, and the first shape is not always the last: headless Chromium opened at 1600 × 913 and resized to 1600 × 1000 moments later. Fit again on `resize` while the camera has not been moved by hand.
- Fit by halving the distance until every corner of the model's box clears the writing on the page, the bars measured with `getBoundingClientRect()`. One multiplication by the overshoot leaves the model half the size it could be, because the near corners grow faster than the far ones shrink.

## The writing on the page

- White text needs a dark backing over a sunlit floor: the title and the hint sit on the same 80% black glass as the buttons. Text shadows alone were unreadable over pale ground.

## Testing a viewer

- **Headless Chromium, software WebGL, with the console**: `chromium --headless=new --no-first-run --user-data-dir=<dir> --window-size=W,H --hide-scrollbars --virtual-time-budget=8000 --screenshot=out.png --enable-logging=stderr --v=0 <url>`. It prints the page's console as `INFO:CONSOLE` lines; count `useProgram: program not valid` for programs that failed. Two to five seconds a picture, any window shape.
- **The real card**: add `--ignore-gpu-blocklist --enable-gpu --use-angle=gl`, and `WEBGL_debug_renderer_info` names it (`ANGLE (NVIDIA Corporation, NVIDIA GeForce RTX 3060 ...)`).
- **Real input**: `chromedriver --port=<p>`, then the WebDriver protocol over HTTP from Python's `urllib`: `POST /session` with `goog:chromeOptions.args`; `POST /session/:id/actions` with a pointer (`pointerMove`, `pointerDown`, `pause`, `pointerUp`) or a wheel (`scroll`); `POST /session/:id/window/rect` to resize the window; `GET /session/:id/screenshot`; `POST /session/:id/execute/sync` to read the page. A frame's cost: 30 draws, then one `readPixels` that waits for the card.
- The in-app browser of the agent harness (ZCode) never fired `requestAnimationFrame` in this environment: screenshots and evaluates that wait for a frame hang until timeout, while a plain `execute` works. Test in headless Chromium or through chromedriver.
- **Firefox**: `firefox --headless --no-remote --profile <dir> --window-size=W,H --screenshot out.png <url>` takes the picture the moment the page has loaded, before a model arrives, and does not capture a WebGL canvas at all (the page's background shows where it should be, while a `readPixels` from the same context reads the scene). Hold the load event open with a `<script defer src="/hold.js">` that the server answers late, and have the page post `canvas.toDataURL()` in the same task as its last draw.

## The light table, for a viewer that matches the pictures

| | day | dusk |
|---|---|---|
| sun on level ground | 3.2 | 0 |
| what the sky gives a level white surface | 0.42 | 0.027 |
| what the ground throws back at a wall | 0.4 | 0.035 |
| a room's glow | 0.4 | 0.25 |
| exposure | 0.87 | 8 |
| sky colour of the light | (0.45, 0.62, 1) | (0.5, 0.55, 1) |
| zenith, horizon | #6480a9, #8fb0d4 | #797d9a, #9698b4 |
| haze, from and to, metres | 40, 700 | 300, 2600 |

The sky is three directional lights 40 degrees up, a third of a turn apart, each casting shadows so a roof still keeps the sky out of a room. With these, the viewer's Mid, West lane, Store and Lookout line up with the README's pictures to the pixel.
