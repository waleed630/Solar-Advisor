<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { MONTHS } from '../store'

const model = ref(null)
const config = ref(null)
onMounted(async () => {
  // Both are optional: the page works without them
  try { model.value = (await api.get('/model')).data.seasonal } catch { /* ignore */ }
  try { config.value = (await api.get('/settings')).data.config } catch { /* ignore */ }
})

// Real Lahore numbers from the saved settings: units 1 kW of panels makes in each month
const yieldRows = computed(() => {
  const y = config.value?.solar?.yield_per_kw_month
  if (!y) return null
  const vals = MONTHS.map((_, i) => Number(y[i + 1]) || 0)
  const max = Math.max(...vals) || 1
  return MONTHS.map((m, i) => ({ m, v: vals[i], h: Math.round((vals[i] / max) * 100) }))
})
const yearlyPerKw = computed(() => yieldRows.value?.reduce((n, r) => n + r.v, 0))

const tariff = computed(() => config.value?.tariff_residential)
const range = (slabs) => {
  const r = (slabs || []).map((s) => Number(s.rate)).filter((n) => n > 0)
  return r.length ? `Rs ${Math.min(...r)} to ${Math.max(...r)}` : null
}

const steps = [
  { n: '01', icon: 'document_scanner', img: '/home/step-bill.jpg', alt: 'A LESCO electricity bill with the units highlighted', title: 'Upload your bill', tag: 'Photo reading',
    text: 'LESCO bills print 12 months of units. Upload a photo or type them in. Add a second meter if your home has one.',
    left: 'One or more meters', right: 'Check every number' },
  { n: '02', icon: 'satellite_alt', img: '/home/step-roof.jpg', alt: 'Satellite view of Lahore rooftops with the usable roof area marked', title: 'Your home and roof', tag: 'Roof on the map',
    text: 'Tell us your house size and appliances in English or Roman Urdu, then draw your free roof on the satellite map.',
    left: 'Marla, people, load', right: 'Leave out tank and shade' },
  { n: '03', icon: 'lab_profile', img: '/home/step-report.jpg', alt: 'A printed solar report next to a tablet showing savings charts', title: 'Your solar plan', tag: 'PDF and WhatsApp',
    text: 'System size, panels, cost, monthly saving and payback, with and without a battery, plus roof structure and appliances.',
    left: '25-year saving', right: 'Download or share' },
]
</script>

<template>
  <div class="flex flex-col gap-10 md:gap-16">
    <!-- HERO -->
    <section class="relative">
      <div class="absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] max-w-full h-[450px] bg-gradient-to-b from-surface-container-high/60 via-secondary-container/20 to-transparent blur-3xl pointer-events-none rounded-full"></div>
      <div class="relative flex flex-col items-center text-center max-w-4xl mx-auto pt-4">
        <div class="inline-flex items-center gap-1.5 px-4 py-1 rounded-full bg-surface-container-lowest shadow-sm mb-6">
          <span class="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          <span class="eyebrow">Independent solar advice • Made for LESCO and Lahore</span>
        </div>
        <h1 class="font-display text-display-sm md:text-display-lg font-bold tracking-tight text-on-surface mb-4">
          How much solar does your home <span class="text-on-tertiary-container">actually need?</span>
        </h1>
        <p class="text-body-lg text-on-surface-variant max-w-2xl mb-6 leading-relaxed">
          Upload your electricity bill. Get the system size, number of panels, cost, monthly saving and payback,
          with and without a battery. Free and neutral: we don't sell panels.
        </p>
        <div class="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto mb-6">
          <RouterLink to="/plan" class="btn w-full sm:w-auto px-10 py-3.5 rounded-xl shadow-md hover:scale-[1.02]">
            Get my solar plan<span class="icon text-[18px]">arrow_forward</span>
          </RouterLink>
          <RouterLink to="/model" class="btn-white w-full sm:w-auto px-6 py-3.5 rounded-xl">
            <span class="icon text-[18px] text-secondary">analytics</span>See how the model works
          </RouterLink>
        </div>
        <div v-if="model" class="inline-flex flex-wrap items-center justify-center gap-2 px-4 py-2 rounded-lg bg-surface-container-high/60 text-body-sm mb-10">
          <span class="flex items-center gap-1 font-semibold text-on-secondary-container">
            <span class="icon text-[16px] text-secondary">bolt</span>Model trained on {{ model.n_houses }} real Lahore homes so far
          </span>
          <span class="hidden sm:inline text-outline-variant">•</span>
          <span class="text-on-surface-variant">Average error {{ model.mae }} units / month</span>
          <span class="hidden sm:inline text-outline-variant">•</span>
          <span class="text-on-surface-variant font-medium">Retrains with every new bill</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full text-left">
          <div v-for="b in [
            { icon: 'verified_user', t: '100% Independent', d: 'No panel sales or commissions' },
            { icon: 'lock_person', t: 'Privacy first', d: 'No name, address or reference number kept' },
            { icon: 'tune', t: 'LESCO tariff built in', d: 'Protected, unprotected and time of use' },
          ]" :key="b.t" class="flex items-center gap-3 p-4 rounded-xl bg-surface-container-lowest shadow-sm">
            <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0"><span class="icon text-[22px]">{{ b.icon }}</span></div>
            <div>
              <div class="font-display text-[15px] font-semibold text-on-surface">{{ b.t }}</div>
              <div class="text-body-sm text-on-surface-variant">{{ b.d }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Solar output preview, from the saved Lahore yield table -->
      <div v-if="yieldRows" class="relative mt-10 p-4 sm:p-6 rounded-2xl bg-surface-container-lowest shadow-xl max-w-5xl mx-auto">
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4">
          <div>
            <div class="flex flex-wrap items-center gap-2 mb-1">
              <span class="chip bg-secondary-container text-on-secondary-container rounded">Lahore solar output</span>
              <span class="text-body-sm text-on-surface-variant">Units per month from 1 kW of panels</span>
            </div>
            <h2 class="font-display text-headline-md font-bold text-on-surface">What the sun gives you, month by month</h2>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="text-body-sm text-on-surface-variant">Each kW makes about</div>
              <div class="font-display text-numeric-xl font-bold text-secondary num">{{ yearlyPerKw.toLocaleString() }} <span class="text-label-sm text-on-surface-variant font-normal">units / year</span></div>
            </div>
          </div>
        </div>
        <div class="w-full bg-surface-container-low rounded-xl p-4">
          <div class="h-40 sm:h-48 flex items-end gap-1.5 sm:gap-3">
            <div v-for="r in yieldRows" :key="r.m" class="flex-1 h-full flex flex-col justify-end items-center group relative">
              <span class="hidden group-hover:block absolute -top-1 -translate-y-full bg-inverse-surface text-inverse-on-surface text-[11px] px-1.5 py-0.5 rounded num">{{ r.v }}</span>
              <div class="w-full rounded-t bg-tertiary-fixed-dim group-hover:bg-on-tertiary-container transition-colors" :style="{ height: r.h + '%' }"></div>
            </div>
          </div>
          <div class="flex gap-1.5 sm:gap-3 pt-2 text-label-sm text-on-surface-variant">
            <span v-for="r in yieldRows" :key="r.m" class="flex-1 text-center">{{ r.m }}</span>
          </div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 pt-4 text-body-sm text-on-surface-variant">
          <span class="flex items-center gap-1.5"><span class="icon text-[18px] text-secondary">check_circle</span>Your plan matches this against your own 12 months of units.</span>
          <span class="text-label-sm">{{ config.solar.yield_source }}</span>
        </div>
      </div>
    </section>

    <!-- HOW IT WORKS -->
    <section class="-mx-4 md:-mx-8 px-4 md:px-8 py-10 bg-surface-container-low rounded-none md:rounded-3xl">
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-3 mb-10">
        <div class="max-w-xl">
          <div class="eyebrow text-secondary mb-1">How it works</div>
          <h2 class="font-display text-headline-lg font-bold text-on-surface">From your electricity bill to a solar plan in three steps</h2>
        </div>
        <p class="text-body-md text-on-surface-variant max-w-md">
          No sales calls. The plan comes from your own units, the LESCO tariff and a model trained on real Lahore homes.
        </p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div v-for="s in steps" :key="s.n" class="flex flex-col justify-between p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-md transition-shadow group">
          <div>
            <div class="flex items-center justify-between mb-4">
              <span class="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center font-display text-headline-sm font-bold">{{ s.n }}</span>
              <span class="icon text-[24px] text-secondary">{{ s.icon }}</span>
            </div>
            <div class="h-44 w-full rounded-xl mb-4 relative overflow-hidden bg-surface-container">
              <img :src="s.img" :alt="s.alt" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              <div class="absolute bottom-2 left-2 bg-on-surface/80 backdrop-blur-md px-2.5 py-1 rounded text-on-primary text-label-sm font-semibold">{{ s.tag }}</div>
            </div>
            <h3 class="font-display text-headline-sm font-bold text-on-surface mb-1">{{ Number(s.n) }}. {{ s.title }}</h3>
            <p class="text-body-md text-on-surface-variant leading-relaxed">{{ s.text }}</p>
          </div>
          <div class="pt-4 mt-4 flex items-center justify-between text-label-sm text-on-surface-variant">
            <span>{{ s.left }}</span><span class="font-semibold text-secondary">{{ s.right }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- TARIFF CLIFF, from the saved tariff -->
    <section v-if="tariff" class="p-6 md:p-10 rounded-3xl bg-surface-container-high/40 shadow-sm">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        <div class="lg:col-span-5">
          <span class="chip-red rounded uppercase tracking-wider">LESCO tariff jump</span>
          <h3 class="font-display text-headline-lg font-bold text-on-surface mt-2 mb-3">
            Why crossing {{ tariff.protected_limit_units }} units costs so much
          </h3>
          <p class="text-body-md text-on-surface-variant leading-relaxed mb-4">
            A home stays "protected" only while every month stays at or below {{ tariff.protected_limit_units }} units.
            One summer of AC use can push it to the unprotected rates. Your plan shows the tariff before and after solar.
          </p>
          <div class="flex flex-col gap-1.5 text-body-sm text-on-surface">
            <div class="flex items-center gap-1.5"><span class="icon text-[18px] text-secondary">verified</span>Protected rates: {{ range(tariff.protected_slabs) }} per unit</div>
            <div class="flex items-center gap-1.5"><span class="icon text-[18px] text-error">warning</span>Unprotected rates: {{ range(tariff.unprotected_slabs) }} per unit, plus about {{ tariff.calibration.tax_percent }}% taxes</div>
            <div class="flex items-center gap-1.5"><span class="icon text-[18px] text-secondary">check_circle</span>Solar units you sell back earn about Rs {{ config.net_billing.buyback_rate_per_unit }} each</div>
          </div>
        </div>
        <div class="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="p-4 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-label-md font-semibold text-secondary">Protected</span>
                <span class="chip-jade">≤ {{ tariff.protected_limit_units }} units</span>
              </div>
              <div class="font-display text-numeric-xl font-bold text-on-surface mb-1">{{ range(tariff.protected_slabs) }}</div>
              <div class="text-body-sm text-on-surface-variant mb-4">per unit, before taxes</div>
              <div class="w-full bg-surface-container rounded-full h-2 mb-2 overflow-hidden"><div class="bg-secondary h-full rounded-full w-1/4"></div></div>
              <p class="text-body-sm text-on-surface-variant">Only while every month stays within the limit.</p>
            </div>
            <div class="mt-4 bg-surface-container-low p-2.5 rounded-xl text-label-sm">Lower slab rates for small users</div>
          </div>
          <div class="p-4 rounded-2xl bg-primary-container text-on-primary shadow-md flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-label-md font-semibold text-tertiary-fixed">Unprotected</span>
                <span class="chip-red">Above the limit</span>
              </div>
              <div class="font-display text-numeric-xl font-bold mb-1">{{ range(tariff.unprotected_slabs) }}</div>
              <div class="text-body-sm text-on-primary-container mb-4">per unit, before taxes</div>
              <div class="w-full bg-on-primary-container/30 rounded-full h-2 mb-2 overflow-hidden"><div class="bg-tertiary-fixed-dim h-full rounded-full w-[88%]"></div></div>
              <p class="text-body-sm text-inverse-on-surface">Higher rates on every unit, plus taxes and adjustments.</p>
            </div>
            <div class="mt-4 bg-inverse-surface p-2.5 rounded-xl text-label-sm text-tertiary-fixed flex items-center justify-between">
              <span>Time of use peak</span><span class="font-bold">Rs {{ tariff.tou.peak_rate }} / unit</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="p-6 md:p-10 rounded-3xl bg-tertiary text-on-tertiary shadow-xl relative overflow-hidden">
      <div class="absolute -right-20 -bottom-20 w-80 h-80 rounded-full bg-secondary/15 blur-2xl pointer-events-none"></div>
      <div class="relative flex flex-col lg:flex-row items-center justify-between gap-6">
        <div class="max-w-2xl text-center lg:text-left">
          <span class="chip rounded bg-surface-container-lowest/10 text-secondary-fixed uppercase tracking-wider mb-2">Free and independent</span>
          <h2 class="font-display text-headline-lg font-bold mb-1">Ready to see your own numbers?</h2>
          <p class="text-body-md text-inverse-on-surface max-w-xl">
            It takes a few minutes. No sales calls, no installer spam. Take the plan to any installer and compare quotes.
          </p>
        </div>
        <div class="flex flex-col sm:flex-row items-center gap-3 w-full lg:w-auto shrink-0">
          <RouterLink to="/plan" class="btn-jade w-full sm:w-auto px-10 py-4 rounded-xl shadow-lg hover:scale-[1.02]">
            Start my solar plan<span class="icon text-[18px]">bolt</span>
          </RouterLink>
          <RouterLink to="/prices" class="w-full sm:w-auto inline-flex items-center justify-center px-6 py-4 rounded-xl bg-inverse-surface text-on-primary text-label-md font-semibold hover:bg-surface-container-high/20 transition-colors">
            Tariff and prices
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
