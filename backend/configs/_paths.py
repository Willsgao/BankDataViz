# -*- coding:utf-8 -*-
"""
路径工具方法模块（跨 Config / TableConfig 复用）
"""
import os


def get_absolute_path(project_root, relative_path):
    """将相对路径转换为基于 project_root 的绝对路径"""
    if not relative_path:
        return ""

    if os.path.isabs(relative_path):
        return relative_path

    from pathlib import Path
    return str((Path(project_root) / relative_path).resolve())


def create_table_dirs(dirs_to_create):
    """创建表格处理需要的目录（静默跳过已存在的目录）"""
    for dir_path in dirs_to_create:
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)


def create_backend_dirs(project_root):
    """在 project_root 下创建 data/backend 基础目录"""
    data_backend_dir = os.path.join(project_root, "data", "backend")
    if not os.path.exists(data_backend_dir):
        os.makedirs(data_backend_dir, exist_ok=True)
    return data_backend_dir
