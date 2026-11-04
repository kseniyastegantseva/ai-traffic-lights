# WIKI проекта

Эта WIKI является рабочей памятью проекта. Агент обязан читать её перед началом задачи и обновлять после завершения задачи.

## Текущий объём работ

Активный сценарий: анализ фотографии перекрёстка → **Модель 2 — интеллектуальный светофор**.

Детектор и симулятор находятся в одном корневом репозитории. Dashboard скрывает внутренний
этап детекции: пользователь загружает фотографию и автоматически переходит к симуляции.

## Страницы

- `project-strategy.md` — цель исследования и стратегия разработки.
- `architecture.md` — структура кода и публичные интерфейсы.
- `experiments.md` — дизайн экспериментов и метрики.
- `../docs/REVISION_COMPLETION_AUDIT.md` — итоговый проверяемый аудит рукописи PIERE revision.
- `../docs/QUEUE_BASED_FINAL_VALIDATION.md` — журнал независимой проверки, Fixed 8 s и разработки Queue-based improved.
- `../docs/TOTAL_SYSTEM_IMPROVEMENT_AUDIT.md` — продолжающийся системный аудит и результаты следующих исследований Queue-based.
- `../paper/QUEUE_BASED_NEXT_GENERATION_RU.md`, `../paper/NEW_ALGORITHM_COMPARISON.md`, `../paper/NEW_RESEARCH_RESULTS_FOR_PIERE.md` — промежуточное описание gap-out, сравнение и осторожные формулировки для будущей PIERE редакции.
- `../docs/STREAMLIT_DEPLOYMENT.md` — инструкция развёртывания дашборда на целевой ветке.
- `../paper/reviewer_response.md` — ответы по 11 темам ревизии с ограничениями.
- `../paper/revised_manuscript.md` и `../paper/revised_manuscript_ru.md` — английская статья и полный русский перевод.
- `../paper/RUSSIAN_EXPLANATION.md` — пояснение авторам по результатам и правкам.
- `../scripts/build_piere_manuscript.py` и `../scripts/export_piere_pdfs.ps1` — сборка DOCX и экспорт PDF обеих языковых версий.
- `../scripts/generate_piere_figures.py` — воспроизводимая генерация комплектов PNG/SVG/PDF.
- `../paper/perception_results.md` — проверка воспроизводимости и абляция YOLO.
- Конфигурации экспериментов находятся в `../configs/`; расширенная чувствительность к ошибке детекции — `../configs/piere_perception_sensitivity_expanded.yaml`.
- Отдельные seed-явные конфигурации проверки Queue-based находятся в `../configs/queue_based_*.yaml`; стандартные библиотечные аудиторские replay-скрипты — `../scripts/audit_queue_based_results.py` и `../scripts/audit_queue_based_statistics.py`.
- Эмпирический bootstrap ошибок направленного подсчёта — `../configs/piere_perception_empirical_errors.yaml`.
- `../docs/APPROACH_PREVIEW_CAUSALITY_AUDIT.md` — аудит preview и оставшиеся исследовательские задачи.
- `../docs/APPROACH_PREVIEW_V2_PROTOCOL.md` — протокол Approach Preview v2 (причинный датчик, факторный дизайн A/B/C/D, seed, правила выбора и статистика); `../docs/APPROACH_PREVIEW_V2_INTEGRATION.md` — схема интеграции, fallback и статус dashboard; `../docs/APPROACH_PREVIEW_V2_RESULTS.md` — результаты validation/final; `../docs/APPROACH_PREVIEW_V2_REMAINING_WORK.md` — что не закрыто.
- `task-log.md` — хронологический журнал выполненных задач и ограничений среды.

## Правило документации

Вся WIKI и проектная документация ведутся на русском языке.
