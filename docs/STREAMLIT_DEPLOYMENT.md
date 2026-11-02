# Развёртывание Streamlit dashboard

Инструкция относится к ветке `revision/piere-review`. Изменение branch в настройках Streamlit Community Cloud выполняется вручную владельцем приложения; публикация здесь не производилась. Текущие GitHub coordinates и публичный URL опубликованного приложения нужно записать перед переключением.

## Локальная проверка

Из корня репозитория на Python 3.12:

```bash
python -m pip install -e ".[dev]"
python scripts/build_piere_dashboard_data.py
streamlit run app/dashboard.py
```

Для запуска без графиков PIERE приложение показывает предупреждение с командой создания сводного файла. Эта команда только читает уже сохранённые запуски, она не повторяет эксперимент. При использовании фото inference запускает YOLO на CPU, если GPU недоступен.

## Community Cloud

В настройках существующего приложения сохраните его текущий subdomain и GitHub coordinates. Затем откройте настройки приложения в рабочем пространстве Community Cloud и проверьте, можно ли изменить источник на те же repository, ветку `revision/piere-review` и entrypoint `app/dashboard.py`. Сохраните исходный custom subdomain. Если текущая карточка не позволяет заменить branch, используйте создание приложения с прежним custom subdomain только после проверки, что он свободен; сначала не удаляйте существующее приложение. Community Cloud идентифицирует приложения по координатам репозитория, ветки и entrypoint; ручное создание нового приложения предлагает выбрать собственный subdomain. Поэтому сохранение URL зависит от доступности редактирования настроек существующего приложения.

Перед переключением должны быть закоммичены `outputs/piere_dashboard_data.json`, тестовые изображения, `models/visdrone_vehicles.pt` и код в `revision/piere-review`. Выберите Python 3.12. Не подключайте одновременно несколько файлов dependency management: Community Cloud выбирает первый найденный файл, причём requirements-файл рядом с entrypoint имеет приоритет над корневым.

Точка входа импортирует проектный пакет из `src/traffic_light`, а модуль YOLO используется при загрузке фотографии. Для неё добавлен один dependency-файл `app/requirements.txt` с `-e ".[dashboard]"`: он устанавливает пакет из корня и его dashboard-extra вместе с базовыми зависимостями `pyproject.toml`. Перед первой публикацией проверьте логи сборки и то, что Community Cloud запускает установку из корня репозитория и поддерживает Linux-колёса PyTorch/Ultralytics.

Community Cloud документирует приблизительные пределы 0.078–2 CPU cores, 690 MB–2.7 GB RAM и до 50 GB storage; они могут меняться. Загрузка PyTorch и YOLO-весов может упереться в память или время холодного старта. Основные дашборд-графики используют компактный JSON (~1.6 MB до добавления сценариев); полные экспериментальные истории не загружаются в Streamlit-процесс. Первый запуск приложения следует проверить по cloud logs, отдельно выполнить пробную загрузку изображения и посмотреть расход памяти. В случае превышения лимита переводите inference на отдельный сервис или используйте платформу с подходящими ресурсами.

Опубликованная конфигурация здесь не изменялась. Для возврата достаточно выбрать прежние GitHub coordinates в настройках приложения; если был создан отдельный тестовый app, удалять его следует вручную после подтверждения исходного URL.

## Официальная документация

- [Выбор репозитория, ветки, entrypoint и Python version](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Dependency files и их приоритет](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Управление приложением, ресурсы и обновление из GitHub](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
