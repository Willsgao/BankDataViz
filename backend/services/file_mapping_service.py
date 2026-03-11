# backend/services/file_mapping_service.py
import os
import json
from pathlib import Path
from backend.utils.constants import SAVE_PATH


class FileMappingService:
    def __init__(self):
        self.mapping_folder = Path(SAVE_PATH)
        self.mapping_file = self.mapping_folder / "file_mapping.json"
        self.mapping = self._load_mapping()

    def _load_mapping(self):
        """加载文件映射"""
        if self.mapping_file.exists():
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_mapping(self):
        """保存文件映射"""
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

    def add_mapping(self, file_id, original_name, file_type):
        """添加文件映射"""
        self.mapping[file_id] = {
            "original_name": original_name,  # 原始中文名称
            "file_type": file_type,
            "disk_name": f"{file_id}.{file_type}"  # 磁盘上的存储名称（ID.ext）
        }
        self._save_mapping()
        print(f"文件映射已添加: {file_id} -> {original_name}")

    def search_files(self, keyword, file_type=None):
        """根据关键词搜索文件（搜索原始中文名）"""
        results = []
        for file_id, info in self.mapping.items():
            # 检查文件类型
            if file_type and info.get("file_type") != file_type:
                continue

            # 检查原始中文文件名是否包含关键词
            original_name = info.get("original_name", "")
            if keyword and keyword.lower() in original_name.lower():
                results.append({
                    "id": file_id,  # 文件的UUID
                    "name": original_name,  # 显示给用户的原始中文名
                    "disk_name": info.get("disk_name", file_id),  # 磁盘上的文件名
                    "file_type": info.get("file_type", ""),
                    "matchType": "文件名匹配"
                })

        print(f"搜索关键词 '{keyword}' 找到 {len(results)} 个结果")
        return results

    def get_file_info(self, file_id):
        """根据文件ID获取文件信息"""
        return self.mapping.get(file_id)

    def file_exists(self, file_id):
        """检查文件是否存在"""
        return file_id in self.mapping


# 创建全局实例
file_mapping_service = FileMappingService()