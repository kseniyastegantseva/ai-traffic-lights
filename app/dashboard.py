from __future__ import annotations

import base64
import hashlib
import json
import tempfile
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from traffic_light.config import LaneName
from traffic_light.interactive import InteractiveSimulationResult, simulate_interactive_traffic

LANE_LABELS = {
    "north": "Север",
    "west": "Запад",
    "south": "Юг",
    "east": "Восток",
}

VEHICLE_SPRITE_PATH = Path(__file__).parent / "assets" / "vehicle_sprites.jpeg"
SPRITE_X = (0, 33.333, 66.667, 100)
SPRITE_Y = (0, 50, 100)
DASHBOARD_STATE_VERSION = 4
SIGNAL_COLORS = {
    "red": ("КРАСНЫЙ", "#ef2b2d"),
    "yellow": ("ЖЁЛТЫЙ", "#ffd21f"),
    "green": ("ЗЕЛЁНЫЙ", "#20d866"),
}


def main() -> None:
    st.set_page_config(page_title="Интеллектуальный светофор", layout="wide")
    _apply_styles()

    st.title("Интеллектуальный светофор")
    if st.session_state.get("dashboard_page", "upload") == "upload":
        _upload_screen()
        return

    result: InteractiveSimulationResult | None = st.session_state.get("interactive_result")
    if not _is_current_result(result):
        st.session_state.dashboard_page = "upload"
        st.session_state.interactive_result = None
        st.rerun()
    _simulation_screen(result)


def _upload_screen() -> None:
    st.subheader("Загрузите фотографию перекрёстка")
    st.caption("Система сама определит автомобили по четырём направлениям и запустит симуляцию.")
    uploaded = st.file_uploader(
        "Фотография перекрёстка",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )
    if not uploaded:
        st.info("После загрузки анализ начнётся автоматически.")
        return

    file_bytes = uploaded.getvalue()
    upload_key = hashlib.sha256(file_bytes).hexdigest()
    if st.session_state.get("processed_upload_key") == upload_key:
        return

    upload_dir = Path(tempfile.gettempdir()) / "traffic_light_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / f"{upload_key}{Path(uploaded.name).suffix.lower()}"
    image_path.write_bytes(file_bytes)

    with st.spinner("Анализируем изображение и определяем очереди..."):
        try:
            from traffic_light.vision_detector import analyze_image_json

            queues = json.loads(analyze_image_json(image_path))
        except Exception as error:  # noqa: BLE001 - показываем понятную ошибку пользователю
            st.error(f"Не удалось обработать изображение: {error}")
            return

    st.session_state.processed_upload_key = upload_key
    st.session_state.detected_queues = {
        lane: int(queues.get(lane, 0)) for lane in LANE_LABELS
    }
    st.session_state.interactive_result = simulate_interactive_traffic(
        st.session_state.detected_queues
    )
    st.session_state.dashboard_state_version = DASHBOARD_STATE_VERSION
    st.session_state.dashboard_page = "simulation"
    st.rerun()


def _simulation_screen(result: InteractiveSimulationResult) -> None:
    st.caption("Количество автомобилей определено автоматически по загруженной фотографии.")
    if st.button("Загрузить другую фотографию", type="secondary"):
        st.session_state.dashboard_page = "upload"
        st.session_state.processed_upload_key = None
        st.session_state.interactive_result = None
        st.rerun()

    detected = result.initial_queues
    columns = st.columns(4)
    for column, lane in zip(columns, LANE_LABELS, strict=True):
        column.metric(f"{LANE_LABELS[lane]}", detected[lane])

    _scenario_banner(result)
    _metrics(result)

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.subheader("Работа перекрёстка")
        st.iframe(_animation_html(result), height=690, width="stretch")
    with right:
        st.subheader("Как меняется очередь")
        st.plotly_chart(_queue_chart(result), width="stretch", config={"displayModeBar": False})
        st.caption(
            "Линия показывает, сколько автомобилей ещё ожидает проезда. "
            "Снижение до нуля означает завершение работы алгоритма."
        )
        _phase_table(result)


def _scenario_banner(result: InteractiveSimulationResult) -> None:
    st.markdown(
        f"""
        <div class="scenario-banner">
          <div><span class="eyebrow">ОПРЕДЕЛЁННЫЙ СЦЕНАРИЙ</span>
          <strong>{escape(result.scenario.title)}</strong></div>
          <p>{escape(result.scenario.description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metrics(result: InteractiveSimulationResult) -> None:
    total = sum(result.initial_queues.values())
    columns = st.columns(4)
    columns[0].metric("Автомобилей", total)
    columns[1].metric("Время работы", _format_seconds(result.total_time_seconds))
    columns[2].metric("Переключений фаз", result.switches)
    columns[3].metric("Проехало", result.departed)


def _queue_chart(result: InteractiveSimulationResult):
    rows = [
        {
            "Время, с": frame.second,
            "Осталось автомобилей": sum(frame.queues.values()),
        }
        for frame in result.frames
    ]
    frame = pd.DataFrame(rows)
    figure = px.line(
        frame,
        x="Время, с",
        y="Осталось автомобилей",
        markers=result.total_time_seconds <= 30,
    )
    figure.update_traces(line_color="#166534", line_width=3)
    figure.update_layout(
        height=320,
        margin={"l": 10, "r": 10, "t": 16, "b": 10},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        hovermode="x unified",
    )
    figure.update_yaxes(rangemode="tozero", gridcolor="#e5e7eb")
    figure.update_xaxes(gridcolor="#f3f4f6")
    return figure


def _phase_table(result: InteractiveSimulationResult) -> None:
    st.subheader("Распределение времени")
    north, east = st.columns(2)
    north.metric("Светофор Юг–Север", _format_seconds(result.north_south_green_seconds))
    east.metric("Светофор Восток–Запад", _format_seconds(result.east_west_green_seconds))
    if result.phases:
        st.dataframe(_phase_rows(result.phases), hide_index=True, width="stretch", height=220)


def _is_current_result(result: object) -> bool:
    if result is None or not hasattr(result, "frames") or not hasattr(result, "phases"):
        return False
    frames = getattr(result, "frames", [])
    phases = getattr(result, "phases", [])
    frames_are_current = all(
        _frame_signals(frame) is not None
        and hasattr(frame, "queues")
        and hasattr(frame, "second")
        and hasattr(frame, "departed")
        for frame in frames
    )
    phases_are_current = all(
        hasattr(phase, "axis") and hasattr(phase, "color") for phase in phases
    )
    return frames_are_current and phases_are_current


def _frame_to_dict(frame: object) -> dict:
    if hasattr(frame, "to_dict"):
        data = frame.to_dict()
    elif isinstance(frame, dict):
        data = frame.copy()
    else:
        data = {
            "second": getattr(frame, "second", 0),
            "queues": getattr(frame, "queues", {}),
            "departed": getattr(frame, "departed", 0),
        }
    data["signals"] = _frame_signals(frame) or {"north_south": "red", "east_west": "red"}
    data.setdefault("second", getattr(frame, "second", 0))
    data.setdefault("queues", getattr(frame, "queues", {}))
    data.setdefault("departed", getattr(frame, "departed", 0))
    return data


def _frame_signals(frame: object) -> dict[str, str] | None:
    data_signals = None
    if isinstance(frame, dict):
        data_signals = frame.get("signals")
    elif hasattr(frame, "to_dict"):
        data_signals = frame.to_dict().get("signals")
    if data_signals is None:
        data_signals = getattr(frame, "signals", None)
    if isinstance(data_signals, dict):
        return {
            "north_south": _safe_signal_color(data_signals.get("north_south")),
            "east_west": _safe_signal_color(data_signals.get("east_west")),
        }
    legacy_signal = getattr(frame, "signal", None)
    if isinstance(frame, dict):
        legacy_signal = frame.get("signal", legacy_signal)
    if legacy_signal == "north_south":
        return {"north_south": "green", "east_west": "red"}
    if legacy_signal == "east_west":
        return {"north_south": "red", "east_west": "green"}
    if legacy_signal == "yellow":
        return {"north_south": "yellow", "east_west": "red"}
    return None


def _safe_signal_color(color: object) -> str:
    return color if color in SIGNAL_COLORS else "red"


def _phase_rows(phases: list[object]) -> list[dict[str, str]]:
    axis_labels = {"north_south": "Юг–Север", "east_west": "Восток–Запад"}
    color_labels = {"green": "Зелёный", "yellow": "Жёлтый", "red": "Красный"}
    rows = []
    for phase in phases:
        axis = getattr(phase, "axis", None)
        color = getattr(phase, "color", None)
        legacy_signal = getattr(phase, "signal", None)
        if axis is None and legacy_signal in axis_labels:
            axis, color = legacy_signal, "green"
        if axis is None and legacy_signal == "yellow":
            axis, color = "transition", "yellow"
        rows.append(
            {
                "Светофор": axis_labels.get(axis, "Смена фазы"),
                "Сигнал": color_labels.get(color, "Не определён"),
                "Начало": f"{getattr(phase, 'started_at', 0)} с",
                "Длительность": f"{getattr(phase, 'duration_seconds', 0)} с",
            }
        )
    return rows


def _animation_html(result: InteractiveSimulationResult) -> str:
    frames = [_frame_to_dict(frame) for frame in result.frames]
    initial = result.initial_queues
    initial_signals = (
        frames[0]["signals"]
        if frames
        else {"north_south": "red", "east_west": "red"}
    )
    car_markup = _vehicle_markup(initial)
    signal_markup = {
        "north_south": _signal_markup(
            "north_south", "ЮГ–СЕВЕР", initial_signals["north_south"]
        ),
        "east_west": _signal_markup(
            "east_west", "ВОСТОК–ЗАПАД", initial_signals["east_west"]
        ),
    }
    sprite_uri = _vehicle_sprite_uri()
    car_slot_size = _car_slot_size(max(initial.values(), default=0))
    return f"""
<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:Inter,Arial,sans-serif; color:#17211b; background:#fff; }}
.sim {{ border:1px solid #d9e1dc; border-radius:8px; overflow:hidden; background:#f5f7f5; }}
.toolbar {{ height:58px; display:flex; align-items:center; gap:10px; padding:10px 14px; background:#fff; border-bottom:1px solid #d9e1dc; }}
button,select {{ height:36px; border:1px solid #c9d3cc; background:#fff; border-radius:6px; padding:0 12px; font-weight:650; color:#17211b; cursor:pointer; }}
button.primary {{ background:#166534; border-color:#166534; color:#fff; }}
.status {{ margin-left:auto; text-align:right; }}
.status strong {{ display:block; font-size:16px; }} .status span {{ font-size:12px; color:#637068; }}
.scene {{ position:relative; height:555px; background:#dce8dc; overflow:hidden; }}
.road-v {{ position:absolute; width:30%; height:100%; left:35%; top:0; background:#414844; border-left:3px solid #f8faf9; border-right:3px solid #f8faf9; }}
.road-h {{ position:absolute; width:100%; height:30%; left:0; top:35%; background:#414844; border-top:3px solid #f8faf9; border-bottom:3px solid #f8faf9; }}
.center {{ position:absolute; width:30%; height:30%; left:35%; top:35%; background:#4b534e; z-index:2; }}
.lane {{ --slot:{car_slot_size}px; position:absolute; z-index:4; display:flex; gap:1px; align-content:flex-start; overflow:hidden; }}
.lane.north {{ width:25%; height:32%; left:37.5%; top:2%; flex-wrap:wrap-reverse; align-content:flex-end; }}
.lane.south {{ width:25%; height:32%; left:37.5%; bottom:2%; flex-wrap:wrap; align-content:flex-start; }}
.lane.west {{ width:33%; height:25%; left:2%; top:37.5%; flex-wrap:wrap-reverse; align-content:flex-end; justify-content:flex-end; }}
.lane.east {{ width:33%; height:25%; right:2%; top:37.5%; flex-wrap:wrap; align-content:flex-start; }}
.car-slot {{ width:var(--slot); height:var(--slot); display:flex; align-items:center; justify-content:center; flex:0 0 var(--slot); opacity:1; transition:opacity .35s,transform .45s ease-in; }}
.car-model {{ display:block; width:62%; height:92%; background-color:#414844; background-image:url("{sprite_uri}"); background-size:400% 300%; background-position:var(--sprite-x) var(--sprite-y); background-repeat:no-repeat; background-blend-mode:multiply; filter:saturate(2.4) contrast(1.05) drop-shadow(0 1px 1px #0008); }}
.north .car-model {{ transform:rotate(180deg); }} .south .car-model {{ transform:rotate(0deg); }}
.west .car-model {{ transform:rotate(90deg); }} .east .car-model {{ transform:rotate(-90deg); }}
.north .car-slot.passed {{ opacity:0; transform:translateY(190px); }}
.south .car-slot.passed {{ opacity:0; transform:translateY(-190px); }}
.west .car-slot.passed {{ opacity:0; transform:translateX(240px); }}
.east .car-slot.passed {{ opacity:0; transform:translateX(-240px); }}
.lane-label {{ position:absolute; z-index:6; padding:5px 8px; background:#ffffffed; border:1px solid #cad4cd; border-radius:5px; font-size:12px; font-weight:700; }}
.label-north {{ left:8px; top:8px; }} .label-south {{ right:8px; bottom:8px; }}
.label-west {{ left:8px; bottom:8px; }} .label-east {{ right:8px; top:8px; }}
.signal-panel {{ position:absolute; z-index:8; left:50%; top:50%; transform:translate(-50%,-50%); width:180px; display:flex; align-items:flex-start; justify-content:center; gap:14px; flex-wrap:wrap; }}
.signal-unit {{ width:76px; padding:6px; border-radius:6px; background:#f7faf8; border:2px solid #cbd5ce; text-align:center; transition:border-color .2s,box-shadow .2s; }}
.signal-unit.changed {{ animation:housingFlash .55s ease-out; }}
.signal-name {{ display:block; min-height:22px; font-size:10px; line-height:1.1; font-weight:800; color:#253229; }}
.housing {{ width:38px; margin:4px auto; display:flex; flex-direction:column; align-items:center; gap:5px; padding:6px; border-radius:7px; background:#171b18; box-shadow:0 3px 7px #0009; }}
.bulb {{ width:24px; height:24px; border-radius:50%; background:#3d4540; border:2px solid #090b0a; opacity:.55; transition:background .18s,box-shadow .18s,opacity .18s; }}
.bulb.active {{ opacity:1; animation:lampPulse .65s ease-in-out infinite alternate; }}
.bulb.active.red {{ background:#ef2b2d; box-shadow:0 0 8px #ef2b2d,0 0 18px #ef2b2d; }}
.bulb.active.yellow {{ background:#ffd21f; box-shadow:0 0 8px #ffd21f,0 0 18px #ffd21f; animation-duration:.32s; }}
.bulb.active.green {{ background:#20d866; box-shadow:0 0 8px #20d866,0 0 18px #20d866; }}
.signal-status {{ display:block; margin-top:5px; padding:3px 2px; border-radius:3px; color:#fff; font-size:8px; font-weight:900; line-height:1; }}
.signal-status.status-red {{ background:#b91c1c; }} .signal-status.status-yellow {{ background:#a16207; }} .signal-status.status-green {{ background:#15803d; }}
@keyframes lampPulse {{ from {{ transform:scale(.92); filter:brightness(.72); }} to {{ transform:scale(1.08); filter:brightness(1.3); }} }}
@keyframes housingFlash {{ 0% {{ border-color:#fff; box-shadow:0 0 0 0 #fff; }} 55% {{ border-color:#facc15; box-shadow:0 0 0 5px #facc1555; }} 100% {{ border-color:#cbd5ce; box-shadow:none; }} }}
.phase-label {{ flex-basis:100%; padding:3px 5px; border-radius:4px; background:#202622e8; color:#fff; text-align:center; font-size:10px; font-weight:750; }}
.progress {{ height:7px; background:#e6ebe8; }} .progress>div {{ height:100%; background:#166534; width:0; transition:width .2s; }}
.legend {{ padding:10px 14px; font-size:12px; color:#637068; background:#fff; border-top:1px solid #d9e1dc; }}
@media(max-width:700px) {{ .scene {{ height:470px; }} .signal-panel {{ transform:translate(-50%,-50%) scale(.88); }} }}
</style></head>
<body><div class="sim">
  <div class="toolbar">
    <button id="play" class="primary">Пауза</button><button id="reset">Сначала</button>
    <select id="speed" aria-label="Скорость"><option value="0.5">0.5x</option><option value="1">1x</option><option value="2">2x</option><option value="4" selected>4x</option><option value="8">8x</option></select>
    <div class="status"><strong id="clock">0 с / {result.total_time_seconds} с</strong><span id="remaining">Ожидает: {sum(initial.values())}</span></div>
  </div>
  <div class="progress"><div id="progress"></div></div>
  <div class="scene">
    <div class="road-v"></div><div class="road-h"></div><div class="center"></div>
    <div class="lane north" id="cars-north">{car_markup['north']}</div>
    <div class="lane west" id="cars-west">{car_markup['west']}</div>
    <div class="lane south" id="cars-south">{car_markup['south']}</div>
    <div class="lane east" id="cars-east">{car_markup['east']}</div>
    <div class="lane-label label-north">Север: <span id="count-north">{initial['north']}</span></div>
    <div class="lane-label label-west">Запад: <span id="count-west">{initial['west']}</span></div>
    <div class="lane-label label-south">Юг: <span id="count-south">{initial['south']}</span></div>
    <div class="lane-label label-east">Восток: <span id="count-east">{initial['east']}</span></div>
    <div class="signal-panel">
      {signal_markup['north_south']}
      {signal_markup['east_west']}
      <div class="phase-label" id="phase-label"></div>
    </div>
  </div>
  <div class="legend">Два светофора работают взаимоисключающе: Юг–Север управляет вертикальным потоком, Восток–Запад — горизонтальным. Один шаг равен одной секунде модели.</div>
</div>
<script>
const frames={json.dumps(frames, ensure_ascii=False)};
const initial={json.dumps(initial)};
const signalColors={{red:'#ef2b2d',yellow:'#ffd21f',green:'#20d866'}};
let index=0,playing=true,timer;
const lanes=['north','west','south','east'];
function paint(){{
  const frame=frames[index];if(!frame)return;
  lanes.forEach(lane=>{{
    document.getElementById('count-'+lane).textContent=frame.queues[lane];
    const cars=document.querySelectorAll('#cars-'+lane+' .car-slot');
    cars.forEach((car,i)=>car.classList.toggle('passed',i>=frame.queues[lane]));
  }});
  function setSignal(axis,color){{
    const unit=document.getElementById('signal-'+axis);
    if(unit.dataset.color!==color){{
      unit.dataset.color=color;unit.classList.remove('changed');void unit.offsetWidth;unit.classList.add('changed');
    }}
    unit.querySelectorAll('.bulb').forEach(bulb=>{{
      const active=bulb.dataset.color===color;
      bulb.classList.toggle('active',active);
      bulb.style.backgroundColor=active?signalColors[color]:'#3d4540';
      bulb.style.opacity=active?'1':'.55';
      bulb.style.boxShadow=active?'0 0 8px '+signalColors[color]+',0 0 18px '+signalColors[color]:'none';
    }});
    const status=document.getElementById('status-'+axis);
    const colorLabels={{red:'КРАСНЫЙ',yellow:'ЖЁЛТЫЙ',green:'ЗЕЛЁНЫЙ'}};
    status.textContent=colorLabels[color];status.className='signal-status status-'+color;
  }}
  const northSouth=frame.signals.north_south;
  const eastWest=frame.signals.east_west;
  setSignal('north_south',northSouth);setSignal('east_west',eastWest);
  let label='Оба светофора: красный';
  if(northSouth==='green')label='Проезд: Юг–Север';
  if(eastWest==='green')label='Проезд: Восток–Запад';
  if(northSouth==='yellow')label='Юг–Север завершает фазу';
  if(eastWest==='yellow')label='Восток–Запад завершает фазу';
  let nextChange=index+1;
  while(nextChange<frames.length && frames[nextChange].signals.north_south===northSouth && frames[nextChange].signals.east_west===eastWest)nextChange++;
  const phaseLeft=Math.max(1,nextChange-index);
  document.getElementById('phase-label').textContent=label+' · ещё '+phaseLeft+' с';
  document.getElementById('clock').textContent=frame.second+' с / {result.total_time_seconds} с';
  document.getElementById('remaining').textContent='Ожидает: '+lanes.reduce((s,l)=>s+frame.queues[l],0)+' · Проехало: '+frame.departed;
  document.getElementById('progress').style.width=(100*(index+1)/frames.length)+'%';
  if(index>=frames.length-1){{playing=false;document.getElementById('play').textContent='Повторить';clearInterval(timer);}}
}}
function startTimer(){{clearInterval(timer);if(playing)timer=setInterval(()=>{{if(index<frames.length-1){{index++;paint();}}}},1000/Number(document.getElementById('speed').value));}}
document.getElementById('play').onclick=()=>{{if(index>=frames.length-1){{index=0;playing=false;}}playing=!playing;document.getElementById('play').textContent=playing?'Пауза':'Продолжить';paint();startTimer();}};
document.getElementById('reset').onclick=()=>{{index=0;playing=true;document.getElementById('play').textContent='Пауза';paint();startTimer();}};
document.getElementById('speed').onchange=startTimer;
paint();startTimer();
</script></body></html>
"""


def _signal_markup(axis: str, label: str, active_color: str) -> str:
    if active_color not in SIGNAL_COLORS:
        active_color = "red"
    bulbs = []
    for color, (_, hex_color) in SIGNAL_COLORS.items():
        active = color == active_color
        class_name = f"bulb {color}" + (" active" if active else "")
        background = hex_color if active else "#3d4540"
        opacity = "1" if active else ".55"
        shadow = f"0 0 8px {hex_color},0 0 18px {hex_color}" if active else "none"
        bulbs.append(
            f'<span class="{class_name}" data-color="{color}" '
            f'style="background-color:{background};opacity:{opacity};'
            f'box-shadow:{shadow}"></span>'
        )
    color_label = SIGNAL_COLORS[active_color][0]
    return (
        f'<div class="signal-unit" id="signal-{axis}" data-color="{active_color}">'
        f'<span class="signal-name">{label}</span>'
        f'<div class="housing">{"".join(bulbs)}</div>'
        f'<span class="signal-status status-{active_color}" id="status-{axis}" '
        f'aria-live="polite">{color_label}</span></div>'
    )


def _vehicle_markup(initial: dict[LaneName, int]) -> dict[LaneName, str]:
    lane_offsets = {"north": 0, "west": 3, "south": 6, "east": 9}
    markup: dict[LaneName, str] = {}
    for lane, count in initial.items():
        vehicles = []
        for index in range(count):
            sprite_index = (index + lane_offsets[lane]) % 12
            row, column = divmod(sprite_index, 4)
            vehicles.append(
                '<span class="car-slot"><span class="car-model" '
                f'style="--sprite-x:{SPRITE_X[column]}%;--sprite-y:{SPRITE_Y[row]}%">'
                "</span></span>"
            )
        markup[lane] = "".join(vehicles)
    return markup


def _vehicle_sprite_uri() -> str:
    encoded = base64.b64encode(VEHICLE_SPRITE_PATH.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _car_slot_size(max_lane_count: int) -> int:
    if max_lane_count <= 20:
        return 30
    if max_lane_count <= 50:
        return 21
    if max_lane_count <= 100:
        return 15
    return 10


def _format_seconds(seconds: int) -> str:
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes} мин {remainder} с" if minutes else f"{remainder} с"


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width:1280px;padding-top:2rem;padding-bottom:3rem;}
        h1,h2,h3 {letter-spacing:0 !important;}
        .scenario-banner {display:flex;align-items:center;justify-content:space-between;gap:24px;
          margin:18px 0;padding:16px 18px;border-left:5px solid #166534;background:#f2f7f3;}
        .scenario-banner strong {display:block;font-size:19px;margin-top:3px;}
        .scenario-banner p {margin:0;max-width:560px;color:#4b5d52;}
        .eyebrow {font-size:11px;font-weight:800;color:#166534;}
        div[data-testid="stMetric"] {border-top:2px solid #d7e2da;padding-top:12px;}
        div[data-testid="stForm"] {border-radius:8px;border-color:#d7e2da;}
        @media(max-width:700px) {.scenario-banner {display:block}.scenario-banner p {margin-top:8px}}
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
