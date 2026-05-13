#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
诊断和修复PDF转图问题
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入PyMuPDF
try:
    import fitz
except ImportError:
    print("[ERROR] 无法导入 PyMuPDF (fitz)，请确保已安装: pip install PyMuPDF")
    sys.exit(1)

def check_pdf_images(pdf_disk_name):
    """检查指定PDF的转图图片"""
    # 路径配置
    static_dir = project_root / "data" / "backend" / "static"
    png_output_dir = static_dir / "pdf2pngs"
    upload_dir = static_dir / "uploads"
    
    pdf_dir = png_output_dir / pdf_disk_name
    print(f"\n检查目录: {pdf_dir}")
    
    if not pdf_dir.exists():
        print(f"[X] 目录不存在: {pdf_dir}")
        return
    
    png_files = list(pdf_dir.glob("*.png"))
    print(f"找到 {len(png_files)} 个PNG文件:")
    
    zero_byte_files = []
    valid_files = []
    
    for png in sorted(png_files):
        size = png.stat().st_size
        status = "[OK]" if size > 0 else "[ZERO]"
        print(f"  {png.name}: {size:,} bytes - {status}")
        
        if size == 0:
            zero_byte_files.append(png)
        else:
            valid_files.append(png)
    
    print(f"\n统计:")
    print(f"  有效文件: {len(valid_files)}")
    print(f"  0字节文件: {len(zero_byte_files)}")
    
    return zero_byte_files, valid_files


def delete_zero_byte_images(pdf_disk_name):
    """删除0字节的图片文件"""
    zero_byte_files, valid_files = check_pdf_images(pdf_disk_name)
    
    if not zero_byte_files:
        print("没有0字节文件需要删除")
        return True
    
    print(f"\n删除 {len(zero_byte_files)} 个0字节文件...")
    for png in zero_byte_files:
        try:
            png.unlink()
            print(f"  [DEL] 已删除: {png.name}")
        except Exception as e:
            print(f"  [ERROR] 删除失败: {png.name} - {e}")
    
    return True


def regenerate_single_page(pdf_path, page_num, output_path, dpi=200):
    """重新生成单个页面的图片"""
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(page_num - 1)  # 转为0-based
    
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    
    pix = page.get_pixmap(
        matrix=matrix,
        colorspace="rgb",
        alpha=False
    )
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存
    pix.save(str(output_path))
    
    file_size = output_path.stat().st_size
    doc.close()
    
    return file_size


def fix_pdf_images(pdf_disk_name):
    """修复指定PDF的所有转图图片"""
    # 路径配置
    static_dir = project_root / "data" / "backend" / "static"
    png_output_dir = static_dir / "pdf2pngs"
    upload_dir = static_dir / "uploads"
    
    # 查找原始PDF文件
    pdf_path = None
    for ext in ['.pdf', '.PDF']:
        possible_path = upload_dir / f"{pdf_disk_name}{ext}"
        if possible_path.exists():
            pdf_path = possible_path
            break
    
    if not pdf_path:
        # 尝试在上传目录中查找
        for pdf_file in upload_dir.glob("*.pdf"):
            if pdf_disk_name in pdf_file.stem or pdf_disk_name in str(pdf_file):
                pdf_path = pdf_file
                break
    
    if not pdf_path:
        print(f"[X] 找不到原始PDF文件: {pdf_disk_name}")
        print(f"  搜索目录: {upload_dir}")
        return False
    
    print(f"找到原始PDF: {pdf_path}")
    
    # 获取PDF页数
    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count
    doc.close()
    
    print(f"PDF总页数: {total_pages}")
    
    pdf_dir = png_output_dir / pdf_disk_name
    
    # 检查并删除0字节文件
    print("\n检查现有图片...")
    zero_byte_files = []
    for i in range(1, total_pages + 1):
        png_path = pdf_dir / f"{pdf_disk_name}_{i:03d}.png"
        if png_path.exists():
            if png_path.stat().st_size == 0:
                zero_byte_files.append(png_path)
                print(f"  {png_path.name}: [ZERO] 0 bytes, will regenerate")
            else:
                print(f"  {png_path.name}: [OK] {png_path.stat().st_size:,} bytes")
        else:
            print(f"  {pdf_disk_name}_{i:03d}.png: [MISS] not found, will generate")
            zero_byte_files.append(png_path)
    
    if not zero_byte_files:
        print("所有图片都正常，无需修复")
        return True
    
    print(f"\n开始重新生成 {len(zero_byte_files)} 个图片...")
    
    for i, png_path in enumerate(zero_byte_files, 1):
        page_num = int(png_path.stem.split('_')[-1])
        print(f"  处理页面 {page_num} ({i}/{len(zero_byte_files)})...")
        
        try:
            size = regenerate_single_page(pdf_path, page_num, png_path, dpi=200)
            
            if size > 0:
                print(f"    [OK] 成功: {size:,} bytes")
            else:
                print(f"    [FAIL] 失败: 文件大小为0")
        except Exception as e:
            print(f"    [ERROR] 异常: {e}")
    
    print("\n修复完成！")
    
    # 验证结果
    print("\n验证修复结果:")
    check_pdf_images(pdf_disk_name)
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_pdf_images.py <pdf_disk_name> [--check-only] [--delete-zero]")
        print("\n示例:")
        print("  python fix_pdf_images.py 731b28f5-2bd0-141b-129f-c2ee7fda72a2")
        print("  python fix_pdf_images.py 731b28f5-2bd0-141b-129f-c2ee7fda72a2 --check-only")
        sys.exit(1)
    
    pdf_disk_name = sys.argv[1]
    
    if "--check-only" in sys.argv:
        check_pdf_images(pdf_disk_name)
    elif "--delete-zero" in sys.argv:
        delete_zero_byte_images(pdf_disk_name)
    else:
        fix_pdf_images(pdf_disk_name)
