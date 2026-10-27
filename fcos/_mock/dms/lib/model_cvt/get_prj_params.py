from pathlib import Path
import argparse
import json

import os
import re
import yaml

def get_pth_timestamp(model_path):
    # 获取文件名（不含路径）
    filename = os.path.basename(model_path)
    # 使用正则表达式匹配10位数字或8位数字或6位数字的时间戳
    match_10digit = re.search(r'\d{10}', filename)
    if match_10digit:
        timestamp = match_10digit.group()
    else:
        match_8digit = re.search(r'\d{8}', filename)
        if match_8digit:
            timestamp = match_8digit.group()
        else:
            match_6digit = re.search(r'\d{6}', filename)
            timestamp = match_6digit.group() if match_6digit else ''
    return timestamp

def get_files_in_dir(dir_path, ext='.yml'):
    '''获取目录下所有指定后缀的文件路径列表'''
    return [str(p) for p in Path(dir_path).rglob(f'*{ext}')]

def get_pth_model(model_dir: str, model_tag='latest') -> str:
    '''
    根据模型标签, 获取指定标签的模型路径,模型标签为模型日期,当为latest时,返回最新模型路径
    Args:
        model_dir (str): 模型目录路径
        model_tag (str, optional): 模型标签. Defaults to 'latest'.
    Returns:
        str: 模型路径
    '''
    if not Path(model_dir).exists():
        return ''
    
    model_path_list = sorted(get_files_in_dir(model_dir, ext='.pth'), key=get_pth_timestamp, reverse=True)
    if model_tag == 'latest':
        model_path = model_path_list[0] if model_path_list else ''
    else:
        model_path = next((p for p in model_path_list if model_tag in p), '')
    return model_path

def get_det_classes(prj_path: str) -> list:
    '''
    获取dms项目的检测类别
    Args:
        prj_path (str): dms项目路径
    Returns:
        list: 检测类别列表
    '''
    prj_path = Path(prj_path)
    cfg_file = get_files_in_dir(prj_path / 'config', ext='.yml')[0]

    with open(cfg_file, 'r') as f:
        cfg = yaml.safe_load(f)
    det_class = cfg['MODEL_CONFIG']['OVERRIDE']['DETECTION_CLASSES'][0]
    
    return det_class

def get_prj_params(prj_dir: str, model_tag='latest') -> dict:
    '''
    获取项目参数列表
    Args:
        prj_dir (str): 项目目录路径
        model_tag (str, optional): 模型标签. Defaults to 'latest'.
    Returns:
        dict: 项目参数列表,包括cfg_file,model_resolution,calib_img_dir,model_path,project_name
    '''
    prj_param_dict = {}
    if not Path(prj_dir).exists():
        return prj_param_dict
    
    prj_dir = Path(prj_dir)
    cfg_file = get_files_in_dir(prj_dir / 'config', ext='.yml')[0]
    prj_param_dict['cfg_file'] = cfg_file
    
    with open(cfg_file, 'r') as f:
        cfg = yaml.safe_load(f)
    model_resolution = cfg['MODEL_CONFIG']['OVERRIDE']['EVAL_OUTPUT_SIZE'][0]
    prj_param_dict['model_resolution'] = list(model_resolution)

    calib_img_dir = str(Path(get_files_in_dir(prj_dir / 'mode_convert/calib_imgs', ext='.jpg')[0]).parent)
    prj_param_dict['calib_img_dir'] = calib_img_dir

    model_path = get_pth_model(prj_dir / 'saved_checkpoints', model_tag=model_tag)
    prj_param_dict['model_path'] = model_path

    prj_name = Path(prj_dir).resolve().name
    prj_param_dict['project_name'] = f'{prj_name}_{model_resolution[0]}x{model_resolution[1]}_{get_pth_timestamp(model_path)}'

    return prj_param_dict


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="get project params")
    parser.add_argument("--prj-dir", type=str, required=True, help="project dir")
    parser.add_argument("--model-tag", type=str, default='latest', help="model tag")

    args = parser.parse_args()
    prj_param_dict = get_prj_params(args.prj_dir, model_tag=args.model_tag)
    print(json.dumps(prj_param_dict))

