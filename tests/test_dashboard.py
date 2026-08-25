import importlib.util
from pathlib import Path
from types import SimpleNamespace

from traffic_light.interactive import simulate_interactive_traffic

DASHBOARD_PATH = Path(__file__).parents[1] / "app" / "dashboard.py"
SPEC = importlib.util.spec_from_file_location("traffic_light_dashboard", DASHBOARD_PATH)
assert SPEC and SPEC.loader
DASHBOARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DASHBOARD)


def test_vehicle_markup_contains_one_model_per_input_vehicle():
    queues = {"north": 4, "west": 3, "south": 2, "east": 1}

    markup = DASHBOARD._vehicle_markup(queues)

    assert sum(value.count('class="car-slot"') for value in markup.values()) == 10
    assert all('class="car-model"' in value for value in markup.values())
    assert len(set(markup.values())) == 4


def test_animation_embeds_vehicle_sprite_and_two_dynamic_traffic_lights():
    result = simulate_interactive_traffic({"north": 2, "west": 2, "south": 2, "east": 2})

    html = DASHBOARD._animation_html(result)

    assert "data:image/jpeg;base64," in html
    assert html.count('class="signal-unit"') == 2
    assert "setSignal('north_south',northSouth)" in html
    assert "setSignal('east_west',eastWest)" in html
    assert "@keyframes lampPulse" in html
    assert 'id="status-north_south"' in html
    assert 'id="status-east_west"' in html
    assert "КРАСНЫЙ" in html and "ЖЁЛТЫЙ" in html and "ЗЕЛЁНЫЙ" in html
    assert '<option value="0.5">0.5x</option>' in html
    assert html.count('class="bulb green active"') == 1
    assert html.count('class="bulb red active"') == 1
    assert "background-color:#20d866" in html
    assert "background-color:#ef2b2d" in html
    assert "bulb.style.backgroundColor=active?signalColors[color]" in html
    assert "frame.second<departure" in html
    assert "28+progress*84" in html
    assert "68-progress*80" in html
    assert "left:50%; top:8px; transform:translateX(-50%)" in html
    assert "left:8px; top:50%; transform:translateY(-50%)" in html
    assert "gapX=Math.max(1.8" in html
    assert "gapY=Math.max(2.8" in html


def test_signal_markup_falls_back_to_visible_red_signal():
    markup = DASHBOARD._signal_markup("north_south", "ЮГ–СЕВЕР", "unknown")

    assert 'data-color="red"' in markup
    assert 'class="bulb red active"' in markup
    assert 'style="background-color:#ef2b2d;opacity:1;' in markup
    assert '>КРАСНЫЙ</span>' in markup


def test_car_models_scale_down_for_large_queues():
    assert (
        DASHBOARD._car_slot_size(20)
        > DASHBOARD._car_slot_size(50)
        > DASHBOARD._car_slot_size(100)
        > DASHBOARD._car_slot_size(250)
    )


def test_dashboard_rejects_result_from_legacy_session_schema():
    legacy = SimpleNamespace(
        frames=[SimpleNamespace(signal="north_south")],
        phases=[SimpleNamespace(signal="north_south")],
    )
    current = simulate_interactive_traffic({"north": 2, "west": 2, "south": 2, "east": 2})

    assert not DASHBOARD._is_current_result(legacy)
    assert DASHBOARD._is_current_result(current)


def test_animation_html_recovers_when_frame_dict_has_no_signals():
    class HalfMigratedFrame(SimpleNamespace):
        def to_dict(self):
            return {
                "second": self.second,
                "queues": self.queues,
                "departed": self.departed,
            }

    result = simulate_interactive_traffic({"north": 2, "west": 2, "south": 2, "east": 2})
    result.frames[0] = HalfMigratedFrame(
        second=0,
        signals={"north_south": "green", "east_west": "red"},
        queues={"north": 2, "west": 2, "south": 2, "east": 2},
        departed=0,
    )

    html = DASHBOARD._animation_html(result)

    assert '"signals": {"north_south": "green", "east_west": "red"}' in html
    assert html.count('class="bulb green active"') == 1


def test_phase_table_supports_legacy_phase_objects_without_crashing():
    legacy_phases = [
        SimpleNamespace(
            signal="north_south", started_at=0, duration_seconds=8
        ),
        SimpleNamespace(signal="yellow", started_at=8, duration_seconds=3),
    ]

    rows = DASHBOARD._phase_rows(legacy_phases)

    assert rows[0]["Светофор"] == "Юг–Север"
    assert rows[0]["Сигнал"] == "Зелёный"
    assert rows[1]["Светофор"] == "Смена фазы"
    assert rows[1]["Сигнал"] == "Жёлтый"
