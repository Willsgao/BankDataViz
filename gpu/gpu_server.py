#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 布局服务  /do-pp-layout
接收 zip（png 文件夹）→ 返回 all_layouts.json
"""
import io, json, tempfile, shutil
from pathlib import Path
from zipfile import ZipFile
from flask import Flask, request, jsonify, send_file
from paddlex.inference import create_predictor

app = Flask(__name__)
model = create_predictor("PP-DocLayout_plus-L")   # 预加载

@app.route("/do-pp-layout", methods=["POST"])
def do_pp_layout():
    if "file" not in request.files:
        return jsonify(error="missing zip file"), 400
    zip_bytes = request.files["file"].read()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ZipFile(io.BytesIO(zip_bytes)).extractall(tmp)
        # 找第一个文件夹（前端按约定打包）
        img_dir = next(d for d in tmp.iterdir() if d.is_dir())
        all_layouts = {}
        for img in sorted(img_dir.glob("*.png")):
            out = model.predict(str(img), batch_size=1, layout_nms=True)
            for res in out:
                all_layouts[img.stem] = res.json
        json_path = tmp / "all_layouts.json"
        json_path.write_text(json.dumps(all_layouts, ensure_ascii=False, indent=2))
        return send_file(json_path, as_attachment=True)

if __name__ == "__main__":
    import fire
    fire.Fire(lambda host="0.0.0.0", port=8090: app.run(host=host, port=port, debug=False))