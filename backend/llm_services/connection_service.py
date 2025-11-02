
import time

from flask import jsonify

from backend.llm_services.utils import validate_required_params


async def _test_connection_internal(data):
    """测试LLM连接的内部异步函数"""
    try:
        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['base_url', 'api_key', 'model_id']
        )
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        base_url = data.get('base_url')
        api_key = data.get('api_key')
        model_id = data.get('model_id')

        print(
            f"🔧 测试连接参数: base_url={base_url}, model_id={model_id}, api_key_length={len(api_key) if api_key else 0}")

        # 确保URL格式正确
        if not base_url.endswith('/'):
            base_url = base_url + '/'

        # 创建临时客户端进行测试
        from openai import AsyncOpenAI

        try:
            test_client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_key
            )

            # 测试连接 - 使用更简单的消息
            print(f"🔧 开始API调用测试...")
            response = await test_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "Hello, please respond with just 'OK'"}],
                max_tokens=10,
                timeout=30.0  # 添加超时设置
            )

            print(f"🔧 API响应: {response}")

            return {
                "success": True,
                "message": "LLM连接测试成功",
                "data": {
                    "model_response": bool(response.choices),
                    "response_content": response.choices[0].message.content if response.choices else None
                }
            }

        except Exception as api_error:
            print(f"❌ API调用失败: {str(api_error)}")
            error_detail = str(api_error)

            # 提供更详细的错误信息
            if "401" in error_detail:
                error_msg = "API密钥无效或未授权"
            elif "404" in error_detail:
                error_msg = "模型不存在或URL路径错误"
            elif "connect" in error_detail.lower():
                error_msg = "无法连接到服务器，请检查网络和URL"
            elif "timeout" in error_detail.lower():
                error_msg = "连接超时，请检查网络或服务器状态"
            else:
                error_msg = f"API调用失败: {error_detail}"

            return {
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        print(f"❌ 连接测试异常: {str(e)}")
        return {
            "success": False,
            "error": f"连接测试失败: {str(e)}"
        }


def get_available_models():
    """获取可用的模型列表"""
    models = [
        {
            "id": "doubao-1-5-vision-pro-250328",
            "name": "豆包视觉专业版",
            "description": "支持视觉识别的专业模型",
            "max_tokens": 16000
        },
        {
            "id": "doubao-seed-1-6-vision-250815",
            "name": "豆包视觉种子版",
            "description": "视觉识别基础模型",
            "max_tokens": 16000
        }
    ]

    return jsonify({
        "success": True,
        "data": models
    })



def health_check_internal():
    """健康检查内部实现 - 需要修改，从llm_routes.py移入"""
    from .core_service import get_table_processor
    processor = get_table_processor()

    base_url = getattr(processor.llm_client, 'base_url', None)
    if base_url is not None:
        base_url = str(base_url)

    return {
        "success": True,
        "data": {
            "service": "running",
            "llm_configured": processor.llm_client is not None,
            "model_id": processor.model_id,
            "base_url": base_url,
            "timestamp": time.time()
        }
    }


def check_llm_config():
    """检查LLM配置状态 - 需要修改，从llm_routes.py移入"""
    from .core_service import get_table_processor
    processor = get_table_processor()

    return {
        "success": True,
        "data": {
            "llm_configured": processor.llm_client is not None,
            "model_id": getattr(processor, 'model_id', '未设置'),
            "base_url": getattr(processor.llm_client, 'base_url', None) if processor.llm_client else None,
            "client_type": type(processor.llm_client).__name__ if processor.llm_client else '未配置'
        }
    }