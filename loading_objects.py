"""Load a single object into a MuJoCo scene and open the interactive viewer.

Each object lives at:
    models/{category}/{category}{obj_id}/{category}{obj_id}.xml

The script wraps that object XML in a minimal scene (floor + lights + skybox)
and launches the passive viewer. On launch it prompts for the category and
object id interactively — no command-line flags required.

Press ESC in the viewer window to exit.
"""

import math
import re
import tempfile
import time
from pathlib import Path

import mujoco
import mujoco.viewer

MODELS_ROOT = Path(__file__).resolve().parent / "models"

# Categories present on disk but excluded from the interactive menu.
EXCLUDED_CATEGORIES = {"handle"}

SCENE_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<mujoco model="scene">
  <option timestep="0.002" gravity="0 0 -9.81"/>

  <statistic center="0 0 0.25" extent="0.8" meansize="0.05"/>

  <visual>
    <headlight diffuse="0.6 0.6 0.6" ambient="0.1 0.1 0.1" specular="0 0 0"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global azimuth="120" elevation="-20"/>
  </visual>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
    <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
      markrgb="0.8 0.8 0.8" width="300" height="300"/>
    <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
  </asset>

  <worldbody>
    <light pos="0 0 1.5" directional="true"/>
    <geom name="floor" size="0 0 0.05" type="plane" material="groundplane" rgba="1 1 1 1"/>
  </worldbody>

  <include file="{include_path}"/>
</mujoco>
"""


def discover_categories() -> dict[str, list[int]]:
    """Return {category: sorted [ids]} for every category folder that
    contains at least one `{category}{N}/{category}{N}.xml` object."""
    catalog: dict[str, list[int]] = {}
    for cat_dir in sorted(p for p in MODELS_ROOT.iterdir() if p.is_dir()):
        if cat_dir.name in EXCLUDED_CATEGORIES:
            continue
        pattern = re.compile(rf"^{re.escape(cat_dir.name)}(\d+)$")
        ids: list[int] = []
        for obj_dir in cat_dir.iterdir():
            m = pattern.match(obj_dir.name)
            if m and (obj_dir / f"{obj_dir.name}.xml").is_file():
                ids.append(int(m.group(1)))
        if ids:
            catalog[cat_dir.name] = sorted(ids)
    return catalog


def pick(prompt: str, options: list) -> int:
    """Show a numbered menu and return the index the user selected."""
    width = len(str(len(options)))
    for i, opt in enumerate(options, 1):
        print(f"  [{i:>{width}}] {opt}")
    while True:
        raw = input(f"{prompt} (1-{len(options)}): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  invalid choice: {raw!r}")


def run_viewer(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    """Open the passive viewer and run the sim until the window is closed."""
    with mujoco.viewer.launch_passive(
        model, data, show_left_ui=False, show_right_ui=False
    ) as viewer:
        viewer.opt.geomgroup[1] = 1
        # Collision hulls (group 3) are hidden by default — with CoACD
        # multi-hull collision the overlap of dozens of translucent pieces
        # obscures the textured visual mesh. Toggle on inside the viewer
        # with the "3" key if you need to inspect collision geometry.
        viewer.opt.geomgroup[3] = 0

        # Articulated joints (limited slide/hinge: drawer slide, cabinet
        # hinge, ...) are swept back and forth across their range so they
        # visibly open and close on load. We force qpos kinematically each
        # frame rather than relying on the position actuator, which can be
        # too weak to fight gravity (e.g. a near-vertical drawer slide).
        # Everything else still runs full dynamics via mj_step, so free
        # bodies (cups, pots, ...) fall under gravity and settle on the floor.
        sweep_joints = []  # (qpos_addr, dof_addr, lo, hi)
        for i in range(model.njnt):
            jtype = model.jnt_type[i]
            if jtype not in (mujoco.mjtJoint.mjJNT_SLIDE,
                             mujoco.mjtJoint.mjJNT_HINGE):
                continue
            if not model.jnt_limited[i]:
                continue
            lo, hi = model.jnt_range[i]
            sweep_joints.append((model.jnt_qposadr[i], model.jnt_dofadr[i], lo, hi))
        sweep_period = 4.0  # seconds per open+close cycle

        # Decouple physics from rendering: step physics to catch up with
        # wall-clock time, then render once per frame. Rendering after every
        # 2 ms step would stall heavy-to-draw objects (e.g. a cup with dozens
        # of collision hulls), making them fall in slow motion.
        render_period = 1.0 / 60.0  # target ~60 fps
        sim_start = time.time()
        while viewer.is_running():
            frame_start = time.time()
            # advance physics until sim time matches elapsed wall-clock time
            while data.time < time.time() - sim_start:
                mujoco.mj_step(model, data)
                # Override swept joints to follow the open/close cycle,
                # leaving the rest of the state (free bodies, etc.) as
                # physics computed.
                for qadr, dadr, lo, hi in sweep_joints:
                    phase = 0.5 * (1.0 - math.cos(2.0 * math.pi *
                                                  data.time / sweep_period))
                    data.qpos[qadr] = lo + (hi - lo) * phase
                    data.qvel[dadr] = 0.0
            if sweep_joints:
                mujoco.mj_forward(model, data)
            viewer.sync()
            dt = render_period - (time.time() - frame_start)
            if dt > 0:
                time.sleep(dt)
        print(f"viewer closed after {time.time() - sim_start:.1f}s")


def main() -> None:
    catalog = discover_categories()
    if not catalog:
        raise SystemExit(f"no object categories found under {MODELS_ROOT}")

    categories = list(catalog.keys())
    print("\nAvailable categories:")
    choice = pick("pick a category", categories)

    cat = categories[choice]
    ids = catalog[cat]
    print(f"\nAvailable {cat} ids:")
    obj_id = ids[pick(f"pick a {cat} id", ids)]

    obj_name = f"{cat}{obj_id}"
    obj_xml = MODELS_ROOT / cat / obj_name / f"{obj_name}.xml"

    # Write the scene wrapper next to the object XML so that <include>'s
    # relative path resolution and the included file's meshdir/texturedir
    # both resolve correctly.
    scene_src = SCENE_TEMPLATE.format(include_path=obj_xml.name)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", dir=obj_xml.parent, delete=False
    ) as f:
        f.write(scene_src)
        scene_path = Path(f.name)

    try:
        print(f"\nloading {obj_name} from {obj_xml}")
        t0 = time.time()
        model = mujoco.MjModel.from_xml_path(str(scene_path))
        data = mujoco.MjData(model)
        print(f"compiled in {time.time() - t0:.2f}s "
              f"(nbody={model.nbody}, nmesh={model.nmesh}, ngeom={model.ngeom})")
        run_viewer(model, data)
    finally:
        scene_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
