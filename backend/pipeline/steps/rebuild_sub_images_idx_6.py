# rebuild_sub_images_idx_6.py

import os
import json
from typing import Dict, List, Any
from PIL import Image


class ImageRebuilder:
    def __init__(self, tol: int = 3):
        self.tol = tol

    # ----------------------------------------------------
    # ↓↓↓ 下面这一段是原脚本全部函数，一字不改 ↓↓↓
    # ----------------------------------------------------
    @staticmethod
    def resort_boxes(boxes):
        # 排序：先按 y1（coordinate[1]）升序，再按 x1（coordinate[0]）升序
        sorted_boxes = sorted(boxes, key=lambda item: (item["coordinate"][1], item["coordinate"][0]))
        return sorted_boxes

    @staticmethod
    def get_resorted_level_info(input_info):
        new_input_info = {}
        for idx, info in input_info.items():
            idx_info = info['res']
            boxes = idx_info['boxes']
            input_path = idx_info['input_path']
            sorted_boxes = ImageRebuilder.resort_boxes(boxes)
            res = {}
            res['input_path'] = input_path
            res['boxes'] = sorted_boxes
            new_input_info[idx] = res
        return new_input_info

    @staticmethod
    def replace_null_in_object(obj):
        """仅替换字典中的 null 值，不处理数组"""
        if isinstance(obj, dict):
            return {
                k: "" if v is None else ImageRebuilder.replace_null_in_object(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            # 数组中的元素不处理
            return [ImageRebuilder.replace_null_in_object(item) for item in obj]
        else:
            return obj

    @staticmethod
    def get_new_info(json_file):
        # 从文件读取
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cleaned_data = ImageRebuilder.replace_null_in_object(data)

        result = ImageRebuilder.get_resorted_level_info(cleaned_data)

        return result

    @staticmethod
    def get_single_img_range(coordinates, img, img_name,pre_last_state):
        """
        根据给定的坐标从图片中截取指定区域并保存。

        :param img_path: 原始图片的路径
        :param coordinates: 一个包含四个点坐标的列表，每个点是一个(x, y)元组
        :param img_name: 保存截取后图片的文件名
        """

        width, height = img.size

        # 获取截取区域的左上角和右下角坐标

        left = 0 #coordinates[0]
        upper = coordinates[1]
        right = width #coordinates[2]
        lower = coordinates[3]
        if ("_0_" in img_name or "_0." in img_name) and not pre_last_state:
            upper = 0

        # 截取指定区域
        cropped_img = img.crop((left, upper, right, lower))

        # 获取保存路径的目录部分
        save_dir = os.path.dirname(img_name)

        # 如果目录不存在，则创建它
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)

        print("img_name===================:", img_name, pre_last_state)

        # 保存截取后的图片
        cropped_img.save(img_name)  # 保存到指定路径

    @staticmethod
    def is_contained(inner, outer, tol=3):
        return (
            outer[0] - tol <= inner[0] and
            outer[1] - tol <= inner[1] and
            inner[2] <= outer[2] + tol and
            inner[3] <= outer[3] + tol
        )

    @staticmethod
    def filter_nested_tables_with_removed_indices(data, tol=3):
        # 找出所有 label == "table" 的原始索引
        table_indices = [i for i, item in enumerate(data) if item.get("label") == "table"]
        tables = [data[i] for i in table_indices]

        # 需要保留的 table 原始索引
        keep_indices = []
        for i, t in enumerate(tables):
            coord = t['coordinate']
            if not any(
                ImageRebuilder.is_contained(coord, other['coordinate'], tol)
                for j, other in enumerate(tables)
                if j != i
            ):
                keep_indices.append(table_indices[i])

        # 被删除的索引 = 原始 table 索引 - 保留的索引
        removed_indices = [idx for idx in table_indices if idx not in keep_indices]

        return removed_indices

    # ----------------------------------------------------
    # 原 save_sub_pics 整体搬进类，一字不改
    def save_sub_pics(self, pic_data, save_dir, image_path='', save_join_dir='', sub_name='', pre_last_state=0):
        if pic_data:
            print("******************pic_data***************")
            print("image_path:", image_path)
            print(pic_data)
            boxes = pic_data['boxes']
            if not image_path:
                image_path = pic_data['input_path']
            if not isinstance(image_path, str):
                image_path = str(image_path)
            image_path = image_path.replace("\\", "/")

            # 打开原始图片
            img = Image.open(image_path)
            table_state = 0
            box_num = 0
            label_boxes = {}
            header_y = 0
            for i, box in enumerate(boxes):
                label = box['label']
                coordinate = box['coordinate']
                if 'header' in label:
                    header_y = max(header_y, coordinate[3])
                if sub_name:
                    img_name = "{}/{}_{}_{}.png".format(save_dir, sub_name, label, str(i))
                else:
                    img_name = "{}/{}_{}.png".format(save_dir,  label, str(i))

                self.get_single_img_range(coordinate, img, img_name, 0)

                if label in ["table"]:
                    table_state += 1
                box_num += 1
                print("label:", label)
                label_boxes[i] = label

            box_len = len(label_boxes)
            start_len_num = 999999
            for k in range(box_len):
                j_lable = label_boxes[k]
                # print("j_lable:", j_lable, k)
                if j_lable in ['table']:
                    start_len_num = 0
                elif j_lable in ['number', 'footer', 'seal']:
                    start_len_num += 1

            if start_len_num < 100 and start_len_num > 0:
                box_num -= (start_len_num - 1)

            uni_high = 0
            cur_pre_last_state = 0
            if table_state:
                removed_indices = self.filter_nested_tables_with_removed_indices(boxes)

                y1 = 0
                j = 0
                title_state = 0
                text_state = 0
                start_state = 1

                # 记录上一个 table 的索引，用于判断相邻 table 之间是否仅有 text
                last_table_idx = -1

                for i, box in enumerate(boxes):
                    label = box['label']
                    coordinate = box['coordinate']

                    # print(">>>>>>i, label:", label, i, start_state)

                    # 当遇到 table 时，检查它与上一个 table 之间是否只包含 text
                    if label == "table":
                        between = range(last_table_idx + 1, i)
                        # 仅当区间非空且全为 text 时才融合
                        if between and all(boxes[k]['label'] == 'text' for k in between):
                            min_upper = min(boxes[k]['coordinate'][1] for k in between)
                            coordinate[1] = min_upper
                        last_table_idx = i  # 更新为当前 table 索引

                    if label == "text":
                        if uni_high:
                            text_high = coordinate[3]-coordinate[1]
                            if text_high < uni_high*3:
                                label = 'title'
                                # print("*******ooooo**********>label:", text_high, uni_high, label, start_state)

                    if label == "header":
                        title_state = 0
                        text_state = 0
                        if not uni_high:
                            uni_high = coordinate[3]-coordinate[1]

                    elif "title" in label:
                        if not title_state:
                            y1 = coordinate[1]

                        if not uni_high:
                            uni_high = coordinate[3]-coordinate[1]

                        title_state = 1
                        text_state = 0
                        start_state = 0

                    elif label == "table":
                        j += 1
                        if y1:
                            coordinate[1] = y1
                            y1 = 0

                        j_idx = str(j)
                        if j == 1:
                           if start_state:
                               j_idx = str(0)

                        if i >= box_num - 2:
                            label += "_last"

                        if text_state:
                            j_idx = "{}_tex".format(j_idx)

                        # print("***********sub_name:", sub_name, j_idx, label, j)

                        if sub_name:
                            img_name = "{}/{}_{}_{}.png".format(save_join_dir, sub_name, j_idx, label)
                        else:
                            img_name = "{}/{}_{}.png".format(save_join_dir, j_idx, label)

                        if removed_indices:
                            print("removed_indices:", removed_indices)

                        if i not in removed_indices:
                            self.get_single_img_range(coordinate, img, img_name, pre_last_state)
                            print("保存整合图片名称:", img_name)
                            title_state = 0
                            text_state = 0
                            start_state = 0
                            if '_last' in img_name:
                                cur_pre_last_state = 1

                    else:
                        change_state = 0
                        if label == "text":
                            text_state = 1
                            x1 = coordinate[0]
                            x2 = coordinate[2]
                            if x1 > x2 / 2 and not title_state:
                                y1 = coordinate[1]
                                change_state = 1
                        else:
                            title_state = 0

                        if start_state and label == "text" and change_state:
                            start_state = 1
                        elif header_y and coordinate[1] < header_y:
                            pass
                        else:
                            start_state = 0

                        # title_state = 0

                    # print("*****************>label:", label, start_state, img_name)

            pre_last_state = cur_pre_last_state

        return pre_last_state

    # ----------------------------------------------------
    # 原 save_batch_pics 也保持不变，仅把函数名加 self.
    # ----------------------------------------------------
    def save_batch_pics_1(self, json_file, ori_path, sub_save_path, join_save_path="", sub_name=''):
        sorted_info = self.get_new_info(json_file)
        i = 0
        pre_last_state = 0
        for idx, idx_info in sorted_info.items():
            # if idx not in ['514002_017']:
            #     continue
            print("id-", idx, idx_info)
            sub_idx_dir = "{}/{}".format(sub_save_path, idx)
            sub_idx_name = "{}/{}.png".format(ori_path, idx)
            save_join_dir = "{}/{}".format(join_save_path, idx)
            pre_last_state = self.save_sub_pics(idx_info, sub_idx_dir, image_path=sub_idx_name, save_join_dir=join_save_path,sub_name=idx,pre_last_state=pre_last_state)

            i += 1
            # if i > 8:
            #     break

    def save_batch_pics(
            self,
            *,
            json_file,
            ori_path,  # 原始 PNG 目录
            subs_save_path,  # 切图输出根目录
            join_save_path,  # 拼表输出根目录
            sub_name: str = "",  # 可选前缀，用于子目录命名
    ) -> None:
        """
        路径全部外部指定，内部不再拼接编号
        """
        sorted_info = self.get_new_info(json_file)

        # 确保输出目录存在
        subs_save_path.mkdir(parents=True, exist_ok=True)
        join_save_path.mkdir(parents=True, exist_ok=True)

        pre_last_state = 0
        for idx, idx_info in sorted_info.items():
            # 1. 切图子目录：subs_save_path / idx
            sub_idx_dir = subs_save_path / idx
            sub_idx_dir.mkdir(exist_ok=True)

            # 2. 原始图片路径：ori_path / idx.png
            sub_idx_name = ori_path / f"{idx}.png"

            # 3. 拼表子目录：join_save_path / idx（已存在）
            pre_last_state = self.save_sub_pics(
                idx_info,
                sub_idx_dir,
                image_path=sub_idx_name,
                save_join_dir=join_save_path,
                sub_name=idx,
                pre_last_state=pre_last_state,
            )



# ----------------------------------------------------------------------
# 使用示例（与原脚本等价）
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from pathlib import Path  # 导入Path类，用于路径处理
    rebuilder = ImageRebuilder(tol=3)

    img_info = {
        # "514001": r"F:\wills\codes\bankdata\new_src_data\pdfs\2024-04-24-1921038.IB-19禾城农商二级01-浙江禾城农村商业银行股份有限公司2023年年度报告.pdf",
        # "514002": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-03-15：平安银行：2024年年度报告.pdf",
        # "514003": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-03-26-600036.SH-招商银行-招商银行股份有限公司2024年度报告.pdf",
        # "514004": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-04-26-601577.SH-长沙银行-601577长沙银行股份有限公司2024年年度报告全文.pdf",
        # "514005": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-04-29-601838.SH-成都银行-601838成都银行股份有限公司2024年年度报告.pdf",
        # "514006": r"F:\wills\codes\bankdata\new_src_data\pdfs\湖南银行股份有限公司2024年年度报告.pdf",
        # "514009": r"F:\wills\codes\bankdata\new_src_data\pdfs\601939建设银行2024年年度报告.pdf",
        "514010": r"F:\wills\codes\bankdata\new_src_data\pdfs\601939建设银行2024年年度报告.pdf",

    }

    for dir_idx,path in img_info.items():
        json_file = rf"F:\wills\codes\bankdata\new_src_data\loc_jsons\all_layouts_{dir_idx}.json"

        print("<UNK>:", dir_idx)

        # rebuilder.save_batch_pics(
        #     json_file=json_file,
        #     ori_path=rf"F:\wills\codes\bankdata\new_src_data\rejoin_pngs\{dir_idx}",
        #     subs_save_path=rf"F:\wills\codes\bankdata\images\subs\{dir_idx}",
        #     join_save_path=rf"F:\wills\codes\bankdata\images\joins\{dir_idx}"
        # )
        # # break

        rebuilder.save_batch_pics(
            json_file=json_file,
            ori_path=Path(rf"F:\wills\codes\bankdata\new_src_data\rejoin_pngs\{dir_idx}"),  # 转为Path
            subs_save_path=Path(rf"F:\wills\codes\bankdata\images\subs\{dir_idx}"),  # 转为Path
            join_save_path=Path(rf"F:\wills\codes\bankdata\images\joins\{dir_idx}")  # 转为Path
        )