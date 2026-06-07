# Flight Alerts — своё приложение дешёвых авиабилетов

Мониторинг **5–10 направлений** с **городом вылета на ваш выбор** и **push на телефон**.  
Данные только через **Travelpayouts / Aviasales Data API** (без парсинга сайтов).

## Структура

| Папка | Назначение |
|-------|------------|
| `backend/` | FastAPI, проверка цен по расписанию, Expo Push |
| `mobile/` | React Native (Expo), iOS + Android |

## Что нужно заранее

1. Регистрация в [Travelpayouts](https://www.travelpayouts.com/) → профиль → **API token** и **marker** (партнёрский id для ссылок Aviasales).
2. [Node.js](https://nodejs.org/) и Python 3.11+.
3. Для push на реальном телефоне — сборка через Expo (development build) или EAS; в Expo Go push ограничен.

## Backend

```powershell
cd flight-alerts\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Заполните TRAVELPAYOUTS_TOKEN и TRAVELPAYOUTS_MARKER
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Ручной запуск проверки цен:

```powershell
curl.exe -X POST "http://localhost:8000/internal/check-prices?secret=ВАШ_CRON_SECRET"
```

## Мобильное приложение

В `mobile/app.json` → `extra.apiUrl`:

- Android-эмулятор: `http://10.0.2.2:8000`
- iOS-симулятор: `http://localhost:8000`
- Телефон в той же Wi‑Fi: `http://192.168.x.x:8000` (IP вашего ПК)

```powershell
cd flight-alerts\mobile
npm install
npx expo start
```

## Как это работает

1. Во вкладке **Вылет** задаёте IATA (например `MOW`).
2. Добавляете направления: `IST`, макс. цена `15000`, подпись «Стамбул».
3. Сервер каждые N часов опрашивает `prices_for_dates` по ближайшим месяцам.
4. Push, если цена **≤ порога** или упала **≥ 10%** от последнего уведомления.

## IATA-коды (примеры)

| Город | Код |
|-------|-----|
| Москва (все аэропорты) | MOW |
| Санкт-Петербург | LED |
| Стамбул | IST |
| Анталья | AYT |
| Дубай | DXB |

Полный список: [IATA](https://www.iata.org/en/publications/directories/code-search/).

## Деплой на Render

В корне проекта лежит `render.yaml` — Blueprint: **Web Service** + **Postgres** (free).

Маршруты хранятся в **PostgreSQL**, а не в SQLite — они **не пропадают**, когда сервер «засыпает».

### 1. Репозиторий на GitHub

```powershell
cd flight-alerts
git add .
git commit -m "Postgres + EAS build"
git push
```

### 2. Blueprint на Render

1. [dashboard.render.com](https://dashboard.render.com/) → ваш Blueprint → **Manual sync** (или создайте Blueprint заново)
2. Render добавит базу **`flight-alerts-db`** и переменную **`DATABASE_URL`**
3. Удалите старую **`DATABASE_PATH`** из Environment вручную, если осталась
4. Секреты: `TRAVELPAYOUTS_TOKEN`, `TRAVELPAYOUTS_MARKER`, `CRON_SECRET`

Проверка:

```powershell
curl.exe https://flight-alerts-api.onrender.com/health
```

### 3. Cron (cron-job.org)

| Задача | URL | Метод | Расписание |
|--------|-----|-------|------------|
| Проверка цен | `.../internal/check-prices?secret=CRON_SECRET` | **POST** | каждые 4 ч |
| (опционально) Будить сервер | `.../health` | GET | каждые 10 мин |

### 4. Мобильное приложение → API

В `mobile/app.json` → `extra.apiUrl`:

```json
"apiUrl": "https://flight-alerts-api.onrender.com"
```

---

## Сборка приложения на телефон (без ПК)

Expo Go требует запущенный `expo start` на компьютере. Чтобы приложение работало **само**:

```powershell
cd mobile
npx.cmd eas-cli login
npm run build:android
```

1. EAS соберёт **APK** в облаке (~10–20 мин)
2. Ссылку на скачивание покажет в терминале и на [expo.dev](https://expo.dev)
3. Скачайте APK на Android и установите
4. Разрешите уведомления при первом запуске

Для iPhone нужен Apple Developer ($99/год):

```powershell
npm run build:ios
```

Профиль **`preview`** в `eas.json` — внутренняя установка (APK / TestFlight), не Store.

### Free tier Render

| Тема | Поведение |
|------|-----------|
| Сон сервиса | ~15 мин без запросов; cron `/health` помогает |
| Postgres free | ~30 дней, потом нужен upgrade или экспорт данных |
| APScheduler | дублирует cron, пока сервис не спит |

## Ограничения API

- Цены — **снимки поисков Aviasales за ~48 ч**, не live-тарифы в моменте.
- Рекомендуется кэшировать запросы; в коде уже выбирается минимум по нескольким месяцам за один проход.
