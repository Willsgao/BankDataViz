import camelot.io as camelot
import pandas as pd
from openpyxl.styles.alignment import horizontal_alignments
from tqdm import tqdm
import fitz  # PyMuPDF
import re
import os
import cv2
import base64
import numpy as np
from openai import OpenAI
from PIL import Image


class PDFAnalyzer:
    def __init__(self, ark_api_key="90b9c47f-815c-4216-913a-3d1a567e35ac"):
        """
        初始化PDFAnalyzer类。

        参数:
        pdf_path (str): PDF文件的路径。
        ark_api_key (str): 方舟API密钥。
        """
        self.ark_api_key = ark_api_key
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=self.ark_api_key
        )
        self.title = ''
        self.system_prompt1 = '''
        请检查图片中是否有数据表格；如有表格再判断表格是否跨页（对于一个页面上（1）第一个表格上方无文本或文本数不超过2行；（2）最后一个表格下方无文本或文本数不超过2行；只要（1）（2）中有一个满足就认为表格跨页）。
        【返回格式】
        ```
        有表格_跨页/有表格_不跨页/无表格
        并给出详细原因。
        ```
        '''
        self.system_prompt = '''
        请按以下步骤慢慢去检查图片，多想两遍：
        1、观察页眉横线上方是否存在文件名。
        2、判断页面是否包含财务类表格（只要任意一个表格中第2列到最后一列的数据是数值类或者数值取值范围就有财务类表格），如果有返回“有表格”
            （1）忽略图片首行的文件名或页号（如果有）之后的第1行数据（文本或者表格数据）是否在表格中，如果在表格中记为“_上方0”， 否则为“_上方1”
            （2）忽略图片最后一行的文件名或页号（如单个数字或XX页，如果有）之后的倒数第1行数据（文本或者表格数据）是否在表格中，如果在表格中记为“_下方0”， 否则为“_下方1”
            （3）判断图片中是否盖有公章。
        3、若无财务类表格，返回 “无表格”。
        4、如果有财务表格，说明2的（1）中表格上方的文本有哪些
        【返回格式】
        ```
        文件名：XXX
        有表格_上方1_下方0_有公章/有表格_上方1_下方0_无公章/无表格
        再返回结果中解释返回的结果的原因。
        ...
        ```
        '''
        self.system_prompt = '''
        ##角色设定##
        你是一个优秀的金融分析师，具有丰富的金融数据分析能力。
        ##任务目标##
        现在你需要从一个图片中，寻找并识别出金融数据表格的相关信息。
        ##任务步骤##
            1、判断图片页眉、页脚位置是否有文件名或页号
            2、确定图片内容区中是否含有表格形式（属于表格一部分也可以）
            3、如果2中找到表格，则从上往下为编号1号,2号……
            4、分别计算每个表格的行数row和列数col；
            5、确定表格中是否存在金融表格（存在一列数据是金额、利润、收入等内容的数值列或取值范围列）
            6、如果表格在图片上方，需要判断表格是否存在跨页可能（1号表格上面没有文本或只有文件名、页号则跨页，否则不跨页）
            7、如果表格在图片下方，需要判断表格是否存在跨页可能（最后一个表格下面没有文本或只有文件名、页号则跨页，否则不跨页）
            8、判断图片中是否有公章
        ##返回结果格式##
        ```
        文件名：XXXXXXX/无_END
        表格个数：Y_END
        表格性质：财务表格_END/非财务表格_END/无表格_END
        表格编号：1号-表格名_END，2号-表格名_END
        表格行列数：1号-row_col_END，2号-row_col_END，……（row行数，col列数）
        1号表格：上方文本_XXXXXXXX/无_END（注意1号是“上方文本”）
        Y号表格：下方文本_YYYYYYYY/无_END（注意Y号是倒数第一个表格，是“下方文本”）
        公章特征：有公章_END/无公章_END
        ```
        注意：结果中严格按照上面格式给出，使用紧凑模式，不要包含多余空格
                '''

        self.system_prompt_direct = '''
        请仔细观察这张图片，判断图片中表格外部的文字的布局方向是横向（从左到右、行与行从上到下排列）还是纵向（从上到下、列与列从右到左或从左到右排列）；识别要检查确认行数是否正确。
        【返回格式】
        ```
        横向/纵向
        ```
        '''
        # 顶部检测：图片顶部与版心顶部距离 < 1行文字高度
        # 底部检测：图片底部与版心底部距离 < 1行文字高度
        self.doc = None
        self.direction_nums = []

    def get_filename_without_extension(self, file_path):
        """
        从文件路径中提取文件名并去除扩展名。

        参数:
        file_path (str): 文件路径。

        返回:
        str: 去除扩展名的文件名。
        """
        # 获取文件名（带扩展名）
        # filename_with_ext = os.path.basename(file_path)
        # # 去除扩展名
        # filename_without_ext = os.path.splitext(filename_with_ext)[0]
        filename_without_ext = re.split(r'\\|/', file_path)[-1][:-4]

        return filename_without_ext

    def ensure_directory_exists(self, directory_path):
        """
        检查指定的目录是否存在，如果不存在则创建该目录。

        参数:
        directory_path (str): 要检查和创建的目录路径。
        """
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            print(f"Directory '{directory_path}' created.")
        else:
            print(f"Directory '{directory_path}' already exists.")

    def get_total_pages(self):
        """
        获取PDF文件的总页数。

        返回:
        int: PDF文件的总页数。
        """
        self.doc = fitz.open(self.pdf_path)
        return len(self.doc)

    def concatenate_images_vertically(self, image_folder, output_path):
        # 获取文件夹中所有png文件
        image_files = [f for f in os.listdir(image_folder) if f.endswith('.png')]
        image_files.sort()  # 按文件名排序

        images = [Image.open(os.path.join(image_folder, img)) for img in image_files]

        # 计算新图片的宽度和高度
        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        total_height = sum(heights)

        # 创建一个新的空白图片
        new_image = Image.new('RGB', (max_width, total_height))

        y_offset = 0
        for im in images:
            new_image.paste(im, (0, y_offset))
            y_offset += im.height

        # 保存新图片
        new_image.save(output_path)

    def extract_text_from_pdf(self):
        """
        从PDF文件中提取每一页的文本信息。

        返回:
        tuple: 包含三个列表，
        第一个是含有文本的页面编号列表，
        第二个是不含文本的页面编号列表，
        第三个是文本行数少于10行的页面编号列表。
        """
        text_page_numbers = []
        image_page_numbers = []
        short_text_page_numbers = []

        total_pages = self.get_total_pages()
        doc = self.doc

        for page_num in tqdm(range(1, total_pages + 1), desc="Extracting Text"):
            page = doc.load_page(page_num - 1)
            text = page.get_text("text")

            lines = text.strip().split('\n')
            line_count = len(lines)

            if line_count >= 10:
                text_page_numbers.append(page_num)
            else:
                short_text_page_numbers.append(page_num)

            if not text.strip():
                image_page_numbers.append(page_num)

        return text_page_numbers, image_page_numbers, short_text_page_numbers

    def is_financial_table(self, df):
        """
        判断一个DataFrame是否包含财务数据表格。

        参数:
        df (pandas.DataFrame): 要判断的DataFrame。

        返回:
        bool: 如果包含财务数据表格返回True，否则返回False。
        """
        # 判断表格的列数是否不少于3列
        print("df.columns:", len(df.columns))
        if len(df.columns) < 3:
            return False

        # 定义一个正则表达式来匹配数字，包括带有小括号和分位符的数字
        number_pattern = re.compile(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*\(\w+\))?')

        # 检查每一列是否有多个数字值
        i = -1

        for col in df.columns:
            i += 1
            if not i:
                continue
            numeric_count = sum(
                1 for value in df[col] if isinstance(value, str) and number_pattern.fullmatch(value.strip()))

            res = [number_pattern.fullmatch(value.strip()) for value in df[col] if isinstance(value, str) and number_pattern.fullmatch(value.strip())]
            print("res=======res:", res)

            if numeric_count > 1:
                return True

        return False

    def check_for_financial_tables(self, text_page_numbers):
        """
        检查指定的文本页面是否包含财务数据表格。

        参数:
        text_page_numbers (list): 含有文本的页面编号列表。

        返回:
        list: 包含财务数据表格的页面编号列表。
        """
        table_page_numbers = []

        for page_number in text_page_numbers:
            tables = camelot.read_pdf(self.pdf_path, pages=str(page_number), flavor='stream')
            for table in tables:
                df = table.df
                if self.is_financial_table(df):
                    table_page_numbers.append(page_number)
                    break
                else:
                    print("======not_is_financial_table====", page_number)

        return table_page_numbers

    def encode_image(self, img_path):
        """
        将图片编码为Base64格式。

        参数:
        img_path (str): 图片路径。

        返回:
        str: Base64编码后的字符串。
        """
        print("img_path:", img_path)
        with open(img_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
        return encoded_string

    def get_batch_images(self, img_list):
        """
        批量编码图片为Base64格式。

        参数:
        img_list (list): 图片路径列表。

        返回:
        list: Base64编码后的字符串列表。
        """
        batch_images = {}
        for img_path in img_list:
            img_name = self.get_filename_without_extension(img_path)
            img_base = self.encode_image(img_path)
            batch_images[img_name] = img_base

        return batch_images

    def get_image_info(self, base64_image, system_prompt):
        response = self.client.chat.completions.create(
            # 替换 <Model> 为模型的Model ID
            model="doubao-1-5-vision-pro-250328",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                # 需要注意：传入Base64编码前需要增加前缀 data:image/{图片格式};base64,{Base64编码}：
                                # PNG图片："url":  f"data:image/png;base64,{base64_image}"
                                # JPEG图片："url":  f"data:image/jpeg;base64,{base64_image}"
                                # WEBP图片："url":  f"data:image/webp;base64,{base64_image}"
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
        )

        first_choice = response.choices[0]

        # 从choice中获取message的内容
        content = first_choice.message.content

        return content

    def get_effect_image_nums(self, need_nums, image_path_list):
        effect_nums = []
        cross_page_nums = []
        image_bs_dict = self.get_batch_images(image_path_list)
        for idx,image_bs in image_bs_dict.items():
            if int(idx) in need_nums or str(idx) in need_nums:
                image_cont = self.get_image_info(image_bs, self.system_prompt)
                print("-------------->", idx, image_cont)

                if '有表格' in image_cont:
                    effect_nums.append(idx)
                    if '不跨页' in image_cont:
                        pass
                    elif '跨页' in image_cont:
                        cross_page_nums.append(idx)
                        print('>>>>>>>>>>>>>>>>>跨页：', image_cont)
                elif '无表格' in image_cont:
                    print('-------->无表格', image_cont)
                else:
                    print("----其他:", image_cont)

        return effect_nums, cross_page_nums

    def first_table_state(self, name_cont, first_cont):
        state = 0
        if first_cont in ['无']:
            state = 1
        else:
            if name_cont in first_cont or first_cont in name_cont:
                state = 1
        return state

    def last_table_state(self, name_cont, last_cont):
        num_pat = r"[第共]*\d+[\s页]*$"
        state = 0
        if last_cont in ['无']:
            state = 1
        else:
            if name_cont in last_cont or last_cont in name_cont:
                state = 1
            else:
                mat_res = re.match(num_pat, last_cont)
                print("mat_res:", mat_res, last_cont)
                if mat_res:
                    state = 1
        return state

    def get_effect_join_image_nums(self, need_nums, image_path_list):

        filename_pat = r"文件名[:：](.*)_END"
        tablenum_pat = r"表格个数[:：](\d+)_END"
        row_col_pat = r"号.*?(\d+_\d+)_END"
        tablefeat_pat = r"表格性质[:：](.*)_END"
        stampfeat_pat = r"公章特征[:：](.*)_END"

        table_errors = []
        table_no_tables = []
        table_no_financial_tables = []
        table_financial_tables = []

        filename_errors = []
        tablenum_errors = []
        stamp_nums = []
        pre_join_nums = []
        post_join_nums = []
        row_col_num_idxs = {}

        idx_conts = {}

        image_bs_dict = self.get_batch_images(image_path_list)
        for idx,image_bs in image_bs_dict.items():
            if int(idx) in need_nums or str(idx) in need_nums:
                image_cont = self.get_image_info(image_bs, self.system_prompt)
                print("-------------->", idx, image_cont)
                idx_conts[idx] = image_cont

                tablefeat_res = re.search(tablefeat_pat, image_cont).groups()

                tablefeat = '代码有误'
                if tablefeat_res:
                    tablefeat = tablefeat_res[0]

                if tablefeat in ['代码有误']:
                    table_errors.append(int(idx))
                elif tablefeat in ['无表格']:
                    table_no_tables.append(int(idx))
                elif tablefeat in ['非财务表格']:
                    table_no_financial_tables.append(int(idx))
                else:
                    table_financial_tables.append(int(idx))

                    name_res = re.search(filename_pat, image_cont).groups()

                    name_cont = '文件名有误'
                    if name_res:
                        name_cont = name_res[0]

                    if name_cont in ['文件名有误']:
                        filename_errors.append(int(idx))

                    tablenum_res = re.search(tablenum_pat, image_cont).groups()
                    tablenum = -1
                    if tablenum_res:
                        tablenum = int(tablenum_res[0])

                    if tablenum == -1:
                        tablenum_errors.append(int(idx))
                    else:
                        row_col_num = 0
                        row_col_res = re.findall(row_col_pat, image_cont)
                        print("row_col_res:", row_col_res)
                        for row_col in row_col_res:
                            row_col_cts = row_col.split('_')
                            row = int(row_col_cts[0])
                            col = int(row_col_cts[1])
                            row_col_num += row*col

                        row_col_num_idxs[int(idx)] = row_col_num

                        first_pat = r"1号表格[:：]上方文本_(.*)_END"
                        last_pat = r"{}号表格[:：]下方文本_(.*)_END".format(tablenum)

                        first_mid_res = re.search(first_pat, image_cont)
                        first_res = first_mid_res.groups() if first_mid_res else None
                        last_mid_res = re.search(last_pat, image_cont)
                        last_res = last_mid_res.groups() if last_mid_res else None

                        first_cont = "上方文本有误"
                        if first_res:
                            first_cont = first_res[0].strip()
                        last_cont = "下方文本有误"
                        if last_res:
                            last_cont = last_res[0].strip()

                        if self.first_table_state(name_cont, first_cont):
                            pre_join_nums.append(int(idx))

                        if self.last_table_state(name_cont, last_cont):
                            post_join_nums.append(int(idx))

                    stamp_res = re.search(stampfeat_pat, image_cont).groups()
                    if stamp_res:
                        stamp_cont = stamp_res[0]
                        if stamp_cont in ['有公章']:
                            stamp_nums.append(int(idx))

        result = {}

        result['idx_conts'] = idx_conts
        result['table_errors'] = table_errors
        result['table_no_tables'] = table_no_tables
        result['table_no_financial_tables'] = table_no_financial_tables
        result['filename_errors'] = filename_errors
        result['tablenum_errors'] = tablenum_errors
        result['table_financial_tables'] = list(sorted(table_financial_tables))
        result['pre_join_nums'] = list(sorted(pre_join_nums))
        result['post_join_nums'] = list(sorted(post_join_nums))
        result['direction_nums'] = list(set(self.direction_nums))
        result['stamp_nums'] = stamp_nums
        result['row_col_num_idxs'] = row_col_num_idxs

        return result

    def detect_table_orientation(self, image_path):
        # Read the image
        print("image_path:", image_path)
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to read image: {image_path}")
            return 1

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply GaussianBlur to reduce noise and improve edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Use Canny Edge Detection
        edges = cv2.Canny(blurred, 50, 150)

        # Find lines using Hough Line Transform
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)

        if lines is None:
            return "No lines detected"

        vertical_lines_count = 0
        horizontal_lines_count = 0

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi

            if -10 <= angle <= 10 or 170 <= angle <= 190:
                horizontal_lines_count += 1
            elif 80 <= angle <= 100 or -100 <= angle <= -80:
                vertical_lines_count += 1

        if horizontal_lines_count > vertical_lines_count:
            return 1
        else:
            return 0

    def rotate_and_save_image(self, input_path, output_path, direction='clockwise'):
        """
        Rotate an image and save it.

        Parameters:
        input_path (str): Path to the input image.
        output_path (str): Path to save the rotated image.
        direction (str): Rotation direction ('clockwise' or 'counterclockwise').
        """
        # Read the image
        image = cv2.imread(input_path)
        if image is None:
            print(f"Failed to read image: {input_path}")
            return

        # Determine rotation code based on direction
        if direction == 'clockwise':
            rotation_code = cv2.ROTATE_90_CLOCKWISE
        elif direction == 'counterclockwise':
            rotation_code = cv2.ROTATE_90_COUNTERCLOCKWISE
        else:
            print(f"Invalid rotation direction: {direction}. Using default clockwise.")
            rotation_code = cv2.ROTATE_90_CLOCKWISE

        # Rotate the image
        rotated_image = cv2.rotate(image, rotation_code)

        # Save the rotated image
        success = cv2.imwrite(output_path, rotated_image)
        if not success:
            print(f"Failed to save rotated image: {output_path}")
            return False
        print(f"Rotated image saved successfully at: {output_path}")
        return True

    def pdf_page_to_png(self, page_numbers, output_dir):
        """
        将PDF的指定页转为PNG图片，并以页码命名。

        参数:
        pdf_path (str): PDF文件路径。
        page_number (int): 要转换的页码（从1开始）。
        output_dir (str): 输出PNG图片的目录。
        """

        image_list = []
        doc = self.doc
        for page_number in tqdm(page_numbers, desc="Extracting PDF"):
            page = doc.load_page(page_number - 1)  # 索引从0开始
            pix = page.get_pixmap()
            output_path = f"{output_dir}/{page_number}.png"
            pix.save(output_path)
            print("图片{}已存储".format(output_path))
            image_list.append(output_path)
        return image_list

    def rotate_some_images(self, image_list, output_dir):
        for output_path in tqdm(image_list):
            horizon_state = self.detect_table_orientation(output_path)
            print(output_path, "horizon state:", horizon_state)
            if not horizon_state:
                img_base = self.encode_image(output_path)
                image_cont = self.get_image_info(img_base, self.system_prompt_direct)
                print("image_cont:", image_cont)
                print("output_path:", output_path)
                if '纵向' in image_cont:
                    print(f"Rotated image saved successfully at: {output_path}", image_cont)
                    name_idx = re.split(r"\\|/", output_path)[-1].split('.')[0]
                    temp_name = 'temp_{}.png'.format(name_idx)
                    temp_path = f"{output_dir}/{temp_name}"
                    image = cv2.imread(output_path)
                    # Save the rotated image
                    cv2.imwrite(temp_path, image)
                    self.rotate_and_save_image(temp_path, output_path)
                    os.remove(temp_path)
                    self.direction_nums.append(int(name_idx))
                    print("图片已旋转！！")

    def save_dict_to_json(self, data, file_path):
        import json
        """
        将字典数据存入JSON文件。

        参数:
        data (dict): 要保存的字典数据。
        file_path (str): JSON文件的路径。
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
            print(f"Data successfully saved to {file_path}")
        except Exception as e:
            print(f"Failed to save data to {file_path}: {e}")

    def main(self, pdf_path, image_output_dir, result_file):
        import json
        """
        主函数，执行整个流程。
        """
        self.doc = None
        self.direction_nums = []
        self.pdf_path = pdf_path

        result = {}

        text_page_numbers, image_page_numbers, short_text_page_numbers = self.extract_text_from_pdf()

        result['image_output_dir'] = image_output_dir
        result['text_page_numbers'] = list(set(text_page_numbers))
        result['image_page_numbers'] = list(set(image_page_numbers))
        result['short_text_page_numbers'] = list(set(short_text_page_numbers))

        table_page_numbers = []
        if text_page_numbers:
            table_page_numbers = self.check_for_financial_tables(text_page_numbers)
        result['table_page_numbers'] = list(set(table_page_numbers))

        need_check_nums =  image_page_numbers+short_text_page_numbers+table_page_numbers
        # all_image_nums = image_page_numbers+short_text_page_numbers+table_page_numbers
        result['need_check_nums'] = list(set(need_check_nums))
        # result['all_image_nums'] = list(set(all_image_nums))

        save_state = True
        image_path_list = []
        if save_state:
            # image_path_list = self.pdf_page_to_png(all_image_nums, image_output_dir)
            image_path_list = self.pdf_page_to_png(need_check_nums, image_output_dir)
            self.rotate_some_images(image_path_list, image_output_dir)

        result['image_path_list'] = list(set(image_path_list))

        # check_effect_nums, cross_page_nums = self.get_effect_image_nums(need_check_nums, image_path_list)
        join_res = self.get_effect_join_image_nums(need_check_nums, image_path_list)

        result.update(join_res)

        # print("check_effect_nums:", check_effect_nums)
        print("Table Pages:", table_page_numbers)

        result_file = r"{}/{}".format(image_output_dir, result_file)
        self.save_dict_to_json(result, result_file)


# 示例调用
if __name__ == "__main__":
    # PDF_FILE = r"F:\wills\codes\bankdata\data\pdfs\2024-04-24-1921038.IB-19禾城农商二级01-浙江禾城农村商业银行股份有限公司2023年年度报告.pdf"  # 替换为您的PDF文件路径
    # PDF_FILE = r"F:\wills\codes\bankdata\data\pdfs\2025-03-26-600036.SH-招商银行-招商银行股份有限公司2024年度报告.pdf"
    # PDF_FILE = r"F:\wills\codes\bankdata\data\pdfs\2025-03-15：平安银行：2024年年度报告.pdf"
    PDF_FILE = r"F:\wills\codes\bankdata\data\pdfs\0514\2025-04-26-601577.SH-长沙银行-601577长沙银行股份有限公司2024年年度报告全文.pdf"
    # PDF_FILE = r"F:\wills\codes\bankdata\data\pdfs\0514\2025-04-29-601838.SH-成都银行-601838成都银行股份有限公司2024年年度报告.pdf"
    # PDF_FILE = r"F:\wills\codes\bankdata\data\pdfs\0514\湖南银行股份有限公司2024年年度报告.pdf"

    model = PDFAnalyzer()
    name = model.get_filename_without_extension(PDF_FILE)
    print("PDF_FILE:", PDF_FILE, name)
    # file_num = 514002
    file_num = 514001
    # file_num = 514003
    output_dir = r"F:\wills\codes\bankdata\outputs\images\{}".format(file_num)
    output_res_dir = r"F:\wills\codes\bankdata\outputs\results\{}".format(name)
    model.ensure_directory_exists(output_dir)


    json_file = r"PDF原始图片信息_2.json"
    model.main(PDF_FILE, output_dir, json_file)

    # model.check_pic_info(output_dir)


#     API_KEY = "90b9c47f-815c-4216-913a-3d1a567e35ac"  # 替换为你的密钥
#
#     analyzer = FinancialTableAnalyzerLLM(api_key=API_KEY)
#     pdf_file = r"E:\Datas\base_pros\DocuVista\test_codes/英语1.pdf"






