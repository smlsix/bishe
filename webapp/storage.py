from __future__ import annotations

import csv
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils.tools import writexls


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "output" / "webapp"
RUNS_DIR = OUTPUT_ROOT / "runs"
HISTORY_DIR = OUTPUT_ROOT / "history"
EXPORT_DIR = OUTPUT_ROOT / "exports"
HISTORY_FILE = HISTORY_DIR / "records.json"


class HistoryStore:
    def __init__(self, base_dir: Path = OUTPUT_ROOT) -> None:
        self.base_dir = Path(base_dir)
        self.runs_dir = self.base_dir / "runs"
        self.history_dir = self.base_dir / "history"
        self.export_dir = self.base_dir / "exports"
        self.history_file = self.history_dir / "records.json"
        self._lock = threading.Lock()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self.history_file.write_text("[]", encoding="utf-8")

    def create_run_dir(self, task_type: str) -> Path:
        run_name = f"{task_type}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')}"
        run_dir = self.runs_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def to_media_url(self, path: Optional[Path]) -> Optional[str]:
        if path is None:
            return None
        resolved = Path(path).resolve()
        relative = resolved.relative_to(self.base_dir.resolve()).as_posix()
        return f"/media/{relative}"

    def write_json(self, path: Path, payload: Dict) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_records(self, limit: Optional[int] = None) -> List[Dict]:
        with self._lock:
            records = self._load_records_unlocked()
        if limit is None:
            return records
        return records[:limit]

    def count(self) -> int:
        with self._lock:
            return len(self._load_records_unlocked())

    def add_record(self, record: Dict) -> Dict:
        with self._lock:
            records = self._load_records_unlocked()
            records.insert(0, record)
            self.history_file.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return record

    def get_record(self, record_id: str) -> Optional[Dict]:
        with self._lock:
            records = self._load_records_unlocked()
        for record in records:
            if record.get("id") == record_id:
                return record
        return None

    def export_history(self, export_format: str) -> Path:
        records = self.list_records()
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        rows = [
            [
                "ID",
                "Created At",
                "Task Type",
                "Source Name",
                "Model",
                "Device",
                "Confidence",
                "Image Size",
                "Detection Count",
                "Frame Count",
                "FPS",
                "Latency Seconds",
                "Class Counts",
                "Source URL",
                "Result URL",
                "CSV URL",
            ]
        ]

        for record in records:
            summary = record.get("summary", {})
            class_counts = summary.get("class_counts", {})
            rows.append(
                [
                    record.get("id", ""),
                    record.get("created_at", ""),
                    record.get("task_type", ""),
                    record.get("source_name", ""),
                    record.get("model_label", ""),
                    record.get("device", ""),
                    summary.get("confidence", ""),
                    summary.get("image_size", ""),
                    summary.get("detection_count", ""),
                    summary.get("frame_count", ""),
                    summary.get("fps", ""),
                    summary.get("latency_seconds", ""),
                    json.dumps(class_counts, ensure_ascii=False),
                    record.get("source_url", ""),
                    record.get("result_url", ""),
                    record.get("csv_url", ""),
                ]
            )

        if export_format == "csv":
            export_path = self.export_dir / f"history_{timestamp}.csv"
            with open(export_path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerows(rows)
            return export_path

        if export_format == "xls":
            export_path = self.export_dir / f"history_{timestamp}.xls"
            writexls(rows, str(export_path))
            return export_path

        raise ValueError("Unsupported export format. Use csv or xls.")

    def _load_records_unlocked(self) -> List[Dict]:
        try:
            payload = self.history_file.read_text(encoding="utf-8")
            records = json.loads(payload)
            if isinstance(records, list):
                return records
        except (json.JSONDecodeError, OSError):
            pass
        return []
