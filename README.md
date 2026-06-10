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

## Download assets

```bash
cd ~/robotube
gdown "https://drive.google.com/uc?id=1fEC1ABeLkZM5XEC6zlXvmqr9VoVnRu0M"
unzip models.zip 
```

## Load digital twins in MuJoCo

```bash
uv run python loading_objects.py
```


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
