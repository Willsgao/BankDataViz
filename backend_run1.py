from backend.app import app
from flask_cors import CORS

# 完整的 CORS 配置
CORS(
    app,
    resources={
        r"/api/*": {  # 对 /api/ 开头的所有路由应用 CORS
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://172.17.0.1:8080",
                # "http://101.43.35.52:8080",
                "http://122.51.196.65:8080",
                "http://122.51.196.65:5000",
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "expose_headers": ["Content-Type", "Content-Disposition"],
            "supports_credentials": True,
            "max_age": 86400
        }
    }
)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)