#!/usr/local/miniconda3/bin/python3
"""
远程版面+表格裁切服务
GPUSHARE 强制 0.0.0.0:8080
"""

import cv2
import numpy as np          # 新增两行
import os, base64, io, json
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
from PIL import Image
from paddleocr import LayoutDetection

# ---------------- 模型初始化 ----------------
model = LayoutDetection(
    model_name="PP-DocLayout_plus-L",
    model_dir="/hy-tmp/ocr_codes/weights/PP-DocLayout_plus-L",
    device="gpu:0"
)

# ---------------- GPUSHARE 强制地址 ----------------
host = '0.0.0.0'
port = 8080



class LayoutHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/layout':
            content_len = int(self.headers['Content-Length'])
            post_body   = self.rfile.read(content_len)
            try:
                data       = json.loads(post_body)
                b64        = data["png_b64"]

                # ① 解码 → numpy → 推理
                img_pil = Image.open(io.BytesIO(base64.b64decode(b64)))
                img_np  = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                results = model.predict(img_np, batch_size=1, layout_nms=True)
                if not results:
                    raise RuntimeError("no layout detected")

                # ② 直接返回原始 JSON（不计算 table_zones，不裁切）
                raw_json = results[0].json
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(raw_json).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())


if __name__ == '__main__':
    server_address = (host, port)
    httpd = HTTPServer(server_address, LayoutHandler)
    print(f'Layout service started on {host}:{port}')
    httpd.serve_forever()