from pathlib import Path
from collections import OrderedDict
import shutil
import json
import os

def join_paths(path_parts_i, path_type_i='str'):
    """
    将给定的路径部分列表拼接为一个完整的路径。
    
    param:
        path_parts_i (list of str): 包含路径各个部分的列表。
        path_type_i: 'str' or 'os'
    return:
        Path: 拼接后的完整路径。
    """
    # 使用 Path() 和 / 操作符来拼接路径部分
    full_path = Path(*path_parts_i)
    if path_type_i == 'str':
        full_path = str(full_path)
    return full_path


# 删除指定文件
def delete_file(file_path_i):
    path = Path(file_path_i)
    if path.is_file():
        path.unlink()


# 删除指定目录
def delete_folder(folder_path_i):
    path = Path(folder_path_i)
    if path.exists():
        [p.unlink() if p.is_file() else None for p in path.rglob('*')]
        [p.rmdir() for p in path.rglob('*')]
        path.rmdir()


def delete_directory(directory_path_i):
    """
    删除给定路径的目录及其所有子文件夹和文件。
    
    参数:
        directory_path_i (str 或 Path): 要删除的目录路径。
        
    返回:
        None
    """
    path = Path(directory_path_i)

    if not path.exists():
        print(f"Error: Directory '{directory_path_i}' does not exist.")
        return
    
    if not path.is_dir():
        print(f"Error: Path '{directory_path_i}' is not a directory.")
        return
    
    try:
        shutil.rmtree(path)
        # print(f"Successfully deleted directory and all its contents: {directory_path_i}")
    except OSError as e:
        print(f"Error: Failed to delete directory '{directory_path_i}'. Reason: {e}")


def delete_target_folders(root_dir_i, folder_name_i):
    """
    删除指定目录及其子目录下所有名为 folder_name_i 的文件夹。

    :param root_dir_i: 要搜索的根目录
    :param folder_name_i: 要删除的文件夹名称
    """
    for dirpath, dirnames, filenames in os.walk(root_dir_i, topdown=False):
        for dirname in dirnames:
            if dirname == folder_name_i:
                full_path = os.path.join(dirpath, dirname)
                try:
                    shutil.rmtree(full_path)
                    print(f"Deleted: {full_path}")
                except Exception as e:
                    print(f"Failed to delete {full_path}: {e}")

def is_path_exist(path_i):
    """
    检查给定路径是否存在。

    :param path_i: 文件或文件夹路径
    :return: 如果路径存在，返回 True; 否则返回 False
    """
    path = Path(path_i)
    return path.exists()


# 创建新目录，如果目录存在，目录将被删除后重新创建
def create_new_folder(folder_path_i, delete_exist_i=True):
    if isinstance(folder_path_i, list):
        folder_path_list = folder_path_i
    else:
        folder_path_list = [folder_path_i]
    for folder_path in folder_path_list:
        path = Path(folder_path)
        if delete_exist_i and path.exists():
            delete_directory(path)
        path.mkdir(parents=True, exist_ok=True)


# 删除目录下的指定后缀名文件
# file_suffix_i: str('.jpg') or list(['.jpg',])
def delete_files_in_folder(folder_path_i, file_suffix_i='.jpg'):
    path = Path(folder_path_i)
    if path.exists():
        if isinstance(file_suffix_i, list):
            file_suffix_list = file_suffix_i
        else:
            file_suffix_list = [file_suffix_i]
        for suffix in file_suffix_list:
            [p.unlink() if p.is_file() else None for p in path.rglob('*' + suffix)]


def get_abs_path(path_i):
    """
    获取绝对路径。

    :param path_i: 文件或文件夹路径
    :return: 绝对路径
    """
    path = Path(path_i)
    return path.resolve()


def get_relative_path(parent_path_i, child_path_i):
    """
    获取子目录相对于父目录的相对路径。

    :param parent_path_i: 父目录路径
    :param child_path_i: 子目录路径
    :return: 相对对路径
    """
    parent_path = Path(parent_path_i)
    child_path = Path(child_path_i)
    return child_path.relative_to(parent_path)


def get_parent(path_i, path_type_i='str'):
    """
    获取文件或文件夹父目录。

    :param
        path_i: 文件或文件夹路径
        path_type_i: 'str' or 'os
    :return: 父目录
    """
    path = Path(path_i)
    parent = path.parent
    if path_type_i == 'str':
        parent = str(parent)
    return parent


def get_file_name(file_path_i, with_suffix_i=False):
    """
    获取文件名。

    :param file_path_i: 文件路径
    :param with_suffix_i: 输出文件名是否带后缀
    :return: 文件名
    """
    path = Path(file_path_i)
    if with_suffix_i:
        return path.name
    else:
        return path.stem

def change_file_suffix(file_path_i, new_suffix_i):
    '''
    修改文件后缀
    :param file_path_i: 文件路径
    :param new_suffix_i: 新后缀
    :return: 新文件路径
    '''
    path = Path(file_path_i)
    new_path = path.with_suffix(new_suffix_i)
    return str(new_path)


# 返回文件路径列表
# abs_path_i: bool, 是否返回绝对路径
# path_type_i: 'str' or 'os
# return: [relative_path/file_name1, relative_path/file_name2...](abs_path_i==False)
def read_file_into_list(folder_path_i, file_suffix_i='.jpg', abs_path_i=False, path_type_i='str'):
    path = Path(folder_path_i)
    file_list = []
    if isinstance(file_suffix_i, list):
        file_suffix_list = file_suffix_i
    else:
        file_suffix_list = [file_suffix_i]
    for suffix in file_suffix_list:
        for p in path.rglob('*' + suffix):
            if abs_path_i:
                if path_type_i == 'str':
                    file_list.append(str(p))
                else:
                    file_list.append(p)
            else:
                relative_path = p.parent.relative_to(path)
                if path_type_i == 'str':
                    file_list.append(str(relative_path.joinpath(p.name)))
                else:
                    file_list.append(relative_path.joinpath(p.name))
    return file_list


# dict{file_folder: [file_name]}
# path_type_i: 'str' or 'os
def read_file_into_dict_simple(folder_path_i, file_suffix_i='.jpg', abs_path_i=False, path_type_i='str'):
    file_dict = OrderedDict()
    path = Path(folder_path_i)
    if isinstance(file_suffix_i, list):
        file_suffix_list = file_suffix_i
    else:
        file_suffix_list = [file_suffix_i]
    for suffix in file_suffix_list:
        for p in path.rglob('*' + suffix):
            if p.is_file():
                if abs_path_i:
                    file_folder = p.parent
                else:
                    file_folder = p.parent.relative_to(path)
                
                if path_type_i == 'str':
                    file_folder = str(file_folder)
                
                if file_folder not in file_dict.keys():
                    file_dict[file_folder] = []
                file_dict[file_folder].append(p.name)
    return file_dict


# dict{folder1: {folder2: {file_name: file_full_path}}}
def read_file_into_dict(folder_path_i):
    file_dict = OrderedDict()
    folder_path = Path(folder_path_i)
    for p in folder_path.glob('*'):
        relative_p = str(p.relative_to(folder_path))
        if p.is_dir():
            if relative_p not in file_dict.keys():
                file_dict[relative_p] = OrderedDict()
            file_dict[relative_p] = read_file_into_dict(p)
        elif p.is_file():
            file_dict[relative_p] = str(p)
    return file_dict


def dump_data_to_json(json_file_path_i, data_i):
    json_str = json.dumps(data_i, indent=4)
    with open(json_file_path_i, 'w') as f_obj:
        f_obj.write(json_str)


def load_data_from_json(json_file_path_i):
    with open(json_file_path_i) as f_obj:
        json_str = f_obj.read()
    return json.loads(json_str, object_pairs_hook=OrderedDict)


def read_file_to_str_list(file_path_i):
    """
    将文件内容保存为str列表, 每行为一个元素

    :param file_path_i: 要打开的文件路径
    """
    with open(file_path_i) as f_obj:
        lines = f_obj.readlines()
    return [line.strip() for line in lines]


def write_str_list_to_file(file_path_i, str_list_i, mode_i='w'):
    """
    将str list写入文件, 每个list元素一行

    :param file_path_i: 要打开的文件路径
    :param str_list_i: 要写入的str list
    :param mode_i: 文件打开模式
    """
    with open(file_path_i, mode_i) as f_obj:
        f_obj.write('\n'.join(str_list_i))


def file_copy(src_path_i, dest_path_i):
    """
    将文件从src_path_i拷贝到dest_path_i

    :param src_path_i: 源文件路径
    :param dest_path_i: 目的文件路径
    """
    shutil.copy(src_path_i, dest_path_i)

def folder_copy(src_path_i, dest_path_i):
    """
    将文件夹从src_path_i拷贝到dest_path_i

    :param src_path_i: 源文件夹路径
    :param dest_path_i: 目的文件夹路径
    """
    shutil.copytree(src_path_i, dest_path_i, dirs_exist_ok=True)