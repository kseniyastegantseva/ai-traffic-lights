import json

from traffic_light import vision_detector


def test_vision_detector_uses_visdrone_model():
    assert vision_detector.MODEL_PATH.name == "visdrone_vehicles.pt"
    assert vision_detector.VEHICLE_CLASSES == (0, 1, 2, 3)


def test_vision_detector_returns_dashboard_json_contract(monkeypatch):
    monkeypatch.setattr(
        vision_detector,
        "analyze_image",
        lambda image_path: {
            "north": 4,
            "south": 2,
            "west": 1,
            "east": 3,
            "total": 10,
        },
    )

    payload = json.loads(vision_detector.analyze_image_json("unused.jpg"))

    assert payload == {
        "north": 4,
        "south": 2,
        "west": 1,
        "east": 3,
        "total": 10,
    }
