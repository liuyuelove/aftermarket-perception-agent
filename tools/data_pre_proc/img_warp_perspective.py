'''
@Time: 2025/10/17 11:13:00
@Author: songyufei
@Description:
'''

import argparse
import numpy as np
from tqdm import tqdm
from PIL import Image

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # add lib dir

from tools.lib.file_proc import create_new_folder, join_paths, dump_data_to_json, load_data_from_json, read_file_into_dict_simple
from tools.lib.cv_img_proc import read_img_to_ndarray, Warper
from tools.lib.cnn_result_proc import cnn_result_file_read, gen_cnn_result_filter_index, get_max_bbox
from tools.lib.voc_xml import read_xml_to_dict, write_xml_dict_to_file

def single_img_bbox_warp(img_data_i, bbox_i, owidth, oheight, warp_param_i, warp_points_list_i=None):
    '''
    对单张图片中的目标框进行透视变换
    Args:
        img_data_i: ndarray, [H,W,C]
        bbox_i: list, [x0, y0, x1, y1]
        owidth (int): 输出图片宽度
        oheight (int): 输出图片高度
        warp_param_i: tuple, (x0_coef, y0_coef, width_coef, height_coef)
        warp_points_list_i: list, 待变换点列表，每个元素为(x, y)
    Returns:
        warped_param: list, [x0, y0, x1, y1, owidth, oheight]
        warped_img: ndarray, [H,W,C]
        warped_points: list, 变换后的点列表，每个元素为(x, y)
    '''
    wp = Warper()
    
    x0, y0, x1, y1 = bbox_i
    width_x, width_y = abs(x1 - x0 + 1), abs(y1 - y0 + 1)
    center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
    side_len = max(width_x, width_y)

    x0 = max(0, center_x - side_len * warp_param_i[0])
    y0 = max(0, center_y - side_len * warp_param_i[1])
    x1 = x0 + side_len * warp_param_i[2]
    y1 = y0 + side_len * warp_param_i[3]

    # warp perspective
    src_points = np.float32([
            (x0, y0), (x1, y0),
            (x0, y1), (x1, y1)
        ])

    dst_points = np.float32([
            (0, 0), (owidth-1, 0),
            (0, oheight-1), (owidth-1, oheight-1),
        ])

    wp.set_perspective_transform(src=src_points, dst=dst_points)
    warped_img = wp.warp_img(img_data_i, target_shape=(owidth, oheight)).astype(np.uint8)
    warped_param = [x0, y0, x1, y1, owidth, oheight]

    if warp_points_list_i is not None:
        warped_points = list(wp.warp_points(np.float32(warp_points_list_i)))
        return warped_param, warped_img, warped_points
    else:
        return warped_param, warped_img


def img_warp_perspective(src_img_folder, cnn_result_file_path, owidth, oheight, result_folder, warp_param = (1, 0.5, 2, 2), clr_dst_folder_i=True):
    '''
    透视变换，将src_img_folder中的图片根据cnn检测结果对最大目标进行透视变换，变换后的图片保存到result_folder中
    Args:
        src_img_folder (str): 源图片目录
        cnn_result_file_path (str): cnn结果文件路径
        owidth (int): 输出图片宽度
        oheight (int): 输出图片高度
        result_folder (str): 输出图片目录
        warp_param (tuple): 透视变换参数，默认值为(1, 0.5, 2, 2)
        clr_dst_folder_i (bool): 是否清空result_folder, 若为True, 则清空result_folder, 否则在result_folder基础上进行操作
    Returns:
        None
    '''
    # 判断cnn_result_file是txt文件还是json文件
    if cnn_result_file_path.endswith('.txt'):
        cnn_result_dict = cnn_result_file_read(cnn_result_file_path)
        cnn_result_dict = gen_cnn_result_filter_index(cnn_result_dict, bbox_num = [1, 2, 3], obj_cls = [])
    elif cnn_result_file_path.endswith('.json'):
        cnn_result_dict = load_data_from_json(cnn_result_file_path)
    else:
        raise ValueError('cnn_result_file_path must be txt or json file')

    result_file_path = join_paths([result_folder, 'warp_param.json'])
    create_new_folder(result_folder, delete_exist_i=clr_dst_folder_i)

    warp_parm_dict = cnn_result_dict.copy()
    for img_dir, img_infor in tqdm(cnn_result_dict.items(), desc='img_warp folders'):
        create_new_folder(join_paths([result_folder, img_dir]))
        for image_name, bbox_infor in tqdm(img_infor.items(), desc='files'):
            # read img
            img_data = read_img_to_ndarray(str(join_paths([src_img_folder, img_dir, image_name + '.jpg'])))
            # get max bbox
            max_bbox_infor = get_max_bbox(bbox_infor)
            # cal warp x0,y0,x1,y1
            x0 = float(max_bbox_infor['x0'][0])
            y0 = float(max_bbox_infor['y0'][0])
            x1 = float(max_bbox_infor['x1'][0])
            y1 = float(max_bbox_infor['y1'][0])

            warped_param, warped_img = single_img_bbox_warp(img_data, [x0, y0, x1, y1], owidth, oheight, warp_param)

            # write img
            img_ndarray = warped_img[:,:,::-1]
            image = Image.fromarray(img_ndarray)
            image.save(str(join_paths([result_folder, img_dir, image_name + '.jpg'])))

            # write warp param
            warp_parm_dict[img_dir][image_name] = warped_param
    
    dump_data_to_json(result_file_path, warp_parm_dict)


def img_warp_with_label(src_img_folder, owidth, oheight, result_folder, warp_param = (1, 0.5, 2, 2), warp_class = 'head', src_label_folder=None, clr_dst_folder_i=True):
    '''
    透视变换, 将src_img_folder中的图片根据label_folder中的标签以及warp_class类别进行透视变换, 变换后的图片和标签保存到result_folder中
    Args:
        src_img_folder (str): 源图片目录
        src_label_folder (str): 源标签目录, 若为None, 则与src_img_folder相同
        owidth (int): 输出图片宽度
        oheight (int): 输出图片高度
        result_folder (str): 输出图片和标签目录
        warp_param (tuple): 透视变换参数，默认值为(1, 0.5, 2, 2)
        warp_class (str): 透视变换目标类别，默认值为'head'
        clr_dst_folder_i (bool): 是否清空result_folder, 若为True, 则清空result_folder, 否则在result_folder基础上进行操作
    Returns:
        None
    '''

    create_new_folder(result_folder, delete_exist_i=clr_dst_folder_i)

    if src_label_folder is None:
        src_label_folder = src_img_folder
    files_dict = read_file_into_dict_simple(src_label_folder, '.xml')
    for file_relative_folder, file_name_list in tqdm(files_dict.items()):
        
        result_file_folder = join_paths([result_folder, file_relative_folder])
        create_new_folder(result_file_folder)
        
        for file_name in tqdm(file_name_list):
            
            src_img_path = join_paths([src_img_folder, file_relative_folder, file_name.replace('.xml', '.jpg')])
            img_data = read_img_to_ndarray(str(src_img_path))

            xml_dict = read_xml_to_dict(join_paths([src_label_folder, file_relative_folder, file_name]))
            obj_dict = xml_dict['annotation']['object']
            warp_bbox_list = []
            warp_points_list = []
            for obj in obj_dict:
                if obj['name'] == warp_class:
                    warp_bbox_list.append([float(obj['bndbox']['xmin']), float(obj['bndbox']['ymin']), float(obj['bndbox']['xmax']), float(obj['bndbox']['ymax'])])
                else:
                    warp_points_list.append([float(obj['bndbox']['xmin']), float(obj['bndbox']['ymin']), float(obj['bndbox']['xmax']), float(obj['bndbox']['ymax'])])

            if len(warp_bbox_list) == 0:
                continue
            
            if len(warp_bbox_list) == 1:
                bbox = warp_bbox_list[0]
            else:
                # 计算warp_bbox_list中面积最大的bbox
                max_area = 0
                for bbox in warp_bbox_list:
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    if area > max_area:
                        max_area = area
                        max_bbox = bbox
                bbox = max_bbox
            
            warp_points_list += warp_bbox_list
            warp_points_list = np.array(warp_points_list).reshape(-1, 2)

            _, warped_img, warped_points = single_img_bbox_warp(img_data, bbox, owidth, oheight, warp_param, warp_points_list_i=warp_points_list)
            warped_points = list(np.array(warped_points).reshape(-1, 4))
            for obj in obj_dict:
                if obj['name'] == warp_class:
                    warped_point = warped_points.pop(-1)
                else:
                    warped_point = warped_points.pop(0)
                
                x_min = max(0, warped_point[0])
                y_min = max(0, warped_point[1])
                x_max = min(owidth, warped_point[2])
                y_max = min(oheight, warped_point[3])
                if x_min >= x_max or y_min >= y_max:
                    del obj
                else:
                    obj['bndbox']['xmin'] = str(x_min)
                    obj['bndbox']['ymin'] = str(y_min)
                    obj['bndbox']['xmax'] = str(x_max)
                    obj['bndbox']['ymax'] = str(y_max)
            
            if 'size' in xml_dict['annotation']:
                xml_dict['annotation']['size']['width'] = str(owidth)
                xml_dict['annotation']['size']['height'] = str(oheight)

            # write img
            img_ndarray = warped_img[:,:,::-1]
            image = Image.fromarray(img_ndarray)
            image.save(str(join_paths([result_file_folder, file_name.replace('.xml', '.jpg')])))
            # write label
            write_xml_dict_to_file(xml_dict, join_paths([result_file_folder, file_name]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='extract video frames')
    parser.add_argument('-sf', '--src_folder', type=str, default='data/src_imgs/', help='src imgs folder path')
    parser.add_argument('-of', '--output_folder', type=str, default='data/result_imgs/', help='output result imgs folder path')
    parser.add_argument('-cst', '--cnn_rslt_txt', type=str, default='', help='cnn result txt file path')
    parser.add_argument('-ow', '--oimg_width', type=int, default=720, help='output img width')
    parser.add_argument('-oh', '--oimg_height', type=int, default=720, help='output img height')
    parser.add_argument('-wp', '--warp_param', type=float, nargs=4, default=(1, 0.5, 2, 2), help='warp param')

    args = parser.parse_args()
    img_warp_perspective(args.src_folder, args.cnn_rslt_txt, args.oimg_width, args.oimg_height, args.output_folder, args.warp_param, clr_dst_folder_i=True)

    # img_warp_with_lable(src_img_folder='/mnt/fpga/songyufei/work/git/aftermarket-perception-agent/test_img', owidth=288, oheight=288, result_folder='/mnt/fpga/songyufei/work/git/aftermarket-perception-agent/test_img_warpped', warp_param=(1, 0.5, 2, 2), warp_class='head')