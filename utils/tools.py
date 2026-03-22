import cv2
import xlwt
import numpy as np
import colorsys
import os
import platform
import subprocess
from PIL import ImageFont, ImageDraw, Image


def print_model_info(metrics, model_path):
    print('-------------------------')
    speed = metrics.speed
    fps = calculate_fps_from_speed(speed)
    print('FPS:', fps)
    model_size = get_model_size_mb(model_path)
    if model_size is not None:
        print(f"✅ 模型大小为：{model_size} MB")


def calculate_fps_from_speed(speed):
    # 计算FPS
    pre_ms = speed.get('preprocess', 0)
    infer_ms = speed.get('inference', 0)
    loss_ms = speed.get('loss', 0)
    post_ms = speed.get('postprocess', 0)
    total_ms = pre_ms + infer_ms
    fps = round(1000.0 / total_ms, 2) if total_ms > 0 else 0
    return fps


def get_model_size_mb(model_path):
    """
    获取模型文件的大小（单位：MB）

    参数:
        model_path (str): 模型文件的路径（如 .pt）

    返回:
        float: 文件大小（MB），若文件不存在返回 None
    """
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在：{model_path}")
        return None

    size_bytes = os.path.getsize(model_path)
    size_mb = size_bytes / (1024 * 1024)
    return round(size_mb, 2)


def result_info_format(result_info, box, score, cls_name):
    '''
        格式组合
    '''
    # 类别
    result_info['cls_name'] = cls_name
    # 置信度
    result_info['score'] = round(score, 2)
    result_info['label_xmin_v'] = int(box[0])
    result_info['label_ymin_v'] = int(box[1])
    result_info['label_xmax_v'] = int(box[2])
    result_info['label_ymax_v'] = int(box[3])

    return result_info


def format_data(results, chinese_name, draw_chinese=False):
    '''
    整理模型的识别结果
    :param results: 检测结果
    :param chinese_name: 英文-中文名映射字典
    :param draw_chinese: 是否使用中文名输出
    :return:
        lst_results: [英文名, 置信度, 坐标]列表（固定英文）
        tab_res_chinese: 中文名或英文名列表（根据draw_chinese）
    '''
    lst_results = []
    tab_res_list = []

    for i, r in enumerate(results):
        boxes = r.boxes.xyxy.cpu().numpy().tolist()
        conf = r.boxes.conf.cpu().numpy().tolist()
        cls = r.boxes.cls.cpu().numpy().tolist()
        names = r.names

        for box, con, c in zip(boxes, conf, cls):
            class_name = names[c]

            if draw_chinese and chinese_name and class_name in chinese_name:
                lst_results.append([chinese_name[class_name], round(con, 2), box])
                tab_res_list.append(chinese_name[class_name])
            else:
                lst_results.append([class_name, round(con, 2), box])
                tab_res_list.append(class_name)

    if not tab_res_list:
        tab_res_list = '无目标'

    return lst_results, tab_res_list


def open_image_with_default_viewer(img_path):
    """
    调用系统默认图片查看器打开图片
    """
    try:
        system_platform = platform.system()
        if system_platform == "Windows":
            os.startfile(img_path)
        elif system_platform == "Darwin":  # macOS
            subprocess.call(["open", img_path])
        else:  # Linux
            subprocess.call(["xdg-open", img_path])
    except Exception as e:
        print(f"打开图片失败: {e}")


def writexls(DATA, path):
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Data')
    for i, Data in enumerate(DATA):
        for j, data in enumerate(Data):
            ws.write(i, j, str(data))
    wb.save(path)


def writecsv(DATA, path):
    try:
        f = open(path, 'w', encoding='utf8')
        for data in DATA:
            f.write(','.join('%s' % dat for dat in data) + '\n')
        f.close()
    except Exception as e:
        print(e)


def resize_with_padding(image, target_width, target_height, padding_value):
    """
    填充原图片的四周
    """
    # 原始图像大小
    original_height, original_width = image.shape[:2]

    # 计算宽高比例
    width_ratio = target_width / original_width
    height_ratio = target_height / original_height

    # 确定调整后的图像大小和填充大小
    if width_ratio < height_ratio:
        new_width = target_width
        new_height = int(original_height * width_ratio)
        top = (target_height - new_height) // 2
        bottom = target_height - new_height - top
        left, right = 0, 0
    else:
        new_width = int(original_width * height_ratio)
        new_height = target_height
        left = (target_width - new_width) // 2
        right = target_width - new_width - left
        top, bottom = 0, 0

    # 调整图像大小并进行固定值填充
    resized_image = cv2.resize(image, (new_width, new_height))
    padded_image = cv2.copyMakeBorder(resized_image, top, bottom, left, right, cv2.BORDER_CONSTANT,
                                      value=padding_value)

    return padded_image


def compute_color_for_labels(label):
    """
    根据类别名生成固定颜色
    """
    if isinstance(label, str):
        label = abs(hash(label)) % 1000

    golden_ratio_conjugate = 0.618033988749895
    hue = (label * golden_ratio_conjugate) % 1

    saturation = 0.7
    value = 0.95

    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
    return int(r * 255), int(g * 255), int(b * 255)


def draw_text_with_background(img, text, position, font_path, font_size, text_color, bg_color):
    """
    在图像上绘制带背景色的中文（或英文）文本
    """
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, font_size, encoding="utf-8")

    text_width, text_height = draw.textsize(text, font)

    # 背景矩形
    background = [position[0], position[1], position[0] + text_width + 4, position[1] + text_height + 4]
    draw.rectangle(background, fill=bg_color)

    # 文字
    draw.text((position[0] + 2, position[1] + 2), text, font=font, fill=text_color)

    return np.array(img_pil)


def draw_info(frame, results, draw_chinese=False, chinese_name=None):
    """
    绘制检测框和标签，保证文字整体对齐统一、美观，适合论文图片
    """
    CHINESE_FONT_PATH = 'fonts/Arial.Unicode.ttf'
    img_h, img_w = frame.shape[:2]

    for i, bbox in enumerate(results):
        cls_name = bbox[0]  # 类别名
        conf = bbox[1]  # 置信度
        box = bbox[2]  # 框坐标 [x1, y1, x2, y2]

        color = compute_color_for_labels(cls_name)

        x1, y1, x2, y2 = map(int, box)
        # 绘制检测框
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # 文字内容
        if draw_chinese and chinese_name is not None and cls_name in chinese_name:
            display_name = chinese_name[cls_name]
        else:
            display_name = cls_name

        display_text = f"{display_name} {conf:.2f}"

        if draw_chinese:
            font_size = 20
            font = ImageFont.truetype(CHINESE_FONT_PATH, font_size, encoding="utf-8")
            dummy_img = Image.new('RGB', (100, 100))
            dummy_draw = ImageDraw.Draw(dummy_img)
            text_width, text_height = dummy_draw.textsize(display_text, font)
        else:
            font_scale = 0.5
            thickness = 1
            (text_width, text_height), baseline = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                                                                  thickness)

        padding = 6  # 内边距
        margin = 2  # 框和文字之间的外边距

        # 默认文字块放在框的上方靠左
        bg_x1 = x1
        bg_y1 = y1 - (text_height + 2 * padding + margin)

        # 如果上方超界了，就放到框下方
        if bg_y1 < 0:
            bg_y1 = y1 + margin

        bg_x2 = bg_x1 + text_width + 2 * padding
        bg_y2 = bg_y1 + text_height + 2 * padding

        # 检查右边界
        if bg_x2 > img_w:
            bg_x1 = img_w - (text_width + 2 * padding + margin)
            bg_x2 = img_w - margin

        # 最终绘制
        if draw_chinese:
            img_pil = Image.fromarray(frame)
            draw = ImageDraw.Draw(img_pil)

            # 画带填充的矩形背景
            background_rect = [bg_x1, bg_y1, bg_x2, bg_y2]
            draw.rectangle(background_rect, fill=color)

            # 写文字
            draw.text(
                (bg_x1 + padding, bg_y1 + padding),
                display_text,
                font=font,
                fill=(255, 255, 255)
            )

            frame = np.array(img_pil)

        else:
            cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)
            cv2.putText(frame, display_text,
                        (bg_x1 + padding, bg_y1 + text_height + padding - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                        (255, 255, 255), thickness, cv2.LINE_AA)

    return frame

