import os
import zipfile
import subprocess
from tqdm import tqdm

# rarfile / py7zr 在函数内按需导入：
# 它们是可选依赖（还要配 unrar/7z 命令行），不该在 import 图的时候就把进程拦下来。

def extract_rar(rar_path : str, extract_to : str = None):
    """
    解压RAR压缩包
    :param rar_path: RAR文件的路径
    :param extract_to: 解压目标目录，如果为None，则解压到当前目录下的同名文件夹
    """
    # 确保rarfile能正确处理中文
    import rarfile

    rarfile.NATIVE_EXTENSIONS = False  # 使用Python内置编码处理（通常更兼容）
    
    try:
        # # 检查是否安装了unrar或unar工具
        # def check_tool(tool_name):
        #     try:
        #         subprocess.run([tool_name, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        #         return True
        #     except (subprocess.SubprocessError, FileNotFoundError):
        #         return False
        
        # # 尝试安装unrar（Ubuntu/Debian系统）
        # if not check_tool('unrar') and not check_tool('unar'):
        #     print("未找到RAR解压工具(unrar或unar)。正在尝试安装unrar...")
        #     try:
        #         subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        #         subprocess.run(['sudo', 'apt-get', 'install', '-y', 'unrar'], check=True)
        #         print("unrar安装成功！")
        #     except subprocess.SubprocessError:
        #         print("错误：无法自动安装unrar工具。请手动安装：sudo apt-get install unrar 或 sudo apt-get install unar")
        #         return
        
        # 打开RAR文件
        with rarfile.RarFile(rar_path) as rf:
            # 获取所有文件列表（会正确显示中文名）
            file_list = rf.namelist()
            print("压缩包内文件列表：")
            for filename in file_list:
                print(f"  - {filename}")
            
            # 设置解压目录
            if extract_to is None:
                # 默认解压到以RAR文件名命名的文件夹
                extract_to = os.path.splitext(rar_path)[0]
            # 创建解压目录
            os.makedirs(extract_to, exist_ok=True)
            
            # 解压所有文件
            rf.extractall(path=extract_to)
            # print(f"\n解压成功！文件已解压到：{extract_to}")
            
    except rarfile.BadRarFile:
        print("错误：文件不是有效的RAR格式或已损坏。")
    except FileNotFoundError:
        print(f"错误：未找到RAR文件：{rar_path}")
    except Exception as e:
        print(f"解压过程中发生未知错误：{e}")
        print("提示：请确保已安装unrar或unar工具，Ubuntu可以通过以下命令安装：")
        print("sudo apt-get install unrar 或 sudo apt-get install unar")

def extract_zip(zip_path : str, extract_to : str = None):
    """
    解压zip压缩包
    :param zip_path: zip文件的路径
    :param extract_to: 解压目标目录，如果为None，则解压到当前目录下的同名文件夹
    """
    try:
        # 确保zipfile能正确处理中文
        with zipfile.ZipFile(zip_path, 'r') as z:
            # 获取所有文件列表
            file_list = z.namelist()
            print("压缩包内文件列表：")
            for filename in file_list:
                print(f"  - {filename}")
            
            # 设置解压目录
            if extract_to is None:
                # 默认解压到以zip文件名命名的文件夹
                extract_to = os.path.splitext(zip_path)[0]
            
            # 创建解压目录
            os.makedirs(extract_to, exist_ok=True)
            
            # 解压所有文件，处理中文文件名
            for file in file_list:
                # 如果file是目录，则直接跳过
                if file.endswith('/') or file.endswith('\\'):
                    continue
                try:
                    # 获取正确的文件名编码

                    try:
                        # 尝试使用UTF-8解码
                        decoded_file = file.encode('cp437').decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            # 尝试使用GBK解码
                            decoded_file = file.encode('cp437').decode('gbk')
                        except UnicodeDecodeError:
                            # 如果都失败，使用原始文件名
                            decoded_file = file
                    
                    extracted_path = os.path.join(extract_to, decoded_file)
                    
                    # 确保目录存在
                    extracted_dir = os.path.dirname(extracted_path)
                    if extracted_dir and not os.path.exists(extracted_dir):
                        try:
                            os.makedirs(extracted_dir, exist_ok=True)
                        except PermissionError:
                            print(f"警告：无法创建目录 {extracted_dir}，可能是权限问题")
                            continue

                    # 写入文件内容
                    try:
                        with z.open(file, 'r') as source, open(extracted_path, 'wb') as target:
                            target.write(source.read())
                    except PermissionError:
                        print(f"警告：无法写入文件 {extracted_path}，可能是权限问题")
                        continue
                except Exception as e:
                    print(f"解压文件 {file} 时出错：{e}")
                    continue
            # print(f"\n解压成功！文件已解压到：{extract_to}")
    except FileNotFoundError:
        print(f"错误：未找到zip文件：{zip_path}")
    except Exception as e:
        print(f"解压过程中发生未知错误：{e}")


def extract_7z(sevenz_path : str, extract_to : str = None):
    """
    解压7z压缩包
    :param sevenz_path: 7z文件的路径
    :param extract_to: 解压目标目录，如果为None，则解压到当前目录下的同名文件夹
    """
    try:
        # 打开7z文件
        import py7zr

        with py7zr.SevenZipFile(sevenz_path, 'r') as z:
            # 获取所有文件列表
            file_list = z.getnames()
            print("压缩包内文件列表：")
            for filename in file_list:
                print(f"  - {filename}")
            
            # 设置解压目录
            if extract_to is None:
                # 默认解压到以7z文件名命名的文件夹
                extract_to = os.path.splitext(sevenz_path)[0]
            
            # 创建解压目录
            os.makedirs(extract_to, exist_ok=True)
            
            # py7zr库通常能够很好地处理Unicode文件名
            # 直接使用extractall方法解压所有文件
            try:
                z.extractall(path=extract_to)
                # print(f"\n解压成功！文件已解压到：{extract_to}")
            except PermissionError:
                print(f"警告：解压到 {extract_to} 时遇到权限问题")
            except Exception as e:
                print(f"解压时发生错误：{e}")
    except FileNotFoundError:
        print(f"错误：未找到7z文件：{sevenz_path}")
    except Exception as e:
        print(f"解压过程中发生未知错误：{e}")

def extract_files_from_folder(input_dir: str, extract_to: str = None):
    """
    解压目录下所有压缩文件
    
    Args:
        input_dir: 输入目录，包含压缩文件
        extract_to: 解压目标目录，如果为None，则解压到压缩文件所在目录（保持原有行为）
    """
    if not os.path.isdir(input_dir):
        print(f"错误: {input_dir} 不是有效的目录")
        return False

    input_dir = os.path.abspath(input_dir)
    if extract_to:
        extract_to = os.path.abspath(extract_to)
        os.makedirs(extract_to, exist_ok=True)
        print(f"解压目标目录: {extract_to}")

    for root, _, files in tqdm(os.walk(input_dir), desc="处理压缩文件"):
        for file in files:
            file_path = os.path.join(root, file)
            # 确定解压目标目录
            if extract_to:
                relative_path = os.path.relpath(root, input_dir)
                target_dir = extract_to if relative_path == '.' else os.path.join(extract_to, relative_path)
                os.makedirs(target_dir, exist_ok=True)
            else:
                target_dir = root  # 保持原有行为：在当前目录解压
            
            # 根据文件类型解压
            if file.lower().endswith('.rar'):
                extract_rar(file_path, target_dir)
            elif file.lower().endswith('.7z'):
                extract_7z(file_path, target_dir)
            elif file.lower().endswith('.zip'):
                extract_zip(file_path, target_dir)

    return True


if __name__ == "__main__":
    folder_path = 'ftp_data'
    extract_files_from_folder(folder_path)