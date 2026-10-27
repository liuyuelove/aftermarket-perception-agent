"""
训练 / 评估 / 模型转换的调度层。

职责：把「任务规格 + 处理类型」翻译成对 fcos 工程的调用，并把产物整理到
统一的结果目录。算法本身在 fcos/ 下，本层不关心其内部实现。

相对原 `func_proc` 的修正：
  - fcos 目录、数据根目录走配置，不再硬编码
  - train/val 划分加固定种子，保证可复现
  - 评估流程中 post_proc 缺失时给出明确结果，而非 NameError
  - 任务查找走注册表，缺失字段给出可读错误，而非 KeyError
  - checkpoint 归档从 shell 挪到 Python，local / docker 两种执行器行为一致

@Time: 2026/10/18
@Author: 刘越的不努力日记本
"""

from __future__ import annotations

import logging
import os
import random
import shutil
import subprocess
import sys
import time
from functools import cached_property
from pathlib import Path

from config import env
from config.tasks import TaskSpec, get_task
from tools.common_funcs.get_prj_params import get_det_classes
from tools.common_funcs.visualize import draw_bbox_with_xml
from tools.data_pre_proc.img_crop_resize import folder_img_crop_resize
from tools.data_pre_proc.img_warp_perspective import img_warp_perspective, img_warp_with_label
from tools.lib.cnn_result_proc import (
    bbox_dict_merge,
    bbox_remap,
    filter_cnn_result,
    gen_xml_with_bbox_dict,
)
from tools.lib.cv_img_proc import read_img_to_ndarray
from tools.lib.file_proc import (
    create_new_folder,
    dump_data_to_json,
    folder_copy,
    load_data_from_json,
    read_file_into_list,
)
from tools.lib.training_log_path import get_train_log_path
from tools.lib.training_log_proc import (
    parse_pytorch_detection_metrics,
    run_subprocess_with_log_capture,
)

log = logging.getLogger("aftermarket.training")

PRJ_RUNNER = Path(__file__).resolve().parent / "prj_run.sh"

_FUNC_TYPE = {
    "dms1.0": "dms",
    "dms2.0": "dms",
    "bsd": "bsd",
    "hod": "hod",
    "cargo": "cargo",
}

#: train/val 划分的固定种子，保证同一批数据每次划分一致
SPLIT_SEED = 0
VAL_RATIO = 10


class TrainingRunner:
    """一次 train / eval / model_cvt 的执行器。"""

    def __init__(
        self,
        proc_type: str,
        task_type: str,
        task_func: str,
        model_tag: str = "latest",
    ) -> None:
        self.proc_type = proc_type
        self.task_type = task_type
        self.task_func = task_func
        self.model_tag = model_tag or "latest"
        self.spec: TaskSpec = get_task(task_type, task_func)
        self._prj_cache: dict[str, Path] = {}

        if not self.spec.prj:
            raise ValueError(
                f"{task_type}/{task_func} 未配置 fcos 工程名（prj），无法执行 {proc_type}"
            )

    # ------------------------------------------------------------------ #
    # 路径
    # ------------------------------------------------------------------ #
    @property
    def func_type(self) -> str:
        ft = _FUNC_TYPE.get(self.task_type.lower())
        if not ft:
            raise ValueError(f"未知任务类型 {self.task_type!r}，无法映射到 fcos 子目录")
        return ft

    @cached_property
    def prj_path(self) -> Path:
        return self.prj_dir_for(self.task_func)

    def prj_dir_for(self, task_func: str) -> Path:
        """定位 fcos 工程目录：真实工程优先，缺失时退回 `fcos/_mock` 同名目录。

        退到 mock 会打 warning —— 演示能跑通，但结果不是真模型产出。
        """
        if task_func in self._prj_cache:
            return self._prj_cache[task_func]

        spec = self.spec if task_func == self.task_func else get_task(self.task_type, task_func)
        real = env.FCOS_DIR / self.func_type / (spec.prj or "")
        if real.exists():
            resolved = real
        else:
            mock = env.FCOS_MOCK_DIR / self.func_type / (spec.prj or "")
            if mock.exists():
                log.warning("未找到真实 fcos 工程 %s，本次使用 mock：%s", real, mock)
                resolved = mock
            else:
                resolved = real

        self._prj_cache[task_func] = resolved
        return resolved

    @property
    def train_data_new_dir(self) -> Path:
        return env.AFTERMARKET_DATA_PATH / (self.spec.train_data or "")

    @property
    def train_data_old_dir(self) -> Path:
        return Path(str(self.train_data_new_dir).replace("_ai_new", "_ai_old"))

    @property
    def org_data_dir(self) -> Path:
        return env.AFTERMARKET_DATA_PATH / (self.spec.org_data or "")

    # ------------------------------------------------------------------ #
    # 对外入口
    # ------------------------------------------------------------------ #
    def run(self, thread_id: str = "", user_id: str = "", task_name: str = "") -> str:
        """按 proc_type 分派，日志路径由 user_id / task_name / thread_id 决定。"""
        log_path = get_train_log_path(user_id, task_name, thread_id)
        if self.proc_type == "train":
            return self.train(log_path)
        if self.proc_type == "eval":
            return self.evaluate(log_path)
        if self.proc_type == "model_cvt":
            return self.convert_model(log_path)
        return f"proc_type {self.proc_type!r} 不支持"

    def train(self, log_path: str | None = None) -> str:
        log.info("开始训练 %s/%s", self.task_type, self.task_func)
        self._run_prj("train", log_path)
        self._archive_checkpoint()
        return f"{self.spec.prj} train success"

    def evaluate(self, log_path: str | None = None) -> str:
        log.info("开始评估 %s/%s", self.task_type, self.task_func)

        pre_spec = self._pre_spec()
        if pre_spec is not None:
            log.info("先跑前级网络 %s", pre_spec.prj)
            TrainingRunner("eval", pre_spec.task_type, pre_spec.task_func, self.model_tag).evaluate(None)

        img_h, img_w, img_c = self._first_image_shape()
        eval_data_dir = self.prj_path / "eval_data"
        post_proc_folder: Path | None = None

        for step in self.spec.pipeline:
            if "pre_proc" in step:
                self._prepare_eval_data(step["pre_proc"], pre_spec, eval_data_dir)
                self._run_prj("eval", log_path)
            elif "post_proc" in step:
                post_proc_folder = self._apply_post_proc(
                    step["post_proc"], pre_spec, eval_data_dir, (img_w, img_h)
                )
            else:
                raise ValueError(f"pipeline 步骤无法识别：{list(step)}")

        if post_proc_folder is None:
            log.warning("pipeline 未产生 post_proc 结果，跳过结果整理")
            return f"{self.spec.prj} eval success（无后处理产物）"

        self._export_eval_result(post_proc_folder, (img_c, img_h, img_w))
        return f"{self.spec.prj} eval success, result saved in {env.MODEL_EVAL_RESULT_DIR}"

    def convert_model(self, log_path: str | None = None) -> str:
        log.info("开始模型转换 %s/%s", self.task_type, self.task_func)
        script = self._cvt_script()
        if script is None:
            raise FileNotFoundError(
                f"模型转换脚本不存在：{env.FCOS_DIR / self.func_type / 'lib/model_cvt/docker_model_cvt.sh'}"
            )

        self._run_cmd(
            ["bash", str(script), str(self.prj_path), self.model_tag],
            log_path,
            parse_fn=lambda line, lp: lp,
            env=self._sub_env(),
        )

        src = self.prj_path / "mode_convert" / "converted_models"
        dest = env.MODEL_CVT_RESULT_DIR
        create_new_folder(str(dest))
        if src.exists():
            folder_copy(str(src), str(dest))
        else:
            log.warning("转换产物目录不存在：%s", src)
        return f"{self.spec.prj} model convert success, model saved in {dest}"

    # ------------------------------------------------------------------ #
    # 训练数据生成
    # ------------------------------------------------------------------ #
    def build_train_data(self, src_img_dir: Path | None = None) -> str:
        """把标注数据转成训练格式，并做 train/val 划分。

        Returns:
            实际使用的预处理函数名；`none` 表示没有匹配到任何预处理。
        """
        src_img_dir = src_img_dir or env.IMG_WITH_LABEL_DIR
        first_step = self.spec.pipeline[0] if self.spec.pipeline else {}
        pre_proc = first_step.get("pre_proc") or {}
        if not pre_proc:
            raise ValueError(f"{self.task_type}/{self.task_func} 的 pipeline 缺少 pre_proc")

        new_dir = self.train_data_new_dir
        old_dir = self.train_data_old_dir
        new_dir.mkdir(parents=True, exist_ok=True)
        old_dir.mkdir(parents=True, exist_ok=True)

        # 历史数据归位到 _ai_old，_ai_new 只保留本次结果
        for item in list(new_dir.iterdir()):
            dst = old_dir / item.name
            if dst.exists():
                shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
            shutil.move(str(item), str(dst))
        self.gen_indices(old_dir)

        timestamp = time.strftime("%Y%m%d%H", time.localtime())
        dst_dir = new_dir / timestamp
        dst_dir.mkdir(parents=True, exist_ok=True)

        data_proc_name = "none"
        for func_name, func_args in pre_proc.items():
            if func_name == "src_img_copy":
                folder_copy(str(src_img_dir), str(dst_dir))
                data_proc_name = "src_img_copy"
            elif func_name == "crop_resize":
                folder_img_crop_resize(
                    str(src_img_dir),
                    str(dst_dir),
                    *func_args,
                    with_label_i=True,
                    clr_dst_folder_i=False,
                )
                data_proc_name = "crop_resize"
            elif func_name == "warp":
                img_warp_with_label(
                    str(src_img_dir),
                    *func_args[1],
                    str(dst_dir),
                    func_args[0],
                    warp_class="head",
                    clr_dst_folder_i=False,
                )
                data_proc_name = "warp"
            else:
                log.warning("未支持的预处理：%s", func_name)

        if data_proc_name == "none":
            return data_proc_name

        self.gen_indices(new_dir)
        log.info("训练数据已生成 %s/%s → %s", self.task_type, self.task_func, dst_dir)

        if data_proc_name != "src_img_copy":
            backup = self.org_data_dir / timestamp
            backup.mkdir(parents=True, exist_ok=True)
            for item in src_img_dir.iterdir():
                dst = backup / item.name
                if item.is_dir():
                    shutil.copytree(item, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst)
            log.info("原始标注已备份 → %s", backup)

        return data_proc_name

    @staticmethod
    def gen_indices(img_dir: Path, dst_dir: Path | None = None) -> None:
        """生成 train.txt / val.txt。

        固定随机种子 —— 原实现每次划分不同，导致同样的数据无法复现实验。
        """
        dst_dir = dst_dir or img_dir
        img_dir = Path(img_dir)
        dst_dir = Path(dst_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)

        indices = sorted(
            str(p.relative_to(img_dir).with_suffix("")) for p in img_dir.glob("**/*.jpg")
        )
        if not indices:
            log.warning("%s 下没有 .jpg，跳过索引生成", img_dir)
            return

        rng = random.Random(SPLIT_SEED)
        val_count = max(1, len(indices) // VAL_RATIO)
        val_indices = sorted(rng.sample(indices, min(val_count, len(indices))))

        (dst_dir / "train.txt").write_text("\n".join(indices), encoding="utf-8")
        (dst_dir / "val.txt").write_text("\n".join(val_indices), encoding="utf-8")
        log.info(
            "索引已生成 %s：train=%d val=%d", dst_dir, len(indices), len(val_indices)
        )

    # ------------------------------------------------------------------ #
    # 内部：执行 fcos 工程
    # ------------------------------------------------------------------ #
    def _pre_spec(self) -> TaskSpec | None:
        """前级网络规格（两阶段级联）。"""
        if not self.spec.pre_cnn:
            return None
        return get_task(self.task_type, self.spec.pre_cnn)

    def _cvt_script(self) -> Path | None:
        """模型转换脚本，真实工程优先、mock 兜底。"""
        rel = Path(self.func_type) / "lib" / "model_cvt" / "docker_model_cvt.sh"
        for base in (env.FCOS_DIR, env.FCOS_MOCK_DIR):
            candidate = base / rel
            if candidate.exists():
                return candidate
        return None

    def _run_prj(self, run_type: str, log_path: str | None) -> None:
        if not self.prj_path.exists():
            raise FileNotFoundError(
                f"fcos 工程目录不存在：{self.prj_path}\n"
                f"请放入真实 fcos 代码，或保留 fcos/_mock 以跑通演示链路。"
            )
        cmd = [
            "bash",
            str(PRJ_RUNNER),
            self.func_type,
            run_type,
            str(self.prj_path),
            self.model_tag,
            str(env.AFTERMARKET_DATA_PATH),
        ]
        self._run_cmd(cmd, log_path, parse_fn=parse_pytorch_detection_metrics, env=self._sub_env())

    @staticmethod
    def _sub_env() -> dict[str, str]:
        """子进程环境：把当前解释器告诉 prj_run.sh，避免 local 模式用到别的 python。"""
        return {**os.environ, "PYTHON_BIN": sys.executable}

    def _run_cmd(self, cmd: list[str], log_path: str | None, parse_fn, env: dict | None = None) -> None:
        if not log_path:
            subprocess.run(cmd, check=True, env=env)
            return
        metrics_path = str(Path(log_path).with_suffix(".metrics.jsonl"))
        run_subprocess_with_log_capture(cmd, log_path, metrics_path, parse_fn, env=env)

    def _archive_checkpoint(self) -> Path:
        """把最新 checkpoint 归档成带时间戳的副本（与 model_tag 语义对齐）。"""
        ckpt_dir = self.prj_path / "checkpoints"
        candidates = sorted(
            ckpt_dir.rglob("*epochs.pth"), key=lambda p: p.stat().st_mtime
        ) if ckpt_dir.exists() else []
        if not candidates:
            raise FileNotFoundError(f"训练结束但未找到 checkpoint：{ckpt_dir}")

        latest = candidates[-1]
        saved_dir = self.prj_path / "saved_checkpoints"
        saved_dir.mkdir(parents=True, exist_ok=True)

        prefix = self.spec.prj.rsplit("_", 1)[0] if "_" in self.spec.prj else self.spec.prj
        target = saved_dir / f"{prefix}_{time.strftime('%Y%m%d%H')}.pth"
        shutil.copy2(latest, target)
        log.info("checkpoint 已归档 → %s", target)
        return target

    # ------------------------------------------------------------------ #
    # 内部：评估预处理 / 后处理 / 结果导出
    # ------------------------------------------------------------------ #
    def _first_image_shape(self) -> tuple[int, int, int]:
        images = read_file_into_list(str(env.IMG_DIR), ".jpg", abs_path_i=True)
        if not images:
            raise FileNotFoundError(f"{env.IMG_DIR} 下没有 .jpg，无法评估")
        img_h, img_w, img_c = read_img_to_ndarray(images[0]).shape
        return img_h, img_w, img_c

    def _prepare_eval_data(
        self,
        pre_proc: dict,
        pre_spec: TaskSpec | None,
        eval_data_dir: Path,
    ) -> None:
        """按配置对源图做预处理，产出评估输入目录。"""
        if "src_img_copy" in pre_proc:
            create_new_folder(str(eval_data_dir))
            folder_copy(str(env.IMG_DIR), str(eval_data_dir))
        elif "crop_resize" in pre_proc:
            folder_img_crop_resize(
                str(env.IMG_DIR), str(eval_data_dir), *pre_proc["crop_resize"]
            )
        elif "warp" in pre_proc:
            if pre_spec is None:
                raise ValueError("warp 预处理需要前级网络（pre_cnn），但未配置")
            pre_prj_path = self.prj_dir_for(pre_spec.task_func)
            cnn_result_file = pre_prj_path / "post_proc_results" / "cnn_result.json"
            img_warp_perspective(
                str(env.IMG_DIR),
                str(cnn_result_file),
                *pre_proc["warp"][1],
                str(eval_data_dir),
                pre_proc["warp"][0],
            )
        else:
            raise ValueError(f"未支持的预处理：{list(pre_proc)}")

    def _apply_post_proc(
        self,
        post_proc_list: list[dict],
        pre_spec: TaskSpec | None,
        eval_data_dir: Path,
        img_wh: tuple[int, int],
    ) -> Path:
        """把网络输出反算回原图坐标，必要时与前级结果合并。"""
        post_proc_folder = self.prj_path / "post_proc_results"
        img_w, img_h = img_wh

        for post_proc in post_proc_list:
            if "cnn_bbox_remap_to_src" not in post_proc:
                raise ValueError(f"未支持的后处理：{list(post_proc)}")

            cfg = post_proc["cnn_bbox_remap_to_src"]
            cnn_result = filter_cnn_result(
                str(self.prj_path / "results" / "cnn_result.txt"),
                bbox_num=[1, 2, 3],
                obj_cls=[],
            )
            create_new_folder(str(post_proc_folder))
            det_classes = get_det_classes(str(self.prj_path))

            if "crop_resize" in cfg:
                bbox_dict = bbox_remap(
                    cnn_result, det_classes, (img_w, img_h), *cfg["crop_resize"], mode_i="dst2src"
                )
            elif "warp" in cfg:
                warp_param = load_data_from_json(str(eval_data_dir / "warp_param.json"))
                bbox_dict = bbox_remap(
                    cnn_result,
                    det_classes,
                    (img_w, img_h),
                    src_warp_dict_i=warp_param,
                    mode_i="dst2src",
                )
            else:
                raise ValueError(f"未支持的后处理参数：{list(cfg)}")

            if pre_spec is not None:
                pre_result = load_data_from_json(
                    str(self.prj_dir_for(pre_spec.task_func) / "post_proc_results" / "cnn_result.json")
                )
                bbox_dict = bbox_dict_merge([pre_result, bbox_dict])

            dump_data_to_json(str(post_proc_folder / "cnn_result.json"), bbox_dict)

        return post_proc_folder

    def _export_eval_result(
        self, post_proc_folder: Path, img_shape_chw: tuple[int, int, int]
    ) -> None:
        """把评估结果整理成人可看的目录：原图 + 标注 xml + 可视化图。"""
        root = env.MODEL_EVAL_RESULT_DIR
        src_with_label = root / "src_img_with_lable"
        vis_img = root / "vis_eval_result_img"
        vis_video = root / "vis_eval_result_video"
        for p in (root, src_with_label, vis_img, vis_video):
            create_new_folder(str(p))

        folder_copy(str(env.IMG_DIR), str(src_with_label))
        gen_xml_with_bbox_dict(
            str(post_proc_folder / "cnn_result.json"),
            str(src_with_label),
            img_shape_i=img_shape_chw,
        )
        draw_bbox_with_xml(str(src_with_label), str(vis_img), color_i=(0, 0, 255), thickness_i=2)
