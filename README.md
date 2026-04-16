# 钢铁表面缺陷检测系统

基于 YOLOv8 的钢铁表面缺陷检测项目，提供两套使用方式：

- 桌面端：基于 `PyQt5` 的本地图形界面
- Web 端：基于 `FastAPI + HTML/CSS/JavaScript` 的浏览器界面

项目仓库中已经包含一份本地修改过的 `ultralytics` 源码，适合课程设计、毕设演示和后续二次开发。

## 功能概览

### 桌面版功能

- 单张图片检测
- 文件夹批量图片检测
- 视频检测
- 摄像头实时检测
- 检测结果导出为 `CSV / XLS`
- 中文类别名称显示

### Web 版功能

- 单张图片检测
- 批量图片检测
- 视频检测
- 浏览器摄像头实时检测
- 历史记录查看
- 模型切换
- 历史信息导出为 `CSV / XLS`

## 项目结构

```text
code24_yolov8/
├─ main.py                   # PyQt5 图形界面入口
├─ train.py                  # 模型训练脚本
├─ val.py                    # 模型验证脚本
├─ predict.py                # 单张图片推理脚本
├─ run_web.py                # Web 服务启动入口
├─ requirements.txt          # 完整依赖
├─ requirements-web.txt      # 补装 Web 依赖时可用
├─ config/
│  ├─ configs.yaml           # 模型、界面、中文类别等配置
│  └─ traindata.yaml         # 数据集配置
├─ UI/                       # PyQt 界面文件
├─ utils/                    # 工具函数
├─ webapp/
│  ├─ app.py                 # FastAPI 路由
│  ├─ service.py             # Web 推理服务
│  ├─ storage.py             # 历史记录与结果保存
│  └─ static/                # Web 前端页面与脚本
├─ ultralytics/              # 本地修改后的 Ultralytics 源码
├─ fonts/                    # 中文字体
├─ icon/                     # 图标与背景资源
├─ img/                      # 示例图片与视频
├─ output/                   # 运行输出目录（已忽略）
├─ runs/                     # 训练输出目录（已忽略）
└─ weights/                  # 模型权重目录（已忽略）
```

## 环境要求

- Python 3.8 及以上
- Windows 环境更适合当前项目
- 如需 GPU 推理或训练，请自行安装与本机 CUDA 对应的 `torch`

注意：

- 仓库内自带本地 `ultralytics` 源码，因此不要求额外安装官方 `ultralytics` 包
- `weights/`、`output/`、`runs/` 已加入 `.gitignore`，push 到 GitHub 时默认不会上传

## 安装依赖

推荐直接安装完整依赖：

```bash
pip install -r requirements.txt
```

如果你原本已经能跑桌面版，只是后面新增了 Web 功能，也可以只补装 Web 相关依赖：

```bash
pip install -r requirements-web.txt
```

## 数据集配置

默认数据集配置文件为 [config/traindata.yaml](./config/traindata.yaml)。

当前类别如下：

```yaml
names: ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
```

你需要根据自己电脑上的数据集位置修改：

```yaml
path: E:\bishe\data\yolo
train:
  - train
val:
  - val
test:
  - test
```

如果你更换了自己的数据集，建议同步修改：

- `config/traindata.yaml` 中的 `path`
- `config/traindata.yaml` 中的 `names`
- `config/configs.yaml` 中的 `CONFIG.chinese_name`

## 权重配置

默认权重路径在 [config/configs.yaml](./config/configs.yaml) 中：

```yaml
MODEL:
  WEIGHT: './weights/yolov8s-attention-SE/weights/best.pt'
  CONF: 0.4
  IMGSIZE: 640
```

因为 `weights/` 已经被 `.gitignore` 忽略，所以你把代码 push 到 GitHub 后，克隆下来时需要：

1. 自己把训练好的权重放回 `weights/` 目录
2. 或者修改 `MODEL.WEIGHT` 指向你实际的权重文件

## 使用方法

### 1. 启动桌面版

```bash
python main.py
```

### 2. 训练模型

```bash
python train.py
```

### 3. 验证模型

```bash
python val.py
```

### 4. 单张图片推理

```bash
python predict.py
```

### 5. 启动 Web 版

```bash
python run_web.py
```

浏览器访问：

```text
http://127.0.0.1:8000
```

如果你想让同一局域网内的其他设备也能访问，可以继续保留 `run_web.py` 中的：

```python
host="0.0.0.0"
```

## Web 版结果保存位置

Web 版运行后的结果默认保存在：

```text
output/webapp/
```

主要包括：

- `output/webapp/runs/`：图片、批量图片、视频、摄像头检测结果
- `output/webapp/history/records.json`：历史记录索引
- `output/webapp/exports/`：导出的历史汇总表

## GitHub 上传说明

当前 `.gitignore` 已经忽略了这些不适合上传仓库的大文件或生成文件：

- `weights/`
- `output/`
- `runs/`
- `*.pt`
- 各类缓存、日志、虚拟环境目录

因此你 push 到 GitHub 时，主要会上传：

- 源代码
- 配置文件
- Web 前端文件
- README
- requirements

## 说明

- 项目运行时建议在仓库根目录执行命令，这样会优先使用本地的 `ultralytics/`
- 若使用中文类别显示，请保留 `fonts/` 目录
- Web 版代码入口在 [webapp/app.py](./webapp/app.py)，前端页面在 [webapp/static/index.html](./webapp/static/index.html)

## 适用场景

- 毕业设计
- 课程设计
- 缺陷检测演示系统
- YOLOv8 二次开发练习

## Vue Frontend + Login Database (Update: 2026-04-16)

This project now includes a full-stack web upgrade:

- Frontend: `Vue 3 + Vite` (source code in `frontend-vue/`)
- Backend: `FastAPI`
- User/Login database: `SQLite` (stored under `output/webapp/auth/auth.db`)
- Auth mode: Bearer token, all inference/history APIs require login
- User audit: every inference request is recorded into DB audit logs

### Frontend source and build

```bash
cd frontend-vue
npm install
npm run build
```

The build output is generated to:

```text
webapp/static/vue/
```

Backend `/` will automatically serve this Vue app when `webapp/static/vue/index.html` exists.

### Run backend

```bash
python run_web.py
```

Then open:

```text
http://127.0.0.1:8000
```

### First-time usage

1. Open login page
2. If no user exists, go to register
3. After login, access dashboard for image/video inference, history, and personal audit logs

### Multi-page navigation (new)

After login, the Vue frontend is now split into multiple pages:

- Overview
- Image detection
- Video detection
- Camera real-time detection
- History and audit
- Model performance comparison
- Account settings

### Model performance comparison logic

- If user has used 2 or more models: show comparison charts
- If user has only used 1 model: show single-model performance panel
