import logging
from backend.services.llm.state_manager import state_manager
from backend.services.llm.task_management_service import (
    _table_processor_instance,
    _non_financial_table_service)
from backend.services.llm.utils import validate_required_params

logger = logging.getLogger(__name__)



def configure_llm(data=None):
    """配置LLM参数"""
    try:
        if not data:
            return {
                "success": False,
                "error": "请求体不能为空"
            }

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
        table_type = data.get('table_type', 'financial')
        prompts = data.get('prompts', {})

        print(f"🔧 解析配置参数: base_url={base_url}, model_id={model_id}, table_type={table_type}")

        # 根据表格类型选择不同的处理器
        if table_type == 'financial':
            from backend.services.table_llm_service import TableLLMService
            processor = TableLLMService(llm_client=None, model_id=model_id)
            state_manager.set_table_processor(processor)
        else:
            from backend.services.non_financial_table_service import NonFinancialTableService
            processor = NonFinancialTableService(llm_client=None, model_id=model_id)
            state_manager.set_non_financial_table_service(processor)

        # 检查客户端是否配置成功
        if not processor.llm_client:
            return {
                "success": False,
                "error": "LLM客户端配置失败，请检查API密钥和URL是否正确"
            }

        return {
            "success": True,
            "message": f"LLM配置成功",
            "data": {
                "model_id": processor.model_id,
                "base_url": base_url,
                "table_type": table_type,
                "client_configured": processor.llm_client is not None
            }
        }

    except Exception as e:
        logger.error(f"LLM配置失败: {str(e)}")
        return {
            "success": False,
            "error": f"配置失败: {str(e)}"
        }


def get_processor_status():
    """获取处理器状态"""
    try:
        # 检查当前配置的处理器类型
        current_processor = None
        table_type = "unknown"
        processor_type = "未知"

        if _table_processor_instance is not None:
            current_processor = _table_processor_instance
            table_type = "financial"
            processor_type = "金融表格处理器"
        elif _non_financial_table_service is not None:
            current_processor = _non_financial_table_service
            table_type = "non_financial"
            processor_type = "普通表格处理器"
        else:
            # 如果没有配置，使用默认的金融表格处理器
            from backend.services.table_llm_service import get_table_processor
            current_processor = get_table_processor()
            table_type = "financial"
            processor_type = "金融表格处理器（默认）"

        # 确保所有值都是可JSON序列化的
        base_url = getattr(current_processor.llm_client, 'base_url', None)
        if base_url is not None:
            base_url = str(base_url)

        status = {
            "client_configured": current_processor.llm_client is not None,
            "model_id": current_processor.model_id,
            "base_url": base_url,
            "table_type": table_type,
            "processor_type": processor_type,
            "prompts_configured": {}
        }

        # 添加提示词配置信息
        if hasattr(current_processor, 'prompt_registry'):
            status["prompts_configured"] = {
                prompt_type: bool(content) and len(content.strip()) > 0
                for prompt_type, content in current_processor.prompt_registry.items()
            }
        elif hasattr(current_processor, 'prompt'):
            status["prompts_configured"] = {
                "non_financial": bool(current_processor.prompt) and len(current_processor.prompt.strip()) > 0
            }

        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}")
        return {
            "success": False,
            "error": f"获取状态失败: {str(e)}"
        }