"""Причинная модель датчика подъезда: скрытая физика отдельно от наблюдений контроллера.

Раздел ответственности:

* ``build_ground_truth`` — **скрытая** физика. По истинным прибытиям строит траектории
  автомобилей на участке подъезда длиной ``sensor_detection_distance_m``. Это единственное
  место, где используется будущее; результат нигде не отдаётся контроллеру.
* ``build_feed`` — формирует из траекторий поток **сообщений датчика** (``measurement``,
  ``closed``, heartbeat) с моментом выпуска ``release_at`` не раньше физического события:
  кадр камеры + задержка обработки; пересечение стоп-линии — не раньше самого пересечения.
* ``CausalSensorFeed.view(now)`` — единственный вход контроллера. Читает только сообщения с
  ``release_at <= now`` и не хранит ни ``Arrival``, ни траектории. ETA в сообщении — оценка
  ``позиция / скорость``, вычисленная по зашумлённым измерениям в момент кадра, затем линейно
  уменьшается по часам; трек удаляется по событию стоп-линии, по таймауту без измерений либо
  по watchdog датчика, но не по скрытому времени прибытия.

Старый «оракул» (окно и ETA из ``Arrival.at``) остаётся только в ``simulation.py`` как
теоретическая верхняя граница и не является моделью видеодетектора.
"""
from __future__ import annotations

import bisect
import math
import random
from dataclasses import dataclass, field

from traffic_light.config import SimulationConfig

LANES = ("north", "south", "east", "west")
SPEED_FLOOR_MPS = 3.0
SPEED_CEIL_MPS = 30.0


@dataclass(frozen=True)
class SensorParams:
    seed: int
    distance_m: float
    mean_speed_mps: float
    speed_cv: float
    profile_sd: float
    frame_period_seconds: float
    latency_seconds: float
    position_noise_m: float
    speed_noise_mps: float
    eta_bias_seconds: float
    min_speed_mps: float
    track_timeout_seconds: float
    watchdog_seconds: float
    detection_probability: float
    dropout_start_probability: float
    dropout_mean_frames: float
    false_positive_rate_per_minute: float
    duplicate_track_probability: float
    outage_windows: tuple[tuple[float, float], ...]
    eta_cap_seconds: float

    @classmethod
    def from_config(cls, config: SimulationConfig) -> SensorParams:
        return cls(
            seed=config.seed,
            distance_m=config.sensor_detection_distance_m,
            mean_speed_mps=config.sensor_mean_speed_mps,
            speed_cv=config.sensor_speed_cv,
            profile_sd=config.sensor_profile_sd,
            frame_period_seconds=config.sensor_frame_period_seconds,
            latency_seconds=config.sensor_latency_seconds,
            position_noise_m=config.sensor_position_noise_m,
            speed_noise_mps=config.sensor_speed_noise_mps,
            eta_bias_seconds=config.sensor_eta_bias_seconds,
            min_speed_mps=config.sensor_min_speed_mps,
            track_timeout_seconds=config.sensor_track_timeout_seconds,
            watchdog_seconds=config.sensor_watchdog_seconds,
            detection_probability=config.preview_detection_probability,
            dropout_start_probability=config.sensor_dropout_start_probability,
            dropout_mean_frames=config.sensor_dropout_mean_frames,
            false_positive_rate_per_minute=config.sensor_false_positive_rate_per_minute,
            duplicate_track_probability=config.sensor_duplicate_track_probability,
            outage_windows=tuple((float(a), float(b)) for a, b in config.sensor_outage_windows),
            eta_cap_seconds=config.preview_seconds,
        )

    @property
    def max_track_span_seconds(self) -> float:
        """Верхняя граница срока жизни трека; нужна только для ограничения поиска в view()."""
        transit = self.distance_m / SPEED_FLOOR_MPS
        return transit + self.frame_period_seconds + self.latency_seconds + 4.0


def estimate_eta(
    position_m: float, speed_mps: float, min_speed_mps: float, bias_seconds: float = 0.0
) -> float:
    """ETA по измеренным положению и скорости.

    Скорость ниже ``min_speed_mps`` не превращается в «мгновенный подъезд»: деление идёт на
    ``min_speed_mps``, поэтому остановившаяся или очень медленная машина получает ETA не
    меньше ``position / min_speed`` (то есть большую оценку, а не малую).
    """
    return max(0.0, position_m / max(speed_mps, min_speed_mps) + bias_seconds)


@dataclass(frozen=True)
class HiddenApproachTrack:
    """Скрытая истинная траектория: остаток пути r(τ)=D(1-u-b·u(1-u)), u=τ/T."""

    key: tuple[str, str, int]
    lane: str
    entry_at: float
    crossing_at: float
    distance_m: float
    profile_b: float

    @property
    def travel_seconds(self) -> float:
        return self.crossing_at - self.entry_at

    def remaining_m(self, t: float) -> float:
        u = min(1.0, max(0.0, (t - self.entry_at) / self.travel_seconds))
        return max(0.0, self.distance_m * (1.0 - u - self.profile_b * u * (1.0 - u)))

    def speed_mps(self, t: float) -> float:
        u = min(1.0, max(0.0, (t - self.entry_at) / self.travel_seconds))
        return max(0.0, self.distance_m / self.travel_seconds * (1.0 + self.profile_b * (1.0 - 2.0 * u)))


def build_ground_truth(arrivals, params: SensorParams) -> list[HiddenApproachTrack]:
    """Скрытые траектории по истинным прибытиям (используется только при построении ленты)."""
    tracks: list[HiddenApproachTrack] = []
    occurrence: dict[tuple[str, float], int] = {}
    for event in arrivals:
        if event.at <= 0:
            continue
        index = occurrence.get((event.lane, event.at), 0)
        occurrence[(event.lane, event.at)] = index + 1
        key = (event.lane, float(event.at).hex(), index)
        rng = random.Random(f"{params.seed}:{event.lane}:{key[1]}:{index}:sensor-world")
        sigma = math.sqrt(math.log(1.0 + params.speed_cv**2)) if params.speed_cv > 0 else 0.0
        speed = params.mean_speed_mps * math.exp(rng.gauss(-0.5 * sigma**2, sigma)) if sigma else (
            params.mean_speed_mps
        )
        speed = min(SPEED_CEIL_MPS, max(SPEED_FLOOR_MPS, speed))
        travel = params.distance_m / speed
        profile = rng.gauss(0.0, params.profile_sd) if params.profile_sd > 0 else 0.0
        profile = min(0.8, max(-0.8, profile))
        tracks.append(
            HiddenApproachTrack(
                key=key,
                lane=event.lane,
                entry_at=event.at - travel,
                crossing_at=float(event.at),
                distance_m=params.distance_m,
                profile_b=profile,
            )
        )
    return tracks


@dataclass
class _TrackMessages:
    lane: str
    frame_ats: list[float] = field(default_factory=list)
    releases: list[float] = field(default_factory=list)
    etas: list[float] = field(default_factory=list)
    closed_release: float | None = None


@dataclass(frozen=True)
class SensorView:
    offsets: dict[str, list[float]] | None
    status: str  # "ok" | "unavailable"


class CausalSensorFeed:
    """Поток сообщений датчика. Не содержит истинных прибытий и траекторий."""

    def __init__(
        self,
        tracks: list[_TrackMessages],
        heartbeats: list[float],
        params: SensorParams,
    ) -> None:
        ordered = sorted((t for t in tracks if t.releases), key=lambda t: t.releases[0])
        self._tracks = ordered
        self._starts = [t.releases[0] for t in ordered]
        self._heartbeats = sorted(heartbeats)
        self._timeout = params.track_timeout_seconds
        self._watchdog = params.watchdog_seconds
        self._cap = params.eta_cap_seconds
        self._max_span = params.max_track_span_seconds + params.track_timeout_seconds
        self._grace = params.latency_seconds + params.frame_period_seconds + params.watchdog_seconds

    def view(self, now: float) -> SensorView:
        if self._status(now) != "ok":
            return SensorView(None, "unavailable")
        offsets: dict[str, list[float]] = {lane: [] for lane in LANES}
        low = bisect.bisect_left(self._starts, now - self._max_span)
        high = bisect.bisect_right(self._starts, now)
        for track in self._tracks[low:high]:
            if track.closed_release is not None and track.closed_release <= now:
                continue
            latest = bisect.bisect_right(track.releases, now) - 1
            if latest < 0 or now - track.releases[latest] > self._timeout:
                continue
            eta = max(0.0, track.etas[latest] - (now - track.frame_ats[latest]))
            if eta <= self._cap:
                offsets[track.lane].append(eta)
        for values in offsets.values():
            values.sort()
        return SensorView(offsets, "ok")

    def status(self, now: float) -> str:
        """Состояние watchdog: "ok" либо "unavailable"."""
        return self._status(now)

    def _status(self, now: float) -> str:
        latest = bisect.bisect_right(self._heartbeats, now) - 1
        if latest < 0:
            return "ok" if now <= self._grace else "unavailable"
        return "ok" if now - self._heartbeats[latest] <= self._watchdog else "unavailable"


def _in_outage(t: float, windows: tuple[tuple[float, float], ...]) -> bool:
    return any(start <= t < end for start, end in windows)


def _measure(
    track: HiddenApproachTrack, frame_at: float, params: SensorParams, rng: random.Random
) -> float:
    position = max(0.0, track.remaining_m(frame_at) + rng.gauss(0.0, params.position_noise_m))
    speed = max(0.0, track.speed_mps(frame_at) + rng.gauss(0.0, params.speed_noise_mps))
    return estimate_eta(position, speed, params.min_speed_mps, params.eta_bias_seconds)


def _frames_in_zone(track: HiddenApproachTrack, period: float) -> list[float]:
    first = max(0, math.ceil(track.entry_at / period - 1e-12))
    frames: list[float] = []
    k = first
    while k * period < track.crossing_at:
        frames.append(k * period)
        k += 1
    return frames


def build_feed(
    arrivals, params: SensorParams, duration_seconds: float
) -> CausalSensorFeed:
    """Скрытые траектории → сообщения. Единственная функция, читающая истинные прибытия."""
    messages: list[_TrackMessages] = []
    period, latency = params.frame_period_seconds, params.latency_seconds
    for track in build_ground_truth(arrivals, params):
        rng = random.Random(f"{params.seed}:{track.key}:sensor-obs")
        if rng.random() >= params.detection_probability:
            continue
        primary = _TrackMessages(track.lane)
        duplicate: _TrackMessages | None = None
        duplicate_from = None
        if rng.random() < params.duplicate_track_probability:
            duplicate = _TrackMessages(track.lane)
            duplicate_from = rng.randrange(2, 6)
        occluded = 0
        for index, frame_at in enumerate(_frames_in_zone(track, period)):
            if _in_outage(frame_at, params.outage_windows):
                continue
            if occluded > 0:
                occluded -= 1
                continue
            if params.dropout_start_probability and rng.random() < params.dropout_start_probability:
                occluded = max(0, round(rng.expovariate(1.0 / params.dropout_mean_frames)) - 1)
                continue
            primary.frame_ats.append(frame_at)
            primary.releases.append(frame_at + latency)
            primary.etas.append(_measure(track, frame_at, params, rng))
            if duplicate is not None and index >= (duplicate_from or 0):
                duplicate.frame_ats.append(frame_at)
                duplicate.releases.append(frame_at + latency)
                duplicate.etas.append(_measure(track, frame_at, params, rng))
        # Событие стоп-линии/хвоста очереди: физически наступает в момент пересечения.
        primary.closed_release = track.crossing_at
        messages.append(primary)
        if duplicate is not None:
            messages.append(duplicate)

    if params.false_positive_rate_per_minute > 0:
        for lane in LANES:
            rng = random.Random(f"{params.seed}:{lane}:sensor-false-positive")
            t = 0.0
            while True:
                t += rng.expovariate(params.false_positive_rate_per_minute / 60.0)
                if t >= duration_seconds:
                    break
                life = rng.uniform(1.0, 4.0)
                eta0 = rng.uniform(1.0, max(1.5, params.eta_cap_seconds))
                ghost = _TrackMessages(lane)
                frame = math.ceil(t / period) * period
                while frame < t + life:
                    if not _in_outage(frame, params.outage_windows):
                        ghost.frame_ats.append(frame)
                        ghost.releases.append(frame + latency)
                        ghost.etas.append(max(0.0, eta0 - (frame - t)))
                    frame += period
                messages.append(ghost)

    heartbeats: list[float] = []
    frame_index = 0
    while frame_index * period <= duration_seconds:
        frame_at = frame_index * period
        if not _in_outage(frame_at, params.outage_windows):
            heartbeats.append(frame_at + latency)
        frame_index += 1
    return CausalSensorFeed(messages, heartbeats, params)
