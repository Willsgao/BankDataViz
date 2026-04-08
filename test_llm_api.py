"""
火山引擎 ARK API 测试脚本
直接测试 LLM 接口连接是否正常
"""
import base64
import os
import sys
from pathlib import Path
from openai import OpenAI

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 从配置读取
API_KEY = "90b9c47f-815c-4216-913a-3d1a567e35ac"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_NAME = "doubao-1-5-vision-pro-250328"

LOG_FILE = Path(__file__).parent / "test_llm_api.log"


def log(msg):
    """打印到文件和屏幕"""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def test_llm_connection():
    """测试 LLM API 连接"""
    # 清空日志文件
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
    
    log("=" * 60)
    log("VOLCENGINE ARK API TEST")
    log("=" * 60)
    
    log(f"\nConfig:")
    log(f"   API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    log(f"   Base URL: {BASE_URL}")
    log(f"   Model: {MODEL_NAME}")
    
    # 创建客户端
    log(f"\nCreating OpenAI client...")
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        max_retries=0,  # 禁用自动重试
        timeout=30
    )
    
    # 简单文本请求测试
    log(f"\nSending test request (simple text)...")
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": "Please reply with 'Test Success' only"}
            ],
            max_tokens=100
        )
        log(f"\n[SUCCESS] Text request succeeded!")
        log(f"   Response: {response.choices[0].message.content}")
        log(f"   Model: {response.model}")
        log(f"   Usage: {response.usage}")
    except Exception as e:
        log(f"\n[FAILED] Text request failed!")
        log(f"   Error Type: {type(e).__name__}")
        log(f"   Error Message: {str(e)}")
        
        # 尝试解析详细错误
        if hasattr(e, 'response'):
            resp = e.response
            log(f"   Status Code: {resp.status_code if hasattr(resp, 'status_code') else 'N/A'}")
            log(f"   Response Body: {resp.text if hasattr(resp, 'text') else 'N/A'}")
        
        return False
    
    # 图片请求测试 (如果有测试图片)
    test_img_path = Path(__file__).parent / "test_codes" / "test_table.png"
    if test_img_path.exists():
        log(f"\nSending test request (image recognition)...")
        try:
            # 读取图片并转为 base64
            with open(test_img_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Please describe this image"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                        ]
                    }
                ],
                max_tokens=500
            )
            log(f"\n[SUCCESS] Image request succeeded!")
            log(f"   Response: {response.choices[0].message.content[:200]}...")
        except Exception as e:
            log(f"\n[FAILED] Image request failed!")
            log(f"   Error Type: {type(e).__name__}")
            log(f"   Error Message: {str(e)}")
    else:
        log(f"\n[SKIP] Image test skipped (test image not found: {test_img_path})")
    
    log("\n" + "=" * 60)
    log("Test completed!")
    log("=" * 60)
    return True


if __name__ == "__main__":
    success = test_llm_connection()
    sys.exit(0 if success else 1)
