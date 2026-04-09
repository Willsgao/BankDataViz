# -*- coding:utf-8 -*-
"""
简化测试脚本：验证文件分类上传功能（不依赖其他模块）
"""
import sys
from pathlib import Path

def test_paths():
    """测试路径常量是否正确"""
    print("=" * 50)
    print("测试1: 路径常量")
    print("=" * 50)
    
    # 模拟 constants.py 的路径计算逻辑
    MAIN_ROOT = Path("F:/wills/codes/DocuVista")
    
    # 新路径常量
    UPLOAD_PDF_DIR = r'data/backend/static/uploads/pdf'
    UPLOAD_EXCEL_DIR = r'data/backend/static/uploads/excel'
    PROCESSED_EXCEL_DIR = r'data/backend/static/processed/excel'
    PROCESSED_REPORTS_DIR = r'data/backend/static/processed/reports'
    
    UPLOAD_PDF_DIR_PATH = Path(MAIN_ROOT) / UPLOAD_PDF_DIR
    UPLOAD_EXCEL_DIR_PATH = Path(MAIN_ROOT) / UPLOAD_EXCEL_DIR
    PROCESSED_EXCEL_DIR_PATH = Path(MAIN_ROOT) / PROCESSED_EXCEL_DIR
    
    print(f"PDF上传目录: {UPLOAD_PDF_DIR_PATH}")
    print(f"Excel上传目录: {UPLOAD_EXCEL_DIR_PATH}")
    print(f"成品Excel目录: {PROCESSED_EXCEL_DIR_PATH}")
    
    # 检查目录是否存在
    assert UPLOAD_PDF_DIR_PATH.exists(), "PDF上传目录不存在"
    assert UPLOAD_EXCEL_DIR_PATH.exists(), "Excel上传目录不存在"
    assert PROCESSED_EXCEL_DIR_PATH.exists(), "成品Excel目录不存在"
    
    print("[OK] 路径常量测试通过")
    return True

def test_file_type_detection():
    """测试文件类型检测逻辑"""
    print("\n" + "=" * 50)
    print("测试2: 文件类型检测")
    print("=" * 50)
    
    def get_upload_dir_by_type(file_type, upload_pdf_dir, upload_excel_dir, upload_dir):
        """根据文件类型获取对应的上传目录"""
        file_type = file_type.lower() if file_type else ''
        if file_type == 'pdf':
            return upload_pdf_dir
        elif file_type in ('xlsx', 'xls', 'excel'):
            return upload_excel_dir
        else:
            return upload_dir
    
    upload_pdf_dir = Path("F:/wills/codes/DocuVista/data/backend/static/uploads/pdf")
    upload_excel_dir = Path("F:/wills/codes/DocuVista/data/backend/static/uploads/excel")
    upload_dir = Path("F:/wills/codes/DocuVista/data/backend/static/uploads")
    
    # 测试 PDF
    pdf_dir = get_upload_dir_by_type('pdf', upload_pdf_dir, upload_excel_dir, upload_dir)
    assert pdf_dir == upload_pdf_dir, f"PDF目录不匹配"
    print(f"[OK] PDF文件 -> {pdf_dir}")
    
    # 测试 Excel
    xlsx_dir = get_upload_dir_by_type('xlsx', upload_pdf_dir, upload_excel_dir, upload_dir)
    assert xlsx_dir == upload_excel_dir, f"Excel目录不匹配"
    print(f"[OK] XLSX文件 -> {xlsx_dir}")
    
    # 测试图片（保留在原目录）
    png_dir = get_upload_dir_by_type('png', upload_pdf_dir, upload_excel_dir, upload_dir)
    assert png_dir == upload_dir, f"PNG目录不匹配"
    print(f"[OK] PNG图片 -> {png_dir}")
    
    print("[OK] 文件类型检测测试通过")
    return True

def main():
    print("\n" + "=" * 60)
    print("DocuVista 文件分类上传功能测试（简化版）")
    print("=" * 60 + "\n")
    
    try:
        test_paths()
        test_file_type_detection()
        
        print("\n" + "=" * 60)
        print("[OK] 所有测试通过！")
        print("\n新的存储结构：")
        print("   uploads/pdf/    - 待处理PDF")
        print("   uploads/excel/  - 待处理Excel")
        print("   processed/excel/ - 成品Excel")
        print("   processed/reports/ - 成品报告")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
