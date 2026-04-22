# -*- coding:utf-8 -*-

"""
极简增量处理模块 - 独立实现，不依赖现有代码
文件：backend/core/services/incremental_processor/simple_incremental_processor.py
"""

import re
import shutil
from pathlib import Path
from typing import List
import json
import gzip
from backend.utils.constants import OBJ_CACHE_PATH


class SimpleIncrementalProcessor:
    """极简增量处理器 - 使用统一的文件映射路径"""

    def __init__(self, record_file_path=None):
        """
        初始化

        Args:
            record_file_path: 记录文件路径，默认使用统一的映射文件路径
        """
        # 计算根目录路径
        self.project_root = Path(__file__).parent.parent.parent.parent  # 根据实际结构调整

        if record_file_path is None:
            # 使用统一的映射文件路径：data/backend/processing_records.json
            self.record_file = self.project_root / "data" / "backend" / "processing_records.json"
        else:
            self.record_file = Path(record_file_path)

        # 确保目录存在
        self.record_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载记录
        self.records = self._load_records()
        print(f"[OK] Incremental processor initialized, record file: {self.record_file}")

    def _load_records(self) -> dict:
        """加载处理记录 - 极简实现"""
        if not self.record_file.exists():
            print(f"[INFO] Record file not found, creating new: {self.record_file}")
            return {}

        try:
            with open(self.record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
                print(f"[OK] Loaded {len(records)} PDF folders")
                return records
        except Exception as e:
            print(f"[WARN] Failed to load records, using empty: {e}")
            return {}

    def _save_records(self):
        """保存处理记录 - 极简实现"""
        try:
            with open(self.record_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"⚠️ 保存记录文件失败: {e}")
            return False

    def filter_processed_images_000(self, pdf_folder: str, image_names: List[str]) -> List[str]:
        """
        过滤已处理的图片，返回需要处理的图片

        Args:
            pdf_folder: PDF文件夹名称
            image_names: 所有图片名称列表

        Returns:
            List[str]: 需要处理的图片名称列表
        """
        print(f"[DEBUG] Starting incremental check: {pdf_folder}")
        print(f"[DEBUG] Total images: {len(image_names)}")

        # 获取已处理的图片
        processed_images = set(self.records.get(pdf_folder, []))
        print(f"[DEBUG] Processed images count: {len(processed_images)}")

        # 过滤出需要处理的图片
        images_to_process = []
        skipped_images = []

        print("processed_images:", processed_images)

        for image_name in image_names:
            print("image_nameimage_name:", image_name)
            if image_name in processed_images:
                skipped_images.append(image_name)
            else:
                images_to_process.append(image_name)

        print(f"[DEBUG] Filter results:")
        print(f"  - 需要处理: {len(images_to_process)} 张")
        print(f"  - 跳过已处理: {len(skipped_images)} 张")

        if skipped_images:
            print(f"  - 跳过的图片: {skipped_images[:3]}...")  # 只显示前3个

        return images_to_process


    def is_image_processed(self, pdf_folder: str, image_name: str,
                           cache_base: str = "data/backend/obj_cache") -> bool:
        """
        检查图片是否已通过LLM处理

        Args:
            pdf_folder: PDF文件夹名称
            image_name: 图片文件名
            cache_base: 缓存目录基础路径

        Returns:
            bool: 图片是否已处理
        """
        # 1. 从图片文件名中提取页码
        match = re.search(r'_(\d+)\.png$', image_name)
        if not match:
            return False

        page_num = match.group(1).zfill(3)  # 确保3位数字

        # 2. 构建缓存文件路径
        llm_dir = Path(OBJ_CACHE_PATH) / pdf_folder / "llm"
        print("llm_dir::::->;", llm_dir)

        # 3. 查找缓存文件
        cache_pattern = f"{page_num}_*.json.gz"
        cache_files = list(llm_dir.glob(cache_pattern))

        if not cache_files:
            return False

        # 4. 验证最新缓存文件
        cache_file = max(cache_files, key=lambda p: p.stat().st_mtime)

        try:
            with gzip.open(cache_file, 'rt', encoding='utf-8') as f:
                data = json.load(f)

            # 检查是否有表格数据
            tables = data.get('tables', [])
            if not tables:
                tables = data.get('tables_structure', {}).get('tables', [])

            return bool(tables)  # 有表格数据表示已处理

        except Exception as e:
            print(f"⚠️ 读取缓存文件失败: {e}")
            return False

    def filter_processed_images(self, pdf_folder: str, image_names: List[str]) -> List[str]:
        """
        过滤已处理的图片，返回需要处理的图片
        改进版：基于LLM缓存验证图片处理状态

        Args:
            pdf_folder: PDF文件夹名称
            image_names: 所有图片名称列表

        Returns:
            List[str]: 需要处理的图片名称列表
        """
        print(f"[DEBUG] Starting incremental check: {pdf_folder}")
        print(f"[DEBUG] Total images: {len(image_names)}")

        # 过滤出需要处理的图片
        images_to_process = []
        skipped_images = []

        for image_name in image_names:
            # [KEY] 关键改进：使用LLM缓存验证是否已处理
            is_processed = self.is_image_processed(pdf_folder, image_name)

            if is_processed:
                # 已处理，跳过
                skipped_images.append(image_name)
                print(f"⏭️ 跳过已处理: {image_name}")

                # ✅ 同时更新记录，保持向后兼容
                if pdf_folder not in self.records:
                    self.records[pdf_folder] = []
                if image_name not in self.records[pdf_folder]:
                    self.records[pdf_folder].append(image_name)
            else:
                # 未处理，需要处理
                images_to_process.append(image_name)
                print(f"🆕 需要处理: {image_name}")

        print(f"[DEBUG] Filter results:")
        print(f"  - 需要处理: {len(images_to_process)} 张")
        print(f"  - 跳过已处理: {len(skipped_images)} 张")

        if skipped_images:
            print(f"  - 跳过的图片: {skipped_images[:5]}")  # 只显示前5个

        return images_to_process


    def mark_images_processed(self, pdf_folder: str, image_names: List[str]):
        """
        标记图片为已处理

        Args:
            pdf_folder: PDF文件夹名称
            image_names: 已处理的图片名称列表
        """
        if not image_names:
            return

        # 确保PDF文件夹记录存在
        if pdf_folder not in self.records:
            self.records[pdf_folder] = []

        # 添加新处理的图片
        current_processed = set(self.records[pdf_folder])
        new_images = []

        for image_name in image_names:
            if image_name not in current_processed:
                self.records[pdf_folder].append(image_name)
                new_images.append(image_name)

        # 保存记录
        if new_images and self._save_records():
            print(f"✅✅ 标记 {len(new_images)} 张图片为已处理: {pdf_folder}")
            print(f"[DEBUG] New images: {new_images[:3]}...")  # 只显示前3个
        else:
            print(f"ℹℹ️ℹℹ️ 没有新图片需要标记: {pdf_folder}")

    def get_processing_stats(self, pdf_folder: str, all_images: List[str]) -> dict:
        """
        获取处理统计信息

        Args:
            pdf_folder: PDF文件夹名称
            all_images: 所有图片名称列表

        Returns:
            dict: 统计信息
        """
        processed_images = set(self.records.get(pdf_folder, []))
        unprocessed_images = [img for img in all_images if img not in processed_images]

        stats = {
            'pdf_folder': pdf_folder,
            'total_images': len(all_images),
            'processed_images': len(processed_images),
            'unprocessed_images': len(unprocessed_images),
            'progress_percentage': (len(processed_images) / len(all_images) * 100) if all_images else 0,
            'is_completed': len(unprocessed_images) == 0 and len(all_images) > 0
        }

        return stats

    def clear_pdf_records(self, pdf_folder: str):
        """
        清空指定PDF的处理记录（不清除LLM缓存）

        Args:
            pdf_folder: PDF文件夹名称
        """
        if pdf_folder in self.records:
            del self.records[pdf_folder]
            self._save_records()
            print(f"[DEBUG] Clear processing record: {pdf_folder}")
        # 注意：不清除 LLM 缓存目录，保留缓存以便后续复用

    def clear_all_records(self):
        """清空所有处理记录"""
        self.records.clear()
        self._save_records()
        print("[DEBUG] Clear all processing records")

    def get_all_pdf_folders(self) -> List[str]:
        """获取所有有记录的PDF文件夹"""
        return list(self.records.keys())


# 全局实例
incremental_processor = SimpleIncrementalProcessor()