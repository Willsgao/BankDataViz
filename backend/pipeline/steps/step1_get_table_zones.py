import json
from pathlib import Path
from paddleocr import LayoutDetection


# model = LayoutDetection(model_name="PP-DocLayout_plus-L")
import os
root_dir = os.getcwd()
model = LayoutDetection(
    model_name="PP-DocLayout_plus-L",   # 必须还是这个代号，用来告诉接口用哪套网络结构
    model_dir="{}/backend/weights/PP-DocLayout_plus-L".format(root_dir)  # <- 你手动放权重的目录
)

def batch_layout_to_single_json(img_dir: str, out_dir: str) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    all_layouts = {}
    for p in sorted(Path(img_dir).glob("*")):
        for res in model.predict(str(p), batch_size=1, layout_nms=True):
            res.save_to_img(save_path=out_path)          # 可视化
            all_layouts[p.stem] = res.json               # 收集结果

    summary = out_path / "all_layouts.json"
    summary.write_text(
        json.dumps(all_layouts, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"已汇总 {len(all_layouts)} 页 → {summary}")


if __name__ == "__main__":
    dir_name = ""
    batch_layout_to_single_json(
        img_dir=f"{root_dir}/backend/static/pdf2pngs/{dir_name}",
        out_dir=f"/hy-tmp/my_pros/output/{dir_name}"
    )