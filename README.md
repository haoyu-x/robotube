<div align="center">

<h1>RoboTube: Learning Household Manipulation from Human Videos with Simulated Twin Environments</h1>

[[Project page]](https://www.robotube.org/)
[[Paper]](https://proceedings.mlr.press/v205/xiong23a/xiong23a.pdf)

[Haoyu Xiong](https://haoyu-x.github.io/),
[Haoyuan Fu](https://simon-fuhaoyuan.github.io/),
Jieyi Zhang,
[Chen Bao](https://www.chenbao.tech/),
Qiang Zhang,
[Yongxi Huang](https://www.ropl.ai/author/yongxi-huang/),
[Wenqiang Xu](https://wenqiangx.github.io/),
[Animesh Garg](https://animesh.garg.tech/),
[Huazhe Xu](http://hxu.rocks/),
[Cewu Lu](https://www.mvig.org/)

*6th Annual Conference on Robot Learning (CoRL 2022), Oral*

<img width="80%" src="Robotube.png">

</div>

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

cd ~/robotube
uv sync
```


## Download example video dataset

A small example slice of the RoboTube video dataset (cabinet opening task) for quick inspection.

```bash
cd ~/robotube
uv run gdown "https://drive.google.com/uc?id=15mt9GLF299vkxfU83uqf1UIQCetSYE6x"
unzip cabinet_opening_example_dataset.zip
```


Visualize the example video dataset:
```bash
cd ~/robotube
uv run python visualize_videos.py cabinet_opening_example_dataset
```

Each `*_cam_*` folder holds two videos: `rgb.mp4` (color) and
`depth.mp4` (depth colorized with the Turbo colormap). `pos`/`neg` are successful/failed episodes, captured from two synchronized first-person and third-person cameras (`cam_0`, `cam_1`).

```
cabinet_opening_example_dataset/
├── test/                          # env1
│   ├── cluttered/env1/{pos,neg}/
│   └── structured/env1/{pos,neg}/
└── train/                         # env3
    ├── cluttered/env3/{pos,neg}/
    └── structured/env3/{pos,neg}/

# each {pos,neg}/ holds one episode (two synced cameras):
{pos,neg}/
├── <timestamp>_cam_0/   (rgb.mp4, depth.mp4)
└── <timestamp>_cam_1/   (rgb.mp4, depth.mp4)
```



## Load digital twins in MuJoCo

Download assets

```bash
cd ~/robotube
uv run gdown "https://drive.google.com/uc?id=1fEC1ABeLkZM5XEC6zlXvmqr9VoVnRu0M"
unzip models.zip 
```

```bash
uv run python loading_objects.py
```

Follow the prompts to pick a category and object id. Press **ESC** in the viewer
window to exit. Inside the viewer, press **3** to toggle the collision hulls on.

## License

Released under the [MIT License](LICENSE). Note that the bundled object assets
are subject to the licenses of their respective upstream sources listed above.

## BibTeX Citation

```bibtex
@inproceedings{xiong2022robotube,
  title={RoboTube: Learning Household Manipulation from Human Videos
         with Simulated Twin Environments},
  author={Haoyu Xiong and Haoyuan Fu and Jieyi Zhang and Chen Bao
          and Qiang Zhang and Yongxi Huang and Wenqiang Xu
          and Animesh Garg and Cewu Lu},
  booktitle={6th Annual Conference on Robot Learning},
  year={2022},
  url={https://openreview.net/forum?id=VD0nXUG5Qk}
}
```
