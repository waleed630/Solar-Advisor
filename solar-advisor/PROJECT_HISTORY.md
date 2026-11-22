# SolarAdvisor: Project History and Redesign Brief

This file is the full story of the project so far. Give it to an AI (or designer) that will change the **theme and web design** of the app. Section 7 is the actual redesign brief; sections 1 to 6 are context.

---

## 1. What the project is

**SolarAdvisor** is a web app for homeowners in Pakistan (first market: Lahore, LESCO bills).
The user uploads a photo of their electricity bill (or types the units), answers a few questions about the home, draws the roof on a map, and gets:

- solar system size (kW) and number of panels
- total cost and where the money goes
- monthly saving and payback period
- the same plan **with and without a battery**
- roof fit check and the mounting structure the roof needs
- which appliances use the most electricity
- a PDF report that can be shared on WhatsApp

**Goal:** neutral advice. Installers often push oversized systems; this app does not sell panels.
It started as an AI/ML course project (deadline around 2026-11-22) and is meant to grow into a business (installer leads later, commercial customers, other countries).

---

## 2. Timeline

| Date | What happened |
|---|---|
| 2026-11-04 | Idea, project brief, first 5-slide presentation. Bills from 3 houses collected. No code yet. |
| 2026-11-07 | Scope expanded: homes with several meters (add meters together per month), seasonal 12-month estimate, panel count, roof structure type, appliance-wise usage, design must later support **commercial** customers and **other countries** (currency, tariff, sunlight, prices all from config, never hard-coded). |
| 2026-11-08 | Stack decided (MEVN + Python ML service, 14-day plan). Then **all 14 build steps were built in one session**: data cleaning notebook, ML models, tariff calculator, solar sizing and payback, appliance split, FastAPI service, Express + MongoDB server, Vue client, bill OCR, tests, notebooks, README, 13-slide presentation. |
| 2026-11-08 (later) | Review pass: UI clicked through in a headless browser (Playwright, `client/e2e_check.py`). Fixed a roof drawing crash, mobile nav, cramped inputs. Seasonal model improved (error 41% to 33%). 25-year saving now counts inverter and battery replacements. 13 pytest tests added. `start-all.bat` added. |
| 2026-11-11 | Accuracy baseline saved (4 homes: R² 0.84, error 33%). |
| 2026-11-12 | More real bills added to training (now 6 clean homes). Two test copies made through the app were removed. New rules: same home is never trained twice; defective-meter (DF) and meter-changed (MC) months are left out; a bad month drops only that month, not the whole bill. Latest live model: R² 0.872, error 77.5 units/month (32%). |
| After 11-12 | Roof map upgraded (click-to-select roof from satellite photo, yellow "add" and red "remove" pencils, shape cleanup), appliances typed as free text (English or Roman Urdu), PDF download and WhatsApp share added to the result page. |
| Now | Logic works end to end. Next wish: **a new theme and a more professional web design**. |

---

## 3. Tech stack and how to run

| Part | Folder | Tech | Port |
|---|---|---|---|
| Web app | `client/` | Vue 3 (script setup), Vite 8, **Tailwind CSS v4** (`@tailwindcss/vite`), Pinia, vue-router, Chart.js + vue-chartjs, Leaflet + leaflet-draw, Turf, d3-contour, jsPDF | 5173 |
| Server | `server/` | Express, MongoDB (mongoose), JWT admin login, multer uploads | 5000 |
| ML service | `ml-service/` | Python FastAPI, pandas, scikit-learn, Tesseract OCR (optional Claude vision) | 8000 |

Run everything: double-click `start-all.bat`, then open http://localhost:5173.
The client calls `/api/...`; Vite proxies that to the Express server, which calls the ML service.

Other folders: `data/` (real bills, weather, solar output), `config/pakistan.json` (default prices and tariff), `models/` (saved models and history), `notebooks/`, `reports/` (presentation slides).

---

## 4. The ML part (short)

1. **Seasonal "shape" model** (used when the user gives a bill): below about 20°C a home's use is flat; every 1°C above that adds about 9% of the home's average monthly units (AC switching on). Fills in missing months and builds the full 12-month picture.
2. **House-details model** (used when there is no bill): regression on house size, people, AC count, load. Not reliable yet (needs more homes); the UI says so.
3. **retrain()** runs after each consented bill and replaces the model only if the new one scores better. The model choice grows with the number of homes (LinearRegression, then Ridge, then RandomForest at 20+ homes).
4. **Solar calculator:** real Lahore output (about 1,150 units per kW per year), tariff slabs (protected / unprotected / time of use), net billing buyback, picks the size with the best payback and 25-year saving.
5. **Bill OCR:** Tesseract reads the 12-month "bill history" table. Clean online bills: 12/12. Phone photos: about 54%. The user always checks the numbers.

Data rules (must stay true in any redesign): real bills only, never fake data; homes with solar are kept out of training; no names, addresses or reference numbers stored; a bill is used for training only if the user ticks the consent box.

---

## 5. Current pages and components (what the redesign must cover)

### App shell: `client/src/App.vue`
White top bar: logo + "SolarAdvisor" (green), links **My plan**, **Model**, and **Prices** (right side). Content width `max-w-5xl`. Footer: "Estimates only. Prices and tariffs change often..."

### `/` Home: `views/HomeView.vue`
Hero: "How much solar does your home need?", short text, big button **Get my solar plan**, line "Model trained on N real Lahore homes so far" (from `/api/model`). Three cards: 1. Your bill, 2. Your home and roof, 3. Your plan.

### `/plan` Wizard: `views/PlanView.vue` (the main screen)
Step bar with 4 steps: **Bills, Your home, Roof, Result**.
1. **Bills:** one `MeterInput` card per meter (`components/MeterInput.vue`): "Read from bill photo" upload button (OCR, can take up to a minute), "Clear all", 12 month inputs (Jan to Dec), "+ Add another meter".
2. **Your home:** house size (marla), people, sanctioned load (kW); appliances textarea (free text, parsed live into green chips, unknown words shown in amber); checkboxes "already has solar" (with warning) and consent for training.
3. **Roof:** roof type dropdown, roof area (sq ft) input, and the **RoofMap** (`components/RoofMap.vue`): address search, "use my location", click-to-select roof, Smaller / Bigger, yellow pencil (add area) and red pencil (remove area) each with Undo / Clear, "clean shapes" toggle, satellite map, status message. Button **Show my solar plan**.
4. **Result:** `components/PlanResult.vue`.

### Result: `components/PlanResult.vue`
- Summary line (yearly units; note when months were filled by the model or when there was no bill)
- 5 stat cards: System size, Panels, Cost, Saving per month, Payback
- Bar chart: units used per month vs solar output (bill months dark green, model-filled months light green, solar amber) + summer / mild / winter averages
- Table: with vs without battery (size, battery kWh, cost, saving, payback, replacements, 25-year saving, tariff status)
- Bar chart: monthly bill now vs with solar (negative = credit)
- Roof fit card and Structure card
- Cost breakdown tiles
- Appliance usage bars (summer)
- "Other sizes" table, recommended row highlighted
- Confidence box (based on N homes, error, R², whether the bill was added to training)
- Save / share: **Download PDF**, **Share on WhatsApp** (on desktop opens a chooser: WhatsApp Web / app / share file)

### `/model`: `views/ModelView.vue`
Explains the model: degrees rule, 3 stat tiles (homes, error, R²), error per home, house-model card (warning if weak), training history table.

### `/prices` (admin): `views/PricesView.vue`
Password login card. After login: Save / Reset to defaults / Log out, equipment price inputs (with "Estimate: please check" notes), tariff slab inputs, ToU / tax / buyback inputs, solar output per month grid.

### PDF report: `client/src/pdfReport.js`
jsPDF + autotable, includes pictures of the two charts. If the colours change, update this file too so the PDF matches.

---

## 6. Current look (the starting point)

- Tailwind utility classes everywhere, plus shared classes in `client/src/style.css`: `.card`, `.btn`, `.btn-light`, `.input`, `.input-sm`, `.label` (built with `@apply`).
- Colours: page `bg-slate-50`, text `slate-800`, accent **emerald-600** (buttons, active step, highlights), amber for warnings and solar, red for errors.
- Logo / favicon (`client/public/favicon.svg`): navy square `#14213D`, sun `#F2A93B`, green panel `#10B981`. `theme-color` meta is `#14213D`. The logo colours are a good base for a new palette.
- Charts use hard-coded colours in `PlanResult.vue`: `#059669` (bill / with solar), `#a7f3d0` (model-filled), `#f59e0b` (solar), `#94a3b8` (bill now).
- WhatsApp button uses inline `background: #1da851`.
- Roof map: yellow `#F59E0B` = add area, red `#DC2626` = remove area (these meanings must stay clear).
- Font: browser default. No dark mode. Simple, plain, works on mobile but not polished.

---

## 7. Redesign brief (what we want now)

**Goal:** a modern, trustworthy, professional look for a solar / energy product, so it feels like a real startup, not a course demo. Users are normal Pakistani homeowners on phones first, so it must be simple, clear and fast.

### Do
- New theme: colour palette, typography (a clean Google Font), spacing, rounded corners, shadows, icons.
- Put the colours in one place (Tailwind v4 `@theme` tokens or CSS variables in `style.css`) instead of `emerald-600` scattered in every file.
- Better home page: stronger hero, how-it-works steps, trust points ("free and neutral", "based on real bills", "no personal data stored").
- Better wizard: clear progress bar, bigger touch targets, nice upload area for the bill photo, friendly empty / loading / error states.
- Result page should feel like a report: key numbers big at the top, the recommendation clearly highlighted, charts with the new palette.
- Mobile first: every screen must work at phone width (360 px) with no sideways scrolling; tables can scroll inside their card.
- Optional: dark mode, subtle animations.
- Keep chart colours, PDF colours and logo colours consistent with the new palette.

### Do NOT change (logic must keep working)
- Do not change any `<script setup>` logic, API calls (`client/src/api.js`), the Pinia store (`store.js`), or `v-model` / `@click` / props / emits bindings. Restyle the templates and CSS only, unless a layout change truly needs small template moves.
- Do not touch `server/`, `ml-service/`, `data/`, `models/`, `config/`.
- Keep all text meanings (estimates disclaimer, consent wording, solar-house warning, "check the numbers" after OCR, model-not-reliable warning). Wording can be polished, not removed.
- Keep the roof map tools and their yellow = add / red = remove meaning. The map container needs a fixed height (now `h-104 sm:h-136`).
- Keep the stack: Vue 3 + Tailwind. Do not switch to React, Next.js or a component library that replaces Tailwind.
- Keep the 4 routes: `/`, `/plan`, `/model`, `/prices`.

### How to test after the redesign
1. Run `start-all.bat` and open http://localhost:5173.
2. Go through the full flow: type 12 months (or upload a bill photo), fill home details and appliances, draw a roof, press "Show my solar plan".
3. Check the result page, Download PDF, the WhatsApp chooser, the `/model` page, and `/prices` login.
4. Check at phone width in browser dev tools.
5. Optional automated check (services running): `python client/e2e_check.py screens`.

Note for this Windows PC: edit client files with a normal editor. `sed -i` style edits stop Vite's file watcher from noticing changes; if that happens, restart `npm run dev`.

---

## 8. Still open (not part of the redesign)

- Admin password in `server/.env` must be changed from the default before showing the app to anyone.
- More real bills needed to improve the house-details model.
- One 2-meter home's bills are on hold until details are confirmed.
- Later: installer quotes / leads, roof detection from satellite images, commercial customers, other countries.
