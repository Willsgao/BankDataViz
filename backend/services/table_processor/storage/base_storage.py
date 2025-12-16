from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseStorage(ABC):
    """存储基类 - 定义统一接口"""

    @abstractmethod
    def save_processed_result(self,
                              ocr_result: Dict[str, Any],
                              llm_result: Dict[str, Any],
                              reconstructed_data: List[List],
                              final_data: List[Dict[str, Any]],
                              metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存处理结果

        Args:
            ocr_result: OCR识别结果
            llm_result: LLM分析结果
            reconstructed_data: 重构的表格数据
            final_data: 最终长格式数据
            metadata: 元数据（图片路径、时间等）

        Returns:
            存储信息：{id: str, path: str, type: str}
        """
        pass

    @abstractmethod
    def get_processed_result(self, result_id: str) -> Dict[str, Any]:
        """
        获取处理结果

        Returns:
            {
                'ocr_result': ...,
                'llm_result': ...,
                'reconstructed_data': ...,
                'final_data': ...,
                'metadata': ...
            }
        """
        pass

    @abstractmethod
    def list_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """列出所有处理结果"""
        pass

    @abstractmethod
    def delete_result(self, result_id: str) -> bool:
        """删除处理结果"""
        pass

    @abstractmethod
    def save_final_data_only(self, final_data: List[Dict[str, Any]],
                             metadata: Dict[str, Any]) -> str:
        """仅保存最终数据（长格式）"""
        pass