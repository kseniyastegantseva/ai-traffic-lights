# Approach Preview v2: что ещё нужно доделать в локальной копии

Состояние на 2026-11-04 (обновлено после завершения работы). Ветка `feature/approach-preview`, подтянута до
`1317c48`. Изменения закоммичены локально и **не отправлены** в origin (по просьбе «сделать локально»).

## Что уже сделано (код, тесты, протокол)

- Причинный датчик `src/traffic_light/sensor.py`, новые поля `SimulationConfig` / `ControllerConfig` /
  `ScenarioConfig`, интеграция в `simulation.py`, метрики без цензурирования.
- `DetectorVehicleActuatedController`; rollout с остатком обслуживания, потерей времени на старт,
  жёлтым 0…N с и динамическим all-red; режимы `eta_rounding`, `future_arrivals`, `max_work_units`.
- `src/traffic_light/rollout_audit.py`: на 1620 целочисленных случаях расхождение rollout и SimPy
  нулевое; перебор планов, ошибка округления ETA.
- Скрипты: `create_approach_preview_v2_configs.py`, `run_approach_preview_v2.py`,
  `analyze_approach_preview_v2.py`, `freeze_approach_preview_v2.py`, `audit_rollout_vs_simpy.py`,
  `measure_approach_preview_runtime.py`.
- Документы: `APPROACH_PREVIEW_V2_PROTOCOL.md`, `APPROACH_PREVIEW_V2_INTEGRATION.md`.
- Тесты: `tests/test_approach_preview_v2.py` (142 проходят), прежние 79 проходят, `ruff check .` чистый.
  `tests/test_dashboard.py` и `tests/test_vision_contract.py` не запускались (нужны зависимости
  компьютерного зрения).
- Development (seed 31101–31120) посчитан полностью, выбор записан в
  `outputs/approach_preview_v2/development_selection.json`. Для min-green 6 с выбраны
  `A_dva_g0`, `B_dva_pv_g0_e2`, `C_roll_c6_zero`, `D_roll_pv_c6_zero`.

## Что выполнено после первой версии этого файла

Validation (14/14), анализ validation, профиль времени, аудит rollout, заморозка, final (m6, 1800 и 3600 с),
анализ final, документ результатов, WIKI и локальный коммит. Файл ниже перечисляет только оставшееся.

## Что ещё можно сделать

- Запустить final для пресетов датчика, sweeps и min-green 4/8 (конфиги генерируются командой `--stage final`).
- Заменить синтетическую модель траекторий на калиброванную по данным камеры; добавить торможение в хвосте очереди.
- Снизить рост максимального красного у D в слабых режимах (дополнительное ограничение на время красного) и
  повторить development/validation/final заново с новой заморозкой.
- Независимая проверка final другим исполнителем.

## Что принципиально не закрыто

- P18: режим по видео/камере в dashboard не реализован, dashboard не менялся.
- Датчик — синтетическая модель; параметры ошибок не откалиброваны по реальной камере.
- Реальные тайминги на целевом оборудовании и журнал решений для оборудования не сделаны.
- Прежние результаты «17–50 %» не пересчитывались и в публикацию v2 не переносятся.
- Нужна независимая проверка: final запускает тот же автор, что и разработал код.
