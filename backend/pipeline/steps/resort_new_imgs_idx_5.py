

import os
import cv2
from pathlib import Path

def save_new_imgs(img_path1, img_path2, new_path):
    new_path = Path(new_path)
    new_path.mkdir(parents=True, exist_ok=True)

    path_names1 = {}
    for root, dirs, files in os.walk(img_path1):
        for file in files:
            filepath = os.path.join(root, file)
            path_names1[file] = filepath

    path_names2 = {}
    for root, dirs, files in os.walk(img_path2):
        for file in files:
            filepath = os.path.join(root, file)
            new_file = file.replace("rotate_", "")
            path_names2[new_file] = filepath

    # print("path_names2:", path_names2)

    for name, path in path_names1.items():
        if name in path_names2:
            print("name------------>", name)
            path = path_names2[name]

        img = cv2.imread(str(path))

        # 保存
        new_file_name = os.path.join(new_path, name)
        cv2.imwrite(str(new_file_name), img)
        print("new_file_name", new_file_name)

    print("path_names2:", path_names2)


if __name__ == "__main__":

    img_info = {
        # "514001": r"F:\wills\codes\bankdata\new_src_data\pdfs\2024-04-24-1921038.IB-19禾城农商二级01-浙江禾城农村商业银行股份有限公司2023年年度报告.pdf",
        # "514002": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-03-15：平安银行：2024年年度报告.pdf",
        # "514003": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-03-26-600036.SH-招商银行-招商银行股份有限公司2024年度报告.pdf",
        # "514004": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-04-26-601577.SH-长沙银行-601577长沙银行股份有限公司2024年年度报告全文.pdf",
        # "514005": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-04-29-601838.SH-成都银行-601838成都银行股份有限公司2024年年度报告.pdf",
        # "514006": r"F:\wills\codes\bankdata\new_src_data\pdfs\湖南银行股份有限公司2024年年度报告.pdf",
        "514010": r"F:\wills\codes\bankdata\new_src_data\pdfs\601939建设银行2024年年度报告.pdf",

    }


    for dir_idx, pass_folders in img_info.items():
        img_path1 = rf"F:\wills\codes\bankdata\new_src_data\pdf2pngs\{dir_idx}"
        img_path2 = rf"F:\wills\codes\bankdata\new_src_data\rotate_pngs\{dir_idx}"
        new_path = rf"F:\wills\codes\bankdata\new_src_data\rejoin_pngs\{dir_idx}"
        save_new_imgs(img_path1, img_path2, new_path)