import requests
import json
import os
import argparse
import time
from pathlib import Path
from tqdm import tqdm
import shutil
import zipfile
import tempfile

class TaskClient:
    """任务客户端，用于发送任务请求和下载处理后的文件"""

    def __init__(self, server_url):
        """初始化客户端

        Args:
            server_url: 服务器URL，格式如 'http://服务器IP:8000'
        """
        self.server_url = server_url.rstrip('/')

    def submit_task(self, task_name):
        """提交任务请求

        Args:
            task_name: 任务名称

        Returns:
            dict: 包含任务ID和状态的响应
        """
        try:
            response = requests.post(
                f'{self.server_url}/task',
                json={'task_name': task_name}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f'提交任务失败: {e}')
            return None

    def check_task_status(self, task_id):
        """检查任务状态

        Args:
            task_id: 任务ID

        Returns:
            dict: 任务状态信息
        """
        try:
            response = requests.get(
                f'{self.server_url}/task/status',
                params={'task_id': task_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f'查询任务状态失败: {e}')
            return None

    def wait_for_task_completion(self, task_id, check_interval=10):
        """等待任务完成

        Args:
            task_id: 任务ID
            check_interval: 状态检查间隔（秒）

        Returns:
            bool: 任务是否成功完成
        """
        while True:
            status = self.check_task_status(task_id)
            if not status:
                print('无法获取任务状态，退出等待')
                return False

            print(f'任务状态: {status.get("status")}, 消息: {status.get("message")}')

            if status.get('status') == 'completed':
                return True
            elif status.get('status') == 'failed':
                return False

            # 等待一段时间后再次检查
            time.sleep(check_interval)

    def get_file_list(self):
        """获取服务器上的文件列表

        Returns:
            list: 文件和目录列表
        """
        try:
            response = requests.get(f'{self.server_url}/files')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f'获取文件列表失败: {e}')
            return None
        except json.JSONDecodeError:
            print('服务器返回的不是有效的JSON格式')
            return None

    def download_file(self, remote_path, save_dir='./downloads'):
        """下载单个文件

        Args:
            remote_path: 远程文件路径
            save_dir: 本地保存目录

        Returns:
            str: 本地保存的文件路径，如果下载失败返回None
        """
        try:
            # 构建完整的下载URL
            download_url = f'{self.server_url}/files/{remote_path.lstrip("/")}'

            # 发送GET请求获取文件
            # 流式处理大文件
            with requests.get(download_url, stream=True) as response:
                response.raise_for_status()

                # 获取文件名
                filename = os.path.basename(remote_path)

                # 确保保存目录存在
                os.makedirs(save_dir, exist_ok=True)

                # 构建保存路径
                save_path = os.path.join(save_dir, filename)

                # 写入文件
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # 过滤掉保持连接的空块
                            file.write(chunk)

            # print(f'文件下载成功: {save_path}')
            return save_path

        except requests.exceptions.RequestException as e:
            print(f'下载文件失败: {e}')
            return None

    def download_all_files(self, save_dir='./download_data'):
        """下载所有文件

        Args:
            save_dir: 本地保存目录
        """
        # 获取文件列表
        items = self.get_file_list()
        if not items:
            print('无法获取文件列表，下载失败')
            return False

        # 清空保存目录
        if os.path.exists(save_dir):
            shutil.rmtree(save_dir)
        else:
            os.makedirs(save_dir)

        # 筛选出所有文件并下载
        files = [item for item in items if item['type'] == 'file']
        total_files = len(files)

        print(f'找到 {total_files} 个文件，开始下载...')

        for i, file_info in tqdm(enumerate(files, 1), total=total_files, desc='下载进度'):
            file_path = file_info['path']
            # print(f'下载文件 {i}/{total_files}: {file_path}')

            # 构建保存子目录
            dir_path = os.path.dirname(file_path)
            local_dir = os.path.join(save_dir, dir_path)

            self.download_file(file_path, local_dir)

        print('所有文件下载完成')
        return True
def task_data_download_from_server(server_url: str = 'http://localhost:8000',
                                   task_name: str = '易甲文-NT323-DMS2.0闭眼误报',
                                   output_dir: str = './download_data',
                                   check_interval: int = 10) -> bool:
    """
    从服务器获取预处理任务数据

    Args:
        server_url: 服务器URL，格式如 http://服务器IP:8000，默认 'http://localhost:8000'
        task_name: 要处理的任务名称
        output_dir: 下载文件的保存目录，默认 './images'
        check_interval: 任务状态检查间隔（秒），默认 10

    Returns:
        bool: 任务是否成功完成，True 表示成功，False 表示失败
    """

    # 创建客户端实例
    client = TaskClient(server_url)

    # 提交任务
    print(f'提交任务: {task_name}')
    task_response = client.submit_task(task_name)

    if not task_response:
        print('任务提交失败，程序退出')
        return False

    task_id = task_response.get('task_id')
    print(f'任务提交成功，任务ID: {task_id}')

    # 等待任务完成
    print('开始等待任务处理完成...')
    task_success = client.wait_for_task_completion(task_id, check_interval)

    if not task_success:
        print('任务处理失败，程序退出')
        return False

    # 任务成功完成，下载所有文件
    print('任务处理成功，开始下载文件...')
    download_success = client.download_all_files(output_dir)

    if download_success:
        print('所有文件下载完成，程序退出')
    else:
        print('文件下载过程中出现错误')

    return download_success

def call_preannotation_service(server_url: str,
                               ftp_data_dir: str,
                               task_name: str,
                               batch_job_id: str = None) -> dict:
    """
    调用预标注服务，将ftp_data目录打包上传

    Args:
        server_url: 预标注服务器URL（241服务器）
        ftp_data_dir: ftp_data目录路径（包含压缩文件）
        task_name: 任务名称
        batch_job_id: 批量任务ID（可选，不提供则自动生成）

    Returns:
        预标注结果字典，包含：
        - status: 'success' | 'failed'
        - transfer.remote_path: 224服务器上的VOC数据路径（如果成功）
        - error: 错误信息（如果失败）
    """
    if not os.path.exists(ftp_data_dir):
        return {
            'status': 'failed',
            'error': f'ftp_data目录不存在: {ftp_data_dir}'
        }

    # 检查目录是否为空
    files = [f for f in os.listdir(ftp_data_dir) if os.path.isfile(os.path.join(ftp_data_dir, f))]
    if not files:
        return {
            'status': 'failed',
            'error': f'ftp_data目录为空: {ftp_data_dir}'
        }

    # 打包ftp_data目录为zip
    print(f'\n开始打包ftp_data目录: {ftp_data_dir}')
    temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip_path = temp_zip_file.name
    temp_zip_file.close()

    try:
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files_list in os.walk(ftp_data_dir):
                for file in files_list:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, ftp_data_dir)
                    zipf.write(file_path, arcname)

        zip_size = os.path.getsize(temp_zip_path) / 1024 / 1024
        print(f'✓ 已打包 {len(files)} 个文件到临时zip ({zip_size:.2f} MB)')

        # 发送预标注请求
        url = f"{server_url.rstrip('/')}/preannotate"
        print(f'正在发送预标注请求到 {url}...')

        with open(temp_zip_path, 'rb') as zip_file:
            files_data = {'videos_zip': zip_file}
            data = {
                'task_name': task_name,
                'batch_job_id': batch_job_id or f"batch_{int(time.time())}",
                'copy_source_videos': 'true'
            }

            try:
                response = requests.post(url, files=files_data, data=data, timeout=3600)
                response.raise_for_status()
                result = response.json()

                if result.get('status') in ['success', 'partial_success']:
                    print('✓ 预标注成功')
                    print(f'  批量任务ID: {result.get("batch_job_id")}')
                    print(f'  输出路径: {result.get("output_path")}')
                    transfer_info = result.get('transfer', {})
                    if transfer_info.get('success'):
                        print(f'  传输路径: {transfer_info.get("remote_path")}')
                    else:
                        print(f'  警告: 传输失败 - {transfer_info.get("message", "Unknown error")}')
                    return result
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f'✗ 预标注失败: {error_msg}')
                    return {
                        'status': 'failed',
                        'error': error_msg
                    }
            except requests.exceptions.RequestException as e:
                error_msg = f'请求失败: {str(e)}'
                print(f'✗ {error_msg}')
                return {
                    'status': 'failed',
                    'error': error_msg
                }
    finally:
        # 清理临时zip文件
        if os.path.exists(temp_zip_path):
            try:
                os.unlink(temp_zip_path)
            except Exception as e:
                print(f'警告: 清理临时zip文件失败: {e}')

# 命令行接口
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='任务客户端')
    parser.add_argument('--server', default='http://localhost:8000', help='服务器URL，格式如 http://服务器IP:8000')
    parser.add_argument('--task', default='易甲文-NT323-DMS2.0闭眼误报', help='要处理的任务名称')
    parser.add_argument('--output-dir', default='./download_data', help='下载文件的保存目录')
    parser.add_argument('--check-interval', type=int, default=10, help='任务状态检查间隔（秒）')

    args = parser.parse_args()

    task_data_download_from_server(args.server, args.task, args.output_dir, args.check_interval)