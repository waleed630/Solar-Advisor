<script setup>
import { computed, onMounted, ref } from 'vue'
import api, { errorText } from '../api'
import LedgerTabs from '../components/LedgerTabs.vue'

const info = ref(null)
const error = ref('')
onMounted(async () => {
  try {
    info.value = (await api.get('/model')).data
  } catch (e) {
    error.value = errorText(e)
  }
})
const s = computed(() => info.value?.seasonal)
const h = computed(() => info.value?.house_model)
const pct = computed(() => (s.value ? (s.value.per_degree * 100).toFixed(1) : null))

// The learned temperature rule drawn as a line: extra use (% of a home's average) at each temperature
const curve = computed(() => {
  if (!s.value) return null
  const base = s.value.base_temp ?? 10
  const T0 = 10, T1 = 45
  const lift = (t) => Math.max(0, s.value.per_degree * (t - base)) * 100
  const top = Math.max(lift(T1), 1)
  const x = (t) => 40 + ((t - T0) / (T1 - T0)) * 340
  const y = (v) => 150 - (v / top) * 120
  const pts = []
  for (let t = T0; t <= T1; t += 1) pts.push(`${x(t).toFixed(1)},${y(lift(t)).toFixed(1)}`)
  return { path: 'M ' + pts.join(' L '), baseX: x(base), hasBase: s.value.base_temp != null, top: Math.round(top), half: Math.round(top / 2), x, y }
})

const homes = computed(() => {
  const m = s.value?.mae_per_house || {}
  const max = Math.max(...Object.values(m), 1)
  return Object.entries(m).map(([k, v]) => ({ k, v, w: Math.round((v / max) * 100), good: v <= s.value.mae }))
})
const r2Width = computed(() => Math.max(0, Math.min(100, (Number(s.value?.r2) || 0) * 100)))
</script>

<template>
  <LedgerTabs
    crumb="ML Model"
    title="How the model works"
    text="The model retrains every time a new bill is added (with consent) and only replaces the old model if it scores better."
  />
  <p v-if="error" class="note-red"><span class="icon text-[18px]">error</span>{{ error }}</p>

  <div v-if="s" class="flex flex-col gap-6">
    <!-- Rule banner -->
    <div class="card">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        <div class="lg:col-span-8 flex flex-col gap-2">
          <span class="chip-jade self-start"><span class="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>1. Shape of the year (used when you upload a bill)</span>
          <h2 class="font-display text-headline-md">Temperature drives the summer jump</h2>
          <p class="text-body-md text-on-surface-variant leading-relaxed">
            <template v-if="s.base_temp != null">
              Below {{ s.base_temp }}°C a home's use stays flat. Every 1°C above {{ s.base_temp }}°C adds about
              <b class="text-on-surface">{{ pct }}%</b> of its average monthly units (that is the AC switching on).
            </template>
            <template v-else>
              Every 1°C hotter adds about <b class="text-on-surface">{{ pct }}%</b> of a home's average monthly units.
            </template>
            The same pattern holds for small and big homes.
          </p>
          <div class="panel flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <span class="eyebrow block">Learned rule</span>
              <span class="font-display text-headline-sm font-semibold">{{ s.base_temp != null ? `Degree-day model (base ${s.base_temp}°C)` : 'Temperature model' }}</span>
            </div>
            <div class="px-4 py-1 rounded-lg bg-surface-container-highest font-display text-numeric-lg text-right num">
              +{{ pct }}%<span class="text-label-sm text-on-surface-variant block font-normal font-sans">extra use per 1°C{{ s.base_temp != null ? ` above ${s.base_temp}°C` : '' }}</span>
            </div>
          </div>
        </div>
        <div class="lg:col-span-4 rounded-lg bg-surface-container p-4 flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <span class="text-label-md font-semibold">Data rules</span><span class="icon text-secondary">security</span>
          </div>
          <div class="flex flex-col gap-2 text-body-sm text-on-surface-variant">
            <div class="flex items-start gap-1.5"><span class="icon text-[16px] text-on-surface mt-0.5 shrink-0">check_circle</span><span><strong>Real bills only:</strong> no made-up or simulated bills are used for training.</span></div>
            <div class="flex items-start gap-1.5"><span class="icon text-[16px] text-on-surface mt-0.5 shrink-0">block</span><span><strong>No solar homes:</strong> their bills only show grid units, so they are left out.</span></div>
            <div class="flex items-start gap-1.5"><span class="icon text-[16px] text-on-surface mt-0.5 shrink-0">tune</span><span><strong>Only if better:</strong> a retrained model replaces the old one only when it scores better.</span></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-2"><span class="eyebrow">Homes</span><span class="icon text-on-surface-variant">cottage</span></div>
          <div class="font-display text-numeric-xl num">{{ s.n_houses }} real homes</div>
          <p class="text-body-sm text-on-surface-variant mt-1">Bills shared with consent. More homes make the model better.</p>
        </div>
        <div class="mt-4 flex items-center gap-1.5 text-on-secondary-container text-label-sm font-semibold"><span class="icon text-[16px]">verified</span>Real bills only</div>
      </div>
      <div class="card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-2"><span class="eyebrow">Avg error</span><span class="icon text-on-surface-variant">query_stats</span></div>
          <div class="font-display text-numeric-xl num">{{ s.mae }} units / mo</div>
          <p class="text-body-sm text-on-surface-variant mt-1">Average miss for a home the model has not seen.</p>
        </div>
        <div class="mt-4 text-label-sm text-on-surface-variant">Tested by leaving one home out each time and predicting it.</div>
      </div>
      <div class="card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-2"><span class="eyebrow">Goodness of fit</span><span class="icon text-on-surface-variant">insights</span></div>
          <div class="font-display text-numeric-xl num">{{ s.r2 }} R²</div>
          <p class="text-body-sm text-on-surface-variant mt-1">1.0 would be perfect. Above 0.7 is a good fit.</p>
        </div>
        <div class="mt-4 w-full bg-surface-container-high rounded-full h-2 overflow-hidden"><div class="bg-secondary h-full rounded-full" :style="{ width: r2Width + '%' }"></div></div>
      </div>
    </div>

    <!-- Curve + per home -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div v-if="curve" class="lg:col-span-5 card flex flex-col gap-4">
        <div>
          <h3 class="card-title">Temperature curve</h3>
          <p class="text-body-sm text-on-surface-variant">Extra units, as a share of a home's average month, at each average temperature.</p>
        </div>
        <div class="panel flex flex-col items-center">
          <svg class="w-full h-44 text-on-surface overflow-visible" viewBox="0 0 400 180">
            <line stroke="currentColor" stroke-opacity="0.15" stroke-width="1.5" x1="40" x2="380" y1="150" y2="150" />
            <line stroke="currentColor" stroke-dasharray="4" stroke-opacity="0.1" x1="40" x2="380" y1="90" y2="90" />
            <line stroke="currentColor" stroke-dasharray="4" stroke-opacity="0.1" x1="40" x2="380" y1="30" y2="30" />
            <text fill="currentColor" fill-opacity="0.5" font-size="10" text-anchor="end" x="35" y="154">0%</text>
            <text fill="currentColor" fill-opacity="0.5" font-size="10" text-anchor="end" x="35" y="94">+{{ curve.half }}%</text>
            <text fill="currentColor" fill-opacity="0.5" font-size="10" text-anchor="end" x="35" y="34">+{{ curve.top }}%</text>
            <template v-if="curve.hasBase">
              <line stroke="#006c4a" stroke-dasharray="3" stroke-width="1.5" :x1="curve.baseX" :x2="curve.baseX" y1="30" y2="150" />
              <text fill="#006c4a" font-size="10" font-weight="600" text-anchor="middle" :x="curve.baseX" y="22">Base {{ s.base_temp }}°C</text>
            </template>
            <path :d="curve.path" fill="none" stroke="#0b1c30" stroke-width="2.5" stroke-linejoin="round" />
            <circle v-for="t in [15, 25, 35, 45]" :key="t" :cx="curve.x(t)" :cy="curve.y(Math.max(0, s.per_degree * (t - (s.base_temp ?? 10))) * 100)" r="3.5" fill="#006c4a" />
          </svg>
          <div class="w-full flex justify-between text-label-sm text-on-surface-variant pt-1 px-2">
            <span>10°C</span><span>Winter</span><span>Summer</span><span>45°C</span>
          </div>
        </div>
      </div>

      <div class="lg:col-span-7 card flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <div>
              <h3 class="card-title">Error per home</h3>
              <p class="text-body-sm text-on-surface-variant">Each home was left out of training, then predicted. Lower is better.</p>
            </div>
            <span class="chip-plain shrink-0">{{ homes.length }} homes</span>
          </div>
          <div class="overflow-x-auto">
            <table class="table text-body-sm">
              <thead><tr><th>Home</th><th class="w-1/2">Error</th><th class="text-right">Units / month</th><th class="text-right">Compared with average</th></tr></thead>
              <tbody>
                <tr v-for="r in homes" :key="r.k">
                  <td class="font-medium">{{ r.k }}</td>
                  <td><div class="w-full h-2 rounded-full bg-surface-container overflow-hidden"><div class="h-full rounded-full" :class="r.good ? 'bg-secondary' : 'bg-tertiary-fixed-dim'" :style="{ width: r.w + '%' }"></div></div></td>
                  <td class="text-right font-semibold num">{{ r.v }}</td>
                  <td class="text-right"><span :class="r.good ? 'chip-jade' : 'chip-amber'">{{ r.good ? 'Better' : 'Worse' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="mt-4 panel p-2 text-label-sm text-on-surface-variant">Average across all homes: <strong class="text-on-surface">{{ s.mae }} units / month</strong></div>
      </div>
    </div>

    <!-- Home details model -->
    <div v-if="h" class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="card-title">2. Home details only (used when there is no bill)</h2>
        <span :class="h.r2 < 0.3 ? 'chip-amber' : 'chip-jade'">{{ h.r2 < 0.3 ? 'Not reliable yet' : 'Usable' }}</span>
      </div>
      <p class="text-body-md text-on-surface-variant">{{ h.model }} on {{ h.features.join(', ') }}. Error {{ h.mae }} units / month, R² {{ h.r2 }}.</p>
      <p v-if="h.r2 < 0.3" class="note-amber mt-2"><span class="icon text-[18px]">warning</span>Not reliable yet: it needs more homes of different sizes. Upload a bill for a better estimate.</p>
    </div>

    <!-- History -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="card-title">Training history</h2><span class="icon text-on-surface-variant">history</span>
      </div>
      <div class="overflow-x-auto">
        <table class="table text-body-sm">
          <thead><tr><th>Time</th><th class="text-right">Homes</th><th class="text-right">Months</th><th class="text-right">Shape model error</th><th class="text-right">Shape R²</th><th class="text-right">Home model R²</th></tr></thead>
          <tbody>
            <tr v-for="r in [...info.history].reverse()" :key="r.time">
              <td>{{ r.time }}</td><td class="text-right num">{{ r.n_houses }}</td><td class="text-right num">{{ r.n_rows }}</td><td class="text-right num">{{ r.seasonal_mae }}</td><td class="text-right num">{{ r.seasonal_r2 }}</td><td class="text-right num">{{ r.house_r2 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
