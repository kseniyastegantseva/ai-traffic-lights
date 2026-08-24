# Интеллектуальное управление светофором

Проект объединяет компьютерное зрение и дискретно-событийное моделирование регулируемого
перекрёстка. Пользователь загружает фотографию, система под капотом считает автомобили по
четырём направлениям, а затем автоматически запускает симуляцию управления фазами.

Главный пользовательский сценарий включает анализ фотографии и **Модель 2 — интеллектуальный
светофор**.

## Пользовательский сценарий

1. Откройте dashboard на `http://localhost:8501`.
2. Загрузите фотографию перекрёстка.
3. После автоматического анализа dashboard сам откроет экран симуляции.
4. Для нового сценария нажмите «Загрузить другую фотографию».

Ручного ввода количества автомобилей нет: числа по направлениям формируются детектором.

## Запуск на новом устройстве

### 1. Установите инструменты

Нужны:

- Git;
- Docker Desktop с Docker Compose;
- Python 3.12, если планируется запуск без Docker.

На Windows удобнее всего установить Docker Desktop и запускать команды из PowerShell.
Если проект хранится внутри WSL, включите интеграцию Docker Desktop с нужным WSL-дистрибутивом
или используйте `docker-compose.ci.yml`, как показано ниже.

### 2. Склонируйте проект

```bash
git clone https://github.com/kseniyastegantseva/traffic_light.git
cd traffic_light
```

### 3. Запустите dashboard через Docker

Если Docker видит папку проекта как обычную локальную папку, используйте основной compose-файл:

```bash
docker compose build
docker compose up dashboard
```

После запуска откройте в браузере:

```text
http://localhost:8501
```

Если проект находится в WSL, а Docker Desktop не может смонтировать WSL-папку, используйте
вариант без bind mount:

```bash
docker compose -f docker-compose.ci.yml build
docker compose -f docker-compose.ci.yml up dashboard
```

После изменений в коде для этого варианта нужно пересобрать dashboard:

```bash
docker compose -f docker-compose.ci.yml up -d --build dashboard
```

### 4. Проверьте CLI-симуляцию

```bash
docker compose run --rm sim traffic-sim compare --config configs/demo_uniform.yaml
```

Для WSL-варианта без bind mount:

```bash
docker compose -f docker-compose.ci.yml run --rm sim traffic-sim compare --config configs/demo_uniform.yaml
```

Результаты экспериментов сохраняются в `outputs/`.

### 5. Запуск без Docker

```bash
python -m venv .venv
```

Linux/macOS/WSL:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
traffic-sim compare --config configs/demo_uniform.yaml
streamlit run app/dashboard.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
traffic-sim compare --config configs/demo_uniform.yaml
streamlit run app/dashboard.py
```

### 6. Быстрая проверка разработки

```bash
ruff check .
pytest -q
```

## Быстрый старт через Docker

```bash
docker compose build
docker compose run --rm sim traffic-sim compare --config configs/demo_uniform.yaml
docker compose up dashboard
```

Dashboard будет доступен на `http://localhost:8501`.

На главном экране введите четыре значения: количество машин с севера, запада, юга и
востока. Dashboard сам определит сценарий загрузки, покажет точное начальное число машин,
анимацию сигналов и проезда, время работы алгоритма и график освобождения очереди.
Предварительный запуск эксперимента для просмотра dashboard больше не требуется.

На перекрёстке моделируются два взаимоисключающих светофора: первый управляет потоком
Юг–Север, второй — потоком Восток–Запад. Во время зелёного или жёлтого сигнала одного
светофора второй остаётся красным.

Автомобили отображаются моделями разных цветов и кузовов из спрайт-листа, поворачиваются
по направлению потока и анимированно проезжают через перекрёсток на разрешающий сигнал.

Если Docker Desktop запускается из Windows, а WSL integration для Ubuntu ещё не включена, используйте compose-файл без bind mount:

```bash
docker compose -f docker-compose.ci.yml build
docker compose -f docker-compose.ci.yml run --rm sim traffic-sim compare --config configs/demo_uniform.yaml
docker compose -f docker-compose.ci.yml up dashboard
```

`sim`-образ собирается на лёгком Docker target `base`. Dashboard и API используют target `app`, куда дополнительно устанавливаются Streamlit, Plotly и FastAPI.

## Запуск без Docker

```bash
python -m pip install -e ".[dev]"
traffic-sim compare --config configs/demo_uniform.yaml
streamlit run app/dashboard.py
```

## Основные команды

```bash
traffic-sim run --config configs/base.yaml
traffic-sim train --config configs/ai.yaml
traffic-sim sweep --config configs/ai.yaml --episodes 10,25,50,100 --seeds 1,2,3,4,5
traffic-sim select-policy --config configs/ai.yaml
traffic-sim compare --config configs/experiment.yaml
traffic-sim compare --config configs/demo_uniform.yaml
traffic-sim compare --config configs/experiment_suite.yaml
traffic-sim compare --config configs/experiment_suite_rl.yaml
```

## Обучение первого RL baseline

```bash
traffic-sim train --config configs/ai.yaml --episodes 200
```

Команда обучает табличную Q-learning policy в Gymnasium-совместимой среде и сохраняет её в `outputs/q_learning_policy.json`.

Чтобы проверить, как число эпизодов влияет на качество policy, используйте sweep:

```bash
traffic-sim sweep --config configs/ai.yaml --episodes 10,25,50,100 --seeds 1,2,3,4,5
```

Sweep сохраняет:

- `outputs/q_learning_sweep.json` — машинно-читаемые результаты;
- `outputs/q_learning_sweep.csv` — подробные прогоны по каждому seed;
- `outputs/q_learning_sweep_summary.csv` — агрегированную сводку по episodes;
- `outputs/q_learning_sweep.md` — краткий Markdown-отчёт;
- `outputs/q_learning_policy_<episodes>_seed_<seed>.json` — отдельную policy для каждой пары episodes/seed.

Чтобы использовать лучший вариант из sweep в общем SimPy-сравнении, выполните:

```bash
traffic-sim select-policy --config configs/ai.yaml
```

Команда копирует лучшую policy в `outputs/q_learning_policy.json`.

После этого policy можно включить в общий эксперимент:

```bash
traffic-sim compare --config configs/experiment_suite_rl.yaml
```

В `docker-compose.ci.yml` нет bind mount, поэтому для проверки Q-learning в Docker запускайте обучение и сравнение в одном контейнере:

```bash
docker compose -f docker-compose.ci.yml run --rm --no-deps sim sh -lc "traffic-sim train --config configs/ai.yaml --episodes 50 && traffic-sim compare --config configs/experiment_suite_rl.yaml"
```

Для полного первичного сравнения стратегий используйте:

```bash
traffic-sim compare --config configs/experiment_suite.yaml
```

Проектная память, решения и журнал задач ведутся в `wiki/`.
