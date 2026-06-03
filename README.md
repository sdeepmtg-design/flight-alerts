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

В корне проекта лежит `render.yaml` — Blueprint для **Web Service** (бесплатный план).

### 1. Репозиторий на GitHub

```powershell
cd flight-alerts
git init
git add .
git commit -m "Flight alerts MVP"
# Создайте пустой репозиторий на GitHub и:
git remote add origin https://github.com/ВАШ_ЛОГИН/flight-alerts.git
git push -u origin main
```

### 2. Blueprint на Render

1. [dashboard.render.com](https://dashboard.render.com/) → **New** → **Blueprint**
2. Подключите GitHub-репозиторий `flight-alerts`
3. Render создаст сервис `flight-alerts-api`
4. При первом деплое введите секреты:
   - `TRAVELPAYOUTS_TOKEN` — из профиля Travelpayouts
   - `TRAVELPAYOUTS_MARKER` — партнёрский marker (можно пустым, если нет)
5. `CRON_SECRET` Render сгенерирует сам — **скопируйте** из вкладки **Environment** (нужен для cron ниже)

После деплоя URL будет вида `https://flight-alerts-api.onrender.com`. Проверка:

```powershell
curl.exe https://flight-alerts-api.onrender.com/health
```

### 3. Cron бесплатно (cron-job.org)

На free tier Render **нет** встроенного cron. Настройте [cron-job.org](https://cron-job.org):

| Поле | Значение |
|------|----------|
| URL | `https://flight-alerts-api.onrender.com/internal/check-prices?secret=ВАШ_CRON_SECRET` |
| Метод | **POST** |
| Расписание | каждые 4 часа |

Запрос будит «спящий» сервис и запускает проверку цен. Дополнительно можно раз в 10 мин дергать `GET /health`, чтобы сервис реже засыпал.

### 4. Мобильное приложение → production

В `mobile/app.json` замените `extra.apiUrl`:

```json
"apiUrl": "https://flight-alerts-api.onrender.com"
```

Перезапустите Expo (`npx.cmd expo start --lan`).

### 5. Free tier — что учесть

| Тема | Поведение |
|------|-----------|
| Сон сервиса | После ~15 мин без запросов API «засыпает»; первый запрос будит ~30–60 с |
| SQLite | Данные живут между перезапусками, но **сбрасываются при redeploy** |
| APScheduler | Работает, пока сервис не спит; основной триггер — cron-job.org |

### Mobile Store

- `eas build` для публикации в App Store / Google Play

## Ограничения API

- Цены — **снимки поисков Aviasales за ~48 ч**, не live-тарифы в моменте.
- Рекомендуется кэшировать запросы; в коде уже выбирается минимум по нескольким месяцам за один проход.
