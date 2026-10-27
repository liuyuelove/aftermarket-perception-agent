"""
数据获取与预处理：下载 → 解压 → 解帧。

把原先散在 `task_proc.task_data_get_pre_proc` 里的编排逻辑收拢到一处，
所有路径来自 `config.env`，不再依赖函数默认参数里的内网地址。

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
from pathlib import Path

from config import env
from tools.data_pre_proc.extract_files import extract_files_from_folder
from tools.data_pre_proc.video_to_frames import extract_frames_from_dir

log = logging.getLogger("aftermarket.dataset")


def local_archives() -> list[Path]:
    """本地待处理的数据包（只算文件，不算目录）。"""
    root = Path(env.FTP_DATA_DIR)
    if not root.exists():
        return []
    return sorted(p for p in root.iterdir() if p.is_file())


def matches_task(archive_name: str, task_name: str) -> bool:
    """判断本地数据包是否属于这个任务。

    文件名形如 `NT323_MS_闭眼误报_V1.0.0.62.2_T20251020.rar`，未必包含
    `DMS2.0` / `人头` 这类字段，所以按「任务名的任意一段出现在文件名里」判定，
    命不中不代表一定不是，只是需要人来确认。
    """
    if not archive_name or not task_name:
        return False
    if task_name in archive_name:
        return True
    parts = [p.strip() for p in task_name.replace("_", "-").split("-") if p.strip()]
    return any(part in archive_name for part in parts)


def download(task_name: str) -> bool:
    """从数据服务器拉取该任务的数据包。

    没配 `DATA_SERVER_URL` 时复用 `ai_data/ftp_data` 里的本地数据 —— 但必须确认
    这批数据和当前任务对得上。原实现「只要有文件就复用」，会让 A 任务悄悄用 B 任务
    的数据训练，结果看着还挺正常。这里把数据包名字打出来，不匹配时按
    `DATA_REUSE_STRICT` 决定是警告还是拒绝。
    """
    if not env.DATA_SERVER_URL:
        archives = local_archives()
        if not archives:
            log.error(
                "未配置 DATA_SERVER_URL 且本地 %s 为空，无法下载。"
                "请在 .env 中设置 DATA_SERVER_URL。",
                env.FTP_DATA_DIR,
            )
            return False

        names = [p.name for p in archives]
        matched = [n for n in names if matches_task(n, task_name)]
        if matched:
            log.warning(
                "未配置 DATA_SERVER_URL，复用本地数据（与任务名匹配）：%s", matched
            )
            return True

        message = (
            f"未配置 DATA_SERVER_URL，本地数据与任务 {task_name!r} 对不上。"
            f"现有：{names}。确认要用就设 DATA_REUSE_STRICT=0，"
            f"否则请配置 DATA_SERVER_URL。"
        )
        if env.DATA_REUSE_STRICT:
            log.error(message)
            return False
        log.warning("%s（当前 DATA_REUSE_STRICT=0，继续执行）", message)
        return True

    from tools.http_server.task_client import task_data_download_from_server

    log.info("下载数据 task=%s from=%s", task_name, env.DATA_SERVER_URL)
    ok = task_data_download_from_server(env.DATA_SERVER_URL, task_name, str(env.FTP_DATA_DIR))
    if not ok:
        log.error("数据下载失败 task=%s", task_name)
    return ok


def extract() -> bool:
    """解压下载到的压缩包。"""
    log.info("解压 %s → %s", env.FTP_DATA_DIR, env.EXTRACTED_DATA_DIR)
    ok = extract_files_from_folder(
        input_dir=str(env.FTP_DATA_DIR),
        extract_to=str(env.EXTRACTED_DATA_DIR),
    )
    if not ok:
        log.error("解压失败")
    return ok


def to_frames() -> bool:
    """视频抽帧到图片目录。"""
    log.info(
        "解帧 %s → %s (fps=%s, res=%s)",
        env.EXTRACTED_DATA_DIR,
        env.IMG_DIR,
        env.FRAME_FPS,
        env.FRAME_RESOLUTION,
    )
    ok = extract_frames_from_dir(
        input_dir=str(env.EXTRACTED_DATA_DIR),
        output_dir=str(env.IMG_DIR),
        fps=env.FRAME_FPS,
        output_resolution=env.FRAME_RESOLUTION,
    )
    if not ok:
        log.error("解帧失败")
    return ok


def fetch_and_preprocess(task_name: str) -> bool:
    """完整的数据准备链路。任一步失败即整体失败。"""
    return download(task_name) and extract() and to_frames()
