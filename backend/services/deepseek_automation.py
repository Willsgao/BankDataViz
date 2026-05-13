#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
DeepSeek 浏览器自动化服务
用 Playwright 控制用户已登录的 Chrome 浏览器，
完成截图→粘贴→发送→读取结果的完整流程。
"""
import base64
import json
import os
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# 尝试导入 playwright
try:
    from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright 未安装，请运行: pip install playwright && playwright install chromium")


class DeepSeekAutomation:
    """DeepSeek 浏览器自动化控制器"""

    DEEPSEEK_URL = "https://chat.deepseek.com"

    def __init__(self, user_data_dir: Optional[str] = None):
        """
        Args:
            user_data_dir: Chrome 用户数据目录（用于复用已登录状态）。
                          不传则启动新的 Chrome 实例。
        """
        self.user_data_dir = user_data_dir
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #

    def launch(self, headless: bool = False) -> "DeepSeekAutomation":
        """启动 Chrome 浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("playwright 未安装")

        self.playwright = sync_playwright().start()

        launch_kwargs = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        }

        # 如果指定了用户数据目录，使用持久化上下文
        if self.user_data_dir:
            logger.info(f"使用 Chrome profile: {self.user_data_dir}")
            self.context = self.playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                **launch_kwargs
            )
        else:
            logger.info("启动新的 Chrome 实例（无 profile）")
            self.browser = self.playwright.chromium.launch(**launch_kwargs)
            self.context = self.browser.new_context()

        self.page = self.context.new_page()
        logger.info("Chrome 浏览器已启动")
        return self

    def close(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Chrome 浏览器已关闭")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------ #
    # 核心操作
    # ------------------------------------------------------------------ #

    def _switch_to_expert_mode(self, timeout: int = 10000):
        """
        将 DeepSeek 切换到「专家模式」。

        DeepSeek 页面默认是「快速模式」，专家模式识别更准确但稍慢。
        通过 JS 在页面 DOM 中精确查找模式切换元素并点击。
        切换前后各截一张图，方便调试按钮位置。
        """
        logger.info("尝试切换到专家模式...")

        # 先截图保存当前页面状态（用于调试，保存到 sent_screenshots 的兄弟目录）
        try:
            debug_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "data", "backend", "static", "excel_data", "mode_screenshots"
            )
            os.makedirs(debug_dir, exist_ok=True)
            before_path = os.path.join(debug_dir, f"mode_before_{int(time.time())}.png")
            self.page.screenshot(path=before_path)
            logger.info(f"切换前截图已保存: {before_path}")
        except Exception:
            pass

        # 用 JS 在页面中精确查找并点击"专家模式" radio 按钮
        # DeepSeek 的模式切换是 radio 按钮组：div[role="radio"][data-model-type="expert"]
        result = self.page.evaluate("""() => {
            // 方法1: 直接通过 data-model-type="expert" 属性查找
            let expertRadio = document.querySelector('[data-model-type="expert"][role="radio"]');

            // 方法2: 如果没找到，通过文字查找包含"专家模式"的 radio 元素
            if (!expertRadio) {
                const allRadios = document.querySelectorAll('[role="radio"]');
                for (const radio of allRadios) {
                    const txt = (radio.innerText || radio.textContent || '').trim();
                    if (txt.includes('专家模式')) {
                        expertRadio = radio;
                        break;
                    }
                }
            }

            // 方法3: 查找包含"专家模式"文字的元素，然后向上找 radio 父元素
            if (!expertRadio) {
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    if (el.offsetParent === null) continue;
                    const txt = (el.innerText || el.textContent || '').trim();
                    if (txt === '专家模式') {
                        // 向上查找 radio 父元素
                        let parent = el;
                        for (let i = 0; i < 5 && parent; i++) {
                            if (parent.getAttribute('role') === 'radio') {
                                expertRadio = parent;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        if (expertRadio) break;
                    }
                }
            }

            if (expertRadio) {
                // 检查是否已选中
                const isChecked = expertRadio.getAttribute('aria-checked') === 'true' ||
                                  expertRadio.classList.contains('checked') ||
                                  expertRadio.classList.contains('selected');
                if (isChecked) {
                    return { status: 'already_expert', className: expertRadio.className.slice(0,50) };
                }

                // 点击切换到专家模式
                try {
                    expertRadio.click();
                    // 有些 radio 需要触发 change 事件
                    expertRadio.dispatchEvent(new Event('change', { bubbles: true }));
                    return { status: 'clicked_expert', className: expertRadio.className.slice(0,50) };
                } catch(e) {
                    return { status: 'click_error', error: e.message };
                }
            }

            return { status: 'not_found' };
        }""")

        logger.info(f"模式切换点击结果: {result}")

        if result and result.get('status') == 'clicked':
            # 等待 1.5 秒让下拉菜单出现
            self.page.wait_for_timeout(1500)

            # 再截图看下拉菜单是否出现
            try:
                menu_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "logs",
                    f"mode_menu_{int(time.time())}.png"
                )
                self.page.screenshot(path=menu_path)
                logger.info(f"下拉菜单截图已保存: {menu_path}")
            except Exception:
                pass

            # 查找并点击"专家模式"选项
            expert_result = self.page.evaluate("""() => {
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    if (el.offsetParent === null) continue;
                    const txt = el.innerText || el.textContent || '';
                    if (txt.includes('专家模式') && !txt.includes('快速模式')) {
                        try { el.click(); return { status: 'clicked_expert', text: txt.slice(0,40) }; } catch(e) {}
                    }
                }
                return { status: 'expert_not_found' };
            }""")
            logger.info(f"专家模式选择结果: {expert_result}")

            # 等待切换完成
            self.page.wait_for_timeout(1000)

            # 截图确认最终状态
            try:
                after_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "logs",
                    f"mode_after_{int(time.time())}.png"
                )
                self.page.screenshot(path=after_path)
                logger.info(f"切换后截图已保存: {after_path}，请检查截图确认是否切换成功")
            except Exception:
                pass
        else:
            logger.warning("未找到'快速模式'按钮，可能页面结构已变化，请查看 logs/ 目录下的截图")

    def goto_deepseek(self, timeout: int = 15000):
        """打开 DeepSeek 对话页"""
        logger.info(f"打开 {self.DEEPSEEK_URL}")
        self.page.goto(self.DEEPSEEK_URL, timeout=timeout)
        self.page.wait_for_load_state("networkidle", timeout=timeout)
        logger.info("DeepSeek 页面加载完成")
        # 打开页面后自动切换到专家模式
        self._switch_to_expert_mode()

    def upload_image(self, image_base64: str):
        """
        将 base64 图片粘贴到 DeepSeek 输入框。

        策略（优先使用剪贴板，兜底用文件上传）：
        1. 将图片写入系统剪贴板（Windows API via pywin32）
        2. 在 DeepSeek 输入框按 Ctrl+V 粘贴
        3. 如果剪贴板方式失败，fallback 到文件 input 方式
        """
        # 解码图片数据
        clean_b64 = image_base64.split(",")[-1]
        img_data = base64.b64decode(clean_b64)

        # 保存截图到本地，方便调试（发送给 DeepSeek 前保存）
        try:
            # __file__ = backend/services/deepseek_automation.py
            # 项目根目录 = 往上三级：backend/services -> backend -> 项目根
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            screenshot_dir = os.path.join(
                project_root, "data", "backend", "static", "excel_data", "sent_screenshots"
            )
            os.makedirs(screenshot_dir, exist_ok=True)
            timestamp = int(time.time() * 1000)
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{timestamp}.png")
            with open(screenshot_path, "wb") as f:
                f.write(img_data)
            logger.info(f"[调试] 截图已保存: {screenshot_path}")
        except Exception as e:
            logger.warning(f"[调试] 保存截图失败: {e}")

        # 先尝试剪贴板方式
        clipboard_success = self._set_clipboard_image(img_data)

        if clipboard_success:
            logger.info("图片已写入剪贴板，等待输入框就绪...")
            self._wait_for_input_ready()
            # Ctrl+V 粘贴
            self.page.keyboard.press("Control+v")
            self.page.wait_for_timeout(1500)
            logger.info("图片已粘贴到 DeepSeek 输入框")
        else:
            logger.warning("剪贴板方式失败，尝试文件上传方式")
            self._upload_via_file_input(clean_b64)

    def _set_clipboard_image(self, img_bytes: bytes) -> bool:
        """
        将图片写入 Windows 剪贴板。
        返回是否成功。
        """
        try:
            from io import BytesIO as _BytesIO
            from PIL import Image as _Image
            import win32clipboard as _wc
            import win32con as _wc2

            # PIL 转 RGB PNG
            img = _Image.open(_BytesIO(img_bytes)).convert("RGB")
            output = _BytesIO()
            img.save(output, format="PNG")
            png_data = output.getvalue()

            _wc.OpenClipboard(None)
            _wc.EmptyClipboard()
            _wc.SetClipboardData(_wc2.CF_DIB, self._create_dib(png_data))
            _wc.CloseClipboard()
            logger.info("剪贴板图片写入成功")
            return True
        except Exception as e:
            logger.warning(f"剪贴板方式失败: {e}，将使用文件上传兜底")
            try:
                import win32clipboard
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            return False

    def _create_dib(self, png_bytes: bytes) -> bytes:
        """
        将 PNG 转为 DIB 格式（Windows 剪贴板需要的格式）。
        这是 BMP 的一种变体（不含文件头）。
        """
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        width, height = img.size

        # BMP DIB: BITMAPINFOHEADER + 像素数据（bottom-up）
        # BITMAPINFOHEADER: 40 bytes
        header_size = 40
        planes = 1
        bit_count = 24
        compression = 0  # BI_RGB
        image_size = width * height * 3
        x_pels = y_pels = 0
        colors_used = 0
        colors_important = 0

        # 打包 BITMAPINFOHEADER (little-endian)
        import struct
        header = struct.pack(
            "<IiiHHIIiiII",
            header_size, width, height,  # height 可以是负值表示 top-down
            planes, bit_count, compression,
            image_size, x_pels, y_pels,
            colors_used, colors_important,
        )

        # 像素数据：RGB，行顺序从下到上（bottom-up）
        pixels = []
        for y in range(height - 1, -1, -1):
            row = []
            for x in range(width):
                r, g, b = img.getpixel((x, y))
                row.extend([b, g, r])  # BMP 用 BGR 顺序
            # BMP 行必须 4 字节对齐
            row_len = len(row)
            padded = row_len + (4 - row_len % 4) % 4
            row.extend([0] * (padded - row_len))
            pixels.extend(row)

        return header + bytes(pixels)

    def _wait_for_input_ready(self, timeout: int = 15000):
        """
        等待 DeepSeek 输入框就绪。
        在批量场景下，每次发送后需要等待新输入框出现。
        """
        selectors = [
            "div[contenteditable='true'][role='textbox']",
            "textarea",
        ]
        for _ in range(30):  # 最多 30 * 0.5 = 15 秒
            for sel in selectors:
                try:
                    el = self.page.query_selector(sel)
                    if el and el.is_enabled() and el.is_visible():
                        # 额外等一小段时间让 UI 完全渲染
                        self.page.wait_for_timeout(300)
                        return
                except Exception:
                    pass
            self.page.wait_for_timeout(500)

        raise RuntimeError("等待 DeepSeek 输入框超时")

    def _upload_via_file_input(self, clean_b64: str):
        """
        兜底方案：通过文件 input 上传图片。
        保存 base64 → 找到 input → JS 赋值 FileList → 触发 change。
        """
        img_data = base64.b64decode(clean_b64)
        temp_path = os.path.join(tempfile.gettempdir(), f"ds_img_{int(time.time()*1000)}.png")
        with open(temp_path, "wb") as f:
            f.write(img_data)

        abs_path = os.path.abspath(temp_path)
        # Windows 路径转 file:// URL（JS fetch 需要）
        file_url = "file:///" + abs_path.replace("\\", "/")
        logger.info(f"临时图片已保存: {temp_path}")

        self._wait_for_input_ready()

        # 尝试多种选择器找到文件 input
        selectors = [
            "input[type='file'][accept*='image']",
            "button[aria-label*='image'] input",
            "label[for] input[type='file']",
        ]
        input_el = None
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el:
                    input_el = el
                    logger.info(f"找到文件 input: {sel}")
                    break
            except Exception:
                pass

        if not input_el:
            # 兜底：查找所有 file input
            try:
                input_el = self.page.query_selector("input[type='file']")
            except Exception:
                pass

        if not input_el:
            raise RuntimeError("未找到 DeepSeek 的图片上传 input")

        # 通过 JS 直接赋值 DataTransfer.files
        # Playwright evaluate: 第二个参数是 arg（单个值），用 dict 传多个变量
        self.page.evaluate("""
            (args) => {
                const inputEl = args.inputEl;
                const fileUrl = args.fileUrl;
                const dt = new DataTransfer();
                fetch(fileUrl)
                    .then(r => r.blob())
                    .then(blob => {
                        const file = new File([blob], 'snapshot.png', { type: 'image/png' });
                        dt.items.add(file);
                        Object.defineProperty(inputEl, 'files', {
                            value: dt.files,
                            writable: true,
                            configurable: true,
                        });
                        inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                    });
            }
        """, {"inputEl": input_el, "fileUrl": file_url})

        self.page.wait_for_timeout(2000)
        logger.info("文件上传方式成功")

    def send_message(self, prompt: str = "请识别这张图片中的表格内容，保持原有格式输出"):
        """
        发送消息（批量场景友好）。
        1. 等待输入框就绪
        2. 清空输入框内容（批量场景可能有旧内容）
        3. 填入 prompt
        4. 点击发送按钮
        """
        # 确保 prompt 有内容
        if not prompt or not prompt.strip():
            prompt = "请识别这张图片中的表格内容，保持原有格式输出"

        # 等待输入框就绪
        self._wait_for_input_ready()

        input_sel = "div[contenteditable='true'][role='textbox'], textarea"
        input_el = None

        for _ in range(5):
            try:
                input_el = self.page.query_selector(input_sel)
                if input_el and input_el.is_enabled():
                    break
            except Exception:
                pass
            self.page.wait_for_timeout(500)

        if not input_el:
            raise RuntimeError(f"未找到 DeepSeek 输入框")

        # 清空输入框（批量场景必须清空）
        input_el.click()
        input_el.press("Control+a")
        input_el.press("Delete")
        self.page.wait_for_timeout(200)

        # 填入文字
        input_el.fill(prompt)
        logger.info(f"已填入 prompt: {prompt[:30]}...")

        # 等待发送按钮变蓝（图片上传完成后按钮会变为可用/高亮）
        logger.info("等待发送按钮可用（图片上传中）...")
        send_selectors = [
            "button:has-text('发送')",
            "button[type='submit']",
            "button[aria-label*='发送']",
            ".send-button",
        ]
        send_btn = None
        for _ in range(30):  # 最多等 30 秒
            for sel in send_selectors:
                try:
                    btn = self.page.query_selector(sel)
                    # 按钮存在、可见、且 enabled（DeepSeek 上传图片后按钮会变蓝/可用）
                    if btn and btn.is_visible() and btn.is_enabled():
                        send_btn = btn
                        logger.info(f"发送按钮已可用: {sel}")
                        break
                except Exception:
                    pass
            if send_btn:
                break
            self.page.wait_for_timeout(1000)

        if not send_btn:
            logger.warning("未找到发送按钮，使用 Enter 键发送")
            input_el.press("Enter")
        else:
            send_btn.click()

        logger.info("消息已发送")

    def wait_for_response(self, timeout: int = 180000) -> str:
        """
        等待 DeepSeek 返回结果。
        策略：周期性提取回答内容，内容稳定（连续3次不变）即认为回答完成。
        返回最终答案文本。
        """
        logger.info("等待 DeepSeek 生成回答...")

        # 创建 logs 目录
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = int(time.time())

        # 提取回答内容的 JS 函数（在浏览器中执行）
        def extract_answer():
            return self.page.evaluate("""() => {
                // 尝试多种选择器匹配助手回答（DeepSeek 页面）
                const selectors = [
                    '[data-role="assistant"]',
                    '.ds-chat-message:last-child',
                    '.chat-message:last-child',
                    '[class*="assistant"]',
                    '[data-message-author-role="assistant"]',
                    '.message:last-child',
                    '.conversation-turn:last-child',
                    '[class*="message"][class*="assistant"]',
                    'div[class*="chat"][class*="msg"]:last-child',
                    'div[class*="turn"]:last-child',
                ];

                let bestText = '';

                for (const sel of selectors) {
                    try {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {
                            const el = els[els.length - 1];
                            const text = el.innerText || el.textContent || '';
                            if (text.trim().length > bestText.length) {
                                bestText = text.trim();
                            }
                        }
                    } catch(e) {}
                }

                // 如果还没找到，尝试查找所有包含较多文本的元素
                if (!bestText) {
                    const allEls = document.querySelectorAll('div, p, pre, article');
                    let maxLen = 0;
                    for (const el of allEls) {
                        if (el.offsetParent === null) continue;
                        const text = el.innerText || el.textContent || '';
                        if (text.length > maxLen && text.length > 50) {
                            maxLen = text.length;
                            bestText = text.trim();
                        }
                    }
                }

                return bestText;
            }""")

        # 等待回答完成：检测内容是否稳定
        last_text = ""
        stable_count = 0
        start_time = time.time()
        check_interval = 2000  # 每 2 秒检查一次

        logger.info("开始轮询回答内容是否稳定...")

        while time.time() - start_time < timeout:
            self.page.wait_for_timeout(check_interval)
            current_text = extract_answer() or ""

            if current_text and current_text == last_text and len(last_text) > 10:
                stable_count += 1
                if stable_count >= 3:
                    logger.info(f"回答内容已稳定，长度: {len(last_text)}")
                    break
            else:
                if current_text:
                    logger.info(f"回答生成中... 当前长度: {len(current_text)}")
                stable_count = 0
                last_text = current_text

        if not last_text:
            logger.warning("未能提取到助手回答，保存调试信息...")

            # 保存调试信息：截图 + 页面 HTML
            screenshot_path = os.path.join(log_dir, f"screenshot_{timestamp}.png")
            html_path = os.path.join(log_dir, f"page_{timestamp}.html")

            try:
                self.page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"调试截图已保存: {screenshot_path}")
            except Exception as e:
                logger.error(f"截图失败: {e}")

            try:
                html_content = self.page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"页面 HTML 已保存: {html_path}，请查看 DOM 结构以修正选择器")
            except Exception as e:
                logger.error(f"保存 HTML 失败: {e}")

        else:
            logger.info(f"提取到回答，长度: {len(last_text)}")

        return last_text

    # ------------------------------------------------------------------ #
    # 一站式方法
    # ------------------------------------------------------------------ #

    def recognize_one(
        self,
        image_base64: str,
        prompt: str = "请识别这张图片中的表格内容，保持原有格式输出Markdown表格",
    ) -> dict:
        """
        单区域识别（调用前必须已调用 launch()）。
        不会关闭浏览器，方便批量复用。

        Args:
            image_base64: 图片 base64 字符串
            prompt: 提示词

        Returns:
            dict: {"success": bool, "result": str, "error": str}
        """
        result = {"success": False, "result": "", "error": ""}

        try:
            # 每次发新消息前，清空输入框（如果 DeepSeek 已打开则直接粘贴）
            self.upload_image(image_base64)
            self.send_message(prompt)
            answer = self.wait_for_response()
            result["success"] = True
            result["result"] = answer
            logger.info(f"识别成功，结果长度: {len(answer)}")
        except Exception as e:
            logger.exception("DeepSeek 单区域识别失败")
            result["error"] = str(e)

        return result

    def recognize(
        self,
        image_base64: str,
        prompt: str = "请识别这张图片中的表格内容，保持原有格式输出Markdown表格",
        headless: bool = False,
    ) -> dict:
        """
        完整的一站式识别流程（启动浏览器 → 识别 → 关闭浏览器）。

        Args:
            image_base64: 图片 base64 字符串（可带 data:image/... 前缀）
            prompt: 发给 DeepSeek 的提示词
            headless: 是否无头模式运行

        Returns:
            dict: {"success": bool, "result": str, "error": str}
        """
        result = {"success": False, "result": "", "error": ""}

        try:
            self.launch(headless=headless)
            self.goto_deepseek()
            answer = self.recognize_one(image_base64, prompt).get("result", "")
            result["success"] = True
            result["result"] = answer
            logger.info(f"识别成功，结果长度: {len(answer)}")
        except Exception as e:
            logger.exception("DeepSeek 识别失败")
            result["error"] = str(e)
        finally:
            self.close()

        return result


# ------------------------------------------------------------------ #
# 独立测试入口
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    import sys

    if len(sys.argv) < 2:
        print("用法: python deepseek_automation.py <base64_image_string>")
        print("或者直接传入图片路径: python deepseek_automation.py --test")
        sys.exit(1)

    if sys.argv[1] == "--test":
        # 测试模式：用一个简单的白色图片测试
        from PIL import Image
        import io

        img = Image.new("RGB", (400, 200), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        prompt = "请描述这张图片的内容"
    else:
        img_b64 = sys.argv[1]
        prompt = sys.argv[2] if len(sys.argv) > 2 else "请识别这张图片中的表格内容"

    automation = DeepSeekAutomation()
    result = automation.recognize(img_b64, prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
