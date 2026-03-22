# -*- coding: utf-8 -*-

import utils.font_sync
import os
import warnings

import cv2
import torch
from ultralytics import YOLO

warnings.filterwarnings('ignore')


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def run_inference():
    model = YOLO(model_path)
    results = model.predict(image_path, imgsz=img_size, conf=conf_threshold, device=device)

    result_list = []

    # 提取原图文件名
    filename = os.path.basename(image_path)
    name, ext = os.path.splitext(filename)
    result_filename = f"{name}_result.jpg"

    for i, r in enumerate(results):
        boxes = r.boxes.xyxy.cpu().numpy().tolist()
        confs = r.boxes.conf.cpu().numpy().tolist()
        clses = r.boxes.cls.cpu().numpy().tolist()
        names = r.names
        speed = r.speed
        infer_time = round((speed['preprocess'] + speed['inference'] + speed['postprocess']) / 1000, 3)

        for box, conf, cls in zip(boxes, confs, clses):
            result_list.append({
                "class": names[int(cls)],
                "confidence": round(conf, 3),
                "bbox": [round(x, 2) for x in box]
            })

        print(f"[INFO] 推理耗时: {infer_time}s")
        print(f"[INFO] FPS: {round(1 / infer_time, 2)}")
        for item in result_list:
            print(item)

        ensure_dir(save_dir)
        save_path = os.path.join(save_dir, result_filename)

        im_bgr = r.plot()
        cv2.imwrite(save_path, im_bgr)
        print(f"[INFO] 结果图像已保存: {save_path}")

        if show_image:
            cv2.imshow("Detection Result", im_bgr)
            cv2.waitKey(0)
            cv2.destroyAllWindows()


if __name__ == '__main__':
    # 模型路径
    model_path = r"weights/yolov8s/weights/best.pt"
    # 图片路径
    image_path = r"img/crazing_149.jpg"
    # 图片大小
    img_size = 640
    # 置信度阈值
    conf_threshold = 0.4
    device = "cuda" if torch.cuda.is_available() else "cpu"
    save_dir = "output"
    show_image = True

    run_inference()
