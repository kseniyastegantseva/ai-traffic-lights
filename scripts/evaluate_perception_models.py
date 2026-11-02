"""Compare COCO and VisDrone YOLO counts, multiscale crops, and NMS effects.

Run from the repository root. The evaluator imports the existing detector from
the nested computer-vision source tree but writes outputs only to the requested
output path. It does not edit that source tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CV_SOURCE = ROOT / "computer-vision"
if str(CV_SOURCE) not in sys.path:
    sys.path.insert(0, str(CV_SOURCE))

import cv2
import main as detector
import torch
from auto_zones import create_auto_zones
from ultralytics import YOLO

LANES = ("north", "south", "west", "east")
COCO_CLASSES = (2, 3, 5, 7)  # car, motorcycle, bus, truck
VISDRONE_CLASSES = (0, 1, 2, 3)
VARIANTS = (
    "coco_yolo11s_single",
    "visdrone_single",
    "visdrone_full_only",
    "visdrone_plus_x2_nms",
    "visdrone_plus_x2_no_nms",
    "visdrone_plus_x3_nms",
    "visdrone_plus_x3_no_nms",
    "visdrone_plus_x2_x3_nms",
    "visdrone_plus_x2_x3_no_nms",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_metadata(model: YOLO) -> dict[str, Any]:
    checkpoint = getattr(model, "ckpt", None)
    if not isinstance(checkpoint, dict):
        return {}
    training = checkpoint.get("train_args")
    keys = ("data", "epochs", "imgsz", "batch", "seed", "model", "pretrained")
    return {
        key: checkpoint.get(key)
        for key in ("date", "version", "license", "epoch")
    } | {
        "train_args": {key: training.get(key) for key in keys}
        if isinstance(training, dict)
        else None
    }


def load_coco_model(path: Path) -> tuple[YOLO, Path]:
    if path.exists():
        return YOLO(str(path)), path
    if path.name != "yolo11s.pt":
        raise FileNotFoundError(f"COCO weights not found: {path}")

    cache_dir = Path(tempfile.gettempdir()) / "ai-traffic-lights-models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_weights = cache_dir / path.name
    if not cached_weights.exists():
        previous_directory = Path.cwd()
        try:
            os.chdir(cache_dir)
            model = YOLO(path.name)
        finally:
            os.chdir(previous_directory)
        return model, cached_weights
    return YOLO(str(cached_weights)), cached_weights


def single_scale_counts(
    model: YOLO, image: Any, zones: dict, class_ids: Sequence[int], device: str
) -> dict[str, int]:
    counts = {lane: 0 for lane in LANES}
    result = model.predict(
        image,
        classes=list(class_ids),
        conf=0.03,
        imgsz=1280,
        device=device,
        verbose=False,
    )[0]
    for box in result.boxes:
        x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
        lane = detector.get_zone_for_point((x1 + x2) / 2, (y1 + y2) / 2, zones)
        if lane:
            counts[lane] += 1
    return counts


def summarize(
    name: str, predictions: dict[str, dict[str, int]], ground_truth: dict
) -> dict:
    absolute_error = sum(
        abs(predictions[image][lane] - counts[lane])
        for image, counts in ground_truth.items()
        for lane in LANES
    )
    actual_total = sum(counts[lane] for counts in ground_truth.values() for lane in LANES)
    predicted_total = sum(
        counts[lane] for counts in predictions.values() for lane in LANES
    )
    per_lane = {
        lane: {
            "actual": sum(counts[lane] for counts in ground_truth.values()),
            "predicted": sum(counts[lane] for counts in predictions.values()),
        }
        for lane in LANES
    }
    return {
        "variant": name,
        "images": len(ground_truth),
        "directional_pairs": len(ground_truth) * len(LANES),
        "total_actual": actual_total,
        "total_predicted": predicted_total,
        "sum_abs_directional_error": absolute_error,
        "vehicle_count_accuracy_percent": max(
            0.0, 100 * (1 - absolute_error / actual_total)
        ),
        "directional_mae": absolute_error / (len(ground_truth) * len(LANES)),
        "per_lane": per_lane,
    }


def evaluate(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    cv2.setNumThreads(1)
    ground_truth_path = args.test_dir / "ground_truth.json"
    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    if not ground_truth:
        raise ValueError(f"No test images found in {ground_truth_path}")

    coco, coco_path = load_coco_model(args.coco_weights)
    visdrone_path = args.visdrone_weights.resolve()
    if not visdrone_path.exists():
        raise FileNotFoundError(f"VisDrone weights not found: {visdrone_path}")
    visdrone = YOLO(str(visdrone_path))

    predictions: dict[str, dict[str, dict[str, int]]] = {
        variant: {} for variant in VARIANTS
    }
    per_image: dict[str, dict] = {}
    for image_name, actual in ground_truth.items():
        image_path = args.test_dir / image_name
        image = cv2.imread(str(image_path))
        if image is None:
            raise RuntimeError(f"Could not read image: {image_path}")
        zones = create_auto_zones(image_path)
        predictions["coco_yolo11s_single"][image_name] = single_scale_counts(
            coco, image, zones, COCO_CLASSES, args.device
        )
        predictions["visdrone_single"][image_name] = single_scale_counts(
            visdrone, image, zones, VISDRONE_CLASSES, args.device
        )
        image_result = {
            "actual": actual,
            "coco_yolo11s_single": predictions["coco_yolo11s_single"][image_name],
            "visdrone_single": predictions["visdrone_single"][image_name],
        }

        for scales, label in (
            ([], "full_only"),
            ([2.0], "plus_x2"),
            ([3.0], "plus_x3"),
            ([2.0, 3.0], "plus_x2_x3"),
        ):
            detector.SCALES = scales
            detections: list[dict] = []
            detector.detect_full_image(image, zones, detections)
            if scales:
                detector.detect_zone_crops(image, zones, detections)
            raw_result = detector.create_result(image, zones, detections)[1]
            deduplicated_result = detector.create_result(
                image, zones, detector.remove_duplicates(detections)
            )[1]
            raw = {lane: int(raw_result[lane]) for lane in LANES}
            deduplicated = {lane: int(deduplicated_result[lane]) for lane in LANES}
            if not scales:
                predictions["visdrone_full_only"][image_name] = deduplicated
                image_result["visdrone_full_only"] = deduplicated
                continue

            raw_key = f"visdrone_{label}_no_nms"
            nms_key = f"visdrone_{label}_nms"
            predictions[raw_key][image_name] = raw
            predictions[nms_key][image_name] = deduplicated
            image_result[raw_key] = raw
            image_result[nms_key] = deduplicated
        per_image[image_name] = image_result
        print(f"Processed {image_name} ({len(per_image)}/{len(ground_truth)})", flush=True)

    detector.SCALES = [2.0, 3.0]
    summaries = [summarize(name, result, ground_truth) for name, result in predictions.items()]
    return {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "environment": {
            "ultralytics": __import__("ultralytics").__version__,
            "torch": torch.__version__,
            "device": args.device,
            "torch_threads": torch.get_num_threads(),
        },
        "ground_truth": str(ground_truth_path),
        "weights": {
            "coco_yolo11s": {
                "path": str(coco_path),
                "sha256": sha256(coco_path),
                "checkpoint": checkpoint_metadata(coco),
            },
            "visdrone_finetuned": {
                "path": str(visdrone_path),
                "sha256": sha256(visdrone_path),
                "checkpoint": checkpoint_metadata(visdrone),
            },
        },
        "inference": {
            "imgsz": 1280,
            "single_scale_confidence": 0.03,
            "coco_vehicle_classes": list(COCO_CLASSES),
            "visdrone_vehicle_classes": list(VISDRONE_CLASSES),
            "multiscale": {
                "crop_scales": [2, 3],
                "crop_confidence": detector.CROP_CONF,
                "iou_deduplication_threshold": detector.IOU_THRESHOLD,
                "zone_padding_pixels": detector.PADDING,
            },
        },
        "summary": summaries,
        "per_image": per_image,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-dir", type=Path, default=ROOT / "computer-vision/data/test")
    parser.add_argument(
        "--visdrone-weights", type=Path, default=ROOT / "models/visdrone_vehicles.pt"
    )
    parser.add_argument(
        "--coco-weights",
        type=Path,
        default=Path(tempfile.gettempdir()) / "ai-traffic-lights-models/yolo11s.pt",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/perception_comparison.json"
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    result = evaluate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
