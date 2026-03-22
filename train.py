# -*- coding: utf-8 -*-

import utils.font_sync
import os
import torch
from ultralytics import YOLO
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

if __name__ == '__main__':
    # 原yolov8s，这里的yolov8s.yaml对应的就是文件夹下的yolov8.yaml， s 只是为了限定模型大小
    yaml_yolov8s = 'ultralytics/cfg/models/v8/yolov8s.yaml'
    # SE 注意力机制
    yaml_yolov8_SE = 'ultralytics/cfg/models/v8/det_self/yolov8s-attention-SE.yaml'

    # 替换一下变量名即可
    model_yaml = yaml_yolov8s
    # 模型加载
    model = YOLO(model_yaml)
    # 数据集路径的yaml文件
    data_path = os.path.join('config', 'traindata.yaml')
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    # 以yaml文件的名字进行命名
    name = os.path.basename(model_yaml).split('.')[0]
    # 模型训练
    model.train(data=data_path,             # 数据集
                imgsz=640,                  # 训练图片大小
                epochs=200,                 # 训练的轮次
                batch=2,                    # 训练batch
                workers=0,                  # 加载数据线程数
                device=device,              # 使用显卡
                optimizer='SGD',            # 优化器
                project='runs/train',       # 模型保存路径
                name=name,                  # 模型保存命名
                )
