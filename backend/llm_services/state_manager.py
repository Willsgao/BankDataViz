"""
中心化状态管理器
确保所有模块共享相同的状态
"""

import logging

logger = logging.getLogger(__name__)


class StateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化所有状态"""
        self.TASK_RESULTS = {}
        self.PROCESSING_STATUS = {}
        self._table_processor_instance = None
        self._non_financial_table_service = None
        print("✅ 状态管理器初始化完成")

    # TASK_RESULTS 相关方法
    def set_task_result(self, task_id, result):
        """设置任务结果"""
        self.TASK_RESULTS[task_id] = result
        print(f"✅ 任务结果已存储: {task_id}, 当前任务数: {len(self.TASK_RESULTS)}")

    def get_task_result(self, task_id):
        """获取任务结果"""
        return self.TASK_RESULTS.get(task_id)

    def task_exists(self, task_id):
        """检查任务是否存在"""
        return task_id in self.TASK_RESULTS

    # PROCESSING_STATUS 相关方法
    def set_processing_status(self, task_id, status):
        """设置处理状态"""
        self.PROCESSING_STATUS[task_id] = status

    def get_processing_status(self, task_id):
        """获取处理状态"""
        return self.PROCESSING_STATUS.get(task_id)

    # 处理器实例相关方法
    def set_table_processor(self, processor):
        """设置金融表格处理器"""
        self._table_processor_instance = processor
        print("✅ 金融表格处理器已设置")

    def get_table_processor(self):
        """获取金融表格处理器"""
        if self._table_processor_instance is None:
            from backend.service.table_llm_service import get_table_processor as get_processor
            self._table_processor_instance = get_processor()
            print("🔄 创建默认金融表格处理器")
        return self._table_processor_instance

    def set_non_financial_table_service(self, service):
        """设置普通表格服务"""
        self._non_financial_table_service = service
        print("✅ 普通表格服务已设置")

    def get_non_financial_table_service(self):
        """获取普通表格服务"""
        if self._non_financial_table_service is None:
            from backend.service.non_financial_table_service import NonFinancialTableService
            self._non_financial_table_service = NonFinancialTableService()
            print("🔄 创建默认普通表格服务")
        return self._non_financial_table_service

    def get_appropriate_processor(self, table_type=None):
        """根据表格类型获取合适的处理器"""
        if table_type == 'non_financial' or self._non_financial_table_service is not None:
            return self.get_non_financial_table_service()
        else:
            return self.get_table_processor()


# 创建全局单例实例
state_manager = StateManager()

