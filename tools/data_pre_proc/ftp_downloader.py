import argparse
import ftplib
import os
from pathlib import Path
import shutil
from typing import Union

## FTP 配置示例（凭据走环境变量 FTP_SERVER / FTP_USER / FTP_PASSWORD，勿硬编码）
# 多个远程目录列表
# REMOTE_DIRS = [
#     '/remote/demo/task-a',
#     '/remote/demo/task-b',
# ]
# LOCAL_DIR = 'data'

def str2list(strings):
    """
    Convert string to str list.
    
    :param strings: A string representing a list, e.g., "[a,b,c,d]"
    :return: list with four string.
    """
    
    if strings == "None":
        return None
    
    try:
        # Remove spaces and parentheses, then split by comma
        cleaned = strings.replace('[', '').replace(']', '').replace(' ', '').split(',')
        # Convert strings to integers or floats
        return cleaned
    except:
        raise "list must be comma-separated strings enclosed in parentheses"

def download_ftp_files(FTP_SERVER : str, FTP_USER : str, FTP_PASSWORD : str, REMOTE_DIRS : Union[list, str], LOCAL_DIR : str):
    """
    从FTP服务器下载多个指定目录及其子目录下的所有文件到本地目录
    每个远程目录会在本地创建独立的子目录
    """
    ftp = None
    try:
        # 连接FTP服务器
        ftp = ftplib.FTP(FTP_SERVER)
        ftp.login(FTP_USER, FTP_PASSWORD)
        print(f"成功连接并登录到FTP服务器: {FTP_SERVER}")

        # 切换到二进制传输模式
        ftp.voidcmd('TYPE I')

        def download_directory(remote_dir, local_dir):
            """递归下载远程目录到本地"""
            # 创建本地目录
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            print(f"正在处理目录: {remote_dir} -> {local_dir}")

            # 尝试使用MLSD命令获取目录列表（机器可读格式）
            try:
                entries = []
                for entry in ftp.mlsd(remote_dir):
                    name, facts = entry
                    entries.append((name, facts))
            except ftplib.error_perm as e:
                # 如果不支持MLSD，回退到LIST命令
                print(f"MLSD命令不受支持，使用LIST命令: {e}")
                entries = []
                ftp.retrlines(f'LIST {remote_dir}', lambda line: entries.append(line))

            for entry in entries:
                if isinstance(entry, tuple):
                    # MLSD格式: (名称, 事实字典)
                    name, facts = entry
                    entry_type = facts.get('type', 'file')
                else:
                    # LIST格式: 需要解析行内容
                    line = entry
                    # 简单解析LIST输出（适用于Unix风格）
                    # 示例行: "drwxr-xr-x 1 user group 0 Jan 01 00:00 directory"
                    parts = line.split()
                    if len(parts) < 9:
                        continue  # 忽略无法解析的行
                    name = ' '.join(parts[8:])  # 文件名可能包含空格
                    entry_type = 'dir' if line.startswith('d') else 'file'

                # 跳过当前目录(.)和父目录(..)
                if name in ('.', '..'):
                    continue

                remote_path = os.path.join(remote_dir, name).replace('\\', '/')
                local_path = os.path.join(local_dir, name)

                if entry_type == 'dir':
                    # 递归下载子目录
                    download_directory(remote_path, local_path)
                else:
                    # 下载文件
                    print(f"正在下载: {remote_path} -> {local_path}")
                    try:
                        with open(local_path, 'wb') as f:
                            ftp.retrbinary(f'RETR {remote_path}', f.write)
                        print(f"下载完成: {name}")
                    except Exception as e:
                        print(f"下载文件 {name} 失败: {str(e)}")

        # 清空并重建输出目录
        if os.path.exists(LOCAL_DIR):
            shutil.rmtree(LOCAL_DIR)
        os.makedirs(LOCAL_DIR, exist_ok=True)
        
        if isinstance(REMOTE_DIRS, str):
            REMOTE_DIRS = [REMOTE_DIRS]
        # 遍历所有远程目录并下载
        for remote_dir in REMOTE_DIRS:
            try:
                # 解析远程目录的最后一级作为本地子目录
                new_local_root = LOCAL_DIR
                
                # 创建本地目录（如果不存在）
                Path(new_local_root).mkdir(parents=True, exist_ok=True)
                
                print(f"\n开始处理远程目录: {remote_dir}")
                download_directory(remote_dir, new_local_root)
                print(f"远程目录处理完成: {remote_dir}")
            except Exception as e:
                print(f"处理远程目录 {remote_dir} 时出错: {str(e)}")
                continue

        print("\n所有远程目录处理完成")

    except ftplib.all_errors as e:
        print(f"FTP操作错误: {str(e)}")
        raise
    except Exception as e:
        print(f"发生错误: {str(e)}")
        raise
    finally:
        if ftp:
            try:
                ftp.quit()
                print("已断开FTP连接")
            except Exception as e:
                print(f"关闭FTP连接时出错: {str(e)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='download data from ftp')
    parser.add_argument('-fs', '--ftp_server', type=str, default=os.getenv("FTP_SERVER", ""), help='ftp server')
    parser.add_argument('-fu', '--ftp_user', type=str, default=os.getenv("FTP_USER", ""), help='ftp user')
    parser.add_argument('-fp', '--ftp_password', type=str, default=os.getenv("FTP_PASSWORD", ""), help='ftp password')
    parser.add_argument('-rf', '--remote_folder', type=str2list, default=['/remote/'], help='ftp remote folder path')
    parser.add_argument('-lf', '--local_folder', type=str, default='data', help='dest local folder path')

    args = parser.parse_args()
    download_ftp_files(args.ftp_server, args.ftp_user, args.ftp_password, args.remote_folder, args.local_folder)
