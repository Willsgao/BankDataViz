import os
from PIL import Image
from pprint import pprint
from pathlib import Path

def concat_images_vertically(img_paths, out_path=None):
    """
    按给定顺序纵向拼接图片
    :param img_paths: List[str]，按顺序排列的图片路径
    :param out_path:  可选，保存路径；为 None 时不保存
    :return: Pillow.Image 对象
    """
    imgs = [Image.open(p) for p in img_paths]

    # 统一用第一张的 mode，宽度取最大
    widths, heights = zip(*(i.size for i in imgs))
    total_height = sum(heights)
    max_width = max(widths)

    new_img = Image.new(imgs[0].mode, (max_width, total_height))

    y_offset = 0
    for im in imgs:
        new_img.paste(im, (0, y_offset))
        y_offset += im.height

    if out_path:
        new_img.save(out_path)
        print("saved ->", out_path)

    return new_img


def re_join_sub_images(ori_path, new_join_save_path=''):
    """将 ori_path 目录下的切片重新拼回整页/整表"""
    file_names = {}
    i = 1

    for root, _, files in os.walk(ori_path):
        for file in files:
            filename = os.path.join(root, file)
            file_names[i] = [file, filename]
            i += 1

    new_join_imgs = []
    cur_imgs = []
    new_dict = {}
    name = file_names[1][0]
    for i, (file, filename) in file_names.items():
        stay_state = 0
        if i + 1 in file_names:
            next_file = file_names[i + 1][0]
            if 'last' in file and '_0_' in next_file:
                pre_idx = int(file.split('_')[1])
                post_idx = int(next_file.split('_')[1])
                if pre_idx+1 == post_idx:
                    stay_state = 1

        if not stay_state:
            cur_imgs.append(filename)
            new_join_imgs.append(cur_imgs)
            if not name:
                name = file
            new_dict[name] = cur_imgs
            cur_imgs = []
            name = ""
        else:

            if not name:
                name = file
            cur_imgs.append(filename)

    if cur_imgs:
        print("cur_imgs:", cur_imgs, name, file)
        new_join_imgs.append(cur_imgs)
        if not name:
            name = file
        new_dict[name] = cur_imgs

    return new_dict


if __name__ == '__main__':
    img_info = {
        # "514001": r"F:\wills\codes\bankdata\new_src_data\pdfs\2024-04-24-1921038.IB-19禾城农商二级01-浙江禾城农村商业银行股份有限公司2023年年度报告.pdf",
        # "514002": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-03-15：平安银行：2024年年度报告.pdf",
        # "514003": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-03-26-600036.SH-招商银行-招商银行股份有限公司2024年度报告.pdf",
        # "514004": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-04-26-601577.SH-长沙银行-601577长沙银行股份有限公司2024年年度报告全文.pdf",
        # "514005": r"F:\wills\codes\bankdata\new_src_data\pdfs\2025-04-29-601838.SH-成都银行-601838成都银行股份有限公司2024年年度报告.pdf",
        # "514006": r"F:\wills\codes\bankdata\new_src_data\pdfs\湖南银行股份有限公司2024年年度报告.pdf",
        "514010": r"F:\wills\codes\bankdata\new_src_data\pdfs\601939建设银行2024年年度报告.pdf",
    }

    import time
    t0 = time.time()
    for dir_idx in img_info:

        ori_path = fr"F:\wills\codes\bankdata\images\joins\{dir_idx}"
        new_join_save_path = fr"F:\wills\codes\bankdata\images\re_sub_imgs\{dir_idx}"
        new_join_save_path = Path(new_join_save_path)
        new_join_save_path.mkdir(parents=True, exist_ok=True)
        new_images = re_join_sub_images(ori_path,  new_join_save_path)


        for name, img_paths in new_images.items():
            outpath = r"{}/{}".format(new_join_save_path, name)
            print("outpath:, outpath", outpath, name)
            concat_images_vertically(img_paths, out_path=outpath)

    t1 = time.time()

    print("t1 - t0:", t1 - t0)







