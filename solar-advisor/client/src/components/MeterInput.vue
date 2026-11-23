<script setup>
import { computed, ref } from 'vue'
import api, { errorText } from '../api'
import { MONTHS } from '../store'

const props = defineProps({ meter: Object, index: Number, removable: Boolean })
const emit = defineEmits(['remove'])
const reading = ref(false)
const ocrMsg = ref('')
const ocrOk = ref(false)

// Season label for each month tile
const SEASON = ['Winter', 'Winter', 'Spring', 'Spring', 'Pre-peak', 'Peak', 'Peak', 'Peak', 'Post-peak', 'Autumn', 'Winter', 'Winter']
const isPeak = (i) => i >= 5 && i <= 7

const values = computed(() => MONTHS.map((_, i) => Number(props.meter.months[i + 1]) || 0))
const hasUnits = computed(() => Object.values(props.meter.months).some((u) => u !== null && u !== ''))
const filled = computed(() => values.value.filter((u) => u > 0).length)
const total = computed(() => values.value.reduce((n, u) => n + u, 0))
const maxVal = computed(() => Math.max(...values.value) || 1)
// Summer peak compared with the lowest winter month, only when both are entered
const peakRatio = computed(() => {
  const winter = [0, 1, 10, 11].map((i) => values.value[i]).filter((u) => u > 0)
  const summer = [5, 6, 7].map((i) => values.value[i]).filter((u) => u > 0)
  if (!winter.length || !summer.length) return null
  return (Math.max(...summer) / Math.min(...winter)).toFixed(1)
})

// Empty all 12 boxes of this meter (asks first, so a slip doesn't lose typed numbers)
function clearAll() {
  if (!confirm(`Clear all 12 months of meter ${props.index + 1}?`)) return
  for (const m of Object.keys(props.meter.months)) props.meter.months[m] = null
  ocrMsg.value = ''
}

async function readPhoto(e) {
  const file = e.target.files[0]
  if (!file) return
  reading.value = true
  ocrMsg.value = ''
  const form = new FormData()
  form.append('bill', file)
  try {
    const { data } = await api.post('/ocr', form)
    let found = 0
    for (const [m, u] of Object.entries(data.months || {})) {
      props.meter.months[m] = u
      found++
    }
    ocrOk.value = found > 0
    ocrMsg.value = found
      ? `Read ${found} months from the photo. Please check every number against your bill.`
      : 'Could not read the months from this photo. Please type them in.'
  } catch (err) {
    ocrOk.value = false
    ocrMsg.value = `Photo reading failed: ${errorText(err)}. Please type the units in.`
  } finally {
    reading.value = false
    e.target.value = ''
  }
}
</script>

<template>
  <div class="card flex flex-col gap-6 relative overflow-hidden">
    <div class="absolute top-0 left-0 w-1.5 h-full bg-tertiary"></div>

    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-2">
      <div>
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="font-display text-headline-md font-bold text-on-surface">Meter {{ index + 1 }}</h3>
          <span class="chip-jade">{{ filled }}/12 months</span>
        </div>
        <p class="text-body-sm text-on-surface-variant mt-1">Units for each bill month, from the "Bill history" table. Leave blank if unknown.</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1.5 bg-surface-container-low px-3 py-1 rounded-lg">
          <span class="icon text-[16px] text-secondary">bolt</span>
          <span class="text-label-sm font-semibold text-on-surface num">Total: {{ total.toLocaleString() }} units</span>
        </div>
        <button
          class="px-3 py-1.5 bg-surface-container text-on-surface-variant hover:text-error hover:bg-error-container/40 rounded-lg text-label-md font-semibold transition-colors flex items-center gap-1 disabled:opacity-40 disabled:pointer-events-none"
          :disabled="!hasUnits || reading" @click="clearAll"
        ><span class="icon text-[18px]">delete_sweep</span>Clear all</button>
        <button v-if="removable" class="px-3 py-1.5 rounded-lg text-label-md font-semibold text-error hover:bg-error-container/40 flex items-center gap-1" @click="emit('remove')">
          <span class="icon text-[18px]">close</span>Remove meter
        </button>
      </div>
    </div>

    <!-- Bill photo upload -->
    <label
      class="bg-surface-container-low hover:bg-surface-container transition-colors rounded-xl p-6 flex flex-col items-center justify-center text-center relative group"
      :class="reading ? 'cursor-wait' : 'cursor-pointer'"
    >
      <input type="file" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" :disabled="reading" @change="readPhoto" />
      <div class="w-14 h-14 rounded-full bg-surface-container-highest flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
        <span class="icon text-[28px] text-on-tertiary-container" :class="reading && 'animate-spin'">{{ reading ? 'sync' : 'document_scanner' }}</span>
      </div>
      <h4 class="font-display text-headline-sm font-semibold text-on-surface">
        {{ reading ? 'Reading your bill… (up to a minute)' : 'Read from bill photo' }}
      </h4>
      <p class="text-body-sm text-on-surface-variant max-w-md mt-1">Finds the 12-month bill history table. Always check the numbers it reads.</p>
      <div class="flex items-center gap-2 mt-4 flex-wrap justify-center">
        <span v-for="t in ['Reads 12 months', 'Photo or screenshot', 'Only units are kept']" :key="t"
          class="inline-flex items-center gap-1 text-label-sm bg-surface-container-lowest px-2 py-1 rounded-md text-on-surface-variant shadow-sm">
          <span class="icon text-[14px] text-secondary">check_circle</span>{{ t }}
        </span>
      </div>
      <div v-if="reading" class="w-full mt-4 h-1.5 rounded-full bg-surface-container-highest overflow-hidden">
        <div class="h-full w-1/3 bg-secondary rounded-full animate-pulse"></div>
      </div>
    </label>
    <p v-if="ocrMsg" :class="ocrOk ? 'note-jade' : 'note-amber'" class="-mt-2">
      <span class="icon text-[18px] shrink-0">{{ ocrOk ? 'fact_check' : 'warning' }}</span>{{ ocrMsg }}
    </p>

    <!-- 12 months -->
    <div>
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <span class="font-display text-headline-sm font-bold text-on-surface">12-month units</span>
        <div class="flex items-center gap-4 text-label-sm text-on-surface-variant">
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-tertiary-fixed-dim"></span>Summer peak</span>
          <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-surface-container-highest"></span>Rest of year</span>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        <div
          v-for="(name, i) in MONTHS" :key="name"
          class="p-2 rounded-lg shadow-sm flex flex-col justify-between"
          :class="isPeak(i) ? 'bg-surface-container-highest ring-2 ring-tertiary-container/20' : 'bg-surface'"
        >
          <div class="flex items-center justify-between mb-1">
            <label :for="`m${index}-${i}`" class="text-label-md font-semibold text-on-surface flex items-center gap-1">
              {{ name }}<span v-if="isPeak(i)" class="icon text-[14px] text-error">local_fire_department</span>
            </label>
            <span v-if="isPeak(i)" class="text-label-sm bg-tertiary-fixed text-on-tertiary-fixed px-1 rounded font-semibold">Peak</span>
            <span v-else class="text-label-sm" :class="SEASON[i] === 'Pre-peak' ? 'text-on-tertiary-container font-semibold' : 'text-on-surface-variant'">{{ SEASON[i] }}</span>
          </div>
          <div class="relative">
            <input
              :id="`m${index}-${i}`" v-model.number="meter.months[i + 1]" type="number" min="0"
              class="w-full bg-surface-container-lowest text-on-surface font-display text-[20px] font-bold py-1 pl-2 pr-12 rounded focus:outline-none focus:bg-surface-container-high transition-colors"
            />
            <span class="unit">units</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Year shape -->
    <div class="panel">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <span class="text-label-md font-semibold text-on-surface">Shape of your year</span>
        <span v-if="peakRatio" class="text-label-sm text-secondary font-semibold">Summer peak: {{ peakRatio }}× the lowest winter month</span>
      </div>
      <div class="w-full h-20 flex items-end gap-1.5 pt-2">
        <div
          v-for="(u, i) in values" :key="i" :title="`${MONTHS[i]}: ${u || 'blank'}`"
          class="flex-1 rounded-t transition-all"
          :class="isPeak(i) ? 'bg-tertiary-fixed-dim' : 'bg-surface-container-highest'"
          :style="{ height: u ? Math.max(4, (u / maxVal) * 100) + '%' : '2px' }"
        ></div>
      </div>
      <div class="flex gap-1.5 text-[11px] text-on-surface-variant mt-1.5">
        <span v-for="m in MONTHS" :key="m" class="flex-1 text-center">{{ m[0] }}</span>
      </div>
    </div>
  </div>
</template>
