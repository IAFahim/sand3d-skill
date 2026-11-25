# sand3d-skill

Agent skills for building 3D with [sand3d](https://github.com/Sandflow-ai/sand3d) from a terminal: Python programs over Blender's `bpy`.

| Skill | For | Where |
|---|---|---|
| `sand3d-field-notes` | every agent, first: which Python has sand3d, writing programs, textures, export in four formats, Cycles on the GPU, proving a layout by ray casts, packed exports, a viewer on GitHub Pages | `skills/sand3d-field-notes/` |

`sand3d-field-notes`:

- `SKILL.md` — the rules, short enough for small models.
- `scripts/sand3d-env.sh [--make]` — prints the Python that imports sand3d; with `--make`, creates one.
- `scripts/glbinfo.py`, `scripts/glbtris.py` — what a GLB holds and where its triangles are, before against after. Nothing but Python: run them with `python -I`.
- `scripts/render_glb.py` — one Cycles picture of a GLB, on the GPU where there is one.
- `scripts/tjunctions.py` — the edges of a GLB where a crack of a pixel can open (a corner of one triangle on the edge of another), counted from the file alone. Nothing but Python: `python -I`.
- `scripts/zfight_tests.js` — two tests of a model as a GPU draws it, in a page that has three.js: pixels whose surface depends on the draw order (z-fighting), and pixels left empty though drawn all round (cracks).
- `scripts/ask.sh "<question>" body.md` — a stuck agent files a `question` issue; stronger models answer and fold the answer back in.
- `references/` — the environment, dressing and export, Cycles, a web viewer, a packed export: the longer material, with the numbers.

Every agent that learns something about sand3d pushes it here, and every stuck agent asks here: see `CONTRIBUTING.md`.

Verified on sand3d 1.6.3 with Blender 5.2 as the `bpy` module, on Linux.

## Install

Symlink the skill folder into your agent's skills directory, so that it is found by what it says it is for:

```sh
ln -s "$PWD/skills/sand3d-field-notes" ~/.agents/skills/sand3d-field-notes   # ZCode, and any agent that reads ~/.agents/skills
ln -s "$PWD/skills/sand3d-field-notes" ~/.claude/skills/sand3d-field-notes   # Claude Code
```

Then have the working folder's `CLAUDE.md` point at it in its "Start here", and say that an agent pulls this repository before sand3d work and pushes what it learned back afterwards.

sand3d is Apache-2.0, by Sandflow AI. The licence of what is written here: to be decided by the repository owner.
