# scripts/init_data_dirs.py
# !/usr/bin/env python3
"""
初始化数据目录结构
将缓存数据统一放到 data/backend 和 data/frontend 目录下
"""

import os
import sys
from pathlib import Path


def init_data_dirs():
    """初始化数据目录结构"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    data_dir = project_root / "data"

    # 后端目录结构
    backend_dirs = [
        "backend/obj_cache",
        "backend/ocr_raw",
        "backend/ocr_final",
        "backend/temp_imgs",
        "backend/llm_cache",
        "backend/outputs",
        "backend/cache",  # 用于缓存数据库等
        "backend/logs"  # 日志目录
    ]

    # 前端目录结构
    frontend_dirs = [
        "frontend/cache",
        "frontend/logs",
        "frontend/assets",
        "frontend/uploads"
    ]

    print(f"项目根目录: {project_root}")
    print(f"数据目录: {data_dir}")
    print("正在创建数据目录结构...\n")

    # 创建后端目录
    print("后端目录:")
    for dir_path in backend_dirs:
        full_path = data_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {full_path.relative_to(project_root)}")

    # 创建前端目录
    print("\n前端目录:")
    for dir_path in frontend_dirs:
        full_path = data_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {full_path.relative_to(project_root)}")

    # 创建数据库文件
    db_path = data_dir / "backend" / "database.db"
    if not db_path.exists():
        # 创建空的数据库文件
        with open(db_path, 'w') as f:
            pass
        print(f"\n✓ 创建数据库文件: {db_path.relative_to(project_root)}")

    # 创建README文件
    readme_path = data_dir / "README2.md"
    if not readme_path.exists():
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("""# 数据目录说明
            ##目录结构
            data/
            ├── backend/ # 后端缓存数据
            │ ├── obj_cache/ # 对象存储缓存（压缩的JSON等）
            │ ├── ocr_raw/ # OCR原始响应数据（调试用）
            │ ├── ocr_final/ # OCR处理后结果（调试用）
            │ ├── temp_imgs/ # 临时图片文件
            │ ├── llm_cache/ # LLM响应缓存
            │ ├── outputs/ # 处理输出文件
            │ ├── cache/ # 缓存数据库等
            │ ├── logs/ # 日志文件
            │ └── database.db # SQLite数据库
            └── frontend/ # 前端缓存数据
            ├── cache/ # 前端缓存
            ├── logs/ # 前端日志
            ├── assets/ # 前端静态资源
            └── uploads/ # 前端上传文件
            ## 注意事项
            1. **此目录下的文件均为运行时生成**，不应提交到版本控制（已在 .gitignore 中排除）
            2. **可以安全删除**，系统会自动重新生成需要的目录
            3. **建议定期清理**大文件，特别是 temp_imgs/ 和 obj_cache/ 目录
            4. **备份时**只需备份此目录即可保留所有运行时数据

            ## 环境变量配置
            项目配置已默认指向此目录结构，如需修改可在以下位置配置：
            - `backend/utils/config.py` - 主配置文件
            - `project-config.json` - 项目配置文件
            - 环境变量（优先级最高）

            ## 迁移指南
            从旧版本迁移到新版本：
            1. 停止所有服务
            2. 运行此初始化脚本
            3. 将旧缓存文件复制到对应新目录
            4. 重新启动服务
            """)

    print(f"\n✓ 创建README文件: {readme_path.relative_to(project_root)}")

    # 创建 .gitignore 文件（如果不存在）
    gitignore_path = data_dir / ".gitignore"
    if not gitignore_path.exists():
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write("""# 忽略 data 目录下的所有文件
    *
    !.gitignore
    !README.md

    # 但排除空目录占位文件
    !.gitkeep

    # 特定的数据库文件需要备份时可以取消注释
    # !backend/database.db
    """)
        print(f"✓ 创建 .gitignore: {gitignore_path.relative_to(project_root)}")

    print(f"\n✅ 数据目录初始化完成！")
    print(f"💡 提示: 现在可以删除旧的缓存目录，如 backend/static/ 下的临时文件")


def check_existing_data():
    """检查是否存在需要迁移的旧数据"""
    project_root = Path(__file__).parent.parent

    old_paths = [
        project_root / "backend" / "data",
        project_root / "test_codes" / "table_analyzer_codes",
        project_root / "obj_cache",
        project_root / "api_cache.db"
    ]

    existing_old = []
    for path in old_paths:
        if path.exists():
            existing_old.append(path)

    if existing_old:
        print("\n⚠️  发现可能存在旧数据的目录:")
        for path in existing_old:
            print(f"  - {path.relative_to(project_root)}")
        print("\n💡 建议: 运行迁移脚本或手动将这些目录的内容移动到 data/backend/")
        return True

    return False


if __name__ == "__main__":
    print("=" * 60)
    print("DocuVista 数据目录初始化工具")
    print("=" * 60)

    try:
        # 检查旧数据
        has_old_data = check_existing_data()

        # 初始化新目录
        init_data_dirs()

        if has_old_data:
            print("\n" + "=" * 60)
            print("下一步建议:")
            print("1. 停止所有正在运行的服务")
            print("2. 将上述旧目录中的文件复制到 data/backend/ 对应子目录中")
            print("3. 更新配置文件，确保指向新的 data/backend/ 路径")
            print("4. 重新启动服务")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)