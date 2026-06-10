"""Visualizer for the RoboTube example video dataset.

Browse episodes in a tree on the left; click one to play its four streams
together in a 2x2 grid:

    cam_0 rgb  |  cam_0 depth
    cam_1 rgb  |  cam_1 depth

All four play synchronized in a loop. Depth videos are already Turbo-colorized.

Usage:
    python visualize_videos.py [DATASET_ROOT]

DATASET_ROOT defaults to ./cabinet_opening_example_dataset (or the env var
ROBOTUBE_DATASET). Requires the `ffmpeg`/`ffprobe` CLI plus pillow + numpy.
"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, font as tkfont

import numpy as np
from PIL import Image, ImageTk

FPS = 30
CELL_W, CELL_H = 380, 285  # display size per cell

# ----- dark palette (mimics simple-mobile/tidybot2/reviewer.py) -----
BG = "#0a0a0f"        # bg-primary / window
BG2 = "#12121a"       # bg-secondary / troughs, pills, status
PANEL = "#1a1a24"     # bg-card / side panel + cards
PANEL_HI = "#232331"  # hover / selected
BORDER = "#2a2a3a"
TEXT = "#e8e8ed"      # text-primary
MUTED = "#8888a0"     # text-secondary
ACCENT = "#00d4aa"    # mint accent
ACCENT_HI = "#00a080" # accent-dim (hover)
DEPTH = "#8888a0"     # depth chip (muted, matches reviewer video-label)
POS = "#2ed573"       # success green
NEG = "#ff6b6b"       # red (failure)


def find_ffmpeg():
    for exe in ("ffmpeg", "ffprobe"):
        if subprocess.run(["which", exe], capture_output=True).returncode != 0:
            sys.exit(f"error: `{exe}` not found on PATH (install ffmpeg).")


def probe_size(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", path],
        capture_output=True, text=True,
    )
    info = json.loads(out.stdout)["streams"][0]
    return int(info["width"]), int(info["height"])


def read_video(path):
    """Decode an mp4 to a list of (H, W, 3) uint8 RGB frames."""
    if not os.path.exists(path):
        return []
    w, h = probe_size(path)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
    ).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    return list(arr)


def discover_episodes(root):
    """Return {split: {scene: {env: {label: {timestamp: {0:dir,1:dir}}}}}}."""
    tree = {}
    for dirpath, dirnames, filenames in os.walk(root):
        base = os.path.basename(dirpath)
        if "_cam_" not in base or "rgb.mp4" not in filenames:
            continue
        rel = os.path.relpath(dirpath, root).split(os.sep)
        if len(rel) < 5:
            continue
        split, scene, env, label, episode = rel[0], rel[1], rel[2], rel[3], rel[4]
        ts, cam = episode.rsplit("_cam_", 1)
        (tree.setdefault(split, {}).setdefault(scene, {}).setdefault(env, {})
             .setdefault(label, {}).setdefault(ts, {}))[cam] = dirpath
    return tree


class Visualizer(tk.Tk):
    def __init__(self, root):
        super().__init__()
        self.title("RoboTube · Video Visualizer")
        self.geometry("1280x880")
        self.minsize(1080, 720)
        self.configure(bg=BG)
        self.dataset_root = root

        self.frames = []
        self.n_frames = 0
        self.idx = 0
        self.playing = False
        self.photos = [None] * 4
        self.placeholders = [None] * 4
        self.node_to_eps = {}

        self._setup_fonts()
        self._setup_style()
        self._build_ui()
        self._populate_tree()

    # ---------- theme ----------
    def _setup_fonts(self):
        # This Tk renders X11 core fonts only, so the reviewer's webfonts
        # (Outfit for UI, JetBrains Mono for code) can't load. Substitute the
        # closest scalable X-core families: helvetica (sans) + courier (mono).
        # TrueType names would silently fall back to the chunky bitmap "fixed".
        avail = {f.lower() for f in tkfont.families()}
        sans = next((c for c in ("helvetica", "nimbus sans l", "avantgarde")
                     if c in avail), "helvetica")
        mono = next((c for c in ("courier", "courier 10 pitch")
                     if c in avail), "courier")
        self.f_base = tkfont.Font(family=sans, size=11)
        self.f_small = tkfont.Font(family=sans, size=9)
        self.f_title = tkfont.Font(family=sans, size=20, weight="bold")
        self.f_cell = tkfont.Font(family=sans, size=10, weight="bold")
        self.f_mono = tkfont.Font(family=mono, size=10)

    def _setup_style(self):
        st = ttk.Style(self)
        st.theme_use("clam")

        st.configure(".", background=BG, foreground=TEXT,
                     fieldbackground=PANEL, font=self.f_base, borderwidth=0)
        st.configure("TFrame", background=BG)
        st.configure("Panel.TFrame", background=PANEL)
        st.configure("Card.TFrame", background=PANEL)
        st.configure("TLabel", background=BG, foreground=TEXT)
        st.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        st.configure("Muted.TLabel", background=BG, foreground=MUTED, font=self.f_small)
        st.configure("Cell.TLabel", background=PANEL, foreground=MUTED, font=self.f_cell)
        st.configure("Header.TLabel", background=BG, foreground=TEXT, font=self.f_title)

        # accent label (mono, mint) — reviewer's .rollout-name / .stats span
        st.configure("Accent.TLabel", background=PANEL, foreground=ACCENT,
                     font=self.f_mono)

        # accent button (.btn-save: mint bg, dark text)
        st.configure("Accent.TButton", background=ACCENT, foreground=BG,
                     font=self.f_base, padding=(18, 8), borderwidth=0, focusthickness=0)
        st.map("Accent.TButton",
               background=[("active", ACCENT_HI), ("pressed", ACCENT_HI)])

        # treeview
        st.configure("Side.Treeview", background=PANEL, fieldbackground=PANEL,
                     foreground=TEXT, borderwidth=0, rowheight=26,
                     font=self.f_base)
        st.map("Side.Treeview",
               background=[("selected", ACCENT)],
               foreground=[("selected", BG)])
        st.layout("Side.Treeview", [("Side.Treeview.treearea", {"sticky": "nswe"})])

        # scale (scrubber)
        st.configure("Horizontal.TScale", background=PANEL, troughcolor=BG2,
                     borderwidth=0)

        # scrollbar
        st.configure("Vertical.TScrollbar", background=BORDER,
                     troughcolor=PANEL, borderwidth=0, arrowcolor=MUTED)

    # ---------- UI ----------
    def _build_ui(self):
        # header bar
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill=tk.X, padx=20, pady=(16, 8))
        ttk.Label(header, text="RoboTube", style="Header.TLabel").pack(side=tk.LEFT)
        sub = tk.Label(header, text="  // video review", bg=BG, fg=ACCENT,
                       font=self.f_mono)
        sub.pack(side=tk.LEFT, pady=(10, 0))

        body = ttk.Frame(self, style="TFrame")
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        # left: episode tree card
        left = ttk.Frame(body, style="Panel.TFrame")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        ttk.Label(left, text="EPISODES", style="Cell.TLabel").pack(
            anchor="w", padx=14, pady=(12, 6))
        tree_wrap = ttk.Frame(left, style="Panel.TFrame")
        tree_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 10))
        self.tree = ttk.Treeview(tree_wrap, show="tree", style="Side.Treeview",
                                 selectmode="browse")
        self.tree.column("#0", width=240, minwidth=200)
        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.tag_configure("pos", foreground=POS)
        self.tree.tag_configure("neg", foreground=NEG)
        self.tree.tag_configure("group", foreground=TEXT)

        # right: video grid + controls
        right = ttk.Frame(body, style="TFrame")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        titles = [("cam_0", "rgb"), ("cam_0", "depth"),
                  ("cam_1", "rgb"), ("cam_1", "depth")]
        self.cells = []
        grid = ttk.Frame(right, style="TFrame")
        grid.pack(padx=0, pady=0)
        for i, (cam, kind) in enumerate(titles):
            card = ttk.Frame(grid, style="Card.TFrame")
            card.grid(row=i // 2, column=i % 2, padx=8, pady=8)
            bar = ttk.Frame(card, style="Card.TFrame")
            bar.pack(fill=tk.X, padx=12, pady=(10, 6))
            ttk.Label(bar, text=cam, style="Accent.TLabel").pack(side=tk.LEFT)
            # pill badge in reviewer's .video-index style
            tag = tk.Label(bar, text=kind.upper(), font=self.f_mono, padx=10, pady=1,
                           bg=BG2, fg=(ACCENT if kind == "rgb" else MUTED))
            tag.pack(side=tk.RIGHT)
            lbl = tk.Label(card, bg=BG, highlightthickness=1,
                           highlightbackground=BORDER, highlightcolor=BORDER,
                           width=CELL_W, height=CELL_H)
            lbl.pack(padx=12, pady=(0, 12))
            self.cells.append(lbl)

        # controls card
        ctrl = ttk.Frame(right, style="Panel.TFrame")
        ctrl.pack(fill=tk.X, pady=(10, 0))
        inner = ttk.Frame(ctrl, style="Panel.TFrame")
        inner.pack(fill=tk.X, padx=14, pady=12)
        self.play_btn = ttk.Button(inner, text="▶  Play", command=self._toggle,
                                   style="Accent.TButton", width=10)
        self.play_btn.pack(side=tk.LEFT)
        self.scrub = ttk.Scale(inner, from_=0, to=0, orient=tk.HORIZONTAL,
                               command=self._on_scrub)
        self.scrub.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=16)
        self.frame_lbl = tk.Label(inner, text="–/–", font=self.f_mono,
                                  bg=PANEL, fg=ACCENT, width=9)
        self.frame_lbl.pack(side=tk.LEFT)

        # status bar
        self.status = tk.Label(self, text="Select an episode to begin.",
                               anchor="w", bg=BG2, fg=MUTED,
                               font=self.f_mono, padx=20, pady=6)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        self._draw_placeholders()

    def _draw_placeholders(self):
        ph = Image.new("RGB", (CELL_W, CELL_H), (10, 10, 15))  # BG #0a0a0f
        for i, lbl in enumerate(self.cells):
            self.placeholders[i] = ImageTk.PhotoImage(ph)
            lbl.config(image=self.placeholders[i], width=CELL_W, height=CELL_H)

    def _populate_tree(self):
        data = discover_episodes(self.dataset_root)
        if not data:
            self.status.config(text=f"No episodes found under {self.dataset_root}")
            return
        for split in sorted(data):
            s_id = self.tree.insert("", "end", text=f"  {split}", open=True,
                                    tags=("group",))
            for scene in sorted(data[split]):
                sc_id = self.tree.insert(s_id, "end", text=f"  {scene}", open=True,
                                         tags=("group",))
                for env in sorted(data[split][scene]):
                    e_id = self.tree.insert(sc_id, "end", text=f"  {env}", open=True,
                                            tags=("group",))
                    for label in sorted(data[split][scene][env]):
                        l_id = self.tree.insert(e_id, "end", text=f"  {label}",
                                                open=True, tags=(label,))
                        for ts, cams in sorted(data[split][scene][env][label].items()):
                            node = self.tree.insert(l_id, "end", text=f"  {ts}",
                                                    tags=(label,))
                            self.node_to_eps[node] = cams

    # ---------- playback ----------
    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel or sel[0] not in self.node_to_eps:
            return
        self._load_episode(self.node_to_eps[sel[0]])

    def _load_episode(self, cams):
        self.playing = False
        self.play_btn.config(text="▶  Play")
        self.status.config(text="Loading…")
        self.update_idletasks()

        paths = [
            os.path.join(cams.get("0", ""), "rgb.mp4"),
            os.path.join(cams.get("0", ""), "depth.mp4"),
            os.path.join(cams.get("1", ""), "rgb.mp4"),
            os.path.join(cams.get("1", ""), "depth.mp4"),
        ]
        self.frames = [read_video(p) for p in paths]
        counts = [len(f) for f in self.frames]
        self.n_frames = min(c for c in counts) if all(counts) else 0
        if not self.n_frames:
            self.status.config(text=f"Could not decode all streams: {counts}")
            return
        self.idx = 0
        self.scrub.config(to=self.n_frames - 1)
        self.scrub.set(0)
        self._show_frame()
        self.status.config(
            text=f"{os.path.dirname(paths[0])}   ·   {self.n_frames} frames @ {FPS} fps")
        self._toggle()  # autoplay

    def _show_frame(self):
        for i, flist in enumerate(self.frames):
            if self.idx < len(flist):
                img = Image.fromarray(flist[self.idx]).resize(
                    (CELL_W, CELL_H), Image.NEAREST if i % 2 else Image.BILINEAR)
                self.photos[i] = ImageTk.PhotoImage(img)
                self.cells[i].config(image=self.photos[i])
        self.frame_lbl.config(text=f"{self.idx + 1}/{self.n_frames}")

    def _tick(self):
        if not self.playing or not self.n_frames:
            return
        self.idx = (self.idx + 1) % self.n_frames
        self.scrub.set(self.idx)
        self._show_frame()
        self.after(int(1000 / FPS), self._tick)

    def _toggle(self):
        if not self.n_frames:
            return
        self.playing = not self.playing
        self.play_btn.config(text="⏸  Pause" if self.playing else "▶  Play")
        if self.playing:
            self._tick()

    def _on_scrub(self, value):
        if not self.n_frames:
            return
        i = int(float(value))
        if i != self.idx:
            self.idx = i
            self._show_frame()


def main():
    find_ffmpeg()
    default = os.environ.get(
        "ROBOTUBE_DATASET",
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "cabinet_opening_example_dataset"))
    root = sys.argv[1] if len(sys.argv) > 1 else default
    if not os.path.isdir(root):
        sys.exit(f"error: dataset root not found: {root}\n"
                 f"pass the path as an argument or set ROBOTUBE_DATASET.")
    Visualizer(root).mainloop()


if __name__ == "__main__":
    main()
