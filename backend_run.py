from backend.app import app
from flask_cors import CORS

# # 完整的 CORS 配置
# CORS(
#     app,
#     origins=["http://localhost:8080", "http://127.0.0.1:8080"],
#     supports_credentials=True,
#     allow_headers=["*"],
#     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]  # ✅ 包含 OPTIONS
# )


CORS(
    app,
    origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://172.17.0.1:8080",      # 容器内网
        "http://101.43.35.52:8080",
    ],
    supports_credentials=True,
    allow_headers=["*"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)