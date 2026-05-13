"""
修复脚本：重新生成0字节的表格图片
使用方法：在 DocuVista 根目录运行
    .venv_311\Scripts\python.exe scripts/regenerate_images.py
"""
import os
import sys
import fitz  # PyMuPDF

# ── 路径配置 ──────────────────────────────────────────────
PDF_PATH = r"F:\wills\codes\DocuVista\data\backend\static\uploads\731b28f5-2bd0-141b-129f-c2ee7fda72a2.pdf"
TABLES_DIR = r"F:\wills\codes\DocuVista\data\backend\static\filtered_tables\731b28f5-2bd0-141b-129f-c2ee7fda72a2\tables"
DPI = 300  # 表格页用高DPI，与原逻辑一致
# ──────────────────────────────────────────────────────────


def main():
    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF 不存在: {PDF_PATH}")
        sys.exit(1)

    os.makedirs(TABLES_DIR, exist_ok=True)

    doc = fitz.open(PDF_PATH)
    total_pages = doc.page_count
    print(f"📄 PDF 总页数: {total_pages}")
    print(f"🎯 目标 DPI: {DPI}")
    print(f"📁 输出目录: {TABLES_DIR}")
    print("-" * 50)

    # 扫描 tables 目录下所有 png 文件（包括0字节的）
    import glob
    png_files = sorted(glob.glob(os.path.join(TABLES_DIR, "*.png")))
    if not png_files:
        print("⚠️  tables 目录下没有 png 文件，无需修复")
        sys.exit(0)

    success = 0
    skipped = 0
    failed = []

    for png_path in png_files:
        fname = os.path.basename(png_path)
        # 从文件名提取页码，如 731b28f5..._005.png → 5
        try:
            page_str = fname.split("_")[-1].replace(".png", "")
            page_num_1idx = int(page_str)   # 1-indexed
            page_idx = page_num_1idx - 1    # 0-indexed for fitz
        except (ValueError, IndexError):
            print(f"⚠️  无法解析页码，跳过: {fname}")
            skipped += 1
            continue

        if page_idx < 0 or page_idx >= total_pages:
            print(f"⚠️  页码越界 p{page_num_1idx}（PDF共{total_pages}页），跳过: {fname}")
            skipped += 1
            continue

        # 检查是否已经是正常大小的文件（非0字节）
        if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
            print(f"✅ 跳过（文件正常）: {fname} ({os.path.getsize(png_path)} bytes)")
            skipped += 1
            continue

        # 重新渲染
        try:
            page = doc.load_page(page_idx)
            mat = fitz.Matrix(DPI / 72, DPI / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
            pix.save(png_path)
            file_size = os.path.getsize(png_path)
            print(f"✅ 已生成 p{page_num_1idx:03d}: {fname} ({file_size // 1024} KB)")
            success += 1
        except Exception as e:
            print(f"❌ 渲染失败 p{page_num_1idx}: {e}")
            failed.append(fname)

    doc.close()

    print("-" * 50)
    print(f"📊 完成: 成功={success}, 跳过={skipped}, 失败={len(failed)}")
    if failed:
        print("❌ 失败文件:")
        for f in failed:
            print(f"   - {f}")


if __name__ == "__main__":
    main()
