"""
自动标注服务模块
提供预标注服务的调用、VOC数据转换等功能
"""
import os
import shutil
from typing import Optional
from pathlib import Path
from tools.http_server.task_client import call_preannotation_service


def _map_task_name_to_vlm_format(task_name: str) -> str:
    """
    提取任务类型和功能，传递给VLM-FO1
    
    Agent格式: DMS2.0-人眼-易甲文-NT98323-DMS2.0闭眼误报
    传递给VLM: DMS2.0-人眼
    
    说明:
    - VLM-FO1的task_manager会自动处理版本号映射（DMS2.0 -> DMS）
    - VLM-FO1的task_manager会自动映射中文任务名称（人眼 -> eye）
    - Agent端只需要提取前两个字段即可
    
    Args:
        task_name: Agent格式的任务名称
    
    Returns:
        传递给VLM-FO1的任务名称
    """
    parts = task_name.split('-', 2)
    if len(parts) < 2:
        return task_name
    
    # 直接提取前两个字段，VLM-FO1会自动处理映射
    task_type = parts[0].strip()
    task_func = parts[1].strip()
    
    return f"{task_type}-{task_func}"


def _convert_voc_to_images_with_label(voc_base_dir: str, output_dir: str, ftp_data_dir: str) -> bool:
    """
    将VOC格式转换为扁平images_with_label格式
    
    只读取voc目录（通过的图片），忽略failed目录
    
    Args:
        voc_base_dir: VOC数据基础目录
        output_dir: 输出目录（images_with_label目录）
        ftp_data_dir: ftp_data目录（用于获取压缩文件名生成前缀）
    
    Returns:
        bool: 是否成功
    """
    voc_base_path = Path(voc_base_dir)
    if not voc_base_path.exists():
        print(f'错误: VOC基础目录不存在: {voc_base_dir}')
        return False
    
    # 获取压缩文件名列表（用于生成前缀）
    archive_names = []
    if os.path.exists(ftp_data_dir):
        for f in sorted(os.listdir(ftp_data_dir)):
            if os.path.isfile(os.path.join(ftp_data_dir, f)):
                archive_names.append(os.path.splitext(f)[0])
    
    os.makedirs(output_dir, exist_ok=True)
    
    total_copied = 0
    video_dirs = [d for d in sorted(voc_base_path.iterdir()) if d.is_dir()]
    
    # 为每个视频分配前缀
    # 策略：如果压缩文件数量 >= 视频数量，按顺序一一对应
    #       如果压缩文件数量 < 视频数量，每个压缩文件对应多个视频，使用压缩文件名+视频索引
    for video_idx, video_dir in enumerate(video_dirs):
        voc_dir = video_dir / 'voc'
        if not voc_dir.exists():
            continue
        
        jpeg_images_dir = voc_dir / 'JPEGImages'
        annotations_dir = voc_dir / 'Annotations'
        
        if not jpeg_images_dir.exists() or not annotations_dir.exists():
            print(f'警告: 跳过不完整的VOC目录: {voc_dir}')
            continue
        
        # 生成前缀
        if archive_names:
            if len(video_dirs) <= len(archive_names):
                # 视频数量 <= 压缩文件数量，一一对应
                prefix = archive_names[video_idx]
            else:
                # 视频数量 > 压缩文件数量，需要分配
                # 计算每个压缩文件对应多少个视频（向上取整）
                videos_per_archive = (len(video_dirs) + len(archive_names) - 1) // len(archive_names)
                archive_idx = video_idx // videos_per_archive
                archive_idx = min(archive_idx, len(archive_names) - 1)
                base_prefix = archive_names[archive_idx]
                # 计算这是该压缩文件的第几个视频（从0开始）
                video_in_archive = video_idx % videos_per_archive
                if video_in_archive == 0:
                    prefix = base_prefix
                else:
                    prefix = f"{base_prefix}_v{video_in_archive + 1}"
        else:
            # 没有压缩文件名，使用video目录名
            prefix = video_dir.name
        
        # 复制图片和XML文件
        for img_file in sorted(jpeg_images_dir.glob('*.*')):
            if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                continue
            
            new_img_name = f"{prefix}_{img_file.name}"
            new_xml_name = f"{prefix}_{img_file.stem}.xml"
            
            shutil.copy2(str(img_file), os.path.join(output_dir, new_img_name))
            
            src_xml_path = annotations_dir / f"{img_file.stem}.xml"
            if src_xml_path.exists():
                shutil.copy2(str(src_xml_path), os.path.join(output_dir, new_xml_name))
                total_copied += 1
        
        video_idx += 1
    
    print(f'✓ 已转换 {total_copied} 个图片-标注对到 {output_dir}')
    return total_copied > 0


class AnnotationService:
    """
    自动标注服务
    
    封装预标注服务的完整流程，包括：
    - 调用远程预标注服务
    - 处理返回结果
    - 转换VOC格式数据
    """
    
    def __init__(self, server_url: Optional[str] = None, ftp_data_dir: Optional[str] = None):
        """
        初始化标注服务

        Args:
            server_url: 预标注服务器URL。为空表示未配置，is_available() 会返回 False
            ftp_data_dir: 待标注压缩包目录。为空表示未配置
        """
        self.server_url = server_url or None
        self.ftp_data_dir = ftp_data_dir or None
    
    def is_available(self) -> bool:
        """检查标注服务是否可用（未配置地址或无待标注数据时视为不可用）。"""
        if not self.server_url:
            return False
        if not self.ftp_data_dir or not os.path.exists(self.ftp_data_dir):
            return False
        return bool(os.listdir(self.ftp_data_dir))
    
    def annotate(self, task_name: str, output_dir: str) -> bool:
        """
        执行自动标注流程
        
        Args:
            task_name: 任务名称
            output_dir: 输出目录（images_with_label）
        
        Returns:
            bool: 是否成功
        """
        if not self.is_available():
            return False
        
        print('\n尝试使用预标注服务...')
        print(f'原始任务名称: {task_name}')
        
        # 映射任务名称为VLM-FO1格式
        vlm_task_name = _map_task_name_to_vlm_format(task_name)
        print(f'VLM任务名称: {vlm_task_name}')
        
        result = call_preannotation_service(
            server_url=self.server_url,
            ftp_data_dir=self.ftp_data_dir,
            task_name=vlm_task_name
        )
        
        if result.get('status') not in ['success', 'partial_success']:
            error_msg = result.get('error', 'Unknown error')
            print(f'✗ 预标注服务失败: {error_msg}，回退到手动标注')
            return False
        
        transfer_info = result.get('transfer', {})
        if not transfer_info.get('success'):
            transfer_msg = transfer_info.get('message', '传输失败')
            print(f'✗ 数据传输失败: {transfer_msg}，回退到手动标注')
            if transfer_info.get('remote_path'):
                print(f'  注意: 返回了路径但传输未成功: {transfer_info.get("remote_path")}')
            return False
        
        remote_path = transfer_info.get('remote_path')
        if not remote_path:
            print('✗ 预标注服务未返回传输路径，回退到手动标注')
            return False
        
        print(f'\n开始转换VOC数据到images_with_label格式...')
        print(f'VOC数据路径: {remote_path}')
        
        # 验证路径是否存在
        if not os.path.exists(remote_path):
            print(f'✗ 传输路径不存在: {remote_path}')
            print('  可能原因：传输失败或路径不正确')
            print('  请检查241服务器的传输日志')
            return False
        
        success = _convert_voc_to_images_with_label(remote_path, output_dir, self.ftp_data_dir)
        
        if not success:
            print('✗ 预标注数据转换失败，回退到手动标注')
            return False
        
        # 检查输出目录是否有文件
        if not os.listdir(output_dir):
            print('✗ 转换后输出目录为空，回退到手动标注')
            return False
        
        print('✓ 预标注数据转换完成')
        return True

