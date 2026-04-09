# -*- coding:utf-8 -*-
"""
测试脚本：验证文件分类上传功能
"""
import sys
sys.path.insert(0, 'F:/wills/codes/DocuVista')

from backend.services.file_upload_service import file_upload_service
from backend.services.excel_storage_service import excel_storage_service
from backend.utils.constants import (
    UPLOAD_PDF_DIR_PATH, 
    UPLOAD_EXCEL_DIR_PATH,
    PROCESSED_EXCEL_DIR_PATH
)

def test_paths():
    """测试路径常量是否正确"""
    print("=" * 50)
    print("测试1: 路径常量")
    print("=" * 50)
    
    print(f"PDF上传目录: {UPLOAD_PDF_DIR_PATH}")
    print(f"Excel上传目录: {UPLOAD_EXCEL_DIR_PATH}")
    print(f"成品Excel目录: {PROCESSED_EXCEL_DIR_PATH}")
    
    # 检查目录是否存在
    assert UPLOAD_PDF_DIR_PATH.exists(), "PDF上传目录不存在"
    assert UPLOAD_EXCEL_DIR_PATH.exists(), "Excel上传目录不存在"
    assert PROCESSED_EXCEL_DIR_PATH.exists(), "成品Excel目录不存在"
    
    print("✅ 路径常量测试通过")
    return True

def test_get_upload_dir_by_type():
    """测试根据文件类型获取上传目录"""
    print("\n" + "=" * 50)
    print("测试2: get_upload_dir_by_type 方法")
    print("=" * 50)
    
    service = file_upload_service
    
    # 测试 PDF
    pdf_dir = service.get_upload_dir_by_type('pdf')
    assert pdf_dir == UPLOAD_PDF_DIR_PATH, f"PDF目录不匹配: {pdf_dir}"
    print(f"✅ PDF文件 -> {pdf_dir}")
    
    # 测试 Excel
    xlsx_dir = service.get_upload_dir_by_type('xlsx')
    assert xlsx_dir == UPLOAD_EXCEL_DIR_PATH, f"Excel目录不匹配: {xlsx_dir}"
    print(f"✅ Excel文件 -> {xlsx_dir}")
    
    # 测试图片（保留在原目录）
    img_dir = service.get_upload_dir_by_type('png')
    assert img_dir == service.upload_dir, f"图片目录不匹配: {img_dir}"
    print(f"✅ PNG图片 -> {img_dir}")
    
    print("✅ get_upload_dir_by_type 测试通过")
    return True

def test_excel_storage_service():
    """测试 Excel 存储服务"""
    print("\n" + "=" * 50)
    print("测试3: ExcelStorageService 成品目录")
    print("=" * 50)
    
    service = excel_storage_service
    print(f"成品Excel目录: {service.processed_excel_dir}")
    
    assert service.processed_excel_dir == PROCESSED_EXCEL_DIR_PATH
    print("✅ ExcelStorageService 测试通过")
    return True

def main():
    print("\n" + "=" * 60)
    print("🚀 DocuVista 文件分类上传功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_paths()
        test_get_upload_dir_by_type()
        test_excel_storage_service()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
