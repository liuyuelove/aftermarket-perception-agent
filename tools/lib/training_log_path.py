"""
训练日志路径封装：按 user_id / task_id / run_id 组织，与 Next.js API 一致。
"""
import os
import re

# tools/lib/ -> tools/ -> 项目根。
# 原实现多退了两级（按 monorepo 里的 backend/aftermarket-perception-agent 布局算的），
# 独立仓库下会解析到用户主目录，日志直接写到 ~ 里。
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_REL_PATH = os.path.join('data', 'training_logs')


def get_logs_base_dir() -> str:
    """获取训练日志根目录。相对路径基于项目根解析。"""
    from_env = os.environ.get('TRAINING_LOGS_DIR')
    if from_env:
        # 绝对路径直接使用，相对路径基于项目根
        if os.path.isabs(from_env):
            return from_env
        return os.path.normpath(os.path.join(_PROJECT_ROOT, from_env))
    return os.path.join(_PROJECT_ROOT, _REL_PATH)


def sanitize_task_id(task_name: str) -> str:
    """将 task_name 转为安全的目录名。"""
    s = (task_name or "").strip()
    s = re.sub(r'[/\\:*?"<>|]', '_', s)
    return s[:120] if s else "unknown"


def get_train_log_path(user_id: str, task_name: str, run_id: str) -> str | None:
    """
    获取单次训练日志路径。train 时调用，返回 .log 所在路径（不含扩展名）。
    Returns:
        完整 .log 路径，或 None（不写日志时）
    """
    if not run_id:
        return None
    base = get_logs_base_dir()
    uid = (user_id or "default").strip() or "default"
    tid = sanitize_task_id(task_name or "")
    subdir = os.path.join(base, uid, tid)
    os.makedirs(subdir, exist_ok=True)
    return os.path.join(subdir, f"{run_id}.log")
