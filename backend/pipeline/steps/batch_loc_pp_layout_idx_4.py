import json
import glob
from pathlib import Path
from paddleocr import LayoutDetection


model = LayoutDetection(model_name="PP-DocLayout_plus-L")
# model = LayoutDetection(model_name="ppstructure_v2_layout")


# from paddlex.inference import create_predictor
# model = create_predictor("PP-DocLayout_plus-L")


def batch_layout_to_single_json(img_dir: str, out_dir: str) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    all_layouts = {}

    for idx, img_path in enumerate(sorted(glob.glob(str(Path(img_dir) / "*"))), start=1):
        output = model.predict(img_path, batch_size=1, layout_nms=True)
        img_name = Path(img_path).stem
        for res in output:
            res.save_to_img(save_path=out_dir)      # 可视化
            all_layouts[img_name] = res.json        # 直接字典

    summary = Path(out_dir) / "all_layouts.json"
    summary.write_text(json.dumps(all_layouts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已汇总 {len(all_layouts)} 页 → {summary}")

if __name__ == "__main__":
    dir_idx = "514009"
    img_dir = f"/hy-tmp/my_pros/imgs/{dir_idx}"
    out_dir = f"/hy-tmp/my_pros/output/{dir_idx}"
    batch_layout_to_single_json(img_dir, out_dir)