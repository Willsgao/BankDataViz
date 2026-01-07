# -*- coding:utf-8 -*-

from typing import Optional
from openai import OpenAI
from backend.configs.config import config

class SimpleBankNameExtractor:
    """简单的银行名称提取器 - 使用LLM直接识别"""

    def __init__(self):
        self.client = OpenAI(
            base_url=config.TABLE_LLM_BASE_URL,
            api_key=config.TABLE_LLM_API_KEY
        )

    def extract_bank_name(self, document_name: str) -> Optional[str]:
        """
        从文档名称中识别银行名称

        Args:
            document_name: 文档名称

        Returns:
            str: 银行名称，识别不了返回None
        """
        if not document_name:
            return None

        # 提取纯文件名（去掉路径）
        import os
        filename = os.path.basename(document_name)

        prompt = f"""
从文档名称中识别银行名称，只返回银行名称，如果没有银行信息就返回空字符串。

文档名称：{filename}

只返回银行名称，不要其他内容：
"""

        try:
            response = self.client.chat.completions.create(
                model="your_model_name",  # 替换为实际模型名
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )

            bank_name = response.choices[0].message.content.strip()

            # 清理结果
            bank_name = bank_name.strip('"\'')  # 去掉引号
            bank_name = bank_name if bank_name else None

            print(f"📄 文档: {filename}")
            print(f"🏦 识别到银行: {bank_name if bank_name else '无'}")

            return bank_name

        except Exception as e:
            print(f"❌ LLM调用失败: {e}")
            return None


# 使用示例
def get_bank_name_from_document(document_name: str) -> str:
    """
    从文档名称识别银行名称

    Args:
        document_name: 文档名称

    Returns:
        str: 银行名称，识别不了返回空字符串
    """
    extractor = SimpleBankNameExtractor()
    result = extractor.extract_bank_name(document_name)
    return result if result else ""


# 测试
if __name__ == "__main__":
    test_cases = [
        "工商银行2024年财务报表.pdf",
        "建设银行年度报告.docx",
        "招商银行Q3业绩.xlsx",
        "某公司财务报告.pdf",  # 这个应该返回空
        "random_document.xlsx"  # 这个应该返回空
    ]

    for doc in test_cases:
        bank_name = get_bank_name_from_document(doc)
        print(f"文档: {doc} -> 银行: {bank_name}")