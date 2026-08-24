"""
Модуль автоматического формирования зон подходов к перекрёстку.

Модуль создаёт четыре области интереса:
NORTH, SOUTH, WEST и EAST.

Зоны формируются автоматически на основе размеров входного изображения
и положения его геометрического центра. Центральная часть перекрёстка
исключается из зон, поскольку итоговый подсчёт должен учитывать
транспортные средства на подходах к перекрёстку.

Модуль также может:
- сохранять координаты зон в JSON-файл;
- создавать диагностическое изображение с нанесёнными полигонами;
- отображать геометрический центр перекрёстка.

Важно:
    Текущая реализация предполагает, что перекрёсток расположен
    приблизительно в центре изображения, а основные направления дорог
    близки к вертикальной и горизонтальной осям кадра.
"""

import cv2
import json
import numpy as np
from pathlib import Path


def create_auto_zones(image_path, output_json=None, output_image=None):
    """
    Автоматически формирует четыре зоны подходов к перекрёстку.

    Геометрия зон рассчитывается относительно центра изображения.
    Размеры центральной исключённой области и ширина дорожных коридоров
    задаются пропорционально ширине и высоте исходного кадра.

    Формируются следующие зоны:
        north:
            Верхний подход к перекрёстку.

        south:
            Нижний подход к перекрёстку.

        west:
            Левый подход к перекрёстку.

        east:
            Правый подход к перекрёстку.

    Центральная область намеренно не входит ни в одну из зон, чтобы
    транспортные средства, уже находящиеся внутри перекрёстка,
    не участвовали в подсчёте транспортной нагрузки на подходах.

    Args:
        image_path (str | pathlib.Path):
            Путь к исходному изображению перекрёстка.

        output_json (str | pathlib.Path | None):
            Путь для сохранения координат сформированных зон.
            Если значение равно None, JSON-файл не создаётся.

        output_image (str | pathlib.Path | None):
            Путь для сохранения диагностического изображения
            с нанесёнными границами зон.
            Если значение равно None, изображение не создаётся.

    Returns:
        dict:
            Словарь с полигонами четырёх зон:

            {
                "north": numpy.ndarray,
                "south": numpy.ndarray,
                "west": numpy.ndarray,
                "east": numpy.ndarray
            }

            Каждый полигон представлен массивом координат точек
            формата (x, y).

    Raises:
        FileNotFoundError:
            Если изображение не удалось загрузить.
    """
    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(image_path)

    # Получаем размеры исходного изображения.
    h, w = image.shape[:2]

    # Геометрический центр изображения принимается
    # за приблизительный центр перекрёстка.
    cx = w // 2
    cy = h // 2

    # Половина ширины и высоты центральной области перекрёстка.
    # Центральная область исключается из подсчёта.
    center_half_w = int(w * 0.10)
    center_half_h = int(h * 0.12)

    # Половина ширины вертикального дорожного коридора
    # для зон NORTH и SOUTH.
    vertical_half_width = int(w * 0.16)

    # Половина высоты горизонтального дорожного коридора
    # для зон WEST и EAST.
    horizontal_half_height = int(h * 0.16)

    # ---------------------------------------------------------
    # NORTH
    # ---------------------------------------------------------
    # Верхняя зона начинается от верхней границы изображения
    # и заканчивается перед центральной областью перекрёстка.
    north = np.array([
        [cx - vertical_half_width, 0],
        [cx + vertical_half_width, 0],
        [cx + vertical_half_width, cy - center_half_h],
        [cx + center_half_w, cy - center_half_h],
        [cx - center_half_w, cy - center_half_h],
        [cx - vertical_half_width, cy - center_half_h]
    ], dtype=np.int32)

    # ---------------------------------------------------------
    # SOUTH
    # ---------------------------------------------------------
    # Нижняя зона начинается после центральной области
    # и продолжается до нижней границы изображения.
    south = np.array([
        [cx - center_half_w, cy + center_half_h],
        [cx + center_half_w, cy + center_half_h],
        [cx + vertical_half_width, cy + center_half_h],
        [cx + vertical_half_width, h - 1],
        [cx - vertical_half_width, h - 1],
        [cx - vertical_half_width, cy + center_half_h]
    ], dtype=np.int32)

    # ---------------------------------------------------------
    # WEST
    # ---------------------------------------------------------
    # Левая зона начинается от левой границы изображения
    # и заканчивается перед центральной областью.
    west = np.array([
        [0, cy - horizontal_half_height],
        [cx - center_half_w, cy - horizontal_half_height],
        [cx - center_half_w, cy - center_half_h],
        [cx - center_half_w, cy + center_half_h],
        [cx - center_half_w, cy + horizontal_half_height],
        [0, cy + horizontal_half_height]
    ], dtype=np.int32)

    # ---------------------------------------------------------
    # EAST
    # ---------------------------------------------------------
    # Правая зона начинается после центральной области
    # и продолжается до правой границы изображения.
    east = np.array([
        [cx + center_half_w, cy - horizontal_half_height],
        [w - 1, cy - horizontal_half_height],
        [w - 1, cy + horizontal_half_height],
        [cx + center_half_w, cy + horizontal_half_height],
        [cx + center_half_w, cy + center_half_h],
        [cx + center_half_w, cy - center_half_h]
    ], dtype=np.int32)

    # Объединяем сформированные полигоны в единый словарь.
    zones = {
        "north": north,
        "south": south,
        "west": west,
        "east": east
    }

    # При необходимости сохраняем координаты зон
    # в формате JSON.
    if output_json:
        json_data = {
            name: polygon.tolist()
            for name, polygon in zones.items()
        }

        with open(
            output_json,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                json_data,
                f,
                ensure_ascii=False,
                indent=2
            )

    # При необходимости создаём диагностическое изображение.
    if output_image:
        preview = image.copy()

        for name, polygon in zones.items():
            # Наносим контур зоны.
            cv2.polylines(
                preview,
                [polygon],
                True,
                (255, 255, 255),
                3
            )

            x, y = polygon[0]

            # Подписываем направление.
            cv2.putText(
                preview,
                name.upper(),
                (
                    int(x) + 10,
                    max(25, int(y) + 25)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        # Отмечаем геометрический центр изображения,
        # используемый как центр перекрёстка.
        cv2.circle(
            preview,
            (cx, cy),
            8,
            (0, 0, 255),
            -1
        )

        cv2.imwrite(
            str(output_image),
            preview
        )

    return zones


def main():
    """
    Выполняет демонстрационное построение зон для тестовых изображений.

    Функция предназначена для автономной проверки модуля auto_zones.py.
    Для изображений test_01.png ... test_05.png создаются:

    - JSON-файлы с координатами зон;
    - изображения с визуализацией зон.

    Результаты сохраняются в каталоге:
        data/test/auto_zones/

    Returns:
        None
    """
    output_dir = Path(
        "data/test/auto_zones"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    for i in range(1, 6):
        image_path = Path(
            f"data/test/test_{i:02d}.png"
        )

        if not image_path.exists():
            print(
                f"Нет файла: {image_path}"
            )
            continue

        json_path = (
            output_dir /
            f"test_{i:02d}_zones.json"
        )

        preview_path = (
            output_dir /
            f"test_{i:02d}_preview.jpg"
        )

        create_auto_zones(
            image_path,
            json_path,
            preview_path
        )

        print(
            f"test_{i:02d}: {json_path}"
        )


if __name__ == "__main__":
    main()
