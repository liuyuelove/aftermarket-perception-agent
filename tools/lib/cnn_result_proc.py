from pathlib import Path
from collections import OrderedDict
import numpy as np
import json

from .voc_xml import xml_file_gen

# {image_folder: {image_name: {'bbox_num': bbox_num, 'class': [], 'x0': [], 'y0': [], 'x1': [], 'y1': [], 'score': []}}}
def cnn_result_file_read(file_path_i):
    cnn_result = OrderedDict()
    with open(file_path_i) as f_obj:
        for line in f_obj.readlines():
            line_split_list = line.split()
            
            img_dir = line_split_list[0]
            if '/' in img_dir:
                img_folder, img_name = img_dir.rsplit('/', 1)
            else:
                img_folder = '.'
                img_name = img_dir
            if img_folder not in cnn_result.keys():
                cnn_result[img_folder] = OrderedDict()
            
            bbox_num = int(line_split_list[1])
            bbox_infor = OrderedDict()
            bbox_infor['bbox_num'] = bbox_num
            bbox_infor['class'] = []
            bbox_infor['x0'] = []
            bbox_infor['y0'] = []
            bbox_infor['x1'] = []
            bbox_infor['y1'] = []
            bbox_infor['score'] = []
            for bbox_id in range(bbox_num):
                bbox_infor['class'].append(line_split_list[bbox_id*6 + 2])
                bbox_infor['x0'].append(line_split_list[bbox_id*6 + 3])
                bbox_infor['y0'].append(line_split_list[bbox_id*6 + 4])
                bbox_infor['x1'].append(line_split_list[bbox_id*6 + 5])
                bbox_infor['y1'].append(line_split_list[bbox_id*6 + 6])
                bbox_infor['score'].append(line_split_list[bbox_id*6 + 7])
                
            cnn_result[img_folder][img_name] = bbox_infor.copy()
    
    return cnn_result

# {img_folder: {img_name: bbox_infor}}
def gen_cnn_result_filter_index(cnn_result, bbox_num = [], obj_cls = []):
    filter_index = OrderedDict()
    for img_folder, img_infor in cnn_result.items():
        filter_index[img_folder] = OrderedDict()
        for img_name, bbox_infor in img_infor.items():
            if((bbox_infor['bbox_num'] in bbox_num) or (set(bbox_infor['class']) & set(obj_cls))):
                filter_index[img_folder][img_name] = bbox_infor.copy()
    return filter_index


def get_max_bbox(bbox_infor_i):
    '''
    获取最大的bbox
    :param bbox_infor: bbox_infor
    :return: max_bbox_infor
    '''
    bbox_num = bbox_infor_i['bbox_num']
    if bbox_num <= 1:
        return bbox_infor_i
    
    max_bbox_infor = OrderedDict()
    max_bbox_infor['bbox_num'] = [1]
    max_bbox_infor['class'] = []
    max_bbox_infor['x0'] = []
    max_bbox_infor['y0'] = []
    max_bbox_infor['x1'] = []
    max_bbox_infor['y1'] = []
    max_bbox_infor['score'] = []
    x0 = np.array(bbox_infor_i['x0'], dtype=float)
    y0 = np.array(bbox_infor_i['y0'], dtype=float)
    x1 = np.array(bbox_infor_i['x1'], dtype=float)
    y1 = np.array(bbox_infor_i['y1'], dtype=float)
    area = (x1 - x0) * (y1 - y0)
    max_area_index = np.argmax(area)
    max_bbox_infor['class'].append(bbox_infor_i['class'][max_area_index])
    max_bbox_infor['x0'].append(bbox_infor_i['x0'][max_area_index])
    max_bbox_infor['y0'].append(bbox_infor_i['y0'][max_area_index])
    max_bbox_infor['x1'].append(bbox_infor_i['x1'][max_area_index])
    max_bbox_infor['y1'].append(bbox_infor_i['y1'][max_area_index])
    max_bbox_infor['score'].append(bbox_infor_i['score'][max_area_index])
    return max_bbox_infor

def filter_cnn_result(cnn_result, bbox_num = [], obj_cls = [], get_max_box=False):
    '''
    根据条件过滤cnn结果, get_max_box=True时, 只保留最大的bbox, 否则保留满足bbox_num或obj_cls的bbox
    params:
        cnn_result: cnn_result txt file path or dict, {img_folder: {img_name: bbox_infor}}
        bbox_num: [int], bbox num filter
        obj_cls: [], obj class filter
        get_max_bbox: bool, if True, only keep the max bbox
    '''
    if isinstance(cnn_result, str):
        cnn_result_dict = cnn_result_file_read(cnn_result)
    else:
        cnn_result_dict = cnn_result

    filtered_result = OrderedDict()
    for img_folder, img_infor in cnn_result_dict.items():
        filtered_result[img_folder] = OrderedDict()
        for img_name, bbox_infor in img_infor.items():
            if get_max_box:
                filtered_result[img_folder][img_name] = get_max_bbox(bbox_infor)
            elif((bbox_infor['bbox_num'] in bbox_num) or (set(bbox_infor['class']) & set(obj_cls))):
                filtered_result[img_folder][img_name] = bbox_infor.copy()
    return filtered_result


def bbox_remap(bbox_dict_i, det_class_list_i=None, src_resolution_i=(1280, 720), src_crop_param_i=None, src_resize_i=None, src_warp_dict_i=None, mode_i='dst2src'):
    '''
    将bbox映射到另一张图上
    param:
        bbox_dict_i: {image_folder: {image_name: {'bbox_num': bbox_num, 'class': [], 'x0': [], 'y0': [], 'x1': [], 'y1': [], 'score': []}}}
        det_class_list_i: ['look_down', 'eye_close', 'normal'], corresponding to class
        src_resolution_i: src img resolution, (W, H)
        src_crop_param_i: src img crop param, (x0, y0, width, height), valid when src_warp_dict_i is None
        src_resize_i: resize coef after crop, (width, height)
        src_warp_dict_i: src img warp param dict, {img_dir: {img_name: [crop_x0, crop_y0, crop_x1, crop_y1, owidth, oheight]}}
        mode_i: 'src2dst'(bbox_dict_i is src) or 'dst2src'(bbox_dict_i is dst)
    '''
    if src_crop_param_i is None:
        src_crop = (0, 0, src_resolution_i[0], src_resolution_i[1])
    else:
        src_crop = src_crop_param_i
    
    if src_resize_i is None:
        dst2src_resize_coef = (1, 1)
    else:
        dst2src_resize_coef = np.array(src_crop[2:4]) / np.array(src_resize_i)
    
    bbox_dict = bbox_dict_i.copy()
    for img_folder, img_infor in bbox_dict.items():
        for img_name, bbox_infor in img_infor.items():
            if det_class_list_i is not None:
                bbox_dict[img_folder][img_name]['class'] = [det_class_list_i[int(i)] for i in bbox_infor['class']]
            
            if src_warp_dict_i is not None:
                crop_x0, crop_y0, crop_x1, crop_y1, warp_owidth, warp_oheight = src_warp_dict_i[img_folder][img_name]
                src_crop = (crop_x0, crop_y0, crop_x1 - crop_x0 + 1, crop_y1 - crop_y0 + 1)
                
                if src_resize_i is None:
                    dst2src_resize_coef = np.array(src_crop[2:4]) / np.array([warp_owidth, warp_oheight])
                else:
                    dst2src_resize_coef = np.array(src_crop[2:4]) / np.array(src_resize_i)

            if mode_i == 'src2dst':
                bbox_dict[img_folder][img_name]['x0'] = list((np.array(bbox_infor['x0'], dtype=float) - src_crop[0]) / dst2src_resize_coef[0])
                bbox_dict[img_folder][img_name]['y0'] = list((np.array(bbox_infor['y0'], dtype=float) - src_crop[1]) / dst2src_resize_coef[1])
                bbox_dict[img_folder][img_name]['x1'] = list((np.array(bbox_infor['x1'], dtype=float) - src_crop[0]) / dst2src_resize_coef[0])
                bbox_dict[img_folder][img_name]['y1'] = list((np.array(bbox_infor['y1'], dtype=float) - src_crop[1]) / dst2src_resize_coef[1])
            else:
                bbox_dict[img_folder][img_name]['x0'] = list(np.array(bbox_infor['x0'], dtype=float) * dst2src_resize_coef[0] + src_crop[0])
                bbox_dict[img_folder][img_name]['y0'] = list(np.array(bbox_infor['y0'], dtype=float) * dst2src_resize_coef[1] + src_crop[1])
                bbox_dict[img_folder][img_name]['x1'] = list(np.array(bbox_infor['x1'], dtype=float) * dst2src_resize_coef[0] + src_crop[0])
                bbox_dict[img_folder][img_name]['y1'] = list(np.array(bbox_infor['y1'], dtype=float) * dst2src_resize_coef[1] + src_crop[1])
            
    return bbox_dict

def bbox_dict_merge(bbox_dict_list_i):
    '''
    合并多个bbox_dict
    param:
        bbox_dict_list_i: [bbox_dict1, bbox_dict2, ...]
    return:
        bbox_dict: 合并后的bbox_dict
    '''
    bbox_dict = OrderedDict()
    for bbox_dict_i in bbox_dict_list_i:
        for img_folder, img_infor in bbox_dict_i.items():
            if img_folder not in bbox_dict:
                bbox_dict[img_folder] = OrderedDict()
                bbox_dict[img_folder].update(img_infor)
            else:
                for img_name, bbox_infor in img_infor.items():
                    if img_name not in bbox_dict[img_folder]:
                        bbox_dict[img_folder][img_name] = bbox_infor.copy()
                    else:
                        bbox_dict[img_folder][img_name]['bbox_num'] += bbox_infor['bbox_num']
                        bbox_dict[img_folder][img_name]['class'].extend(bbox_infor['class'])
                        bbox_dict[img_folder][img_name]['x0'].extend(bbox_infor['x0'])
                        bbox_dict[img_folder][img_name]['y0'].extend(bbox_infor['y0'])
                        bbox_dict[img_folder][img_name]['x1'].extend(bbox_infor['x1'])
                        bbox_dict[img_folder][img_name]['y1'].extend(bbox_infor['y1'])
                        bbox_dict[img_folder][img_name]['score'].extend(bbox_infor['score'])
    return bbox_dict

def gen_xml_with_bbox_dict(bbox_dict_i, xml_dir_i, det_class_list_i=None, img_shape_i=(3, 720, 1280)):
    '''
    根据bbox_dict生成xml文件, 并返回对应的obj_dict
    param:
        bbox_dict_i: str or dict, dict: {image_folder: {image_name: {'bbox_num': bbox_num, 'class': [], 'x0': [], 'y0': [], 'x1': [], 'y1': [], 'score': []}}}
        xml_dir_i: xml文件保存目录
        det_class_list_i: ['look_down', 'eye_close', 'normal'], corresponding to class
        img_shape_i: (C, H, W)
    return:
        obj_dict: {image_folder: {image_name: {obj_name: {'bbox': [[x_min, y_min, x_max, y_max],]}}}}
    '''
    if isinstance(bbox_dict_i, str):
        with open(bbox_dict_i, 'r', encoding='utf-8') as fp:
            bbox_dict = json.load(fp)
    else:
        bbox_dict = bbox_dict_i
    obj_dict = OrderedDict()
    for img_folder, img_infor in bbox_dict.items():
        obj_dict[img_folder] = OrderedDict()
        xml_dir = Path(xml_dir_i) / img_folder
        if not xml_dir.exists():
            xml_dir.mkdir(parents=True)
        for img_name, bbox_infor in img_infor.items():
            obj_dict[img_folder][img_name] = OrderedDict()
            for i in range(bbox_infor['bbox_num']):
                if det_class_list_i is not None:
                    obj_name = det_class_list_i[int(bbox_infor['class'][i])]
                else:
                    obj_name = bbox_infor['class'][i]
                bbox = [bbox_infor['x0'][i], bbox_infor['y0'][i], bbox_infor['x1'][i], bbox_infor['y1'][i]]
                if obj_name not in obj_dict[img_folder][img_name]:
                    obj_dict[img_folder][img_name][obj_name] = {'bbox': []}
                obj_dict[img_folder][img_name][obj_name]['bbox'].append(bbox)
            
            xml_file_gen(obj_dict[img_folder][img_name], xml_dir / f'{img_name}.xml', img_shape_i=img_shape_i)
    
    return obj_dict