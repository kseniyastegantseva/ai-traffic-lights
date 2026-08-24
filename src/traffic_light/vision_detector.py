"""
Модуль обнаружения и подсчёта транспортных средств на изображении перекрёстка.

Модуль реализует полный цикл анализа транспортной обстановки:
1. автоматически формирует зоны подходов NORTH, SOUTH, WEST и EAST;
2. выполняет детекцию транспортных средств на полном изображении с помощью YOLO11m;
3. выполняет многомасштабную детекцию отдельных зон;
4. применяет геометрическое восстановление части ошибочно классифицированных объектов;
5. удаляет повторные детекции с использованием коэффициента IoU;
6. подсчитывает транспортные средства по направлениям;
7. сохраняет визуализацию и результат подсчёта в формате JSON.

Входные данные:
    Изображение регулируемого перекрёстка.

Выходные данные:
    JSON-файл с количеством транспортных средств по направлениям
    north, south, west и east, а также диагностические изображения.

Пример запуска:
    python main.py --image data/test/test_16.png
"""

from pathlib import Path

from ultralytics import YOLO

from .auto_zones import create_auto_zones

import argparse
import cv2
import json


# Путь к предобученной модели детекции объектов.
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "yolo11m.pt"

# Идентификаторы транспортных классов COCO:
# 2 — car, 3 — motorcycle, 5 — bus, 7 — truck.
VEHICLE_CLASSES = {2, 3, 5, 7}

# Класс cell phone используется в механизме geometry recovery,
# поскольку на некоторых аэроснимках YOLO ошибочно относит
# визуально похожие транспортные средства к этому классу.
CELL_PHONE_CLASS = 67

# Минимальная уверенность YOLO при анализе полного изображения.
FULL_CONF = 0.01

# Минимальная уверенность обычной транспортной детекции.
VEHICLE_CONF = 0.03

# Минимальная уверенность при анализе увеличенных фрагментов зон.
CROP_CONF = 0.05

# Масштабы, используемые при многомасштабной обработке.
SCALES = [2.0, 3.0]

# Дополнительный отступ вокруг зоны при её вырезании.
PADDING = 60

# Порог Intersection over Union для удаления повторных детекций.
IOU_THRESHOLD = 0.30


# Загружаем модель один раз при запуске программы.
model = None


def _get_model():
    """Загружает YOLO только при первом обращении к детектору."""
    global model
    if model is None:
        model = YOLO(str(MODEL_PATH))
    return model


def get_zone_for_point(x, y, zones):
    """
    Определяет принадлежность точки одной из зон перекрёстка.

    Для проверки используется функция OpenCV pointPolygonTest,
    определяющая положение точки относительно полигона.

    Args:
        x (int | float):
            Координата точки по горизонтальной оси изображения.

        y (int | float):
            Координата точки по вертикальной оси изображения.

        zones (dict):
            Словарь полигонов зон north, south, west и east.

    Returns:
        str | None:
            Название зоны, внутри которой расположена точка.
            Если точка не принадлежит ни одной зоне, возвращается None.
    """
    for name, polygon in zones.items():
        if cv2.pointPolygonTest(
            polygon,
            (float(x), float(y)),
            False
        ) >= 0:
            return name

    return None


def draw_zones(image, zones):
    """
    Наносит границы автоматически сформированных зон на изображение.

    Для каждой зоны отображается контур полигона и её название:
    NORTH, SOUTH, WEST или EAST.

    Args:
        image (numpy.ndarray):
            Изображение, на которое необходимо нанести зоны.

        zones (dict):
            Словарь полигонов зон перекрёстка.

    Returns:
        numpy.ndarray:
            Изображение с нанесёнными зонами.
    """
    for name, polygon in zones.items():
        cv2.polylines(
            image,
            [polygon],
            True,
            (255, 255, 255),
            2
        )

        x, y = polygon[0]

        cv2.putText(
            image,
            name.upper(),
            (int(x) + 5, max(20, int(y) + 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

    return image


def calculate_iou(box1, box2):
    """
    Вычисляет коэффициент Intersection over Union для двух рамок.

    IoU показывает степень перекрытия двух bounding box и используется
    для определения того, относятся ли несколько детекций к одному
    и тому же транспортному средству.

    Args:
        box1 (tuple):
            Координаты первой рамки в формате (x1, y1, x2, y2).

        box2 (tuple):
            Координаты второй рамки в формате (x1, y1, x2, y2).

    Returns:
        float:
            Коэффициент IoU в диапазоне от 0 до 1.
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection_width = max(0, x2 - x1)
    intersection_height = max(0, y2 - y1)

    intersection = (
        intersection_width *
        intersection_height
    )

    area1 = max(
        1,
        (box1[2] - box1[0]) *
        (box1[3] - box1[1])
    )

    area2 = max(
        1,
        (box2[2] - box2[0]) *
        (box2[3] - box2[1])
    )

    union = area1 + area2 - intersection

    return intersection / union


def looks_like_vehicle(box, zone):
    """
    Проверяет, соответствует ли геометрия объекта транспортному средству.

    Функция применяется механизмом geometry recovery. Он используется,
    когда YOLO определяет объект как cell phone, однако размеры и
    пропорции его bounding box характерны для автомобиля на заданном
    направлении движения.

    Для зон NORTH и SOUTH ожидается преимущественно вертикальная
    ориентация рамки, а для WEST и EAST — горизонтальная.

    Args:
        box (tuple):
            Координаты ограничивающей рамки в формате
            (x1, y1, x2, y2).

        zone (str):
            Название зоны: north, south, west или east.

    Returns:
        bool:
            True, если геометрические признаки соответствуют
            транспортному средству, иначе False.
    """
    x1, y1, x2, y2 = box

    width = x2 - x1
    height = y2 - y1

    if width <= 0 or height <= 0:
        return False

    # Отбрасываем слишком маленькие и слишком большие объекты.
    if width < 12 or height < 12:
        return False

    if width > 120 or height > 120:
        return False

    ratio = width / height

    # Для вертикальных подъездов автомобиль
    # обычно вытянут по вертикали.
    if zone in ("north", "south"):
        return ratio < 0.70

    # Для горизонтальных подъездов автомобиль
    # обычно вытянут по горизонтали.
    if zone in ("west", "east"):
        return ratio > 1.40

    return False


def remove_duplicates(detections):
    """
    Удаляет повторные детекции транспортных средств.

    Повторные детекции появляются из-за совместного использования
    полного кадра и многомасштабного анализа отдельных зон.

    Для каждого направления объекты сортируются по confidence.
    Если IoU очередной рамки с уже сохранённой превышает
    IOU_THRESHOLD, объект считается повторной детекцией.

    Args:
        detections (list[dict]):
            Список всех обнаруженных объектов.

    Returns:
        list[dict]:
            Список уникальных детекций после IoU-фильтрации.
    """
    final_detections = []

    for zone_name in [
        "north",
        "south",
        "west",
        "east"
    ]:

        zone_detections = [
            d
            for d in detections
            if d["zone"] == zone_name
        ]

        zone_detections.sort(
            key=lambda d: d["confidence"],
            reverse=True
        )

        kept = []

        for detection in zone_detections:
            duplicate = False

            for existing in kept:
                if calculate_iou(
                    detection["box"],
                    existing["box"]
                ) > IOU_THRESHOLD:
                    duplicate = True
                    break

            if not duplicate:
                kept.append(detection)

        final_detections.extend(kept)

    return final_detections


def detect_full_image(image, zones, detections):
    """
    Выполняет первичную детекцию объектов на полном изображении.

    Предобученная модель YOLO11m анализирует весь кадр. В итоговый
    список включаются классы car, motorcycle, bus и truck.

    Дополнительно применяется geometry recovery для объектов класса
    cell phone, если их геометрия соответствует транспортному средству.

    Args:
        image (numpy.ndarray):
            Исходное изображение перекрёстка.

        zones (dict):
            Полигоны зон NORTH, SOUTH, WEST и EAST.

        detections (list):
            Список, в который добавляются найденные объекты.

    Returns:
        None:
            Результаты добавляются непосредственно в detections.
    """
    # Здесь специально не ограничиваем classes,
    # поскольку необходим fallback для класса cell phone.
    result = _get_model()(
        image,
        conf=FULL_CONF,
        imgsz=1280,
        verbose=False
    )[0]

    print(
        f"Полный кадр: "
        f"{len(result.boxes)} объектов"
    )

    normal_count = 0
    geometry_count = 0

    for box in result.boxes:
        cls_id = int(box.cls[0])
        confidence = float(box.conf[0])

        x1, y1, x2, y2 = map(
            int,
            box.xyxy[0]
        )

        # Для определения зоны используется центр bounding box.
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        zone = get_zone_for_point(
            cx,
            cy,
            zones
        )

        if zone is None:
            continue

        source = None

        # Обычная транспортная детекция.
        if cls_id in VEHICLE_CLASSES:
            if confidence >= VEHICLE_CONF:
                source = "vehicle"
                normal_count += 1

        # Геометрическое восстановление.
        elif cls_id == CELL_PHONE_CLASS:
            if looks_like_vehicle(
                (x1, y1, x2, y2),
                zone
            ):
                source = "geometry"
                geometry_count += 1

        if source is None:
            continue

        detections.append({
            "box": (
                x1,
                y1,
                x2,
                y2
            ),
            "confidence": confidence,
            "zone": zone,
            "source": source
        })

    print(
        f"  обычные vehicle: {normal_count}"
    )

    print(
        f"  geometry recovery: {geometry_count}"
    )


def detect_zone_crops(image, zones, detections):
    """
    Выполняет многомасштабную детекцию внутри каждой дорожной зоны.

    Каждая зона вырезается из исходного изображения с дополнительным
    отступом PADDING. Затем полученный участок увеличивается в масштабах
    x2 и x3 и повторно анализируется YOLO11m.

    Такой подход позволяет повысить вероятность обнаружения небольших
    транспортных средств на аэроснимках.

    Args:
        image (numpy.ndarray):
            Исходное изображение перекрёстка.

        zones (dict):
            Полигоны зон перекрёстка.

        detections (list):
            Список, который дополняется найденными объектами.

    Returns:
        None:
            Результаты добавляются непосредственно в detections.
    """
    image_height, image_width = image.shape[:2]

    for zone_name, polygon in zones.items():
        x, y, width, height = cv2.boundingRect(
            polygon
        )

        crop_x1 = max(
            0,
            x - PADDING
        )

        crop_y1 = max(
            0,
            y - PADDING
        )

        crop_x2 = min(
            image_width,
            x + width + PADDING
        )

        crop_y2 = min(
            image_height,
            y + height + PADDING
        )

        crop = image[
            crop_y1:crop_y2,
            crop_x1:crop_x2
        ]

        for scale in SCALES:
            enlarged = cv2.resize(
                crop,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC
            )

            result = _get_model()(
                enlarged,
                classes=list(VEHICLE_CLASSES),
                conf=CROP_CONF,
                imgsz=1280,
                verbose=False
            )[0]

            print(
                f"{zone_name.upper()} "
                f"x{scale}: "
                f"{len(result.boxes)} объектов"
            )

            for box in result.boxes:
                confidence = float(
                    box.conf[0]
                )

                x1, y1, x2, y2 = (
                    box.xyxy[0].tolist()
                )

                # Возвращаем координаты рамки
                # из увеличенного crop к исходному изображению.
                x1 = int(
                    x1 / scale + crop_x1
                )

                y1 = int(
                    y1 / scale + crop_y1
                )

                x2 = int(
                    x2 / scale + crop_x1
                )

                y2 = int(
                    y2 / scale + crop_y1
                )

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                detected_zone = (
                    get_zone_for_point(
                        cx,
                        cy,
                        zones
                    )
                )

                if detected_zone != zone_name:
                    continue

                detections.append({
                    "box": (
                        x1,
                        y1,
                        x2,
                        y2
                    ),
                    "confidence": confidence,
                    "zone": zone_name,
                    "source": f"x{scale}"
                })


def create_result(image, zones, detections):
    """
    Формирует итоговую визуализацию и выполняет подсчёт автомобилей.

    Каждая уникальная детекция относится к одному из четырёх направлений.
    На изображение наносятся:
    - границы зон;
    - bounding box транспортных средств;
    - направление;
    - источник детекции;
    - confidence.

    Обозначения источников:
        V — обычная YOLO-детекция;
        G — geometry recovery;
        M — multiscale-детекция.

    Args:
        image (numpy.ndarray):
            Исходное изображение перекрёстка.

        zones (dict):
            Полигоны зон.

        detections (list[dict]):
            Список уникальных транспортных средств.

    Returns:
        tuple:
            output:
                Изображение с визуализацией результатов.

            counts:
                Словарь с количеством транспортных средств
                по направлениям.

            geometry_recovered:
                Количество объектов, полученных посредством
                geometry recovery.
    """
    output = image.copy()

    output = draw_zones(
        output,
        zones
    )

    counts = {
        "north": 0,
        "south": 0,
        "west": 0,
        "east": 0
    }

    geometry_recovered = 0

    for detection in detections:
        zone = detection["zone"]

        counts[zone] += 1

        x1, y1, x2, y2 = (
            detection["box"]
        )

        confidence = (
            detection["confidence"]
        )

        source = detection["source"]

        if source == "geometry":
            geometry_recovered += 1
            source_label = "G"

        elif source == "vehicle":
            source_label = "V"

        else:
            source_label = "M"

        cv2.rectangle(
            output,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            output,
            (
                f"{zone[0].upper()} "
                f"{source_label} "
                f"{confidence:.2f}"
            ),
            (
                x1,
                max(15, y1 - 4)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 0),
            1
        )

    counts["total"] = (
        counts["north"] +
        counts["south"] +
        counts["west"] +
        counts["east"]
    )

    return (
        output,
        counts,
        geometry_recovered
    )


def analyze_image(image_path, output_dir=None):
    """Анализирует изображение и возвращает очереди для симулятора.

    Детектор используется dashboard как внутренний сервис: диагностические
    файлы создаются только при необходимости и не показываются пользователю.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"Не удалось открыть {image_path}")

    output_dir = Path(output_dir) if output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    zones = create_auto_zones(
        image_path,
        output_dir / f"{image_path.stem}_auto_zones.json" if output_dir else None,
        output_dir / f"{image_path.stem}_auto_zones.jpg" if output_dir else None,
    )
    detections = []
    detect_full_image(image, zones, detections)
    detect_zone_crops(image, zones, detections)
    final_detections = remove_duplicates(detections)
    output_image, counts, geometry_recovered = create_result(
        image, zones, final_detections
    )

    if output_dir:
        cv2.imwrite(str(output_dir / f"{image_path.stem}_detection.jpg"), output_image)
        with (output_dir / f"{image_path.stem}_counts.json").open("w", encoding="utf-8") as file:
            json.dump({**counts, "geometry_recovered": geometry_recovered}, file, ensure_ascii=False, indent=2)

    return counts


def analyze_image_json(image_path):
    """Возвращает результат детекции в JSON-контракте dashboard."""
    return json.dumps(analyze_image(image_path), ensure_ascii=False)


def main():
    """
    Запускает полный цикл анализа изображения перекрёстка.

    Путь к исходному изображению передаётся через аргумент --image.

    После выполнения в каталоге data/output создаются:
        <name>_detection.jpg
            Изображение с зонами и найденными автомобилями.

        <name>_counts.json
            Итоговое количество транспортных средств по направлениям.

        <name>_auto_zones.json
            Координаты автоматически сформированных зон.

        <name>_auto_zones.jpg
            Визуализация автоматически сформированных зон.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description=(
            "Обнаружение и подсчёт транспортных "
            "средств на изображении перекрёстка."
        )
    )

    parser.add_argument(
        "--image",
        required=True,
        help="Путь к изображению перекрёстка"
    )

    args = parser.parse_args()

    image_path = Path(args.image)

    if not image_path.exists():
        raise FileNotFoundError(
            image_path
        )

    output_dir = Path(
        "data/output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    image_name = image_path.stem

    output_image_path = (
        output_dir /
        f"{image_name}_detection.jpg"
    )

    output_json_path = (
        output_dir /
        f"{image_name}_counts.json"
    )

    auto_zones_json = (
        output_dir /
        f"{image_name}_auto_zones.json"
    )

    auto_zones_preview = (
        output_dir /
        f"{image_name}_auto_zones.jpg"
    )

    counts = analyze_image(image_path, output_dir)
    result_data = counts

    print()
    print(
        "=============================="
    )
    print("РЕЗУЛЬТАТ")
    print(
        "=============================="
    )

    print(
        json.dumps(
            result_data,
            ensure_ascii=False,
            indent=4
        )
    )

    print()
    print(
        f"Изображение: "
        f"{output_image_path}"
    )

    print(
        f"JSON: "
        f"{output_json_path}"
    )

    print(
        f"Автоматические зоны: "
        f"{auto_zones_json}"
    )


if __name__ == "__main__":
    main()
