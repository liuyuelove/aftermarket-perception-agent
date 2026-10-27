'''
@Time: 2025/12/25 17:02:00
@Author: songyufei
@Description: 可视化相关库
'''
from PIL import Image
from tqdm import tqdm

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.lib.cv_img_proc import img_add_text, img_draw_rectangle, read_img_to_ndarray
from tools.lib.file_proc import read_file_into_dict_simple, create_new_folder, join_paths
from tools.lib.voc_xml import read_xml_to_obj_dict


def print_color(text, color="white"):

    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bold_red": "\033[1;31m",
    }
    reset = "\033[0m"
    print(f"{colors.get(color, '')}{text}{reset}")


def draw_bbox_on_img(img_i, bbox_dict_i, color_i=(0, 0, 255), thickness_i=2):
    '''
    在图像上绘制边界框

    Args:
        img_i: ndarray, [H,W,C]
        bbox_dict_i: dict, {obj_name: {'bbox': [[x_min, y_min, x_max, y_max],]}}
        color_i: (B, G, R)
        thickness_i: int, 线条粗细
    Returns: ndarray, [H,W,C]
    '''

    img_out = img_i.copy()
    for class_name, bbox_dict in bbox_dict_i.items():
        for bbox in bbox_dict['bbox']:
            top_left = (int(bbox[0]), int(bbox[1]))
            bottom_right = (int(bbox[2]), int(bbox[3]))
            img_out = img_draw_rectangle(img_out, top_left, bottom_right, color_i, thickness_i)
            img_out = img_add_text(img_out, class_name, (top_left[0], max(top_left[1] - 5, 0)), font_scale_i=1.0, color_i=color_i, thickness_i=thickness_i)
    
    return img_out

def draw_bbox_with_xml(img_dir_i, result_dir_i, xml_dir_i=None, color_i=(0, 0, 255), thickness_i=2):
    '''
    在图像上绘制XML文件中的边界框

    Args:
        img_dir_i: str, 图像目录路径
        result_dir_i: str, 结果保存目录路径
        xml_dir_i: str, XML文件目录路径
        color_i: (B, G, R)
        thickness_i: int, 线条粗细
    '''
    if xml_dir_i is None:
        xml_dir_i = img_dir_i
    
    create_new_folder(result_dir_i)
    img_dict = read_file_into_dict_simple(img_dir_i, file_suffix_i='.jpg')
    for img_folder, img_file_list in tqdm(img_dict.items(), desc='draw_bbox_with_xml folders'):
        create_new_folder(join_paths([result_dir_i, img_folder]), delete_exist_i=False)
        for img_file in tqdm(img_file_list, desc=f'draw_bbox_with_xml files'):
            img_path = join_paths([img_dir_i, img_folder, img_file])
            xml_path = join_paths([xml_dir_i, img_folder, img_file.replace('.jpg', '.xml')])
            img_out_path = join_paths([result_dir_i, img_folder, img_file])

            img_data = read_img_to_ndarray(img_path)
            if os.path.exists(xml_path):
                obj_dict = read_xml_to_obj_dict(xml_path)[0]
                img_data = draw_bbox_on_img(img_data, obj_dict, color_i, thickness_i)
            
            # write image
            image = Image.fromarray(img_data[:,:,::-1])
            image.save(img_out_path)
