<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import api, { errorText } from '../api'
import { usePlanStore } from '../store'
import { parseAppliances } from '../applianceParser'
import MeterInput from '../components/MeterInput.vue'
import RoofMap from '../components/RoofMap.vue'
import PlanResult from '../components/PlanResult.vue'

const plan = usePlanStore()
// Pages: 1 = bills and home (steps 1 and 2 side by side), 3 = roof, 4 = result
const step = ref(1)
const options = ref({ appliances: {}, roof_types: {} })
const loading = ref(false)
const error = ref('')
const homeEl = ref(null)

const steps = [
  { label: 'Bills & Units', icon: 'receipt_long' },
  { label: 'Your Home', icon: 'home_pin' },
  { label: 'Roof', icon: 'satellite_alt' },
  { label: 'Solar Plan', icon: 'finance_mode' },
]
const stepState = (i) => {
  const page = i <= 1 ? 1 : i + 1
  if (page === step.value) return i === 1 && step.value === 1 ? 'view' : 'active'
  return page < step.value ? 'done' : 'todo'
}
async function goStep(i) {
  if (i === 3 && !plan.result) return
  step.value = i <= 1 ? 1 : i + 1
  await nextTick()
  if (i === 1) homeEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  else window.scrollTo({ top: 0, behavior: 'smooth' })
}
watch(step, () => window.scrollTo({ top: 0 }))

// House size presets (1 kanal = 20 marla)
const PLOTS = [{ label: '5 Marla', v: 5 }, { label: '10 Marla', v: 10 }, { label: '1 Kanal', v: 20 }, { label: '2 Kanal', v: 40 }]

// Appliances typed as free text: parse on every change and keep the counts in the store
const parsed = computed(() => parseAppliances(plan.appliancesText))
watch(parsed, (p) => (plan.appliances = p.counts), { immediate: true })
const ICONS = [
  ['ac_', 'ac_unit'], ['fans', 'mode_fan'], ['fridge', 'kitchen'], ['deep_freezer', 'kitchen'], ['motor', 'water_pump'],
  ['iron', 'iron'], ['led_tv', 'tv'], ['lights', 'lightbulb'], ['washing', 'local_laundry_service'], ['microwave', 'microwave'],
  ['geyser', 'water_heater'], ['heater', 'heat'], ['stove', 'cooking'], ['air_cooler', 'airwave'], ['ups', 'battery_charging_full'],
  ['water_dispenser', 'water_drop'],
]
const iconFor = (key) => (ICONS.find(([k]) => key.startsWith(k) || key.includes(k)) || [, 'electrical_services'])[1]

// Ready with a bill, or without one when load, house size and people are all given
const ready = computed(() => plan.monthsEntered > 0 ||
  (plan.house.sanctioned_load_kw > 0 && plan.house.house_size_marla > 0 && plan.house.people > 0))
const monthsSlots = computed(() => plan.meters.length * 12)

// The ML service can take 10 to 20 seconds to start; keep trying for about 30 seconds before showing an error
onMounted(async () => {
  for (let attempt = 1; attempt <= 10; attempt++) {
    try {
      options.value = (await api.get('/options')).data
      error.value = ''
      return
    } catch (e) {
      error.value = attempt < 10 ? 'Starting up, one moment…' : errorText(e)
      await new Promise((r) => setTimeout(r, 3000))
    }
  }
})

async function calculate() {
  error.value = ''
  // Without a bill the estimate comes from home details, so all three are needed
  if (!plan.monthsEntered) {
    const h = plan.house
    const missing = [
      !h.sanctioned_load_kw && 'sanctioned load',
      !h.house_size_marla && 'house size (marla)',
      !h.people && 'number of people',
    ].filter(Boolean)
    if (missing.length) {
      error.value = `Enter at least one month of units from your bill. Without a bill, please give your ${missing.join(', ')}.`
      return
    }
  }
  loading.value = true
  try {
    const { data } = await api.post('/plan', plan.payload())
    plan.result = data
    plan.submissionId = data.submissionId
    step.value = 4
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <!-- Stepper -->
  <section class="-mx-4 md:-mx-8 -mt-8 md:-mt-10 mb-8 md:mb-10 px-4 md:px-8 py-4 bg-surface-container-low shadow-sm">
    <ol class="grid grid-cols-4 md:flex md:items-center gap-2 md:gap-4">
      <template v-for="(s, i) in steps" :key="s.label">
        <li class="md:flex-1 min-w-0">
          <button
            class="w-full flex flex-col md:flex-row items-center md:items-center gap-1 md:gap-3 text-center md:text-left group disabled:cursor-not-allowed"
            :class="{ 'opacity-50': stepState(i) === 'todo' }"
            :disabled="i === 3 && !plan.result"
            @click="goStep(i)"
          >
            <span
              class="w-10 h-10 shrink-0 rounded-full flex items-center justify-center transition-transform group-hover:scale-105"
              :class="stepState(i) === 'active' ? 'bg-tertiary text-on-tertiary shadow-md'
                : stepState(i) === 'done' ? 'bg-secondary text-on-secondary shadow-sm'
                : 'bg-surface-container-highest text-on-surface shadow-sm'"
            ><span class="icon text-[20px]">{{ stepState(i) === 'done' ? 'check' : s.icon }}</span></span>
            <span class="flex flex-col min-w-0">
              <span class="hidden md:block text-label-sm uppercase tracking-wider font-semibold"
                :class="stepState(i) === 'active' ? 'text-on-tertiary-container' : 'text-on-surface-variant'">
                Step 0{{ i + 1 }}{{ stepState(i) === 'active' ? ' / Active' : stepState(i) === 'view' ? ' / In view' : stepState(i) === 'done' ? ' / Done' : '' }}
              </span>
              <span class="text-label-sm md:text-headline-sm md:font-display font-semibold text-on-surface md:truncate">{{ i + 1 }}. {{ s.label }}</span>
            </span>
          </button>
        </li>
        <li v-if="i < steps.length - 1" class="hidden md:block w-12 h-0.5 bg-surface-container-highest" aria-hidden="true"></li>
      </template>
    </ol>
  </section>

  <p v-if="error" class="note-red mb-6"><span class="icon text-[18px] shrink-0">error</span>{{ error }}</p>

  <!-- 1 + 2: Bills and home -->
  <div v-if="step === 1">
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10">
      <div>
        <div class="flex items-center gap-1.5 text-on-tertiary-container text-label-md font-semibold mb-1">
          <span class="icon text-[18px]">verified</span>Your tariff, local weather
        </div>
        <h1 class="font-display text-display-sm md:text-display-lg font-bold tracking-tight text-on-surface">Your electricity bills</h1>
        <p class="text-body-lg text-on-surface-variant mt-1 max-w-3xl">
          Add one meter per bill. Your bill prints the last 12 months of units, so one recent bill per meter is enough.
          If your home has two meters (for example one per floor), add both.
        </p>
      </div>
      <button class="btn-white shrink-0" @click="plan.addMeter()">
        <span class="icon text-[18px]">add_circle</span>Add another meter
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-10">
      <!-- Step 1: bills -->
      <div class="lg:col-span-7 flex flex-col gap-6">
        <MeterInput
          v-for="(m, i) in plan.meters" :key="i" :meter="m" :index="i"
          :removable="plan.meters.length > 1" @remove="plan.removeMeter(i)"
        />
      </div>

      <!-- Step 2: home -->
      <div ref="homeEl" class="lg:col-span-5 flex flex-col gap-6 scroll-mt-28">
        <div class="card flex flex-col gap-4">
          <div class="flex items-center justify-between pb-2">
            <div>
              <span class="eyebrow text-on-tertiary-container">Step 02</span>
              <h2 class="font-display text-headline-md font-bold text-on-surface">About your home</h2>
            </div>
            <span class="icon text-[24px] text-on-surface-variant">tune</span>
          </div>

          <div>
            <label class="label" for="marla">House size</label>
            <div class="grid grid-cols-4 gap-1 mb-2">
              <button
                v-for="p in PLOTS" :key="p.v" type="button"
                class="py-2 text-center rounded-lg text-label-md transition-colors"
                :class="plan.house.house_size_marla === p.v ? 'bg-tertiary text-on-tertiary font-semibold' : 'bg-surface-container hover:bg-surface-container-high text-on-surface font-medium'"
                @click="plan.house.house_size_marla = p.v"
              >{{ p.label }}</button>
            </div>
            <div class="relative">
              <input id="marla" v-model.number="plan.house.house_size_marla" type="number" min="1" class="input pr-16" placeholder="Or type any size" />
              <span class="unit">marla</span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label" for="people">People living there</label>
              <div class="relative">
                <input id="people" v-model.number="plan.house.people" type="number" min="1" class="input pr-16 font-display text-headline-sm font-semibold" />
                <span class="unit">people</span>
              </div>
            </div>
            <div>
              <label class="label" for="load">Sanctioned load</label>
              <div class="relative">
                <input id="load" v-model.number="plan.house.sanctioned_load_kw" type="number" min="1" step="0.5" class="input pr-10 font-display text-headline-sm font-semibold" />
                <span class="unit">kW</span>
              </div>
              <p class="text-body-sm text-on-surface-variant mt-1">Printed on the bill</p>
            </div>
          </div>

          <div class="pt-1">
            <div class="flex items-center justify-between mb-1">
              <label class="text-label-md font-semibold text-on-surface flex items-center gap-1" for="appl">
                Appliances<span class="icon text-[16px] text-on-tertiary-container" title="English or Roman Urdu">psychology</span>
              </label>
              <span class="text-label-sm text-secondary font-semibold">Understood as you type</span>
            </div>
            <p class="text-body-sm text-on-surface-variant mb-2">Write them with commas, with how many of each. English or Roman Urdu is fine.</p>
            <textarea
              id="appl" v-model="plan.appliancesText" rows="3" class="input resize-none"
              placeholder="e.g. 2 AC 1.5 ton inverter, 5 pankhe, 1 fridge, 1 motor, 1 iron, 1 LED TV, 10 LED bulbs"
            ></textarea>
            <span class="eyebrow block mt-3 mb-1.5">We understood:</span>
            <div class="flex flex-wrap gap-1.5 min-h-[44px] p-2 bg-surface-container-low rounded-lg">
              <span v-if="!parsed.recognised.length && !parsed.unknown.length" class="text-label-sm text-on-surface-variant p-1">Type your appliances above to see them here…</span>
              <span
                v-for="(n, key) in parsed.counts" :key="key"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-secondary-container text-on-secondary-container text-label-sm font-semibold shadow-sm"
              ><span class="icon text-[14px]">{{ iconFor(key) }}</span>{{ n }} × {{ options.appliances[key] || key }}</span>
              <span
                v-for="u in parsed.unknown" :key="'u' + u"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-tertiary-fixed text-on-tertiary-fixed text-label-sm font-medium shadow-sm"
                title="Not recognised, left out"
              ><span class="icon text-[14px]">help</span>{{ u }} (left out)</span>
            </div>
          </div>

          <div class="pt-2 flex flex-col gap-2">
            <label class="flex items-start gap-2 cursor-pointer select-none">
              <input v-model="plan.consent" type="checkbox" class="mt-1 w-4 h-4" />
              <span class="text-body-sm text-on-surface">
                <strong>Help improve the model:</strong> I agree that my bill's units (no name, address or reference number) can be used to improve the model.
              </span>
            </label>
            <label class="flex items-start gap-2 cursor-pointer select-none">
              <input v-model="plan.hasSolar" type="checkbox" class="mt-1 w-4 h-4" />
              <span class="text-body-sm text-on-surface">This home already has solar panels</span>
            </label>
            <div v-if="plan.hasSolar" class="note bg-tertiary-fixed-dim/30 text-on-tertiary-fixed">
              <span class="icon text-[18px] shrink-0 mt-0.5">warning</span>
              <p><strong>Note:</strong> With solar, the bill only shows units taken from the grid, so the result will underestimate your real use.</p>
            </div>
          </div>
        </div>

        <!-- Next -->
        <div class="bg-surface-container-high rounded-xl p-4 flex flex-col gap-2 shadow-sm">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5 text-on-surface text-label-md font-semibold">
              <span class="icon text-[20px]" :class="ready ? 'text-secondary' : 'text-on-tertiary-container'">{{ ready ? 'verified_user' : 'pending' }}</span>
              {{ ready ? 'Ready for the next step' : 'Add units, or load + size + people' }}
            </div>
            <span class="text-label-sm text-on-surface-variant font-mono">{{ plan.monthsEntered }}/{{ monthsSlots }} months</span>
          </div>
          <p class="text-body-sm text-on-surface-variant">Next, find your home on the satellite map and mark the free part of your roof.</p>
          <button class="btn w-full py-3 group" @click="step = 3">
            Next: your roof<span class="icon text-[18px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- 3: Roof -->
  <div v-if="step === 3">
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10">
      <div>
        <div class="flex items-center gap-1.5 text-on-tertiary-container text-label-md font-semibold mb-1">
          <span class="icon text-[18px]">satellite_alt</span>Satellite roof mapping
        </div>
        <h1 class="font-display text-display-sm md:text-display-lg font-bold tracking-tight text-on-surface">Your roof</h1>
        <p class="text-body-lg text-on-surface-variant mt-1 max-w-3xl">Find your home, then select or draw the part of the roof where panels can go.</p>
      </div>
      <button class="btn-white shrink-0" @click="step = 1"><span class="icon text-[18px]">arrow_back</span>Back to bills and home</button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div class="lg:col-span-8 card">
        <RoofMap @area="(a) => (plan.roof.area_sqft = a)" />
      </div>
      <div class="lg:col-span-4 flex flex-col gap-6">
        <div class="card flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div>
              <span class="eyebrow text-on-tertiary-container">Step 03</span>
              <h2 class="font-display text-headline-md font-bold text-on-surface">Roof details</h2>
            </div>
            <span class="icon text-[24px] text-on-surface-variant">roofing</span>
          </div>
          <div>
            <label class="label" for="area">Free roof area</label>
            <div class="relative">
              <input id="area" v-model.number="plan.roof.area_sqft" type="number" min="0" class="input pr-14 font-display text-headline-sm font-semibold" />
              <span class="unit">sq ft</span>
            </div>
            <p class="text-body-sm text-on-surface-variant mt-1">Draw it on the map or type it. Leave out the water tank, stair room and parts in shade. A 5 marla roof is about 1,000 sq ft in total.</p>
          </div>
          <div>
            <span class="label">Roof type</span>
            <div class="flex flex-col gap-1.5">
              <label
                v-for="(name, key) in options.roof_types" :key="key"
                class="flex items-start gap-2 p-2.5 rounded-lg cursor-pointer transition-colors"
                :class="plan.roof.type === key ? 'bg-surface-container-high ring-2 ring-on-surface' : 'bg-surface-container-low hover:bg-surface-container'"
              >
                <input v-model="plan.roof.type" type="radio" :value="key" class="mt-1 accent-black" />
                <span class="text-body-sm"><strong class="capitalize">{{ key }}</strong>: {{ name }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="bg-surface-container-high rounded-xl p-4 flex flex-col gap-2 shadow-sm">
          <div class="flex items-center gap-1.5 text-on-surface text-label-md font-semibold">
            <span class="icon text-[20px] text-secondary">finance_mode</span>Last step
          </div>
          <p class="text-body-sm text-on-surface-variant">We size the system, check the roof, and work out cost, saving and payback.</p>
          <button class="btn w-full py-3" :disabled="loading" @click="calculate">
            <span class="icon text-[18px]" :class="loading && 'animate-spin'">{{ loading ? 'sync' : 'bolt' }}</span>
            {{ loading ? 'Calculating…' : 'Show my solar plan' }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- 4: Result -->
  <section v-if="step === 4 && plan.result">
    <PlanResult :result="plan.result" :submission-id="plan.submissionId" :house="plan.house" />
  </section>
</template>
