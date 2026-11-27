# Forum

Учебный сервис вопросов и ответов на Django и PostgreSQL.

## Запуск через Docker Compose

Создать настройки (в `.env.docker` хост БД — `db`):

```bash
cp .env.example .env.docker
# В .env.docker заменить DB_HOST на db, задать пароль и секретный ключ.
docker compose --env-file .env.docker up --build
```

Миграции применяются автоматически при запуске. Открыть http://localhost:8000/.

```bash
docker compose --env-file .env.docker exec web python manage.py createsuperuser
docker compose --env-file .env.docker exec web python manage.py fill_db 100
```

Данные PostgreSQL и загруженные файлы хранятся в отдельных томах.
Для проверки раздачи статики и аватаров через nginx запустите
`docker compose --env-file .env.docker --profile nginx up --build` и откройте
<http://localhost:8080/>.

## Локальный запуск

Нужен Python 3.9+ и PostgreSQL. Можно запустить только базу через Docker:

```bash
cp .env.example .env.local
# Задать пароль и секретный ключ; DB_HOST оставить 127.0.0.1.
docker compose --env-file .env.local up -d db
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

При установленном локальном PostgreSQL вместо Docker создать БД и пользователя,
указав параметры подключения в `.env.local`.
Открыть http://127.0.0.1:8000/. Админка: `/admin/`.
Настройки локального запуска читаются из `.env.local`; другой файл можно указать через `ENV_FILE`.
`.env.local` и `.env.docker` не коммитятся, образец настроек — `.env.example`.

## Тестовые данные

```bash
python manage.py fill_db 100
```

Команда добавляет `ratio` пользователей и тегов, `ratio * 10` вопросов,
`ratio * 100` ответов и `ratio * 200` оценок. Используются Faker и пакетные
`bulk_create` / `bulk_update`. Повторный запуск добавляет новый набор данных.
Минимальный ratio — 2: с одним пользователем недостаточно уникальных пар
«пользователь — вопрос/ответ» для 200 оценок. Пароли сгенерированных пользователей отключены.

Для полного объёма:

```bash
python manage.py fill_db 10001
```

Это 10 001 пользователь, 100 010 вопросов, 1 000 100 ответов,
10 001 тег и 2 000 200 оценок. Команда также поддерживает `ratio=10000`.

## Страницы

| URL | Страница |
|-----|----------|
| `/` | Новые вопросы |
| `/hot/` | Лучшие вопросы |
| `/tag/<тег>/` | Вопросы по тегу |
| `/question/<id>/` | Вопрос с ответами |
| `/ask/` | Задать вопрос |
| `/login/` | Вход |
| `/logout/` | Выход (POST) |
| `/signup/` | Регистрация |
| `/profile/` | Настройки профиля |
| `/admin/` | Админка |

Для публикации, голосования и редактирования профиля нужен аккаунт.
Автор вопроса может отметить один ответ как правильный.
В профиле можно загрузить JPG или PNG размером до 2 МБ. Аватары хранятся в `MEDIA_ROOT`.
Пагинация — `?page=2`. Некорректная страница не вызывает ошибку;
несуществующий вопрос или тег возвращает 404. Пустые списки показывают сообщение.
Django Debug Toolbar подключается только при `DJANGO_DEBUG=1` (локальные адреса).
Статическая вёрстка ДЗ1 сохранена в `public/`.

## Проверка

```bash
python manage.py check
python manage.py test questions
```

Для тестов пользователь PostgreSQL должен иметь право создавать тестовую базу.
