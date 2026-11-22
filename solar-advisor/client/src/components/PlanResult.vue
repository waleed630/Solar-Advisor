<script setup>
import { computed, ref } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart, BarElement, CategoryScale, LinearScale, Legend, Tooltip } from 'chart.js'
import { MONTHS } from '../store'
import { buildPdf, canShareFile, isMobile, openWhatsApp, pdfFileName, sharePdfFile } from '../pdfReport'

Chart.register(BarElement, CategoryScale, LinearScale, Legend, Tooltip)
Chart.defaults.font.family = 'Inter, system-ui, sans-serif'
Chart.defaults.color = '#45464d'

const props = defineProps({ result: Object, submissionId: String, house: Object })
const rs = (n) => (n == null ? '–' : 'Rs ' + Math.round(n).toLocaleString())
const num = (n) => (n == null ? '–' : Math.round(n).toLocaleString())
// Short money for the stat tiles: Rs 1.42M, Rs 54.8k
const short = (n) => {
  if (n == null) return { v: '–', u: '' }
  const a = Math.abs(n)
  if (a >= 1e6) return { v: 'Rs ' + (n / 1e6).toFixed(2), u: 'M' }
  if (a >= 1e4) return { v: 'Rs ' + (n / 1e3).toFixed(1), u: 'k' }
  return { v: 'Rs ' + Math.round(n).toLocaleString(), u: '' }
}

const p = computed(() => props.result.plan)
const rec = computed(() => p.value.recommended)
const batt = computed(() => p.value.with_battery)
const recOption = computed(() => p.value.size_options?.find((o) => o.panels === rec.value.panels))
const filledMonths = computed(() => MONTHS.filter((_, i) => props.result.months[i + 1].source !== 'bill').length)
const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

// Theme colours for the charts
const JADE = '#006c4a'
const MINT = '#82f5c1'
const AMBER = '#ffb77d'
const NAVY = '#213145'
const bar = { borderRadius: 4, borderSkipped: 'start', maxBarThickness: 18 }

const usageChart = computed(() => ({
  labels: MONTHS,
  datasets: [
    {
      label: 'Units used', ...bar,
      data: MONTHS.map((_, i) => props.result.months[i + 1].units),
      backgroundColor: MONTHS.map((_, i) => (props.result.months[i + 1].source === 'bill' ? JADE : MINT)),
    },
    { label: 'Solar makes', ...bar, data: rec.value.months.map((m) => m.solar), backgroundColor: AMBER },
  ],
}))

const billChart = computed(() => ({
  labels: MONTHS,
  datasets: [
    { label: 'Bill now', ...bar, data: rec.value.months.map((m) => m.bill_before), backgroundColor: NAVY },
    { label: 'Bill with solar', ...bar, data: rec.value.months.map((m) => m.bill_after), backgroundColor: JADE },
  ],
}))
const chartOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { backgroundColor: NAVY, padding: 8, cornerRadius: 6 } },
  scales: {
    x: { grid: { display: false }, border: { display: false } },
    y: { grid: { color: '#e5eeff' }, border: { display: false }, ticks: { maxTicksLimit: 5 } },
  },
}
const billOpts = { ...chartOpts, plugins: { ...chartOpts.plugins, legend: { position: 'bottom', labels: { boxWidth: 12, boxHeight: 12, useBorderRadius: true, borderRadius: 3 } } } }

// The month with the highest bill now, before and after solar
const peak = computed(() => {
  let best = 0
  rec.value.months.forEach((m, i) => { if (m.bill_before > rec.value.months[best].bill_before) best = i })
  const m = rec.value.months[best]
  return { name: MONTHS[best], before: m.bill_before, after: m.bill_after, units: props.result.months[best + 1].units }
})
const peakAfterPct = computed(() => Math.max(0, Math.min(100, (peak.value.after / (peak.value.before || 1)) * 100)))
const creditMonths = computed(() => MONTHS.filter((_, i) => rec.value.months[i].bill_after < 0))
const yearSolar = computed(() => rec.value.months.reduce((n, m) => n + (m.solar || 0), 0))

const statusText = { protected: 'Protected', unprotected: 'Unprotected', tou: 'Time of use (peak / off-peak)' }
const battBetter = computed(() => (batt.value?.lifetime_net_saving ?? -Infinity) > rec.value.lifetime_net_saving)

const roofPct = computed(() => {
  const r = p.value.roof
  return r.area_sqft ? Math.min(100, Math.round((r.needed_sqft / r.area_sqft) * 100)) : null
})
const PART_ICONS = { panels: 'solar_power', inverter: 'electrical_services', structure: 'roofing', installation: 'construction', wiring: 'cable', battery: 'battery_full', fixed: 'receipt_long' }
const partIcon = (k) => PART_ICONS[Object.keys(PART_ICONS).find((x) => k.startsWith(x))] || 'payments'
const r2 = computed(() => Number(props.result.model.seasonal_r2))

// Save the plan as a PDF, or share it on WhatsApp
const usageRef = ref(null)
const billRef = ref(null)
const busy = ref(false)
const shareMsg = ref('')
const shareEl = ref(null)

function makePdf() {
  // Pictures of the two charts as they are on screen, white background so they print well
  const png = (r) => {
    const chart = r.value?.chart
    if (!chart) return null
    const c = document.createElement('canvas')
    c.width = chart.canvas.width
    c.height = chart.canvas.height
    const ctx = c.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, c.width, c.height)
    ctx.drawImage(chart.canvas, 0, 0)
    return c.toDataURL('image/jpeg', 0.85) // JPEG keeps the PDF small enough for WhatsApp
  }
  return buildPdf(props.result, { usage: png(usageRef), bill: png(billRef) })
}

function downloadPdf() {
  makePdf().save(pdfFileName())
}

const ATTACH_TIP = 'The PDF is in your Downloads. In WhatsApp, choose the chat, then attach the PDF with the paperclip.'
const chooser = ref(false) // laptop / PC: ask where to open WhatsApp
const fileShareOk = ref(false) // this computer can also share the PDF file itself (e.g. Windows share)

async function shareWhatsApp() {
  shareMsg.value = ''
  if (!isMobile()) {
    fileShareOk.value = canShareFile(makePdf())
    chooser.value = !chooser.value
    // The header button opens the chooser at the bottom of the page, so bring it into view
    if (chooser.value) setTimeout(() => shareEl.value?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50)
    return
  }
  // Phone: the share menu with the PDF attached (pick WhatsApp, then the chat)
  busy.value = true
  try {
    const how = await sharePdfFile(makePdf(), props.result)
    if (how === 'unsupported') shareTo('app') // no share menu: open the WhatsApp app directly
  } finally {
    busy.value = false
  }
}

async function shareTo(target) {
  chooser.value = false
  if (target === 'file') {
    const how = await sharePdfFile(makePdf(), props.result)
    if (how === 'unsupported') shareMsg.value = 'This computer cannot share the file directly. Please use WhatsApp Web or the app.'
    return
  }
  downloadPdf()
  openWhatsApp(target, props.result, () => {
    shareMsg.value = 'The WhatsApp app did not open. It may not be installed on this device. ' +
      (isMobile() ? 'Install WhatsApp, or send the PDF from your Downloads.' : 'Try WhatsApp Web instead.')
  })
  shareMsg.value = ATTACH_TIP
}
</script>

<template>
  <div class="flex flex-col gap-10">
    <!-- Header -->
    <section class="card p-6 md:p-10 flex flex-col lg:flex-row lg:items-end justify-between gap-6 relative overflow-hidden">
      <div class="absolute -right-16 -top-16 w-80 h-80 bg-surface-container-high/40 rounded-full blur-3xl pointer-events-none"></div>
      <div class="flex flex-col gap-2 max-w-3xl relative">
        <div class="flex flex-wrap items-center gap-1.5">
          <span v-if="submissionId" class="chip-plain font-medium">Plan #{{ submissionId.slice(-6).toUpperCase() }}</span>
          <span class="chip bg-surface-container text-on-surface-variant font-medium">Made {{ today }}</span>
          <span class="chip-jade"><span class="w-1.5 h-1.5 rounded-full bg-secondary"></span>{{ result.basis === 'bill' ? 'Based on your bill' : 'Rough estimate' }}</span>
        </div>
        <h1 class="font-display text-display-sm md:text-display-lg font-bold tracking-tight text-on-surface">Your solar plan</h1>
        <div class="flex flex-wrap items-center gap-1.5 pt-1">
          <div class="inline-flex flex-wrap items-center gap-1.5 px-4 py-1 rounded-lg bg-surface-container text-on-surface text-label-md">
            <span class="icon text-[16px] text-on-surface-variant">home</span>
            <template v-if="house?.house_size_marla"><span>Home: <strong>{{ house.house_size_marla }} marla</strong></span><span class="text-outline-variant">•</span></template>
            <span>Tariff now: {{ statusText[rec.status_before] }}</span>
            <span class="text-outline-variant">•</span>
            <span class="font-semibold num">{{ num(p.yearly_units) }} units a year</span>
          </div>
        </div>
        <div class="flex items-start gap-1.5 p-2 rounded-lg bg-surface-container-low text-on-surface-variant text-body-sm mt-1">
          <span class="icon text-[18px] text-on-tertiary-container shrink-0">psychology</span>
          <span v-if="result.basis === 'bill'">
            Your home uses about <strong class="text-on-surface">{{ num(p.yearly_units) }} units a year</strong>.
            <template v-if="filledMonths">Light green months ({{ filledMonths }}) were filled in by the model.</template>
            <template v-else>All 12 months come from your bill.</template>
          </span>
          <span v-else class="text-on-tertiary-container">No bill given, so this is a rough estimate from your home details.</span>
        </div>
      </div>
      <div class="flex flex-wrap sm:flex-nowrap items-center gap-2 shrink-0 relative">
        <button class="btn" @click="downloadPdf"><span class="icon text-[18px]">download</span>Download PDF</button>
        <button class="btn-jade" :disabled="busy" @click="shareWhatsApp"><span class="icon text-[18px]">share</span>{{ busy ? 'Preparing…' : 'Share on WhatsApp' }}</button>
      </div>
    </section>

    <!-- Main numbers -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="card p-6 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between"><span class="eyebrow">System size</span><span class="icon text-secondary">solar_power</span></div>
        <div class="my-4">
          <div class="font-display text-numeric-xl font-bold tracking-tight num">{{ rec.kw }} <span class="text-headline-sm font-semibold text-on-surface-variant">kW</span></div>
          <p class="text-body-sm text-on-surface-variant mt-1">{{ rec.panels }} panels</p>
        </div>
        <div v-if="recOption" class="text-label-sm text-secondary font-semibold">Covers {{ recOption.covers_percent }}% of your units</div>
      </div>
      <div class="card p-6 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between"><span class="eyebrow">Cost</span><span class="icon text-on-surface-variant">payments</span></div>
        <div class="my-4">
          <div class="font-display text-numeric-xl font-bold tracking-tight num">{{ short(rec.cost).v }}<span class="text-headline-sm font-semibold text-on-surface-variant">{{ short(rec.cost).u }}</span></div>
          <p class="text-body-sm text-on-surface-variant mt-1">{{ rs(rec.cost) }} installed, without battery</p>
        </div>
        <div class="text-label-sm text-on-surface-variant num">About Rs {{ num(rec.cost / (rec.kw * 1000)) }} per watt</div>
      </div>
      <div class="card p-6 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between"><span class="eyebrow">Saving per month</span><span class="icon text-secondary">trending_down</span></div>
        <div class="my-4">
          <div class="font-display text-numeric-xl font-bold tracking-tight text-secondary num">{{ short(rec.monthly_saving).v }}{{ short(rec.monthly_saving).u }} <span class="text-headline-sm font-semibold">/ mo</span></div>
          <p class="text-body-sm text-on-surface-variant mt-1">{{ rs(rec.monthly_saving) }} on average</p>
        </div>
        <div class="text-label-sm text-secondary font-semibold num">{{ rs(rec.monthly_saving * 12) }} a year</div>
      </div>
      <div class="card p-6 flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between"><span class="eyebrow">Payback</span><span class="icon text-on-tertiary-container">bolt</span></div>
        <div class="my-4">
          <div class="font-display text-numeric-xl font-bold tracking-tight num">{{ rec.payback_years }} <span class="text-headline-sm font-semibold text-on-surface-variant">years</span></div>
          <p class="text-body-sm text-on-surface-variant mt-1">Time for the saving to pay the cost</p>
        </div>
        <div class="text-label-sm text-on-tertiary-container font-semibold">Tariff after: {{ statusText[rec.status_after] }}</div>
      </div>
      <div class="p-6 rounded-xl bg-surface-container-high/60 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between"><span class="eyebrow text-on-surface">25-year saving</span><span class="icon">account_balance</span></div>
        <div class="my-4">
          <div class="font-display text-numeric-xl font-bold tracking-tight num">{{ short(rec.lifetime_net_saving).v }}<span class="text-headline-sm font-semibold text-on-surface-variant">{{ short(rec.lifetime_net_saving).u }}</span></div>
          <p class="text-body-sm text-on-surface-variant mt-1">After all costs, including inverter replacement</p>
        </div>
        <div class="text-label-sm text-secondary font-semibold num" v-if="rec.cost">{{ (rec.lifetime_net_saving / rec.cost).toFixed(1) }}× the cost</div>
      </div>
    </section>

    <!-- Charts -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div class="lg:col-span-7 card p-6 md:p-10 flex flex-col justify-between">
        <div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
            <div>
              <span class="eyebrow">Use and solar output</span>
              <h2 class="font-display text-headline-md font-semibold">Units used vs what solar makes</h2>
            </div>
            <div class="flex flex-wrap items-center gap-4 text-label-sm">
              <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-secondary"></span><span class="text-on-surface-variant">From bill</span></span>
              <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-secondary-container"></span><span class="text-on-surface-variant">Filled by model</span></span>
              <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-tertiary-fixed-dim"></span><span>Solar makes</span></span>
            </div>
          </div>
          <div class="h-64"><Bar ref="usageRef" :data="usageChart" :options="chartOpts" /></div>
        </div>
        <div class="grid grid-cols-3 gap-2 mt-6">
          <div v-for="s in ['summer', 'mild', 'winter']" :key="s" class="panel p-3 text-center">
            <div class="eyebrow">{{ s }}</div>
            <div class="font-display font-semibold num">{{ num(result.seasons[s].avg_per_month) }} <span class="text-body-sm font-normal text-on-surface-variant">units / mo</span></div>
          </div>
        </div>
        <div class="mt-2 panel flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-1.5 text-body-sm text-on-surface-variant">
            <span class="icon text-[18px] text-secondary">eco</span>
            Solar makes about <strong class="text-on-surface num">{{ num(yearSolar) }} units</strong> a year
          </span>
          <span class="text-label-sm text-on-surface-variant">Sold back at about Rs {{ result.buyback_rate }} / unit</span>
        </div>
      </div>

      <div class="lg:col-span-5 card p-6 md:p-10 flex flex-col justify-between">
        <div>
          <span class="eyebrow">Your bill</span>
          <h2 class="font-display text-headline-md font-semibold mb-2">Bill before and after solar</h2>
          <p class="text-body-sm text-on-surface-variant mb-6">Your highest bill month now, and the same month with solar (no battery).</p>
          <div class="flex flex-col gap-4">
            <div>
              <div class="flex items-center justify-between text-label-md mb-1">
                <span class="text-on-surface-variant">{{ peak.name }} bill now</span>
                <span class="font-semibold text-error num">{{ rs(peak.before) }}</span>
              </div>
              <div class="w-full h-3 rounded-full bg-surface-container overflow-hidden"><div class="h-full bg-error rounded-full w-full"></div></div>
              <div class="flex items-center justify-between text-label-sm text-on-surface-variant mt-1">
                <span>{{ statusText[rec.status_before] }} tariff</span><span class="num">{{ num(peak.units) }} units</span>
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between text-label-md mb-1">
                <span class="text-on-surface font-semibold">{{ peak.name }} bill with solar</span>
                <span class="font-semibold text-secondary num">{{ rs(peak.after) }}</span>
              </div>
              <div class="w-full h-3 rounded-full bg-surface-container overflow-hidden"><div class="h-full bg-secondary rounded-full" :style="{ width: peakAfterPct + '%' }"></div></div>
              <div class="flex items-center justify-between text-label-sm text-secondary font-semibold mt-1">
                <span v-if="peak.before > 0">{{ Math.round((1 - peak.after / peak.before) * 100) }}% lower</span>
                <span>{{ statusText[rec.status_after] }} tariff</span>
              </div>
            </div>
            <div v-if="creditMonths.length" class="p-4 rounded-lg bg-surface-container">
              <div class="flex items-center justify-between text-label-md mb-1">
                <span class="font-semibold">Credit months ({{ creditMonths.join(', ') }})</span>
                <span class="chip rounded bg-on-secondary-container text-secondary-container">+ credit</span>
              </div>
              <p class="text-body-sm text-on-surface-variant">
                Below zero means a credit: in those months solar sells more units to the grid than you buy
                (net billing, about Rs {{ result.buyback_rate }} per unit sold).
              </p>
            </div>
          </div>
        </div>
        <div class="mt-6 flex items-center justify-between pt-4">
          <div>
            <span class="text-label-sm text-on-surface-variant">Saving in the first year</span>
            <div class="font-display text-headline-sm font-bold num">{{ rs(rec.monthly_saving * 12) }}</div>
          </div>
          <div class="text-right">
            <span class="text-label-sm text-on-surface-variant">Tariff</span>
            <div class="text-label-md font-semibold text-secondary">{{ statusText[rec.status_before] }} → {{ statusText[rec.status_after] }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Monthly bill chart -->
    <section class="card p-6 md:p-10">
      <span class="eyebrow">Month by month</span>
      <h2 class="font-display text-headline-md font-semibold mb-4">Monthly bill, now and with solar (no battery)</h2>
      <div class="h-64"><Bar ref="billRef" :data="billChart" :options="billOpts" /></div>
    </section>

    <!-- Battery comparison -->
    <section class="card p-6 md:p-10">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <span class="eyebrow">Compare</span>
          <h2 class="font-display text-headline-lg font-semibold">With or without battery</h2>
          <p class="text-body-md text-on-surface-variant mt-1">Same home, same tariff. Only the battery is different.</p>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th></th>
              <th class="w-1/3"><div class="flex items-center gap-1.5">Without battery<span v-if="!battBetter" class="chip bg-secondary-container text-on-secondary-container">Saves most</span></div></th>
              <th class="w-1/3"><div class="flex items-center gap-1.5">With battery<span v-if="battBetter" class="chip bg-secondary-container text-on-secondary-container">Saves most</span><span v-else class="chip-plain">Power in load shedding</span></div></th>
            </tr>
          </thead>
          <tbody>
            <tr><td class="text-on-surface-variant font-medium">Panels / size</td><td class="font-semibold">{{ rec.panels }} / {{ rec.kw }} kW</td><td class="font-semibold">{{ batt?.panels }} / {{ batt?.kw }} kW</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Battery</td><td class="text-on-surface-variant">None</td><td class="font-semibold">{{ batt?.battery_kwh }} kWh</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Cost</td><td class="font-display text-headline-sm font-bold text-secondary num">{{ rs(rec.cost) }}</td><td class="font-display text-headline-sm font-bold num">{{ rs(batt?.cost) }}</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Saving per month</td><td class="num">{{ rs(rec.monthly_saving) }}</td><td class="num">{{ rs(batt?.monthly_saving) }}</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Payback</td><td class="font-bold">{{ rec.payback_years }} years</td><td class="font-bold">{{ batt?.payback_years }} years</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Replacing inverter / battery in 25 years</td><td class="num">{{ rs(rec.replacement_cost) }}</td><td class="num">{{ rs(batt?.replacement_cost) }}</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Saving over 25 years (after all costs)</td><td class="font-bold num" :class="!battBetter && 'text-secondary'">{{ rs(rec.lifetime_net_saving) }}</td><td class="font-bold num" :class="battBetter && 'text-secondary'">{{ rs(batt?.lifetime_net_saving) }}</td></tr>
            <tr><td class="text-on-surface-variant font-medium">Tariff before → after</td>
              <td>{{ statusText[rec.status_before] }} → {{ statusText[rec.status_after] }}</td>
              <td>{{ statusText[batt?.status_before] }} → {{ statusText[batt?.status_after] }}</td></tr>
            <tr><td class="text-on-surface-variant font-medium">During load shedding</td>
              <td class="text-error font-medium"><span class="flex items-center gap-1"><span class="icon text-[18px]">cancel</span>Switches off with the grid</span></td>
              <td class="text-secondary font-semibold"><span class="flex items-center gap-1"><span class="icon text-[18px]">check_circle</span>Keeps power on</span></td></tr>
          </tbody>
        </table>
      </div>
      <div class="mt-6 p-4 rounded-xl bg-surface-container flex items-start gap-3">
        <span class="icon text-[24px] text-secondary shrink-0">lightbulb</span>
        <p class="text-body-sm text-on-surface">
          <strong>Neutral advice:</strong> A battery also keeps power on during load shedding, which the saving does not count.
          If your area has little load shedding, the cheaper system without a battery pays back faster.
        </p>
      </div>
    </section>

    <!-- Roof, appliances, model -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4"><span class="eyebrow">Will it fit</span><span class="icon text-secondary">roofing</span></div>
          <h3 class="font-display text-headline-sm font-semibold mb-1">Roof and structure</h3>
          <p v-if="p.roof.area_sqft" class="text-body-sm text-on-surface-variant mb-4">
            Panels need about <b class="text-on-surface">{{ num(p.roof.needed_sqft) }} sq ft</b>; you have <b class="text-on-surface">{{ num(p.roof.area_sqft) }} sq ft</b>
            (room for up to {{ p.roof.max_kw_on_roof }} kW).
          </p>
          <p v-else class="text-body-sm text-on-surface-variant mb-4">Panels need about <b class="text-on-surface">{{ num(p.roof.needed_sqft) }} sq ft</b> of free roof.</p>
          <div v-if="roofPct != null" class="mb-4">
            <div class="flex justify-between text-label-sm mb-1"><span class="text-on-surface-variant">Roof used</span><span class="font-semibold">{{ roofPct }}%</span></div>
            <div class="w-full h-2 rounded-full bg-surface-container overflow-hidden"><div class="h-full rounded-full" :class="p.roof.fits ? 'bg-secondary' : 'bg-error'" :style="{ width: roofPct + '%' }"></div></div>
          </div>
          <div class="flex flex-col gap-1 text-body-sm">
            <div class="flex justify-between gap-4 text-on-surface-variant"><span>Structure:</span><span class="font-medium text-on-surface text-right">{{ p.structure.name }}</span></div>
          </div>
          <p class="text-body-sm text-on-surface-variant mt-2">{{ p.structure.note }}</p>
        </div>
        <div class="pt-4 mt-4 flex items-center gap-1.5 text-label-sm font-semibold" :class="p.roof.fits === false ? 'text-error' : 'text-secondary'">
          <span class="icon text-[16px]">{{ p.roof.fits === false ? 'error' : 'verified' }}</span>
          <span v-if="p.roof.area_sqft">{{ p.roof.fits ? 'It fits.' : 'It does not fit.' }}</span>
          <span v-else>Add your roof area for a fit check</span>
        </div>
      </div>

      <div class="card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4"><span class="eyebrow">Load profile</span><span class="icon text-on-tertiary-container">ac_unit</span></div>
          <h3 class="font-display text-headline-sm font-semibold mb-1">Which appliances use the most (summer)</h3>
          <template v-if="result.appliances.summer">
            <p class="text-body-sm text-on-surface-variant mb-4">Based on typical power and hours of use, scaled to your bill. Approximate.</p>
            <div class="flex flex-col gap-4">
              <div v-for="(a, i) in result.appliances.summer.items" :key="a.appliance">
                <div class="flex justify-between gap-2 text-label-sm mb-1">
                  <span class="font-medium">{{ a.count }} × {{ a.appliance }}</span>
                  <span class="font-semibold whitespace-nowrap num">{{ a.share_percent }}% (~{{ a.units }} units)</span>
                </div>
                <div class="w-full h-2 rounded-full bg-surface-container overflow-hidden">
                  <div class="h-full rounded-full" :class="i === 0 ? 'bg-secondary' : i === 1 ? 'bg-secondary/70' : i === 2 ? 'bg-surface-tint' : 'bg-outline-variant'" :style="{ width: a.share_percent + '%' }"></div>
                </div>
              </div>
            </div>
          </template>
          <p v-else class="text-body-sm text-on-surface-variant">Add your appliances in step 2 to see which ones use the most.</p>
        </div>
        <div class="mt-4 p-2 rounded-lg bg-surface-container text-on-surface-variant text-body-sm">
          <span class="font-medium text-on-surface">Tip:</span> Running ACs in the daytime, when the panels make the most, uses more of your own solar.
        </div>
      </div>

      <div class="card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4"><span class="eyebrow">How sure are we</span><span class="icon text-secondary">insights</span></div>
          <h3 class="font-display text-headline-sm font-semibold mb-1">Model accuracy</h3>
          <p class="text-body-sm text-on-surface-variant mb-4">
            Based on <b class="text-on-surface">{{ result.model.based_on_houses }} homes</b> so far. It improves as more bills are added.
          </p>
          <div class="grid grid-cols-2 gap-2 mb-4">
            <div class="p-2 rounded-lg bg-surface-container">
              <span class="text-label-sm text-on-surface-variant">R² score</span>
              <div class="font-display text-headline-sm font-bold mt-0.5 num">{{ result.model.seasonal_r2 }}</div>
              <span class="text-[10px] font-semibold" :class="r2 >= 0.7 ? 'text-secondary' : 'text-on-tertiary-container'">{{ r2 >= 0.7 ? 'Good fit' : 'Still learning' }}</span>
            </div>
            <div class="p-2 rounded-lg bg-surface-container">
              <span class="text-label-sm text-on-surface-variant">Average error</span>
              <div class="font-display text-headline-sm font-bold mt-0.5 num">{{ num(result.model.seasonal_mae) }} <span class="text-[12px] font-normal text-on-surface-variant">units/mo</span></div>
              <span class="text-[10px] text-on-surface-variant">For homes it has not seen</span>
            </div>
          </div>
        </div>
        <div class="pt-4 mt-4 text-label-sm">
          <span v-if="result.training?.added" class="chip-jade">Your bill was added to the training data. Thank you!</span>
          <span v-else-if="result.training" class="text-on-surface-variant">Not used for training: {{ result.training.reason }}.</span>
        </div>
      </div>
    </section>

    <!-- Cost breakdown and other sizes -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div class="lg:col-span-5 card">
        <span class="eyebrow">Cost breakdown</span>
        <h2 class="font-display text-headline-sm font-semibold mb-4">Where the money goes (without battery)</h2>
        <div class="flex flex-col gap-2">
          <div v-for="(v, k) in rec.cost_parts" :key="k" v-show="v" class="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-surface-container-low">
            <span class="flex items-center gap-2 text-body-md text-on-surface-variant capitalize"><span class="icon text-[18px] text-on-surface">{{ partIcon(k) }}</span>{{ k.replaceAll('_', ' ') }}</span>
            <span class="font-semibold num">{{ rs(v) }}</span>
          </div>
          <div class="flex items-center justify-between gap-2 px-2.5 pt-2 font-display font-bold">
            <span>Total</span><span class="num">{{ rs(rec.cost) }}</span>
          </div>
        </div>
      </div>
      <div class="lg:col-span-7 card">
        <span class="eyebrow">Other sizes</span>
        <h2 class="font-display text-headline-sm font-semibold mb-1">Compare system sizes</h2>
        <p class="text-body-sm text-on-surface-variant mb-4">Highlighted: our pick. Its payback is within 15% of the shortest, and it saves the most over 25 years.</p>
        <div class="overflow-x-auto">
          <table class="table">
            <thead><tr><th>Panels</th><th>kW</th><th class="text-right">Cost</th><th class="text-right">Saving / year</th><th class="text-right">Payback</th><th class="text-right">Covers</th></tr></thead>
            <tbody>
              <tr v-for="o in p.size_options" :key="o.panels" :class="o.panels === rec.panels ? '!bg-secondary-container/30 font-semibold' : ''">
                <td><span class="flex items-center gap-1">{{ o.panels }}<span v-if="o.panels === rec.panels" class="icon text-[16px] text-secondary">star</span></span></td>
                <td>{{ o.kw }}</td><td class="text-right num">{{ rs(o.cost) }}</td><td class="text-right num">{{ rs(o.yearly_saving) }}</td>
                <td class="text-right">{{ o.payback_years }} yrs</td><td class="text-right">{{ o.covers_percent }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Save / share -->
    <section ref="shareEl" class="p-6 md:p-10 rounded-xl bg-inverse-surface text-inverse-on-surface shadow-md">
      <div class="flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex flex-col gap-1 max-w-2xl">
          <div class="flex items-center gap-1.5">
            <span class="icon text-secondary-fixed">gavel</span>
            <span class="eyebrow text-secondary-fixed">Independent advice</span>
          </div>
          <h3 class="font-display text-headline-lg font-bold">Save or share this plan</h3>
          <p class="text-body-md text-surface-dim leading-relaxed">
            Take the PDF to two or three installers and ask each for a quote for the same size, so you can compare fairly.
          </p>
        </div>
        <div class="flex flex-col sm:flex-row items-center gap-3 shrink-0 w-full sm:w-auto">
          <button class="btn-white w-full sm:w-auto px-6 py-3" @click="downloadPdf"><span class="icon text-[18px]">download</span>Download PDF</button>
          <button class="btn-jade w-full sm:w-auto px-6 py-3" :disabled="busy" @click="shareWhatsApp">
            <span class="icon text-[18px]">share</span>{{ busy ? 'Preparing…' : 'Share on WhatsApp' }}
          </button>
        </div>
      </div>
      <div v-if="chooser" class="mt-6 rounded-xl bg-surface-container-lowest text-on-surface p-4">
        <p class="text-label-md font-semibold mb-2">Where do you want to open WhatsApp?</p>
        <div class="flex flex-wrap gap-2">
          <button class="btn-light" @click="shareTo('web')"><span class="icon text-[18px]">computer</span>WhatsApp Web</button>
          <button class="btn-light" @click="shareTo('app')"><span class="icon text-[18px]">desktop_windows</span>WhatsApp app</button>
          <button v-if="fileShareOk" class="btn-light" @click="shareTo('file')"><span class="icon text-[18px]">attach_file</span>Share PDF file directly</button>
          <button class="text-label-md text-on-surface-variant px-2" @click="chooser = false">Cancel</button>
        </div>
        <p class="text-body-sm text-on-surface-variant mt-2">
          WhatsApp does not let websites attach a file, so the PDF downloads first and you attach it in the chat.
          <span v-if="fileShareOk">“Share PDF file directly” sends the file itself.</span>
        </p>
      </div>
      <p v-if="shareMsg" class="mt-4 note bg-tertiary-fixed text-on-tertiary-fixed"><span class="icon text-[18px] shrink-0">info</span>{{ shareMsg }}</p>
    </section>
  </div>
</template>
