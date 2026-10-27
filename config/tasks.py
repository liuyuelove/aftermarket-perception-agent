"""
任务注册表：任务类型 × 任务功能 的单一事实来源。

原先这些信息分散在四个字典里（func_proc_dict / prj_name_dict /
train_data_path_dict / org_data_path_dict），键结构互不一致：
  - prj_name_dict / func_proc_dict 缺 HOD
  - org_data_path_dict 只有 DMS 的 8 个功能，且按 task_func 单键索引
    （'安全带' 在 DMS2.0 / DMS1.0 / HOD 都存在，会串台）
本文件把它们合并为一张表，并用 validate() 在启动时显式报告缺口，
而不是在运行到一半时抛 KeyError。

pipeline 语义（沿用原设计）：
  pre_cnn   前级网络。非空时先跑前级，再把它当预处理输入跑本级（两阶段级联）。
  pipeline  本级要执行的步骤列表：
            {'pre_proc': {...}}   → 预处理（src_img_copy / crop_resize / warp）
            {'post_proc': [...]}  → 后处理（cnn_bbox_remap_to_src，把 bbox 反算回原图）

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskSpec:
    """一个「任务类型 × 任务功能」的完整规格。"""

    task_type: str
    task_func: str
    prj: str | None = None            # fcos/ 下的工程目录名
    train_data: str | None = None     # 训练数据相对 aftermarket_data 的路径
    org_data: str | None = None       # 原始数据相对 aftermarket_data 的路径
    pre_cnn: str | None = None        # 前级网络（同一 task_type 下的另一个 task_func）
    pipeline: list[dict[str, Any]] = field(default_factory=list)


TASKS: dict[tuple[str, str], TaskSpec] = {
    ('BSD', '鱼眼非机动车道路'): TaskSpec(
        task_type='BSD',
        task_func='鱼眼非机动车道路',
        prj='bsd_fisheye_no_motor_road',
        train_data='bsd/fisheye_no_motor_road_ai_new',
        org_data=None,
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (640, 320))}}]}],
    ),
    ('BSD', '鱼眼机动车道路'): TaskSpec(
        task_type='BSD',
        task_func='鱼眼机动车道路',
        prj='bsd_fisheye_motor_only_road',
        train_data='bsd/fisheye_motor_only_road_ai_new',
        org_data=None,
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (640, 320))}}]}],
    ),
    ('BSD', '鱼眼非机动车叉车'): TaskSpec(
        task_type='BSD',
        task_func='鱼眼非机动车叉车',
        prj='bsd_fisheye_no_motor_fork',
        train_data='bsd/fisheye_no_motor_fork_ai_new',
        org_data=None,
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (640, 320))}}]}],
    ),
    ('BSD', '普通非机动车道路'): TaskSpec(
        task_type='BSD',
        task_func='普通非机动车道路',
        prj='bsd_normal_no_motor_road',
        train_data='bsd/normal_no_motor_road_ai_new',
        org_data=None,
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (512, 320))}}]}],
    ),
    ('BSD', '普通机动车道路'): TaskSpec(
        task_type='BSD',
        task_func='普通机动车道路',
        prj=None,
        train_data=None,
        org_data=None,
        pre_cnn=None,
        pipeline=None,
    ),
    ('DMS2.0', '人头'): TaskSpec(
        task_type='DMS2.0',
        task_func='人头',
        prj='dms_head_det',
        train_data='dms1/head_data/head_dataset_ai_new',
        org_data='org_data/dms/head',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (384, 256))}}]}],
    ),
    ('DMS2.0', '安全带'): TaskSpec(
        task_type='DMS2.0',
        task_func='安全带',
        prj='dms_belt_det_fudai',
        train_data='dms2/belt_data/belt_dataset_ai_new',
        org_data='org_data/dms/belt',
        pre_cnn='人头',
        pipeline=[{'pre_proc': {'warp': ((1, 0.5, 2, 2), (288, 288))}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'warp': None}}]}],
    ),
    ('DMS2.0', '抽烟'): TaskSpec(
        task_type='DMS2.0',
        task_func='抽烟',
        prj='dms_cigarette_det_fudai',
        train_data='dms2/cigarette_data/cigarette_dataset_ai_new',
        org_data='org_data/dms/cigarette',
        pre_cnn='人头',
        pipeline=[{'pre_proc': {'warp': ((1, 0.5, 2, 2), (288, 288))}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'warp': None}}]}],
    ),
    ('DMS2.0', '电话'): TaskSpec(
        task_type='DMS2.0',
        task_func='电话',
        prj='dms_phone_det_fudai',
        train_data='dms2/phone_data/phone_dataset_ai_new',
        org_data='org_data/dms/phone',
        pre_cnn='人头',
        pipeline=[{'pre_proc': {'warp': ((1, 0.5, 2, 2), (288, 288))}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'warp': None}}]}],
    ),
    ('DMS2.0', '人眼'): TaskSpec(
        task_type='DMS2.0',
        task_func='人眼',
        prj='dms_eye_det_fudai',
        train_data='dms2/eye_data/eye_dataset_ai_new',
        org_data='org_data/dms/eye',
        pre_cnn='人头',
        pipeline=[{'pre_proc': {'warp': ((0.6, 0.6, 1.2, 1.2), (256, 256))}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'warp': None}}]}],
    ),
    ('DMS2.0', '头部姿态'): TaskSpec(
        task_type='DMS2.0',
        task_func='头部姿态',
        prj='dms_posture_det',
        train_data='dms2/posture_data/posture_dataset_ai_new',
        org_data='org_data/dms/posture',
        pre_cnn='人头',
        pipeline=[{'pre_proc': {'warp': ((0.6, 0.6, 1.2, 1.2), (256, 256))}}, {'post_proc': []}],
    ),
    ('DMS1.0', '人头'): TaskSpec(
        task_type='DMS1.0',
        task_func='人头',
        prj='dms_head_det',
        train_data=None,
        org_data='org_data/dms/head',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (384, 256))}}]}],
    ),
    ('DMS1.0', '人脸'): TaskSpec(
        task_type='DMS1.0',
        task_func='人脸',
        prj='dms_face_det',
        train_data='dms1/face_data/face_dataset_ai_new',
        org_data='org_data/dms/face',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (192, 128))}}]}],
    ),
    ('DMS1.0', '安全带'): TaskSpec(
        task_type='DMS1.0',
        task_func='安全带',
        prj='dms_belt_det',
        train_data='dms1/belt_data/belt_dataset_ai_new',
        org_data='org_data/dms/belt',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (384, 256))}}]}],
    ),
    ('DMS1.0', '抽烟'): TaskSpec(
        task_type='DMS1.0',
        task_func='抽烟',
        prj='dms_cigarette_det',
        train_data='dms1/cigarette_data/cigarette_dataset_ai_new',
        org_data='org_data/dms/cigarette',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (384, 256))}}]}],
    ),
    ('DMS1.0', '电话'): TaskSpec(
        task_type='DMS1.0',
        task_func='电话',
        prj='dms_phone_det',
        train_data='dms1/phone_data/phone_dataset_ai_new',
        org_data='org_data/dms/phone',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (384, 256))}}]}],
    ),
    ('DMS1.0', '人眼'): TaskSpec(
        task_type='DMS1.0',
        task_func='人眼',
        prj=None,
        train_data=None,
        org_data='org_data/dms/eye',
        pre_cnn=None,
        pipeline=None,
    ),
    ('DMS1.0', '吃东西'): TaskSpec(
        task_type='DMS1.0',
        task_func='吃东西',
        prj='dms_eat_det',
        train_data='dms1/eating_data/eating_dataset_ai_new',
        org_data='org_data/dms/eating',
        pre_cnn=None,
        pipeline=[{'pre_proc': {'src_img_copy': None}},
 {'post_proc': [{'cnn_bbox_remap_to_src': {'crop_resize': (None, (384, 256))}}]}],
    ),
    ('HOD', '安全带'): TaskSpec(
        task_type='HOD',
        task_func='安全带',
        prj=None,
        train_data=None,
        org_data='org_data/dms/belt',
        pre_cnn=None,
        pipeline=None,
    ),
    ('HOD', '电话'): TaskSpec(
        task_type='HOD',
        task_func='电话',
        prj=None,
        train_data=None,
        org_data='org_data/dms/phone',
        pre_cnn=None,
        pipeline=None,
    ),
    ('HOD', '方向盘'): TaskSpec(
        task_type='HOD',
        task_func='方向盘',
        prj=None,
        train_data=None,
        org_data=None,
        pre_cnn=None,
        pipeline=None,
    ),
}


TASK_TYPES: tuple[str, ...] = tuple(sorted({tt for tt, _ in TASKS}))
TASK_FUNCS: dict[str, list[str]] = {}
for _tt, _fn in TASKS:
    TASK_FUNCS.setdefault(_tt, []).append(_fn)


class UnknownTaskError(KeyError):
    """任务类型或任务功能不在注册表中。"""


def get_task(task_type: str, task_func: str) -> TaskSpec:
    """取任务规格；找不到时抛出带可选值的清晰错误。

    任务类型大小写不敏感：LLM 偶尔会吐 `dms2.0`，注册表统一按大写存。
    """
    task_type = (task_type or "").strip().upper()
    task_func = (task_func or "").strip()

    key = (task_type, task_func)
    if key in TASKS:
        return TASKS[key]
    if task_type not in TASK_FUNCS:
        raise UnknownTaskError(
            f"未知任务类型 {task_type!r}，可选：{sorted(TASK_FUNCS)}"
        )
    raise UnknownTaskError(
        f"{task_type} 下没有任务功能 {task_func!r}，可选：{TASK_FUNCS[task_type]}"
    )


def validate(verbose: bool = True) -> list[str]:
    """检查注册表完整性，返回问题列表（不抛异常，供启动时打日志）。"""
    problems: list[str] = []
    for (tt, fn), spec in TASKS.items():
        if not spec.prj:
            problems.append(f"{tt}/{fn}: 缺 prj（fcos 目录名），无法执行 train/eval")
        if not spec.pipeline:
            problems.append(f"{tt}/{fn}: 缺 pipeline（预处理/后处理配置）")
        if spec.pre_cnn and (tt, spec.pre_cnn) not in TASKS:
            problems.append(f"{tt}/{fn}: pre_cnn={spec.pre_cnn!r} 未在同类型下注册")
    if verbose and problems:
        import logging

        log = logging.getLogger("aftermarket.config")
        for p in problems:
            log.warning("任务注册表缺口: %s", p)
    return problems
