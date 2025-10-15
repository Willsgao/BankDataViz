# -*- coding:utf-8 -*-


import json, glob, time
from pathlib import Path
from ultralytics import YOLO        # ① 引入 YOLO
from paddleocr import LayoutDetection


yolo = YOLO("yolov8n.pt")           # ② 3 毫秒级检测器
paddle = LayoutDetection("PP-DocLayout_plus-L")  # 高精度兜底


def yolo_crop_valid(img_path: Path) -> bool:
    """
    YOLO 只要检出 table 或 figure 就算有效版面
    """
    results = yolo(img_path, verbose=False)
    for box in results[0].boxes:
        cls = int(box.cls)
        # COCO 类别：table=0, figure=1（如用自定义权重改这里）
        if cls in {0, 1}:
            return True
    return False


def batch_layout_to_single_json(img_dir: str, out_dir: str) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    all_layouts = {}

    img_list = sorted(glob.glob(str(Path(img_dir) / "*")))
    for idx, img_path in enumerate(img_list, start=1):
        img_name = Path(img_path).stem
        t0 = time.time()

        # ③ 先让 YOLO 看有没有表格/图片
        if yolo_crop_valid(img_path):
            # 有 → 再用 PP 精细分割
            output = paddle.predict(img_path, batch_size=1, layout_nms=True)
            for res in output:
                res.save_to_img(save_path=out_dir)   # 可视化
                all_layouts[img_name] = res.json
        else:
            # 无 → 直接空字典，省掉一次 heavy 推理
            all_layouts[img_name] = {}

        print(f"[{idx}/{len(img_list)}] {img_name}  "
              f"YOLO判定={'有' if img_name in all_layouts else '无'}  "
              f"耗时={(time.time()-t0)*1000:.1f}ms")

    summary = Path(out_dir) / "all_layouts.json"
    summary.write_text(json.dumps(all_layouts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已汇总 {len(all_layouts)} 页 → {summary}")


if __name__ == "__main__":
    dir_idx = "514001"
    img_dir = f"/hy-tmp/my_pros/imgs/{dir_idx}"
    out_dir = f"/hy-tmp/my_pros/output/{dir_idx}"
    batch_layout_to_single_json(img_dir, out_dir)
