# SolarAdvisor

Upload a Pakistani electricity bill and get the solar system size, number of panels, mounting structure,
cost, monthly saving and payback, with and without a battery. Free and neutral advice for homeowners.

## How to run

Easiest: double-click **`start-all.bat`**. It opens the three services in their own windows and then the app.

Or by hand in 3 terminals. MongoDB must be running (Windows service, `mongodb://localhost:27017`).

```bash
# 1. ML service (Python, port 8000)
cd ml-service
venv\Scripts\activate
uvicorn main:app --reload --port 8000

# 2. Server (Express, port 5000)
cd server
npm run dev

# 3. Web app (Vue, port 5173)
cd client
npm run dev
```

Open http://localhost:5173

First-time setup on a new computer:

```bash
cd ml-service && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
cd server && npm install && copy .env.example .env      # then set ADMIN_PASSWORD and JWT_SECRET
cd client && npm install
```

Bill photo reading needs Tesseract (`winget install UB-Mannheim.TesseractOCR`). Optional: set
`ANTHROPIC_API_KEY` before starting the ML service to read bills with Claude vision instead (better on phone
photos, small cost per bill).

## Admin

`/prices` in the app: log in with `ADMIN_PASSWORD` from `server/.env` to edit panel, inverter, battery and
structure prices, tariff slabs, buyback rate and solar output. You can also see quote requests there.
**Change the default password `change-me` before showing the app to anyone.**

## Folders

```
client/       Vue 3 + Vite + Tailwind + Leaflet + Chart.js
  src/roofSelect.js   click-to-select roof: grows similar colour from the click on the satellite photo
server/       Express + MongoDB (prices, plans, quote requests)
ml-service/   FastAPI: models, solar calculator, bill OCR
  core/data.py        load bills, weather and houses; data rules
  core/train.py       retrain(): seasonal model + house model, replace only if better
  core/predict.py     12 months from a bill (or from house details)
  core/tariff.py      monthly bill from units (calibrated on real bills)
  core/solar.py       generation, size, cost, savings, payback, battery
  core/appliances.py  appliance-wise split of the bill
  core/ocr.py         Tesseract bill reader; core/ocr_claude.py optional Claude vision
data/         bills.csv, houses.csv, weather, solar output, real bill amounts
config/       pakistan.json: default prices, tariff, solar output (copied into MongoDB on first start)
models/       saved models, scores and training history
notebooks/    01 explore, 02 consumption model, 03 results; ocr_eval.py
reports/      figures for the presentation
```

## Tests

```bash
cd ml-service && venv\Scripts\python -m pytest -q        # 13 tests: data rules, tariff, prediction, plan, bill intake
python client/e2e_check.py screens                        # clicks through the app in a headless browser (services running)
ml-service\venv\Scripts\python notebooks/ocr_eval.py <folder with bill photos>   # OCR accuracy vs hand-entered bills
```

## Data rules

- Real bills only, never generated data.
- Homes with solar are kept out of the consumption model.
- Names, addresses and reference numbers are not stored.
- A user's bill is used for training only if they tick the consent box; it is checked first, then `retrain()` runs.

## Key results (8 November 2026, 4 clean homes)

| | Result |
|---|---|
| Seasonal model | Below 20°C use stays flat; every 1°C above it adds about 9% of a home's average monthly units. On homes it never saw: R² 0.84, average error 104 units (33%). |
| Growth with data | From 2 to 4 homes: R² 0.64 → 0.84, error 39% → 33%. |
| House-details model | Not reliable yet (R² below 0); needs more homes of different sizes. |
| Solar in Lahore | 1 kW makes about 1,150 units a year; January is only 35% of May. |
| Battery | Pays back in 5 to 7 years instead of 2.4 to 4.4, and saves less over 25 years once it is replaced every 10 years. |
| Tariff | Calibrated on 36 real monthly bills; bill estimate within about 10%. |
| Bill OCR (Tesseract) | Clean online bills: 12/12 months. All 6 photos: 54% of months correct; tilted or faded phone photos stay weak. Unreadable months are left empty, not filled with a wrong number. |
