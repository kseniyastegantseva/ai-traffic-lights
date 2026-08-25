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

    assert "data:image/png;base64," in html
    assert html.count('class="signal-unit"') == 2
    assert "setSignal('north_south',northSouth)" in html
    assert "setSignal('east_west',eastWest)" in html
    assert "@keyframes lampPulse" in html
    assert 'id="status-north_south"' in html
    assert 'id="status-east_west"' in html
    assert "КРАСНЫЙ" in html and "ЖЁЛТЫЙ" in html and "ЗЕЛЁНЫЙ" in html
    assert '<option value="0.5" selected>0.5x</option>' in html
    assert '<option value="8">8x</option>' not in html
    assert html.count('class="bulb green active"') == 1
    assert html.count('class="bulb red active"') == 1
    assert "background-color:#20d866" in html
    assert "background-color:#ef2b2d" in html
    assert "bulb.style.backgroundColor=active?signalColors[color]" in html
    assert "frame.second<departure" in html
    assert "const clearedByLane={north:0,west:0,south:0,east:0}" in html
    assert "waitingIndex=Math.max(0,i-completed)" in html
    assert "clearVehicleAfterExit(lane,i,car)" in html
    assert "event.propertyName!=='transform'" in html
    assert "window.setTimeout(()=>finish({propertyName:'transform'})" in html
    assert "movingNorth+progress*(112-movingNorth)" in html
    assert "movingEast-progress*(movingEast+12)" in html
    assert "left:50%; top:8px; transform:translateX(-50%)" in html
    assert "left:8px; top:50%; transform:translateY(-50%)" in html
    assert "repeating-linear-gradient(to bottom" in html
    assert "repeating-linear-gradient(to right" in html
    assert 'class="stop-line stop-north"' in html
    assert "gapX=Math.max(1.8" in html
    assert "gapY=Math.max(2.8" in html
    assert "background:transparent url" in html
    assert ".scene.ready .car-slot" in html
    assert "left*scene.clientWidth/100" in html
    assert "top*scene.clientHeight/100" in html
    assert "car-slot.cleared" in html


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


def test_research_charts_use_expected_metrics():
    import pandas as pd

    summary = pd.DataFrame(
        [
            {
                "scenario_title": "Низкая нагрузка",
                "controller": "fixed",
                "average_wait_seconds": 10.0,
                "wait_95ci_half_width": 1.0,
                "max_queue_length": 8.0,
                "wait_improvement_vs_fixed_pct": 0.0,
                "average_queue_length": 2.0,
            },
            {
                "scenario_title": "Низкая нагрузка",
                "controller": "ai",
                "average_wait_seconds": 7.0,
                "wait_95ci_half_width": 0.8,
                "max_queue_length": 5.0,
                "wait_improvement_vs_fixed_pct": 30.0,
                "average_queue_length": 1.2,
            },
        ]
    )

    assert DASHBOARD._research_wait_chart(summary).layout.title.text == "Среднее время ожидания автомобиля"
    assert DASHBOARD._research_peak_queue_chart(summary).layout.title.text == "Максимальная длина очереди"
    assert DASHBOARD._research_improvement_chart(summary).layout.title.text == "Сокращение времени ожидания"
    assert DASHBOARD._research_queue_chart(summary).layout.title.text == "Средняя длина очереди"


def test_dynamic_queue_chart_aggregates_seed_series():
    import pandas as pd

    runs = pd.DataFrame(
        [
            {"scenario_title": "Низкая нагрузка", "controller": "ai", "queue_series": [4, 2, 0]},
            {"scenario_title": "Низкая нагрузка", "controller": "ai", "queue_series": [2, 2, 0]},
        ]
    )

    figure = DASHBOARD._research_dynamic_queue_chart(runs)

    assert figure.layout.title.text == "Динамика очереди во времени"
    assert len(figure.data) == 1


def test_default_speed_increases_with_detected_traffic():
    assert DASHBOARD._default_simulation_speed(
        {"north": 2, "west": 3, "south": 1, "east": 2}
    ) == 0.5
    assert DASHBOARD._default_simulation_speed(
        {"north": 8, "west": 9, "south": 8, "east": 8}
    ) == 1.0
    assert DASHBOARD._default_simulation_speed(
        {"north": 25, "west": 25, "south": 20, "east": 20}
    ) == 2.0


def test_processing_indicator_uses_traffic_light_animation():
    markup = DASHBOARD._processing_indicator()

    assert "processing-light" in markup
    assert "processing-bulb red" in markup
    assert "Анализируем фотографию" in markup


def test_test_photo_assets_are_available():
    assets = DASHBOARD_PATH.parent / "assets" / "test_images"

    assert (assets / "low_load.png").is_file()
    assert (assets / "uniform_load.png").is_file()
    assert (assets / "oversaturated.png").is_file()


def test_research_graphs_are_not_a_navigation_control():
    source = DASHBOARD_PATH.read_text(encoding="utf-8")

    assert 'st.sidebar.button("Исследовательские графики")' not in source
    assert "_research_charts(result.scenario.code)" in source


def test_research_scenario_mapping_follows_detected_load():
    assert DASHBOARD.INTERACTIVE_TO_RESEARCH_SCENARIO["low_load"] == "low_load"
    assert DASHBOARD.INTERACTIVE_TO_RESEARCH_SCENARIO["north_south_peak"] == "morning_peak_ns"
    assert DASHBOARD.INTERACTIVE_TO_RESEARCH_SCENARIO["east_west_peak"] == "evening_peak_ew"
    assert DASHBOARD._research_wait_chart(
        __import__("pandas").DataFrame(
            [{
                "scenario_title": "Низкая нагрузка",
                "controller": "fixed",
                "average_wait_seconds": 1.0,
                "wait_95ci_half_width": 0.1,
            }]
        )
    ).layout.height == 560


def test_research_graphs_compare_only_standard_and_ai():
    assert DASHBOARD.DISPLAYED_STRATEGIES == ("fixed", "ai")
    assert "actuated" not in DASHBOARD.STRATEGY_DESCRIPTIONS
    source = DASHBOARD_PATH.read_text(encoding="utf-8")
    assert '"scrollZoom": False' in source
    assert '"displayModeBar": False' in source
    assert "_research_distribution_chart" not in source
    assert 'st.dataframe(selected_summary' not in source
