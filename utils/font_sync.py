import shutil
from pathlib import Path


def auto_sync_fonts():
    """自动同步字体到 Ultralytics 的 USER_CONFIG_DIR"""
    from ultralytics.utils import USER_CONFIG_DIR
    # 本地字体目录
    local_fonts_dir = Path(__file__).parent.parent / 'fonts'  # 假设 utils/font_sync.py，上层就是fonts/

    # 要同步的字体列表
    font_files = [
        "Arial.ttf",
        "Arial.Unicode.ttf"
    ]

    # 检查并复制
    for font_name in font_files:
        src_font_path = local_fonts_dir / font_name
        dst_font_path = USER_CONFIG_DIR / font_name

        if not dst_font_path.exists():
            if src_font_path.exists():
                USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_font_path, dst_font_path)
                # print(f"✅ 自动复制字体 {font_name} 到 {USER_CONFIG_DIR}")
            else:
                pass
                # print(f"⚠️ 本地字体 {src_font_path} 不存在，跳过。")

# 模块导入时，自动执行
auto_sync_fonts()
