from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

import utils.font_sync  # noqa: F401
from ultralytics import YOLO
from utils.parser import get_config
from utils.tools import draw_info
from webapp.storage import HistoryStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "configs.yaml"
WEIGHTS_DIR = PROJECT_ROOT / "weights"


class YoloWebService:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.project_root = PROJECT_ROOT
        self.config_path = Path(config_path)
        self.storage = HistoryStore()
        self._load_lock = threading.Lock()
        self._predict_lock = threading.Lock()
        self._models: Dict[str, YOLO] = {}

        config = self._load_config()
        self.default_weight_path = self._resolve_path(str(config.MODEL.WEIGHT))
        self.default_confidence = float(config.MODEL.CONF)
        self.default_image_size = int(config.MODEL.IMGSIZE)
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.draw_chinese = bool(config.CONFIG.draw_chinese)
        self.class_name_map = dict(config.CONFIG.chinese_name)
        self.available_models = self._discover_models()
        self.default_model_id = self._choose_default_model_id()

    def _load_config(self):
        cfg = get_config()
        cfg.merge_from_file(str(self.config_path))
        return cfg

    def _resolve_path(self, value: str) -> Path:
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate
        return (self.project_root / candidate).resolve()

    def _relative_path(self, value: Path) -> str:
        try:
            return value.relative_to(self.project_root).as_posix()
        except ValueError:
            return str(value)

    def _discover_models(self) -> List[Dict[str, Any]]:
        discovered: List[Dict[str, Any]] = []
        seen = set()

        def add_model(path: Path) -> None:
            resolved = Path(path).resolve()
            if not resolved.exists() or resolved.suffix.lower() != ".pt":
                return

            model_id = self._relative_path(resolved)
            if model_id in seen:
                return
            seen.add(model_id)

            if resolved.parent.name == "weights" and resolved.parent.parent != resolved.parent:
                model_name = resolved.parent.parent.name
            else:
                model_name = resolved.parent.name

            discovered.append(
                {
                    "id": model_id,
                    "label": f"{model_name} / {resolved.stem}",
                    "path": resolved,
                    "relative_path": model_id,
                }
            )

        add_model(self.default_weight_path)
        if WEIGHTS_DIR.exists():
            for weight_path in sorted(WEIGHTS_DIR.rglob("*.pt")):
                add_model(weight_path)

        if not discovered:
            raise FileNotFoundError("No .pt model file was found in the weights directory.")

        return discovered

    def _choose_default_model_id(self) -> str:
        default_relative = self._relative_path(self.default_weight_path)
        for model in self.available_models:
            if model["id"] == default_relative:
                return model["id"]
        return self.available_models[0]["id"]

    def app_info(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "default_confidence": self.default_confidence,
            "default_image_size": self.default_image_size,
            "draw_chinese": self.draw_chinese,
            "default_model_id": self.default_model_id,
            "models": self.list_models(),
            "history_count": self.storage.count(),
        }

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model["id"],
                "label": model["label"],
                "relative_path": model["relative_path"],
                "is_default": model["id"] == self.default_model_id,
                "is_loaded": model["id"] in self._models,
            }
            for model in self.available_models
        ]

    def history_records(self, limit: int = 50) -> List[Dict]:
        return self.storage.list_records(limit=limit)

    def history_record_detail(self, record_id: str) -> Dict:
        record = self.storage.get_record(record_id)
        if record is None:
            raise ValueError("History record was not found.")

        detail_path = record.get("detail_path")
        if not detail_path:
            return record

        absolute_detail = self.project_root / detail_path
        if not absolute_detail.exists():
            raise ValueError("History detail file does not exist anymore.")

        import json

        return json.loads(absolute_detail.read_text(encoding="utf-8"))

    def export_history(self, export_format: str) -> Path:
        return self.storage.export_history(export_format)

    def process_image_upload(
        self,
        image_bytes: bytes,
        filename: str,
        model_id: Optional[str] = None,
        confidence: Optional[float] = None,
        image_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._process_still(
            payload=image_bytes,
            filename=filename,
            task_type="image",
            model_id=model_id,
            confidence=confidence,
            image_size=image_size,
        )

    def process_image_batch(
        self,
        files: List[Tuple[bytes, str]],
        model_id: Optional[str] = None,
        confidence: Optional[float] = None,
        image_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not files:
            raise ValueError("Please choose at least one image.")

        model_spec, model = self._get_model(model_id)
        conf_value = self._normalize_confidence(confidence)
        img_size_value = self._normalize_image_size(image_size)

        run_dir = self.storage.create_run_dir("image_batch")
        sources_dir = run_dir / "sources"
        results_dir = run_dir / "results"
        sources_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        csv_path = run_dir / "batch_results.csv"
        meta_path = run_dir / "meta.json"

        total_started_at = time.perf_counter()
        aggregated_counts = Counter()
        items: List[Dict[str, Any]] = []
        used_names = set()

        with open(csv_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "image_name",
                    "detection_count",
                    "class_name",
                    "display_name",
                    "confidence",
                    "x1",
                    "y1",
                    "x2",
                    "y2",
                    "result_path",
                ]
            )

            for index, (payload, filename) in enumerate(files, start=1):
                safe_name = self._dedupe_filename(
                    self._safe_filename(filename, fallback=f"image_{index}.jpg"),
                    used_names,
                )
                source_suffix = Path(safe_name).suffix.lower() or ".jpg"
                source_path = sources_dir / safe_name
                source_path.write_bytes(payload)

                image = self._decode_image(payload)
                frame_result = self._infer_frame(image, model, conf_value, img_size_value)

                result_stem = Path(safe_name).stem
                result_path = results_dir / f"{result_stem}_result.jpg"
                self._save_image(result_path, frame_result["annotated_image"])

                item = {
                    "index": index,
                    "source_name": safe_name,
                    "image": frame_result["image"],
                    "summary": frame_result["summary"],
                    "detections": frame_result["detections"],
                    "source_url": self.storage.to_media_url(source_path),
                    "result_url": self.storage.to_media_url(result_path),
                }
                items.append(item)
                aggregated_counts.update(frame_result["summary"]["class_counts"])

                if frame_result["detections"]:
                    for detection in frame_result["detections"]:
                        bbox = detection["bbox"]
                        writer.writerow(
                            [
                                safe_name,
                                frame_result["summary"]["detection_count"],
                                detection["class_name"],
                                detection["display_name"],
                                detection["confidence"],
                                bbox["x1"],
                                bbox["y1"],
                                bbox["x2"],
                                bbox["y2"],
                                self._relative_path(result_path),
                            ]
                        )
                else:
                    writer.writerow([safe_name, 0, "", "", "", "", "", "", "", self._relative_path(result_path)])

        total_latency = round(time.perf_counter() - total_started_at, 3)
        total_detections = sum(item["summary"]["detection_count"] for item in items)
        avg_latency = round(
            sum(item["summary"]["latency_seconds"] for item in items) / len(items),
            3,
        ) if items else 0.0
        avg_pipeline_ms = round(
            sum(item["summary"]["pipeline_ms"] for item in items) / len(items),
            2,
        ) if items else 0.0
        throughput_fps = round(len(items) / total_latency, 2) if total_latency > 0 else 0.0

        record_id = self._make_record_id("image_batch")
        created_at = self._timestamp()
        summary = {
            "image_count": len(items),
            "detection_count": total_detections,
            "class_counts": dict(aggregated_counts),
            "confidence": conf_value,
            "image_size": img_size_value,
            "latency_seconds": total_latency,
            "pipeline_ms": avg_pipeline_ms,
            "fps": throughput_fps,
            "avg_image_latency_seconds": avg_latency,
        }

        response = {
            "id": record_id,
            "created_at": created_at,
            "task_type": "image_batch",
            "source_name": f"{len(items)} images",
            "model_id": model_spec["id"],
            "model_label": model_spec["label"],
            "device": self.device,
            "summary": summary,
            "items": items,
            "csv_url": self.storage.to_media_url(csv_path),
            "meta_url": self.storage.to_media_url(meta_path),
            "preview_url": items[0]["result_url"] if items else None,
        }

        detail = dict(response)
        detail["run_name"] = run_dir.name
        detail["record_file"] = self._relative_path(meta_path)
        detail["detail_path"] = self._relative_path(meta_path)
        self.storage.write_json(meta_path, detail)

        history_record = {
            key: value for key, value in response.items() if key != "items"
        }
        history_record["detail_path"] = self._relative_path(meta_path)
        history_record["run_name"] = run_dir.name
        self.storage.add_record(history_record)
        return response

    def process_camera_frame(
        self,
        image_bytes: bytes,
        filename: str,
        model_id: Optional[str] = None,
        confidence: Optional[float] = None,
        image_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._process_still(
            payload=image_bytes,
            filename=filename,
            task_type="camera",
            model_id=model_id,
            confidence=confidence,
            image_size=image_size,
        )

    def process_video_upload(
        self,
        video_bytes: bytes,
        filename: str,
        model_id: Optional[str] = None,
        confidence: Optional[float] = None,
        image_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        model_spec, model = self._get_model(model_id)
        conf_value = self._normalize_confidence(confidence)
        img_size_value = self._normalize_image_size(image_size)
        safe_name = self._safe_filename(filename, fallback="video.mp4")
        source_suffix = Path(safe_name).suffix.lower() or ".mp4"

        run_dir = self.storage.create_run_dir("video")
        source_path = run_dir / f"source{source_suffix}"
        source_path.write_bytes(video_bytes)

        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            raise ValueError("Uploaded file is not a valid video.")

        frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        source_fps = float(capture.get(cv2.CAP_PROP_FPS)) or 25.0
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        result_path = run_dir / "result.mp4"
        preview_path = run_dir / "preview.jpg"
        csv_path = run_dir / "frame_results.csv"
        meta_path = run_dir / "meta.json"

        writer, video_codec = self._create_video_writer(
            result_path=result_path,
            fps=source_fps if source_fps > 0 else 25.0,
            frame_size=(frame_width, frame_height),
        )

        aggregated_counts = Counter()
        total_detections = 0
        frames_processed = 0
        latency_values: List[float] = []
        pipeline_values: List[float] = []

        started_at = time.perf_counter()
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as file:
            writer_csv = csv.writer(file)
            writer_csv.writerow(
                [
                    "frame_index",
                    "detection_count",
                    "class_name",
                    "display_name",
                    "confidence",
                    "x1",
                    "y1",
                    "x2",
                    "y2",
                ]
            )

            while True:
                success, frame = capture.read()
                if not success:
                    break

                frame_result = self._infer_frame(frame, model, conf_value, img_size_value)
                writer.write(frame_result["annotated_image"])

                frames_processed += 1
                total_detections += frame_result["summary"]["detection_count"]
                aggregated_counts.update(frame_result["summary"]["class_counts"])
                latency_values.append(frame_result["summary"]["latency_seconds"])
                pipeline_values.append(frame_result["summary"]["pipeline_ms"])

                if frames_processed == 1:
                    self._save_image(preview_path, frame_result["annotated_image"])

                if frame_result["detections"]:
                    for detection in frame_result["detections"]:
                        bbox = detection["bbox"]
                        writer_csv.writerow(
                            [
                                frames_processed,
                                frame_result["summary"]["detection_count"],
                                detection["class_name"],
                                detection["display_name"],
                                detection["confidence"],
                                bbox["x1"],
                                bbox["y1"],
                                bbox["x2"],
                                bbox["y2"],
                            ]
                        )
                else:
                    writer_csv.writerow([frames_processed, 0, "", "", "", "", "", "", ""])

        capture.release()
        writer.release()

        if frames_processed == 0:
            raise ValueError("Uploaded video does not contain readable frames.")

        total_latency = round(time.perf_counter() - started_at, 3)
        avg_pipeline_ms = round(sum(pipeline_values) / len(pipeline_values), 2) if pipeline_values else 0.0
        processing_fps = round(frames_processed / total_latency, 2) if total_latency > 0 else 0.0
        avg_frame_latency = round(sum(latency_values) / len(latency_values), 3) if latency_values else 0.0

        record_id = self._make_record_id("video")
        created_at = self._timestamp()
        summary = {
            "detection_count": total_detections,
            "class_counts": dict(aggregated_counts),
            "confidence": conf_value,
            "image_size": img_size_value,
            "latency_seconds": total_latency,
            "pipeline_ms": avg_pipeline_ms,
            "fps": processing_fps,
            "frame_count": frames_processed,
            "source_fps": round(source_fps, 2),
            "total_frames": total_frames,
            "avg_frame_latency_seconds": avg_frame_latency,
        }

        response = {
            "id": record_id,
            "created_at": created_at,
            "task_type": "video",
            "source_name": safe_name,
            "model_id": model_spec["id"],
            "model_label": model_spec["label"],
            "device": self.device,
            "summary": summary,
            "source_url": self.storage.to_media_url(source_path),
            "result_url": self.storage.to_media_url(result_path),
            "preview_url": self.storage.to_media_url(preview_path),
            "csv_url": self.storage.to_media_url(csv_path),
            "meta_url": self.storage.to_media_url(meta_path),
            "video": {
                "width": frame_width,
                "height": frame_height,
                "codec": video_codec,
            },
        }

        detail = dict(response)
        detail["run_name"] = run_dir.name
        detail["record_file"] = self._relative_path(meta_path)
        detail["detail_path"] = self._relative_path(meta_path)
        self.storage.write_json(meta_path, detail)

        history_record = dict(response)
        history_record["detail_path"] = self._relative_path(meta_path)
        history_record["run_name"] = run_dir.name
        self.storage.add_record(history_record)
        return response

    def _process_still(
        self,
        payload: bytes,
        filename: str,
        task_type: str,
        model_id: Optional[str],
        confidence: Optional[float],
        image_size: Optional[int],
    ) -> Dict[str, Any]:
        safe_name = self._safe_filename(filename, fallback=f"{task_type}.jpg")
        source_suffix = Path(safe_name).suffix.lower() or ".jpg"
        model_spec, model = self._get_model(model_id)
        conf_value = self._normalize_confidence(confidence)
        img_size_value = self._normalize_image_size(image_size)

        run_dir = self.storage.create_run_dir(task_type)
        source_path = run_dir / f"source{source_suffix}"
        source_path.write_bytes(payload)

        image = self._decode_image(payload)
        frame_result = self._infer_frame(image, model, conf_value, img_size_value)

        result_path = run_dir / "result.jpg"
        csv_path = run_dir / "result.csv"
        meta_path = run_dir / "meta.json"

        self._save_image(result_path, frame_result["annotated_image"])
        self._write_still_csv(csv_path, frame_result["detections"])

        record_id = self._make_record_id(task_type)
        created_at = self._timestamp()
        response = {
            "id": record_id,
            "created_at": created_at,
            "task_type": task_type,
            "source_name": safe_name,
            "model_id": model_spec["id"],
            "model_label": model_spec["label"],
            "device": self.device,
            "image": frame_result["image"],
            "summary": frame_result["summary"],
            "detections": frame_result["detections"],
            "source_url": self.storage.to_media_url(source_path),
            "result_url": self.storage.to_media_url(result_path),
            "csv_url": self.storage.to_media_url(csv_path),
            "meta_url": self.storage.to_media_url(meta_path),
        }

        detail = dict(response)
        detail["run_name"] = run_dir.name
        detail["record_file"] = self._relative_path(meta_path)
        detail["detail_path"] = self._relative_path(meta_path)
        self.storage.write_json(meta_path, detail)

        history_record = {
            key: value for key, value in response.items() if key != "detections"
        }
        history_record["detail_path"] = self._relative_path(meta_path)
        history_record["run_name"] = run_dir.name
        self.storage.add_record(history_record)
        return response

    def _get_model(self, model_id: Optional[str]) -> Tuple[Dict[str, Any], YOLO]:
        resolved_model_id = model_id or self.default_model_id
        spec = None
        for item in self.available_models:
            if item["id"] == resolved_model_id:
                spec = item
                break
        if spec is None:
            raise ValueError("Selected model does not exist.")

        if resolved_model_id not in self._models:
            with self._load_lock:
                if resolved_model_id not in self._models:
                    self._models[resolved_model_id] = YOLO(str(spec["path"]))

        return spec, self._models[resolved_model_id]

    def _infer_frame(
        self,
        image: np.ndarray,
        model: YOLO,
        confidence: float,
        image_size: int,
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        with self._predict_lock:
            results = model.predict(
                image,
                imgsz=image_size,
                conf=confidence,
                device=self.device,
                verbose=False,
            )
        latency_seconds = round(time.perf_counter() - started_at, 3)

        detections = []
        class_counts = Counter()
        draw_results = []

        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy().tolist()
            confidences = result.boxes.conf.cpu().numpy().tolist()
            classes = result.boxes.cls.cpu().numpy().tolist()
            names = result.names

            for box, score, cls_idx in zip(boxes, confidences, classes):
                class_name = names[int(cls_idx)]
                display_name = self.class_name_map.get(class_name, class_name) if self.draw_chinese else class_name
                detection = {
                    "class_name": class_name,
                    "display_name": display_name,
                    "confidence": round(float(score), 4),
                    "bbox": {
                        "x1": round(float(box[0]), 2),
                        "y1": round(float(box[1]), 2),
                        "x2": round(float(box[2]), 2),
                        "y2": round(float(box[3]), 2),
                    },
                }
                detections.append(detection)
                class_counts[display_name] += 1
                draw_results.append([class_name, float(score), box])

        annotated_image = draw_info(
            image.copy(),
            draw_results,
            draw_chinese=self.draw_chinese,
            chinese_name=self.class_name_map,
        )

        stage_speed = results[0].speed if results else {}
        pipeline_ms = round(
            float(stage_speed.get("preprocess", 0.0))
            + float(stage_speed.get("inference", 0.0))
            + float(stage_speed.get("postprocess", 0.0)),
            2,
        )
        fps = round(1000.0 / pipeline_ms, 2) if pipeline_ms > 0 else 0.0
        height, width = image.shape[:2]

        return {
            "image": {"width": width, "height": height},
            "annotated_image": annotated_image,
            "detections": detections,
            "summary": {
                "detection_count": len(detections),
                "class_counts": dict(class_counts),
                "confidence": confidence,
                "image_size": image_size,
                "latency_seconds": latency_seconds,
                "pipeline_ms": pipeline_ms,
                "fps": fps,
            },
        }

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        if not image_bytes:
            raise ValueError("Uploaded image is empty.")

        file_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Uploaded file is not a valid image.")
        return image

    def _save_image(self, path: Path, image: np.ndarray) -> None:
        ok, encoded = cv2.imencode(".jpg", image)
        if not ok:
            raise ValueError("Failed to encode the result image.")
        path.write_bytes(encoded.tobytes())

    def _create_video_writer(
        self,
        result_path: Path,
        fps: float,
        frame_size: Tuple[int, int],
    ) -> Tuple[cv2.VideoWriter, str]:
        # Prefer avc1 for browser playback and fall back to mp4v if the local
        # OpenCV/FFmpeg build cannot open the H.264-compatible writer.
        for codec in ("avc1", "mp4v"):
            writer = cv2.VideoWriter(
                str(result_path),
                cv2.VideoWriter_fourcc(*codec),
                fps,
                frame_size,
            )
            if writer.isOpened():
                return writer, codec
            writer.release()

        raise ValueError("Failed to create a video writer for the result video.")

    def _write_still_csv(self, path: Path, detections: List[Dict[str, Any]]) -> None:
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["class_name", "display_name", "confidence", "x1", "y1", "x2", "y2"])
            for detection in detections:
                bbox = detection["bbox"]
                writer.writerow(
                    [
                        detection["class_name"],
                        detection["display_name"],
                        detection["confidence"],
                        bbox["x1"],
                        bbox["y1"],
                        bbox["x2"],
                        bbox["y2"],
                    ]
                )

    def _normalize_confidence(self, value: Optional[float]) -> float:
        if value is None:
            return self.default_confidence
        value = float(value)
        if value < 0 or value > 1:
            raise ValueError("Confidence must be between 0 and 1.")
        return value

    def _normalize_image_size(self, value: Optional[int]) -> int:
        if value is None:
            return self.default_image_size
        value = int(value)
        if value < 32:
            raise ValueError("Image size must be at least 32.")
        return value

    def _safe_filename(self, filename: str, fallback: str) -> str:
        candidate = Path(filename or fallback).name
        if not candidate:
            candidate = fallback
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate)
        return sanitized or fallback

    def _dedupe_filename(self, filename: str, used_names: set) -> str:
        if filename not in used_names:
            used_names.add(filename)
            return filename

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        index = 2
        while True:
            candidate = f"{stem}_{index}{suffix}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            index += 1

    def _make_record_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:10]}"

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@lru_cache(maxsize=1)
def get_service() -> YoloWebService:
    return YoloWebService()
