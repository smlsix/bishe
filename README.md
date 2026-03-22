# 钢铁表面缺陷检测系统

基于 YOLOv8 和 PyQt5 的钢铁表面缺陷检测项目，支持模型训练、验证、单张图片推理，以及图形界面下的图片、文件夹、视频和摄像头检测。

项目中包含一份本地修改过的 `ultralytics` 源码，并提供了一个带界面的检测系统，适合课程设计、毕业设计、演示展示和基础二次开发。

## 功能特性

- 基于 YOLOv8 的钢铁表面缺陷检测
- 支持普通 `yolov8s` 与加入 SE 注意力机制的模型结构
- 支持单张图片推理
- 支持模型训练与验证
- 支持图片、文件夹、视频、摄像头检测
- 支持中文类别名称显示
- 支持检测结果保存为图片、CSV 和 XLS

## 项目结构

```text
code24_yolov8/
├─ main.py                 # PyQt5 图形界面主程序
├─ train.py                # 模型训练脚本
├─ predict.py              # 单张图片推理脚本
├─ val.py                  # 模型验证与对比脚本
├─ config/
│  ├─ configs.yaml         # 界面与推理配置
│  └─ traindata.yaml       # 数据集配置
├─ UI/                     # PyQt 界面文件
├─ utils/                  # 工具函数
├─ ultralytics/            # 本地 Ultralytics 源码
├─ img/                    # 测试图片/视频示例
├─ fonts/                  # 中文显示字体
├─ icon/                   # 界面资源文件
├─ output/                 # 界面推理输出目录
├─ runs/                   # 训练/验证输出目录
└─ weights/                # 模型权重与历史结果
```

## 环境要求

建议环境：

- Python 3.8 或 3.9
- Windows
- CUDA 可选，有 GPU 时会自动优先使用 GPU

项目运行中实际会用到的主要依赖包括：

- `torch`
- `ultralytics`
- `PyQt5`
- `opencv-python`
- `numpy`
- `Pillow`
- `PyYAML`
- `easydict`
- `xlwt`

如果你还没有创建依赖文件，可以先手动安装：

```bash
pip install torch torchvision torchaudio
pip install ultralytics PyQt5 opencv-python numpy pillow pyyaml easydict xlwt
```

## 数据集准备

当前项目默认配置的是 6 类钢铁表面缺陷数据，类别名在 `config/traindata.yaml` 中定义为：

```yaml
names: ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
```

你需要先修改数据集路径：

```yaml
path: E:\bishe\data\yolo
train:
  - train
val:
  - val
test:
  - test
```

也就是说，你的数据集目录建议类似下面这样：

```text
E:\bishe\data\yolo
├─ train
├─ val
└─ test
```

如果你使用的是自己的数据集，请同步修改：

- `config/traindata.yaml` 中的 `path`
- `config/traindata.yaml` 中的 `names`
- `config/configs.yaml` 中的 `chinese_name`

## 配置说明

### 1. 模型与推理配置

在 `config/configs.yaml` 中可以修改：

- 模型权重路径 `MODEL.WEIGHT`
- 置信度阈值 `MODEL.CONF`
- 输入尺寸 `MODEL.IMGSIZE`

示例：

```yaml
MODEL:
  WEIGHT: './weights/yolov8s-attention-SE/weights/best.pt'
  CONF: 0.4
  IMGSIZE: 640
```

### 2. 界面配置

在 `config/configs.yaml` 中还可以修改：

- 界面标题
- 背景图和图标
- 表格颜色和宽度
- 摄像头开关
- 是否显示中文类别名

### 3. 中文类别映射

项目支持将英文类别映射成中文显示，配置位置如下：

```yaml
CONFIG:
  draw_chinese: True
  chinese_name: {
    'crazing': '龟裂',
    'inclusion': '夹杂',
    'patches': '斑块',
    'pitted_surface': '麻点表面',
    'rolled-in_scale': '轧入氧化皮',
    'scratches': '划痕'
  }
```

## 使用方法

### 1. 启动图形界面

```bash
python main.py
```

图形界面支持：

- 选择单张图片检测
- 遍历文件夹内图片检测
- 视频检测
- 摄像头实时检测
- 导出检测记录

检测结果会自动保存在 `output/时间戳/` 目录下，包括：

- `result.csv`
- `img_result/` 检测结果图像

### 2. 模型训练

```bash
python train.py
```

训练前建议先检查以下内容：

- `train.py` 中选择的模型结构
- `config/traindata.yaml` 中的数据集路径
- 训练参数如 `epochs`、`batch`、`imgsz`

当前 `train.py` 中已经预留了两种结构：

- `ultralytics/cfg/models/v8/yolov8s.yaml`
- `ultralytics/cfg/models/v8/det_self/yolov8s-attention-SE.yaml`

训练结果默认保存在：

```text
runs/train/
```

### 3. 单张图片推理

先修改 `predict.py` 中的参数：

- `model_path`
- `image_path`
- `img_size`
- `conf_threshold`

然后运行：

```bash
python predict.py
```

推理结果默认保存到：

```text
output/
```

### 4. 模型验证与对比

```bash
python val.py
```

`val.py` 支持单模型验证，也支持多模型对比。你可以在脚本中修改：

- 参与验证的模型路径
- 验证数据集配置
- `conf`
- `iou`
- `batch`

验证结果默认保存在：

```text
runs/val/
```

## 输出说明

### 1. `output/`

主要保存图形界面和推理脚本生成的结果，例如：

- 检测结果图片
- 结果 CSV

### 2. `runs/`

主要保存 Ultralytics 训练和验证过程中的输出，例如：

- 训练日志
- 指标图
- 混淆矩阵
- 最优权重

### 3. `weights/`

当前仓库中保存了部分训练后的模型结果，用于测试、演示或对比实验。

## 注意事项

- 运行项目时，建议在仓库根目录下执行命令，这样会优先使用本地的 `ultralytics` 源码
- 如果使用中文标签显示，请保留 `fonts/` 目录中的字体文件
- 第一次运行时，项目会自动尝试同步字体到 Ultralytics 用户目录
- 如果你上传到 GitHub，建议不要提交训练输出、大模型权重和缓存文件

## 适用场景

- 毕业设计
- 课程设计
- YOLOv8 二次开发
- 缺陷检测演示系统

