#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# FTP 服务器配置（从环境变量读取，勿在此处硬编码凭据）
FTP_SERVER = os.getenv("FTP_SERVER", "")
FTP_USER = os.getenv("FTP_USER", "")
FTP_PASSWORD = os.getenv("FTP_PASSWORD", "")

# 目录配置
FTP_DATA_DIR = 'ftp_data'
EXTRACTED_IMAGES_DIR = 'extracted_images'
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

# 任务相关配置（示例）
# TASK_NAME = 'demo-type-demo-func-demo-task'
# 根据任务名称推断可能的FTP路径
# REMOTE_DIR = '[/remote/demo/20250101-demo-task]'

# 模型相关配置
MODEL_TYPE = 'dms'
SUB_MODEL_TYPE = 'dms_hands_det'  # 双手检测模型


def clear_directory(directory):
    """清空目录内容"""
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory, exist_ok=True)


def download_data_from_ftp(remote_dir, local_dir):
    """从FTP服务器下载数据"""
    print(f"\n=== 开始从FTP下载数据 ===")
    print(f"FTP服务器: {FTP_SERVER}")
    print(f"远程目录: {remote_dir}")
    print(f"本地目录: {local_dir}")
    
    # 清空本地目录
    clear_directory(local_dir)
    
    # 使用ftp_downloader.py工具下载数据
    ftp_downloader_path = os.path.join(TOOLS_DIR, 'ftp_downloader.py')
    cmd = [
        'python', ftp_downloader_path,
        '--ftp_server', FTP_SERVER,
        '--ftp_user', FTP_USER,
        '--ftp_password', FTP_PASSWORD,
        '--remote_folder', remote_dir,
        '--local_folder', local_dir
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"=== FTP数据下载完成 ===\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FTP数据下载失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False


def uncompress_files(data_dir):
    """解压数据目录中的所有压缩文件"""
    print(f"\n=== 开始解压文件 ===")
    print(f"数据目录: {data_dir}")

    # 确保tools目录存在
    if not os.path.exists(TOOLS_DIR):
        print(f"警告: 工具目录 {TOOLS_DIR} 不存在")
        return
    
    # 遍历数据目录找出所有压缩文件
    compressed_files = []
    rar_exists = False
    zip_exists = False
    for root, _, files in os.walk(data_dir):
        for file in files:
            file_lower = file.lower()
            if file_lower.endswith('.rar'):
                rar_exists = True
                compressed_files.append(os.path.join(root, file))
            if file_lower.endswith('.zip'):
                zip_exists = True
                compressed_files.append(os.path.join(root, file))
    
    # 输出共找到多少压缩文件
    print(f"共找到 {len(compressed_files)} 个压缩文件")
    # 输出压缩文件列表
    print("压缩文件列表:")
    for file in compressed_files:
        print(file)

    # 使用simple_unrar.py解压RAR文件
    if rar_exists:
        unrar_path = os.path.join(TOOLS_DIR, 'simple_unrar.py')
        cmd_rar = ['python', unrar_path, data_dir]
        try:
            print("开始解压RAR文件")
            result = subprocess.run(cmd_rar, capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"RAR文件解压失败: {e}")

    # 使用simple_unzip.py解压ZIP文件
    if zip_exists:
        unzip_path = os.path.join(TOOLS_DIR, 'simple_unzip.py')
        cmd_zip = ['python', unzip_path, '--input-dir', data_dir]
        try:
            print("开始解压ZIP文件")
            result = subprocess.run(cmd_zip, capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"ZIP文件解压失败: {e}")
    
    print(f"=== 文件解压完成 ===\n")


def extract_frames_from_videos(input_dir, output_dir):
    """从视频中提取帧图像"""
    print(f"\n=== 开始提取视频帧 ===")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    
    # 清空输出目录
    clear_directory(output_dir)
    
    # 使用video_to_frames.py工具提取帧
    video_to_frames_path = os.path.join(TOOLS_DIR, 'video_to_frames.py')
    cmd = [
        'python', video_to_frames_path,
        '--input-dir', input_dir,
        '--output-dir', output_dir,
        '--fps', '5',
        '--output-resolution', '1280', '720'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        print(f"=== 视频帧提取完成 ===\n")
        return True
    except Exception as e:
        print(f"视频帧提取失败: {e}")
        print(f"错误输出: {result.stderr if 'result' in locals() else '未知'}")
        return False


# def run_model_prediction(model_dir, data_dir):
#     """运行模型预测"""
#     print(f"\n=== 开始运行模型预测 ===")
#     print(f"模型目录: {model_dir}")
#     print(f"数据目录: {data_dir}")
    
#     # 检查模型目录是否存在
#     if not os.path.exists(model_dir):
#         print(f"警告: 模型目录 {model_dir} 不存在，跳过模型预测")
#         return False
    
#     # 构建eval_data目录
#     eval_data_dir = os.path.join(model_dir, 'eval_data')
#     clear_directory(eval_data_dir)
    
#     # 将提取的图像复制到eval_data目录
#     try:
#         for root, _, files in os.walk(data_dir):
#             for file in files:
#                 if file.lower().endswith(('.jpg', '.jpeg', '.png')):
#                     src_path = os.path.join(root, file)
#                     dst_path = os.path.join(eval_data_dir, file)
#                     shutil.copy2(src_path, dst_path)
#         print(f"已将 {len(os.listdir(eval_data_dir))} 张图像复制到评估数据目录")
#     except Exception as e:
#         print(f"复制评估数据失败: {e}")
#         return False
    
#     # 查找评估脚本
#     eval_script = None
#     for file in os.listdir(model_dir):
#         if file.startswith('eval_') and file.endswith('.py'):
#             eval_script = os.path.join(model_dir, file)
#             break
    
#     if not eval_script:
#         print(f"未找到评估脚本，跳过模型预测")
#         return False
    
#     # 运行评估脚本（在dms环境中）
#     print(f"运行评估脚本: {eval_script}")
    
#     # 注意：根据任务要求，模型预测需要在conda dms环境中运行
#     # 这里仅打印提示信息，实际运行需要在对应环境中执行
#     print("\n=== 模型预测提示 ===")
#     print(f"请在conda dms环境中执行以下命令来运行模型预测:")
#     print(f"cd {model_dir}")
#     print(f"python {os.path.basename(eval_script)}")
#     print(f"确保使用saved_checkpoints目录下的最新模型")
    
#     print(f"=== 模型预测准备完成 ===\n")
#     return True


def main(TASK_NAME, REMOTE_DIR):
    """主函数"""
    print(f"\n===== 开始处理任务: {TASK_NAME} =====")
    
    # 步骤1: 从FTP获取数据
    download_success = download_data_from_ftp(REMOTE_DIR, FTP_DATA_DIR)
    if not download_success:
        print("FTP数据下载失败，任务终止")
        sys.exit(1)
    
    # 步骤2: 数据预处理
    # 2.1 解压文件
    uncompress_files(FTP_DATA_DIR)
    
    # 2.2 提取视频帧
    extract_success = extract_frames_from_videos(FTP_DATA_DIR, EXTRACTED_IMAGES_DIR)
    if not extract_success:
        print("视频帧提取失败，任务终止")
        sys.exit(1)
    
    # 步骤3: 运行模型预测
    # 由于我们没有完整的项目结构信息，这里假设模型路径
    # model_dir = os.path.join('fcos', MODEL_TYPE, SUB_MODEL_TYPE)
    # if not os.path.exists(model_dir):
    #     # 如果模型目录不存在，尝试其他可能的路径
    #     model_dir_candidates = [
    #         os.path.join('fcos', MODEL_TYPE, 'dms_hands_detection'),
    #         os.path.join('fcos', MODEL_TYPE, 'dms_hands_detector')
    #     ]
    #     for candidate in model_dir_candidates:
    #         if os.path.exists(candidate):
    #             model_dir = candidate
    #             break
    
    # prediction_success = run_model_prediction(model_dir, EXTRACTED_IMAGES_DIR)
    
    print(f"\n===== 数据下载及预处理完成: {TASK_NAME} =====")
    print("\n数据预处理总结:")
    print(f"1. FTP数据已下载到: {FTP_DATA_DIR}")
    print(f"2. 视频帧已提取到: {EXTRACTED_IMAGES_DIR}")
    # print(f"3. 模型预测准备{'成功' if prediction_success else '失败'}")
    
    # if not os.path.exists(model_dir):
    #     print(f"\n注意: 未找到模型目录 {model_dir}")
    #     print("请确认模型目录路径并手动运行模型预测")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='data download and proc')
    parser.add_argument('-tn', '--task_name', type=str, default='test', help='task name')
    parser.add_argument('-rf', '--remote_folder', type=str, default='[/remote/test1, /remote/test2]', help='ftp remote folder path, support more than one path')

    args = parser.parse_args()
    main(args.task_name, args.remote_folder)
    print("数据下载处理完成")