<div align="center">

# RoboTube

<a href="https://haoyu-x.github.io/"><strong>Haoyu Xiong</strong></a> 

</div>

A small [MuJoCo](https://mujoco.org/) playground for loading and inspecting a
library of household objects in an interactive viewer. Pick a category and an
object id from a menu, and the script wraps the object in a minimal scene
(floor + lights + skybox) and opens the passive viewer.

On load:

- **Articulated objects** (cabinets, drawers) sweep their joint open and closed
  so you can see the range of motion.
- **Rigid objects** (cups, pots) fall under gravity and settle on the floor.

## Object library

Each object lives at `models/{category}/{category}{id}/{category}{id}.xml`
together with its own `assets/` (meshes + textures).

| Category | Count | Type |
| --- | --- | --- |
| `cabinet` | 4  | articulated (hinge door) |
| `drawer`  | 10 | articulated (sliding drawer) |
| `cup`     | 20 | rigid |
| `pot`     | 16 | rigid |
| `handle`  | 13 | rigid (present on disk, excluded from the menu) |

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

cd robotube_playground
uv sync
```

## Usage

```bash
uv run python loading_objects.py
```

Follow the prompts to pick a category and object id. Press **ESC** in the viewer
window to exit. Inside the viewer, press **3** to toggle the collision hulls on.

## Acknowledgment

The assets are borrowed from
[TidyBot++](https://tidybot2.github.io/),
[BiGym](https://chernyadev.github.io/bigym/),
[Robocasa](https://robocasa.ai/), and
[Gated Memory Policy](https://gated-memory-policy.github.io/).
Please consider citing these works if you find this helpful.

## License

Released under the [MIT License](LICENSE). Note that the bundled object assets
are subject to the licenses of their respective upstream sources listed above.
