'''
@Time: 2025/10/21 15:06:00
@Author: songyufei
@Description:
'''

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.lib.cv_img_proc import img_resize, img_crop_with_expand, read_img_to_ndarray
from tools.lib.file_proc import create_new_folder, read_file_into_dict_simple
from tools.lib.voc_xml import xml_crop_resize

from tqdm import tqdm
from typing import Union
import numpy as np
from PIL import Image

def img_crop_resize(img_i : Union[str, np.ndarray], crop_param_i : tuple = None, resize_resolution_i : tuple = None, save_path_i : str = None, with_param_out_i : bool = False) -> np.ndarray:
    '''
    img_crop_resize
    
    :param img_i: 输入图像, 若是str, 则为图像路径, 若是ndarray, 则为图像数据
    :param crop_param_i: 裁剪参数 (x0, y0, crop_w, crop_h), 若为None, 则不进行裁剪
    :param resize_resolution_i: resize图像分辨率 (width, height), 若为None, 则不进行缩放
    :param save_path_i: 输出图像保存路径, 若为None, 则不保存
    :param with_param_out_i: 是否返回裁剪和缩放参数, 若为True, 则返回裁剪和缩放参数
    :return: 输出图像数据, 若with_param_out_i为True, 则同时返回裁剪和缩放参数
    '''
    if isinstance(img_i, str):
        img_data = read_img_to_ndarray(img_i)
    elif isinstance(img_i, np.ndarray):
        img_data = img_i
    else:
        raise ValueError("img_i must be str or ndarray")
    
    if crop_param_i is not None:
        img_data, crop_param = img_crop_with_expand(img_data, crop_param_i, with_param_out_i=True)
    else:
        crop_param = (0, 0, img_data.shape[1], img_data.shape[0])

    if resize_resolution_i is not None:
        img_data, resize_param = img_resize(img_data, resize_resolution_i, with_param_out_i=True)
    else:
        resize_param = (1, 1)

    if save_path_i is not None:
        # write img
        img_ndarray = img_data[:,:,::-1]
        image = Image.fromarray(img_ndarray)
        image.save(save_path_i)
    
    if with_param_out_i:
        return img_data, (crop_param, resize_param)
    else:
        return img_data

def folder_img_crop_resize(src_img_folder : str, dst_img_folder : str, crop_param_i : tuple = None, resize_resolution_i : tuple = None, with_label_i = False, clr_dst_folder_i : bool = True):
    '''
    folder_img_crop_resize
    
    :param src_img_folder: 源图像文件夹
    :param dst_img_folder: 输出图像文件夹
    :param crop_param_i: 裁剪参数 (x0, y0, crop_w, crop_h), 若为None, 则不进行裁剪
    :param resize_resolution_i: 输出图像分辨率 (width, height), 若为None, 则不进行缩放
    :param with_label_i: 是否包含xml标签文件, 若为True, 则根据裁剪参数和缩放参数处理标签文件
    :param clr_dst_folder_i: 是否清空dst_img_folder, 若为True, 则清空dst_img_folder, 否则在dst_img_folder基础上进行操作
    '''
    create_new_folder(dst_img_folder, delete_exist_i=clr_dst_folder_i)
    img_path_dict = read_file_into_dict_simple(src_img_folder, file_suffix_i='.jpg')
    for img_dir, img_name_list in tqdm(img_path_dict.items(), desc='img_crop_resize folders'):
        create_new_folder(os.path.join(dst_img_folder, img_dir))
        for img_name in tqdm(img_name_list, desc='files'):
            img_path = os.path.join(src_img_folder, img_dir, img_name)
            dst_img_path = os.path.join(dst_img_folder, img_dir, img_name)
            img_data, (crop_param, resize_param) = img_crop_resize(img_path, crop_param_i, resize_resolution_i, dst_img_path, with_param_out_i=True)
            
            if with_label_i:
                xml_path = os.path.join(src_img_folder, img_dir, img_name.replace('.jpg', '.xml'))
                dst_xml_path = os.path.join(dst_img_folder, img_dir, img_name.replace('.jpg', '.xml'))
                if os.path.exists(xml_path):
                    xml_crop_resize(xml_path, crop_param, resize_resolution_i, dst_xml_path)
    
    return True

if __name__ == '__main__':
    img_folder = '/mnt/fpga/songyufei/work/git/aftermarket-perception-agent/images'
    folder_img_crop_resize(img_folder, img_folder+'_resize', resize_resolution_i=(640, 360))
    