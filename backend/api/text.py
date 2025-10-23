# -*- coding:utf-8 -*-
from flask import Blueprint, request, jsonify
import sqlite3
from backend.utils.constants import DATABASE   # 确保能拿到 db 路径

text_bp = Blueprint('text', __name__)

@text_bp.route('/text', methods=['GET', 'POST'])
def text():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS texts(
                    id      INTEGER PRIMARY KEY CHECK(id=1),
                    content TEXT    NOT NULL DEFAULT '')""")
    conn.commit()

    if request.method == 'GET':
        row = c.execute("SELECT content FROM texts WHERE id=1").fetchone()
        conn.close()
        return jsonify({"content": row["content"] if row else ""})

    content = request.json.get('content', '')
    c.execute("INSERT OR REPLACE INTO texts(id, content) VALUES (1, ?)", (content,))
    conn.commit()
    conn.close()
    return jsonify({"status": "saved", "message": "富文本内容已保存"})