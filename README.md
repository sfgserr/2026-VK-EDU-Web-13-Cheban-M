# Forum

Учебный проект VK Education — сервис вопросов и ответов на Django.

## Запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver
```

Открыть <http://127.0.0.1:8000/>.

## Запуск через Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Открыть <http://localhost:8000/>.

## Страницы

| URL | Страница |
|-----|----------|
| `/` | Новые вопросы |
| `/hot/` | Горячие вопросы |
| `/tag/<тег>/` | Вопросы по тегу |
| `/question/<id>/` | Вопрос с ответами |
| `/ask/` | Задать вопрос |
| `/login/` | Вход |
| `/signup/` | Регистрация |
| `/profile/` | Настройки профиля |

Статическая вёрстка из ДЗ 1 лежит в `public/`.
