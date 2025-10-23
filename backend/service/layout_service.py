
import base64
import requests          # 新增：远程调用
from pathlib import Path
from typing import List, Dict, Union, Optional
from PIL import Image, UnidentifiedImageError

# ----------- 常量 -----------
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
REMOTE_LAYOUT_URL = "http://i-2.gpushare.com:59537/layout"  # 远程推理地址



def layout_detect(png_path: Union[str, Path], confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> Dict[str, Union[Dict, List[Dict]]]:
    path = Path(png_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}")

    # ① 读文件 → base64
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # ② 远程只返回原始 JSON
    resp = requests.post(
        REMOTE_LAYOUT_URL,
        json={"png_b64": b64},
        timeout=60
    )
    resp.raise_for_status()
    json_data = resp.json()          # 就是 results[0].json

    # ③ 本地按需提取 table_zones（保持你原来逻辑）
    table_zones = []
    for idx, obj in enumerate(json_data.get("layout", [])):
        if obj["type"].lower() == "table" and obj.get("score", 0.0) >= confidence_threshold:
            table_zones.append({
                "table_id": idx,
                "bbox": [int(round(x)) for x in obj["bbox"]],
                "confidence": round(obj.get("score", 0.0), 4)
            })

    print(f"图片 {path.name} 检测到 {len(table_zones)} 个有效表格")
    return {"json": json_data, "table_zones": table_zones}



def batch_cut_tables(pdf_folder: str,
                     png_names: list[str],
                     output_root: str | Path,
                     confidence_threshold: float = 0.5) -> list[dict]:
    """
    本地只做 HTTP 转发，不再加载模型
    """
    output_root = Path(output_root)
    results = []
    layout_res = {}

    for png_name in png_names:
        png_path = output_root / pdf_folder / png_name
        print("batch_cut_tables:::---->:", "batch_cut_tables", png_path)
        try:
            # ❶ 读文件 → base64
            with open(png_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            print("*************1:", )
            # ❷ 发给远程
            resp = requests.post(
                REMOTE_LAYOUT_URL,
                json={"png_b64": b64, "confidence": confidence_threshold},
                timeout=120
            )
            resp.raise_for_status()
            remote_result = resp.json()  # {"layout":[...], "cuts":[...]}
            layout_res[png_name] = remote_result
            print("*************222:", remote_result)

        except Exception as e:
            print("*************YYYYYY", e)
            results.append({
                "png_name": png_name,
                "success": False,
                "error": str(e),
                "table_count": 0,
                "cuts": []
            })

    return results


