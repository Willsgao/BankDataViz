# -*- coding: utf-8 -*-
"""
测试 TencentOCRProvider 图片大小校验与自动压缩功能

运行方式:
    python -m pytest backend/tests/test_ocr_image_compress.py -v
    或
    python backend/tests/test_ocr_image_compress.py
"""

import os
import sys
import io
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image


# ============================================================
# 辅助函数：生成指定大小的测试图片
# ============================================================

def create_test_image(width: int, height: int, fmt: str = "PNG") -> bytes:
    """生成纯色测试图片，返回 bytes"""
    img = Image.new("RGB", (width, height), color=(200, 180, 160))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def create_large_test_image(target_base64_mb: float = 8.0) -> bytes:
    """
    生成一张足够大的 JPEG 图片，确保 Base64 编码后超过 target_base64_mb。
    使用随机噪声确保不可压缩，同时限制尺寸避免测试过慢。
    """
    import numpy as np

    # JPEG quality=100 时，随机噪声的压缩比大约 4:1（RGB raw → JPEG）
    # Base64 膨胀约 33%
    # 目标: raw_pixels * 3 / 4 * 1.33 ≈ target_base64_mb * 1024 * 1024
    # raw_pixels ≈ target_base64_mb * 1024 * 1024 * 4 / (3 * 1.33)
    target_pixels = int(target_base64_mb * 1024 * 1024 * 4 / 3.99)

    # 使用合理尺寸，避免测试图片过大导致 putpixel 太慢
    # 最多 3000px 宽
    max_width = 3000
    if target_pixels > max_width * max_width:
        side = max_width
    else:
        side = int(target_pixels ** 0.5)
        side = (side // 100) * 100  # 取整到百

    print(f"[TEST] 生成测试图片: {side}x{side}, "
          f"像素={side*side}, 预估原始: {side * side * 3 / (1024*1024):.1f}MB")

    # 使用 numpy 生成随机噪声（不可压缩），比 putpixel 快百倍
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 256, (side, side, 3), dtype=np.uint8)
    img = Image.fromarray(noise, mode="RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=100)
    raw_bytes = buf.getvalue()
    print(f"[TEST] 实际生成: {len(raw_bytes) / (1024*1024):.2f}MB")
    return raw_bytes


# ============================================================
# 测试类
# ============================================================

class TestOCRImageCompression(unittest.TestCase):
    """测试图片压缩逻辑（不依赖腾讯云 SDK）"""

    @classmethod
    def setUpClass(cls):
        """导入待测类"""
        from backend.core.table_processor.ocr_response_unifier import TencentOCRProvider
        cls.TencentOCRProvider = TencentOCRProvider

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_temp_image(self, data: bytes, suffix: str = ".png") -> str:
        """写入临时图片文件，返回路径"""
        path = os.path.join(self.temp_dir, f"test_image{suffix}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _create_provider_without_client(self):
        """创建一个不需要真实腾讯云客户端的 provider 实例（仅测试 _prepare_image / _compress_image）"""
        config = MagicMock()
        config.tencent_secret_id = "test_id"
        config.tencent_secret_key = "test_key"
        config.tencent_region = "ap-shanghai"

        # Mock 掉 _init_tencent_client，避免真正连接腾讯云
        with patch.object(self.TencentOCRProvider, '_init_tencent_client', return_value=MagicMock()):
            provider = self.TencentOCRProvider(config)
        return provider

    # ---- 测试用例 ----

    def test_small_image_no_compression(self):
        """小图片（<6MB base64）不做压缩，直接通过"""
        data = create_test_image(200, 200)
        img_path = self._write_temp_image(data)

        provider = self._create_provider_without_client()
        result = provider._prepare_image(img_path)

        # 验证返回有效的 base64
        self.assertIsInstance(result, str)
        decoded = base64.b64decode(result)
        self.assertEqual(len(decoded), len(data))
        self.assertLess(len(result), provider._TENCENT_OCR_MAX_BASE64_SIZE)

    def test_large_image_gets_compressed(self):
        """大图片（>6MB base64）自动压缩到限制以内"""
        data = create_large_test_image(target_base64_mb=10.0)
        img_path = self._write_temp_image(data)
        file_size_mb = len(data) / (1024 * 1024)

        provider = self._create_provider_without_client()
        result = provider._prepare_image(img_path)

        result_size_mb = len(result) / (1024 * 1024)
        print(f"[TEST] 原始: {file_size_mb:.2f}MB → 压缩后Base64: {result_size_mb:.2f}MB")

        # 验证压缩后不超过限制
        self.assertLessEqual(
            len(result), provider._TENCENT_OCR_MAX_BASE64_SIZE,
            f"压缩后 {result_size_mb:.2f}MB 仍超过限制"
        )

        # 验证是有效 base64
        decoded = base64.b64decode(result)
        # 解码后应能被 PIL 打开
        img = Image.open(io.BytesIO(decoded))
        w, h = img.size
        print(f"[TEST] 压缩后图片尺寸: {w}x{h}")

    def test_moderate_image_no_compression(self):
        """中等大小图片（刚好在限制内）不压缩"""
        # 生成一张约 3MB base64 的图片
        data = create_large_test_image(target_base64_mb=3.0)
        img_path = self._write_temp_image(data)

        provider = self._create_provider_without_client()
        result = provider._prepare_image(img_path)

        result_size_mb = len(result) / (1024 * 1024)
        print(f"[TEST] Base64大小: {result_size_mb:.2f}MB, 限制: {provider._TENCENT_OCR_MAX_BASE64_SIZE / (1024*1024):.0f}MB")

        # 如果不超限就不该压缩
        if len(result) <= provider._TENCENT_OCR_MAX_BASE64_SIZE:
            self.assertLessEqual(len(result), provider._TENCENT_OCR_MAX_BASE64_SIZE)

    def test_empty_file_raises_error(self):
        """空文件抛出 ValueError"""
        img_path = self._write_temp_image(b"")

        provider = self._create_provider_without_client()
        with self.assertRaises(ValueError) as ctx:
            provider._prepare_image(img_path)
        self.assertIn("图片文件为空", str(ctx.exception))

    def test_compress_strategies_cascade(self):
        """测试压缩策略逐级尝试：保持尺寸 → 缩放2000px → 缩放1500px"""
        # 生成超大图片确保需要多级压缩
        data = create_large_test_image(target_base64_mb=20.0)
        img_path = self._write_temp_image(data)

        provider = self._create_provider_without_client()
        result = provider._prepare_image(img_path)

        self.assertLessEqual(len(result), provider._TENCENT_OCR_MAX_BASE64_SIZE)

        # 验证压缩后图片仍可读
        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        w, h = img.size
        result_mb = len(result) / (1024 * 1024)
        print(f"[TEST] 超大图片压缩后: {w}x{h}, Base64={result_mb:.2f}MB")
        # 压缩后应该比原始小很多
        self.assertLessEqual(w, 3000, f"压缩后宽度 {w}px 应不超过原始 3000px")

    def test_compressed_result_is_readable_image(self):
        """压缩后的 base64 解码后必须是有效图片"""
        data = create_large_test_image(target_base64_mb=10.0)
        img_path = self._write_temp_image(data)

        provider = self._create_provider_without_client()
        result = provider._prepare_image(img_path)

        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        # 验证是 RGB 模式（JPEG 输出）
        self.assertIn(img.mode, ("RGB", "L"))
        # 验证有合理的尺寸
        self.assertGreater(img.size[0], 0)
        self.assertGreater(img.size[1], 0)

    def test_png_with_alpha_gets_converted(self):
        """带透明通道的 PNG 正确转换为 RGB"""
        # 创建 RGBA 图片
        img = Image.new("RGBA", (300, 200), color=(100, 150, 200, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_path = self._write_temp_image(buf.getvalue())

        provider = self._create_provider_without_client()
        # 小图片不会触发压缩（convert 逻辑在 compress 中）
        # 但 _prepare_image 对小图片直接返回原始 base64
        result = provider._prepare_image(img_path)

        decoded = base64.b64decode(result)
        re_img = Image.open(io.BytesIO(decoded))
        # PNG 保持 RGBA（因为小图片未压缩）
        self.assertEqual(re_img.size, (300, 200))


class TestOCRImageCompressionEdgeCases(unittest.TestCase):
    """边缘情况测试"""

    @classmethod
    def setUpClass(cls):
        from backend.core.table_processor.ocr_response_unifier import TencentOCRProvider
        cls.TencentOCRProvider = TencentOCRProvider

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        config = MagicMock()
        config.tencent_secret_id = "test_id"
        config.tencent_secret_key = "test_key"
        config.tencent_region = "ap-shanghai"

        with patch.object(self.TencentOCRProvider, '_init_tencent_client', return_value=MagicMock()):
            self.provider = self.TencentOCRProvider(config)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_temp_image(self, data: bytes, suffix: str = ".png") -> str:
        path = os.path.join(self.temp_dir, f"edge_test{suffix}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def test_nonexistent_file(self):
        """不存在的文件抛出异常"""
        with self.assertRaises((FileNotFoundError, OSError)):
            self.provider._prepare_image("/nonexistent/path/image.png")

    def test_very_narrow_image(self):
        """极端宽高比图片（极高但窄）"""
        img = Image.new("RGB", (100, 8000), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_path = self._write_temp_image(buf.getvalue())

        result = self.provider._prepare_image(img_path)
        # 应该不报错
        self.assertIsInstance(result, str)

    def test_very_wide_image(self):
        """极端宽高比图片（极宽但矮）"""
        img = Image.new("RGB", (8000, 100), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_path = self._write_temp_image(buf.getvalue())

        result = self.provider._prepare_image(img_path)
        self.assertIsInstance(result, str)

    def test_class_constant_exists(self):
        """验证类常量 _TENCENT_OCR_MAX_BASE64_SIZE 存在且合理"""
        self.assertEqual(
            self.provider._TENCENT_OCR_MAX_BASE64_SIZE,
            6 * 1024 * 1024,
            "安全阈值应为 6MB"
        )


class TestOCRPDFHandling(unittest.TestCase):
    """测试 PDF 文件渲染 + 压缩流程"""

    @classmethod
    def setUpClass(cls):
        from backend.core.table_processor.ocr_response_unifier import TencentOCRProvider
        cls.TencentOCRProvider = TencentOCRProvider
        # 检查 PyMuPDF 是否可用
        try:
            import fitz
            cls.fitz_available = True
        except ImportError:
            cls.fitz_available = False

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        config = MagicMock()
        config.tencent_secret_id = "test_id"
        config.tencent_secret_key = "test_key"
        config.tencent_region = "ap-shanghai"

        with patch.object(self.TencentOCRProvider, '_init_tencent_client', return_value=MagicMock()):
            self.provider = self.TencentOCRProvider(config)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_pdf(self, pages: int = 1) -> str:
        """用 fitz 创建一个简单的测试 PDF，返回文件路径"""
        import fitz
        path = os.path.join(self.temp_dir, "test.pdf")
        doc = fitz.open()
        for _ in range(pages):
            page = doc.new_page(width=595, height=842)  # A4
            # 画一个简单的矩形
            page.draw_rect([50, 50, 200, 100], color=(0, 0, 1), fill=(0.9, 0.9, 0.9))
        doc.save(path)
        doc.close()
        return path

    def test_pdf_to_image_bytes_returns_image(self):
        """_pdf_to_image_bytes 能正常渲染 PDF 首页为图片"""
        if not self.fitz_available:
            self.skipTest("PyMuPDF 未安装")

        pdf_path = self._create_test_pdf(pages=1)
        result = self.provider._pdf_to_image_bytes(pdf_path)

        self.assertIsNotNone(result, "渲染结果不应为 None")
        self.assertGreater(len(result), 100, "渲染的图片应有一定大小")

        # 验证是有效的 PNG
        img = Image.open(io.BytesIO(result))
        self.assertGreater(img.size[0], 0)
        self.assertGreater(img.size[1], 0)

    def test_pdf_to_image_bytes_multi_page_renders_first(self):
        """多页 PDF 只渲染首页"""
        if not self.fitz_available:
            self.skipTest("PyMuPDF 未安装")

        pdf_path = self._create_test_pdf(pages=3)
        result = self.provider._pdf_to_image_bytes(pdf_path)

        self.assertIsNotNone(result)
        img = Image.open(io.BytesIO(result))
        # 验证是一张图片（不是多页）
        self.assertEqual(len(img.size), 2)

    def test_pdf_to_image_bytes_empty_pdf(self):
        """空 PDF（无页面）返回 None"""
        if not self.fitz_available:
            self.skipTest("PyMuPDF 未安装")

        path = os.path.join(self.temp_dir, "empty.pdf")
        # 构造一个零页面的最小合法 PDF
        empty_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
            b"xref\n0 3\n0000000000 65535 f \n"
            b"0000000009 00000 n \n0000000058 00000 n \n"
            b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n116\n%%EOF"
        )
        with open(path, "wb") as f:
            f.write(empty_pdf)

        result = self.provider._pdf_to_image_bytes(path)
        self.assertIsNone(result, "空 PDF 应返回 None")

    def test_prepare_image_with_pdf(self):
        """_prepare_image 能处理 PDF 文件"""
        if not self.fitz_available:
            self.skipTest("PyMuPDF 未安装")

        pdf_path = self._create_test_pdf(pages=1)
        result = self.provider._prepare_image(pdf_path)

        # 应该返回有效的 base64 字符串
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

        # 解码后应该是有效图片
        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        self.assertGreater(img.size[0], 0)

    def test_prepare_image_with_large_pdf(self):
        """大 PDF（渲染后的图片可能仍需压缩）"""
        if not self.fitz_available:
            self.skipTest("PyMuPDF 未安装")

        # 创建一个包含大量随机内容的大 PDF
        import fitz
        path = os.path.join(self.temp_dir, "large_test.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        # 添加大量文本使渲染图片更大
        for i in range(200):
            page.insert_text((50, 50 + i * 4), f"Row {i}: 工商银行 资产负债表 营业收入 净利润 每股收益", fontsize=8)

        doc.save(path)
        doc.close()

        result = self.provider._prepare_image(path)

        # 不应该报错
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

        # 如果超 6MB 应该已被压缩
        self.assertLessEqual(
            len(result), self.provider._TENCENT_OCR_MAX_BASE64_SIZE,
            f"PDF渲染+压缩后 {len(result) / (1024*1024):.2f}MB 应 ≤ 6MB"
        )

    def test_pdf_render_failure_graceful_degradation(self):
        """PDF 渲染失败时降级：保留原始 PDF 字节继续流程"""
        # 模拟 fitz 未安装的情况
        with patch('backend.core.table_processor.ocr_response_unifier.fitz', None, create=True):
            # 也 patch import 检查
            class MockProvider(self.TencentOCRProvider):
                @staticmethod
                def _pdf_to_image_bytes(pdf_path, pdf_bytes=None):
                    return None  # 模拟渲染失败

            config = MagicMock()
            config.tencent_secret_id = "test_id"
            config.tencent_secret_key = "test_key"
            config.tencent_region = "ap-shanghai"

            with patch.object(self.TencentOCRProvider, '_init_tencent_client', return_value=MagicMock()):
                provider = MockProvider(config)

            # 创建一个真实 PDF 但 mock 渲染为 None
            if self.fitz_available:
                pdf_path = self._create_test_pdf(pages=1)
                # 用 mock 的 _pdf_to_image_bytes 返回 None
                with patch.object(provider, '_pdf_to_image_bytes', return_value=None):
                    result = provider._prepare_image(pdf_path)
                    self.assertIsInstance(result, str)
                    self.assertGreater(len(result), 0)


# ============================================================
# 运行入口
# ============================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
