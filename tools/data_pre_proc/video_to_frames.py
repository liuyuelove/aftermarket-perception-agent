import cv2
import os
import shutil
import argparse
from pathlib import Path
import glob
from PIL import Image
from tqdm import tqdm


def extract_frames(video_path, output_dir, fps=5, output_resolution=None):
    """
    从视频中提取帧并保存为图像
    :param video_path: 视频文件路径
    :param output_dir: 输出图像目录
    :param fps: 提取帧率
    :param output_resolution: 输出图像分辨率 (宽, 高)，为None时不调整分辨率
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 打开视频文件
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"无法打开视频文件: {video_path}")
        return False
    
    # 获取视频原始帧率
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    # 获取视频总帧数
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if original_fps == 0:
        original_fps = 30  # 默认假设30fps
    
    # 计算帧间隔
    frame_interval = max(1, round(original_fps / fps))
    extracted_count = 0
    
    for frame_count in tqdm(range(total_frames), desc="提取进度"):
        ret, frame = cap.read()
        if not ret:
            break
        
        # 按间隔提取帧
        if frame_count % frame_interval == 0:
            # 保存图像（6位帧号）
            img_name = f"{frame_count:06d}.jpg"
            img_path = os.path.join(output_dir, img_name)
            
            # 调整图像分辨率（仅当output_resolution不为None时）
            if output_resolution is not None:
                target_width, target_height = output_resolution
                frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
            
            # 转换BGR为RGB（OpenCV默认BGR格式，PIL需要RGB）
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 使用PIL保存图像
            try:
                image = Image.fromarray(frame_rgb)
                image.save(img_path)
                # print(f"成功保存帧: {img_path}")
            except Exception as e:
                print(f"保存帧失败: {img_path}, 错误: {str(e)}")
            extracted_count += 1
        
    cap.release()
    # print(f"视频 {video_path.name} 处理完成，提取了 {extracted_count} 帧图像")
    return True

def extract_frames_from_dir(input_dir, output_dir, fps=5, output_resolution=None):
    """
    从指定目录下的所有视频文件提取帧图像
    :param input_dir: 输入视频目录路径
    :param output_dir: 输出帧图像目录路径
    :param fps: 提取帧率（默认5fps）
    :param output_resolution: 输出图像分辨率 (宽 高)，为None时不调整分辨率
    """
    # 视频文件扩展名
    VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv')
    
    # 构建输入和输出目录路径
    input_dir = Path(input_dir)
    output_root = Path(output_dir)
    target_fps = fps
    output_resolution = tuple(output_resolution) if output_resolution else None
    
    # 检查输入目录是否存在
    if not input_dir.exists():
        print(f"输入目录不存在: {input_dir}")
        return False
    
    # 清空并重建输出目录
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    
    # 获取所有视频文件路径并去重
    video_paths = set(glob.glob(str(input_dir / '**/*.*'), recursive=True))
    
    # 遍历视频文件
    for video_path_str in tqdm(video_paths, desc="处理视频"):
        video_path = Path(video_path_str)
        if video_path.suffix.lower() in VIDEO_EXTENSIONS:
            # print(f"找到视频文件: {video_path}")
            # 计算相对路径
            relative_path = video_path.relative_to(input_dir)
            # 获取视频文件名（不含扩展名）作为子文件夹名
            video_name = video_path.stem
            # 构建输出目录：output_root / 相对路径的父目录 / 视频文件名
            output_dir = output_root / relative_path.parent / video_name
            # print(f"帧保存目录: {output_dir}")
            
            # 提取帧
            extract_frames(video_path, str(output_dir), target_fps, output_resolution)

    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='将指定目录下的视频文件提取为帧图像')
    parser.add_argument('--input-dir', required=True, type=str, default='ftp_data', help='输入视频目录路径')
    parser.add_argument('--output-dir', required=True, type=str, default='extracted_frames', help='输出帧图像目录路径')
    parser.add_argument('--fps', type=int, default=5, help='提取帧率（默认5fps）')
    parser.add_argument('--output-resolution', type=int, nargs=2, default=None, help='输出图像分辨率 (宽 高)，不指定则不调整分辨率')
    args = parser.parse_args()

    extract_frames_from_dir(args.input_dir, args.output_dir, args.fps, args.output_resolution)
    print("所有视频帧提取完成")