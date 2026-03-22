import os


def get_model_size_mb(model_path):
    """获取模型文件大小（MB）"""
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在：{model_path}")
        return None
    return round(os.path.getsize(model_path) / (1024 * 1024), 2)


def calculate_fps_from_speed(speed):
    """根据毫秒速度计算 FPS（帧率）"""
    pre_ms = speed.get('preprocess', 0)
    infer_ms = speed.get('inference', 0)
    loss_ms = speed.get('loss', 0)
    post_ms = speed.get('postprocess', 0)
    total_ms = pre_ms + infer_ms
    fps = round(1000.0 / total_ms, 2) if total_ms > 0 else 0
    return total_ms, fps


def get_model_params(model):
    return round(sum(p.numel() for p in model.model.parameters()) / 1e6, 1)




def report_model_performance(all_results, model_path, metrics, model):
    # 推理速度和 FPS
    speed = metrics.speed  # 毫秒
    speed_ms, fps = calculate_fps_from_speed(speed)

    # 模型大小
    size_mb = get_model_size_mb(model_path)
    # 模型参数量
    params_m = get_model_params(model)

    mAP50 = getattr(metrics.box, 'map50', 0)
    mAP5095 = getattr(metrics.box, 'map', 0)
    recall = getattr(metrics.box, 'mr', 0)
    precision = getattr(metrics.box, 'mp', 0)

    result = [
        model_path,
        params_m,
        size_mb,
        round(speed_ms, 2),
        round(fps, 2),
        round(precision, 3),
        round(recall, 3),
        round(mAP50, 3),
        round(mAP5095, 3)
    ]
    all_results.append(result)
    return all_results


def get_col_widths(headers, results):
    """
    根据 headers 和 results 自动计算每列最大宽度
    """
    num_cols = len(headers)
    col_widths = [len(h) for h in headers]

    for row in results:
        for i in range(num_cols):
            col_widths[i] = max(col_widths[i], len(str(row[i])))

    return col_widths


def pad_string_cn(text, width):
    """
    中文字符处理：一个中文算两个宽度（更美观对齐）
    """
    count = 0
    for ch in text:
        count += 2 if '\u4e00' <= ch <= '\u9fff' else 1
    return text + ' ' * (width - count)


def print_table(results):
    print("\n📊 多模型评估结果对比表格：")
    header_dict = {
        "Model Name": "模型名称",
        "Params (M)": "参数量(M)",
        "Size (MB)": "模型大小(MB)",
        "Inference Time(ms)": "推理速度(ms)",
        "FPS": "帧率",
        "Precision": "精度",
        "Recall": "召回率",
        "mAP50": "mAP50",
        "mAP50-95": "mAP50-95"
    }

    col_widths = get_col_widths(header_dict.keys(), results)

    # 打印表头
    header_line = "| " + " | ".join(pad_string_cn(h, w) for h, w in zip(header_dict.keys(), col_widths)) + " |"
    print(header_line)

    print("|" + "|".join("-" * (w + 2) for w in col_widths) + "|")

    # 打印每行
    for row in results:
        row_line = "| " + " | ".join(pad_string_cn(str(cell), w) for cell, w in zip(row, col_widths)) + " |"
        print(row_line)

    # print('\n以下是对上方表格表头对应中文的解释说明：')
    # # 打印表头对应的中文解释
    # for en, cn in header_dict.items():
    #     print(f"{en.ljust(15)} -> {cn}")
