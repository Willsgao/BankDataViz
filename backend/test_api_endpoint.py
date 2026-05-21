"""
测试豆包 API 端点是否正确响应 image_url 请求
"""
import os
import base64
import io
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def create_test_image():
    """创建一张 100x100 的测试图片，返回 base64 编码"""
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def test_doubao_endpoint():
    """测试豆包端点"""
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model = "doubao-1-5-vision-pro-32k-250115"
    
    print("=" * 60)
    print("测试豆包端点:")
    print(f"  base_url: {base_url}")
    print(f"  model: {model}")
    print(f"  api_key (前10字符): {api_key[:10]}...")
    
    client = OpenAI(base_url=base_url, api_key=api_key)
    test_image = create_test_image()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "图片里是什么颜色？"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image}"}}
                ]
            }],
            max_tokens=50
        )
        print("  --> SUCCESS: 豆包 API 调用成功!")
        print(f"      回复: {response.choices[0].message.content[:100]}")
        return True
    except Exception as e:
        print(f"  --> FAILED: 豆包 API 调用失败: {type(e).__name__}: {str(e)[:300]}")
        return False

def test_deepseek_endpoint():
    """测试 DeepSeek 端点（预期会失败，因为 deepseek-chat 不支持 image_url）"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    base_url = "https://api.deepseek.com"
    model = "deepseek-chat"
    
    print("\n" + "=" * 60)
    print("测试 DeepSeek 端点 (预期失败 - deepseek-chat 不支持 image_url):")
    print(f"  base_url: {base_url}")
    print(f"  model: {model}")
    print(f"  api_key (前10字符): {api_key[:10]}...")
    
    client = OpenAI(base_url=base_url, api_key=api_key)
    test_image = create_test_image()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "图片里是什么颜色？"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image}"}}
                ]
            }],
            max_tokens=50
        )
        print("  --> WARNING: DeepSeek API 调用成功 (不应该成功!)")
        print(f"      回复: {response.choices[0].message.content[:100]}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"  --> EXPECTED: DeepSeek API 正确拒绝了 image_url")
        print(f"      错误: {error_msg[:300]}")
        # 检查是否是 image_url 相关的错误
        if "image_url" in error_msg.lower() or "variant" in error_msg.lower():
            print("      CONFIRMED: 这就是用户遇到的错误类型!")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("API 端点测试 - 验证 image_url 行为")
    print("=" * 60)
    
    doubao_ok = test_doubao_endpoint()
    deepseek_fail = test_deepseek_endpoint()
    
    print("\n" + "=" * 60)
    print("总结:")
    print(f"  豆包 API (image_url): {'SUCCESS - 正常支持' if doubao_ok else 'FAILED - 请检查配置'}")
    print(f"  DeepSeek API (image_url): {'WARNING - 不应该成功!' if deepseek_fail else 'EXPECTED - 正确拒绝了 image_url'}")
    
    if not doubao_ok:
        print("\n故障排查建议:")
        print("  1. 检查 LLM_API_KEY 是否正确 (应该是豆包 API Key)")
        print("  2. 检查网络是否能访问 ark.cn-beijing.volces.com")
        print("  3. 检查 project-config.json 中的 table_processor.llm 配置")
    
    print("\n下一步:")
    print("  如果豆包 API 测试失败，请检查:")
    print("  - .env 文件中的 LLM_API_KEY")
    print("  - project-config.json 中的 table_processor.llm.base_url")
