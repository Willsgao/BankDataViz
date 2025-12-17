import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base_storage import BaseStorage
from backend.utils.config import tableconfig


class ExcelStorage(BaseStorage):
    """Excel文件存储实现"""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or tableconfig.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.output_dir, "metadata.json")
        self._init_metadata()

    def _init_metadata(self):
        """初始化元数据文件"""
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump({"results": [], "next_id": 1}, f, ensure_ascii=False, indent=2)

    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_metadata(self, metadata: Dict[str, Any]):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def save_processed_result(self, ocr_result, llm_result, reconstructed_data,
                              final_data, metadata) -> Dict[str, Any]:
        """保存完整处理结果到Excel文件"""
        import uuid

        # 生成唯一ID和文件名
        result_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{timestamp}_{result_id}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        # 创建Excel文件，多个sheet
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Sheet1: OCR结果（简化版）
            ocr_df = pd.DataFrame([{
                'tables_count': len(ocr_result.get('tables_result', [])),
                'image_path': ocr_result.get('image_info', {}).get('image_path', '')
            }])
            ocr_df.to_excel(writer, sheet_name='ocr_info', index=False)

            # Sheet2: LLM结果
            llm_tables = llm_result.get('tables_structure', {}).get('tables', [])
            llm_data = []
            for table in llm_tables:
                llm_data.append({
                    'id': table.get('id'),
                    'name': table.get('name', ''),
                    'cols_count': len(table.get('headers', {}).get('cols', [])),
                    'rows_count': len(table.get('headers', {}).get('rows', []))
                })
            if llm_data:
                pd.DataFrame(llm_data).to_excel(writer, sheet_name='llm_info', index=False)

            # Sheet3: 重构数据（如果有）
            if reconstructed_data:
                # 将二维列表转换为DataFrame
                max_cols = max(len(row) for row in reconstructed_data) if reconstructed_data else 0
                data_for_df = []
                for row in reconstructed_data:
                    # 补齐列数
                    padded_row = row + [None] * (max_cols - len(row)) if len(row) < max_cols else row
                    data_for_df.append(padded_row[:max_cols])  # 限制列数

                if data_for_df:
                    pd.DataFrame(data_for_df).to_excel(writer, sheet_name='reconstructed', index=False, header=False)

            # Sheet4: 最终数据
            if final_data:
                pd.DataFrame(final_data).to_excel(writer, sheet_name='final_data', index=False)

            # Sheet5: 元数据
            metadata_df = pd.DataFrame([{
                'result_id': result_id,
                'timestamp': timestamp,
                'image_path': metadata.get('image_path', ''),
                'processing_time': metadata.get('processing_time', 0),
                'status': 'completed'
            }])
            metadata_df.to_excel(writer, sheet_name='metadata', index=False)

        # 更新全局元数据
        meta_data = self._load_metadata()
        meta_data['results'].append({
            'id': result_id,
            'filepath': filepath,
            'filename': filename,
            'timestamp': timestamp,
            'image_path': metadata.get('image_path', ''),
            'size': os.path.getsize(filepath)
        })
        meta_data['next_id'] += 1
        self._save_metadata(meta_data)

        return {
            'id': result_id,
            'filepath': filepath,
            'filename': filename,
            'type': 'excel'
        }

    def get_processed_result(self, result_id: str) -> Dict[str, Any]:
        """从Excel文件读取处理结果"""
        meta_data = self._load_metadata()

        # 查找结果
        result_info = None
        for result in meta_data['results']:
            if result['id'] == result_id:
                result_info = result
                break

        if not result_info or not os.path.exists(result_info['filepath']):
            raise ValueError(f"结果不存在: {result_id}")

        filepath = result_info['filepath']

        # 读取各个sheet
        result = {
            'metadata': {},
            'final_data': []
        }

        try:
            # 读取元数据
            metadata_df = pd.read_excel(filepath, sheet_name='metadata')
            if not metadata_df.empty:
                result['metadata'] = metadata_df.iloc[0].to_dict()

            # 读取最终数据
            final_df = pd.read_excel(filepath, sheet_name='final_data')
            result['final_data'] = final_df.to_dict('records')

        except Exception as e:
            raise ValueError(f"读取Excel文件失败: {e}")

        return result

    def list_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """列出所有处理结果"""
        meta_data = self._load_metadata()
        results = meta_data['results'].copy()

        # 应用过滤条件
        if filters:
            filtered_results = []
            for result in results:
                match = True
                for key, value in filters.items():
                    if key in result and result[key] != value:
                        match = False
                        break
                if match:
                    filtered_results.append(result)
            return filtered_results

        return results

    def delete_result(self, result_id: str) -> bool:
        """删除处理结果"""
        meta_data = self._load_metadata()

        for i, result in enumerate(meta_data['results']):
            if result['id'] == result_id:
                # 删除文件
                filepath = result['filepath']
                if os.path.exists(filepath):
                    os.remove(filepath)

                # 从元数据中移除
                meta_data['results'].pop(i)
                self._save_metadata(meta_data)
                return True

        return False

    def save_final_data_only(self, final_data: List[Dict[str, Any]],
                             metadata: Dict[str, Any]) -> str:
        """仅保存最终数据（简化版）"""
        import uuid

        result_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_{timestamp}_{result_id}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        # 保存到Excel
        df = pd.DataFrame(final_data)
        df.to_excel(filepath, index=False)

        return filepath