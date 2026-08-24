from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from traffic_light.config import RunConfig
from traffic_light.gym_env import TrafficLightEnv


@dataclass
class TrainingResult:
    episodes: int
    average_reward_last_10: float
    evaluation_reward: float
    evaluation_average_queue: float
    policy_path: str

    def to_dict(self) -> dict:
        return asdict(self)


def train_q_learning(
    config: RunConfig,
    episodes: int = 200,
    learning_rate: float = 0.2,
    discount: float = 0.95,
    epsilon: float = 0.2,
    policy_path: str = "outputs/q_learning_policy.json",
) -> TrainingResult:
    env = TrafficLightEnv(
        config.intersection,
        config.simulation,
        decision_interval_seconds=config.controller.decision_interval_seconds,
    )
    rng = np.random.default_rng(config.simulation.seed)
    q_table: dict[str, list[float]] = {}
    episode_rewards: list[float] = []

    for episode in range(episodes):
        observation, _ = env.reset(seed=config.simulation.seed + episode)
        state = discretize_observation(observation)
        total_reward = 0.0
        done = False
        while not done:
            action = _choose_action(q_table, state, epsilon, rng)
            next_observation, reward, terminated, truncated, _ = env.step(action)
            next_state = discretize_observation(next_observation)
            _update_q_value(q_table, state, action, reward, next_state, learning_rate, discount)
            total_reward += reward
            state = next_state
            done = terminated or truncated
        episode_rewards.append(total_reward)

    evaluation_reward, evaluation_average_queue = evaluate_q_policy(config, q_table)
    payload = {
        "type": "tabular_q_learning",
        "state": {
            "queue_bins": [0, 3, 7, 15],
            "actions": {"0": "north_south", "1": "east_west"},
        },
        "training": {
            "episodes": episodes,
            "learning_rate": learning_rate,
            "discount": discount,
            "epsilon": epsilon,
            "seed": config.simulation.seed,
        },
        "evaluation": {
            "reward": evaluation_reward,
            "average_queue": evaluation_average_queue,
        },
        "q_table": q_table,
    }
    Path(policy_path).parent.mkdir(parents=True, exist_ok=True)
    Path(policy_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return TrainingResult(
        episodes=episodes,
        average_reward_last_10=float(np.mean(episode_rewards[-10:])),
        evaluation_reward=evaluation_reward,
        evaluation_average_queue=evaluation_average_queue,
        policy_path=policy_path,
    )


def run_training_sweep(
    config: RunConfig,
    episode_values: list[int],
    seeds: list[int] | None = None,
    output_path: str = "outputs/q_learning_sweep.json",
    csv_path: str = "outputs/q_learning_sweep.csv",
    summary_csv_path: str = "outputs/q_learning_sweep_summary.csv",
    report_path: str = "outputs/q_learning_sweep.md",
) -> pd.DataFrame:
    sweep_seeds = seeds or [config.simulation.seed]
    rows = []
    for seed in sweep_seeds:
        seed_config = _with_seed(config, seed)
        for episodes in episode_values:
            policy_path = f"outputs/q_learning_policy_{episodes}_seed_{seed}.json"
            result = train_q_learning(seed_config, episodes=episodes, policy_path=policy_path)
            rows.append({"seed": seed, **result.to_dict()})

    frame = pd.DataFrame(rows).sort_values(["episodes", "seed"]).reset_index(drop=True)
    summary = aggregate_sweep_results(frame)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    Path(summary_csv_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "duration_seconds": config.simulation.duration_seconds,
            "seeds": sweep_seeds,
            "decision_interval_seconds": config.controller.decision_interval_seconds,
        },
        "runs": frame.to_dict(orient="records"),
        "summary": summary.to_dict(orient="records"),
        "best_by_average_queue": _best_sweep_row(summary),
    }
    Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    frame.to_csv(csv_path, index=False)
    summary.to_csv(summary_csv_path, index=False)
    Path(report_path).write_text(_build_sweep_report(frame, summary), encoding="utf-8")
    return frame


def aggregate_sweep_results(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby("episodes", as_index=False)
        .agg(
            runs=("seed", "count"),
            average_reward_last_10_mean=("average_reward_last_10", "mean"),
            evaluation_reward_mean=("evaluation_reward", "mean"),
            evaluation_average_queue_mean=("evaluation_average_queue", "mean"),
            evaluation_average_queue_std=("evaluation_average_queue", "std"),
        )
        .sort_values("episodes")
        .reset_index(drop=True)
    )
    summary["evaluation_average_queue_std"] = summary["evaluation_average_queue_std"].fillna(0.0)
    summary["evaluation_average_queue_ci95"] = (
        1.96 * summary["evaluation_average_queue_std"] / np.sqrt(summary["runs"])
    )
    return summary


def select_best_policy_from_sweep(
    sweep_path: str = "outputs/q_learning_sweep.json",
    output_policy_path: str = "outputs/q_learning_policy.json",
) -> dict:
    payload = json.loads(Path(sweep_path).read_text(encoding="utf-8"))
    best = _best_policy_run(payload)
    source_policy_path = best.get("policy_path")
    if not source_policy_path:
        raise ValueError(f"В sweep-файле нет best_by_average_queue.policy_path: {sweep_path}")

    source = Path(source_policy_path)
    if not source.exists():
        raise FileNotFoundError(f"Лучшая policy из sweep не найдена: {source}")

    destination = Path(output_policy_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    selected = {
        "source_policy_path": str(source),
        "output_policy_path": str(destination),
        "episodes": best.get("episodes"),
        "seed": best.get("seed"),
        "evaluation_average_queue_mean": best.get("evaluation_average_queue_mean"),
        "evaluation_average_queue": best.get("evaluation_average_queue"),
        "evaluation_average_queue_ci95": best.get("evaluation_average_queue_ci95"),
    }
    return selected


def evaluate_q_policy(config: RunConfig, q_table: dict[str, list[float]]) -> tuple[float, float]:
    env = TrafficLightEnv(
        config.intersection,
        config.simulation,
        decision_interval_seconds=config.controller.decision_interval_seconds,
    )
    observation, _ = env.reset(seed=config.simulation.seed)
    state = discretize_observation(observation)
    total_reward = 0.0
    queues: list[float] = []
    done = False
    while not done:
        action = int(np.argmax(q_table.get(state, [0.0, 0.0])))
        observation, reward, terminated, truncated, info = env.step(action)
        state = discretize_observation(observation)
        total_reward += reward
        queues.append(float(info["total_queue"]))
        done = terminated or truncated
    return total_reward, float(np.mean(queues)) if queues else 0.0


def discretize_observation(observation: np.ndarray) -> str:
    queue_bins = [int(np.digitize(value, [0, 3, 7, 15])) for value in observation[:4]]
    phase = int(observation[4])
    return ",".join([*(str(value) for value in queue_bins), str(phase)])


def _choose_action(
    q_table: dict[str, list[float]],
    state: str,
    epsilon: float,
    rng: np.random.Generator,
) -> int:
    q_table.setdefault(state, [0.0, 0.0])
    if rng.random() < epsilon:
        return int(rng.integers(0, 2))
    return int(np.argmax(q_table[state]))


def _update_q_value(
    q_table: dict[str, list[float]],
    state: str,
    action: int,
    reward: float,
    next_state: str,
    learning_rate: float,
    discount: float,
) -> None:
    q_table.setdefault(state, [0.0, 0.0])
    q_table.setdefault(next_state, [0.0, 0.0])
    current = q_table[state][action]
    target = reward + discount * max(q_table[next_state])
    q_table[state][action] = current + learning_rate * (target - current)


def _with_seed(config: RunConfig, seed: int) -> RunConfig:
    seed_config = config.model_copy(deep=True)
    seed_config.simulation.seed = seed
    return seed_config


def _best_policy_run(payload: dict) -> dict:
    best = payload.get("best_by_average_queue") or {}
    if best.get("policy_path"):
        return best

    runs = payload.get("runs") or []
    if not runs:
        return best

    episodes = best.get("episodes")
    candidates = [run for run in runs if run.get("episodes") == episodes] if episodes else runs
    selected_run = min(
        candidates,
        key=lambda run: (
            run.get("evaluation_average_queue", float("inf")),
            run.get("episodes", float("inf")),
            run.get("seed", float("inf")),
        ),
    )
    return {**best, **selected_run}


def _best_sweep_row(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {}
    queue_column = (
        "evaluation_average_queue_mean"
        if "evaluation_average_queue_mean" in frame.columns
        else "evaluation_average_queue"
    )
    return frame.sort_values([queue_column, "episodes"]).iloc[0].to_dict()


def _build_sweep_report(frame: pd.DataFrame, summary: pd.DataFrame) -> str:
    best = _best_sweep_row(summary)
    lines = [
        "# Sweep обучения Q-learning",
        "",
        "Цель sweep — проверить, как число episodes и seed влияют на качество обученной policy.",
        "",
        "## Агрегированная сводка",
        "",
        _summary_to_markdown(summary),
        "",
        "## Подробные прогоны",
        "",
        _runs_to_markdown(frame),
        "",
    ]
    if best:
        lines.extend(
            [
                "## Вывод",
                "",
                (
                    f"Минимальная средняя очередь на evaluation получена при "
                    f"{int(best['episodes'])} episode: "
                    f"{best['evaluation_average_queue_mean']:.2f} "
                    f"± {best['evaluation_average_queue_ci95']:.2f}."
                ),
                "",
            ]
        )
    return "\n".join(lines)


def _summary_to_markdown(frame: pd.DataFrame) -> str:
    columns = [
        "episodes",
        "runs",
        "average_reward_last_10_mean",
        "evaluation_reward_mean",
        "evaluation_average_queue_mean",
        "evaluation_average_queue_ci95",
    ]
    headers = [
        "Episodes",
        "Прогонов",
        "Reward последних 10, mean",
        "Evaluation reward, mean",
        "Средняя очередь, mean",
        "CI95 очереди",
    ]
    return _markdown_table(frame, columns, headers)


def _runs_to_markdown(frame: pd.DataFrame) -> str:
    columns = [
        "seed",
        "episodes",
        "average_reward_last_10",
        "evaluation_reward",
        "evaluation_average_queue",
        "policy_path",
    ]
    headers = [
        "Seed",
        "Episodes",
        "Reward последних 10",
        "Evaluation reward",
        "Средняя очередь",
        "Policy",
    ]
    return _markdown_table(frame, columns, headers)


def _markdown_table(frame: pd.DataFrame, columns: list[str], headers: list[str]) -> str:
    rows = [headers, ["---"] * len(headers)]
    for _, row in frame[columns].iterrows():
        rows.append([_format_markdown_value(row[column]) for column in columns])
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def _format_markdown_value(value: object) -> str:
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}"
    if isinstance(value, int | np.integer):
        return str(value)
    return str(value)
