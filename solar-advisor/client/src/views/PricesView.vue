<script setup>
import { onMounted, ref } from 'vue'
import api, { errorText } from '../api'
import { MONTHS } from '../store'
import LedgerTabs from '../components/LedgerTabs.vue'

const token = ref(localStorage.getItem('adminToken'))
const password = ref('')
const config = ref(null)
const updatedAt = ref('')
const msg = ref('')
const toast = ref('')
let toastTimer

const labels = {
  panel_per_watt: 'Panel price',
  panel_watt: 'Panel size',
  inverter_hybrid_per_kw: 'Hybrid inverter',
  inverter_ongrid_per_kw: 'On-grid inverter',
  min_inverter_kw: 'Smallest inverter',
  battery_lithium_per_kwh: 'Lithium battery',
  structure_normal_per_kw: 'Normal structure',
  structure_elevated_per_kw: 'Elevated structure',
  installation_per_kw: 'Installation',
  wiring_protection_per_kw: 'Wiring and protection',
  fixed_costs: 'Fixed costs per system',
}
// Unit shown inside each price box, worked out from the key name
const unitFor = (key) =>
  key.endsWith('_per_watt') ? 'Rs / W' : key.endsWith('_per_kwh') ? 'Rs / kWh' : key.endsWith('_per_kw') ? 'Rs / kW'
    : key.endsWith('_watt') ? 'W' : key.endsWith('_kw') ? 'kW' : 'Rs'

function showToast(text) {
  toast.value = text
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2800)
}

async function load() {
  const { data } = await api.get('/settings')
  config.value = data.config
  updatedAt.value = new Date(data.updatedAt).toLocaleString()
  if (token.value) {
    try {
      await api.get('/admin/check')
    } catch {
      logout() // saved login has expired
    }
  }
}

async function login() {
  msg.value = ''
  try {
    const { data } = await api.post('/admin/login', { password: password.value })
    localStorage.setItem('adminToken', data.token)
    token.value = data.token
    password.value = ''
    await load()
  } catch (e) {
    msg.value = errorText(e)
  }
}

function logout() {
  localStorage.removeItem('adminToken')
  token.value = null
}

async function save() {
  msg.value = ''
  try {
    const { data } = await api.put('/settings', { config: config.value })
    config.value = data.config
    updatedAt.value = new Date(data.updatedAt).toLocaleString()
    showToast('Saved. New plans use these prices.')
  } catch (e) {
    msg.value = errorText(e)
  }
}

async function resetDefaults() {
  if (!confirm('Replace all prices with the defaults from config/pakistan.json?')) return
  const { data } = await api.post('/admin/reset-settings')
  config.value = data.config
  showToast('Defaults restored.')
}

onMounted(load)
</script>

<template>
  <LedgerTabs
    crumb="Tariff & Prices"
    title="Prices and tariff"
    text="Panel and inverter prices change often. Every new plan uses the saved values below. Only the admin can change them."
  />

  <div class="flex flex-col gap-6">
    <!-- Admin bar: log in, or who is editing -->
    <div class="p-4 rounded-xl bg-surface-container-highest flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-tertiary text-on-tertiary flex items-center justify-center shrink-0"><span class="icon">admin_panel_settings</span></div>
        <div>
          <div class="flex flex-wrap items-center gap-1.5">
            <span class="card-title">{{ token ? 'Editing prices' : 'Saved prices (read only)' }}</span>
            <span :class="token ? 'chip-jade' : 'chip-plain'">{{ token ? 'Admin' : 'View only' }}</span>
          </div>
          <p class="text-body-sm text-on-surface-variant">Last saved: {{ updatedAt || '…' }}. Changes apply to every new plan straight away.</p>
        </div>
      </div>
      <div v-if="token" class="flex items-center gap-2 self-end md:self-auto shrink-0">
        <button class="btn-white text-error hover:bg-error-container hover:text-on-error-container" @click="logout">Log out</button>
      </div>
      <form v-else class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full md:w-auto" @submit.prevent="login">
        <label class="sr-only" for="pw">Admin password</label>
        <input id="pw" v-model="password" type="password" class="input bg-surface-container-lowest sm:w-56" placeholder="Admin password" />
        <button class="btn" type="submit"><span class="icon text-[18px]">lock_open</span>Log in</button>
      </form>
    </div>
    <p v-if="msg" class="note-red"><span class="icon text-[18px]">error</span>{{ msg }}</p>

    <template v-if="config">
      <fieldset :disabled="!token" class="grid grid-cols-1 lg:grid-cols-2 gap-6 min-w-0">
        <!-- Equipment -->
        <div class="card flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="card-title">Equipment prices</h2>
              <p class="text-body-sm text-on-surface-variant">Market prices in Lahore. Check them often.</p>
            </div>
            <span class="icon text-on-surface-variant">solar_power</span>
          </div>
          <div v-for="(item, key) in config.prices" :key="key">
            <div class="flex items-center justify-between gap-2 mb-1">
              <label class="text-label-md font-semibold" :for="'p-' + key">{{ labels[key] || key }}</label>
              <span v-if="item.confidence === 'low'" class="chip-amber">Estimate: please check</span>
            </div>
            <div class="relative">
              <input :id="'p-' + key" v-model.number="item.value" type="number" class="input pr-24 font-display text-[16px] font-semibold disabled:opacity-80" />
              <span class="unit">{{ unitFor(key) }}</span>
            </div>
            <p class="text-body-sm text-on-surface-variant mt-1">{{ item.source }}</p>
          </div>
        </div>

        <!-- Tariff -->
        <div class="card flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="card-title">Tariff (Rs per unit)</h2>
              <p class="text-body-sm text-on-surface-variant">LESCO residential rates, taxes and the buyback rate.</p>
            </div>
            <span class="icon text-on-surface-variant">bolt</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <h3 class="text-label-md font-semibold mb-2">Protected (all months ≤ {{ config.tariff_residential.protected_limit_units }} units)</h3>
              <div v-for="s in config.tariff_residential.protected_slabs" :key="'p' + s.up_to" class="relative mb-2">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-label-sm text-on-surface-variant pointer-events-none">up to {{ s.up_to }}</span>
                <input v-model.number="s.rate" type="number" step="0.01" class="input pl-20 pr-16 text-right font-semibold" />
                <span class="unit">Rs</span>
              </div>
            </div>
            <div>
              <h3 class="text-label-md font-semibold mb-2">Unprotected</h3>
              <div v-for="s in config.tariff_residential.unprotected_slabs" :key="'u' + s.up_to" class="relative mb-2">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-label-sm text-on-surface-variant pointer-events-none">{{ s.up_to ? 'up to ' + s.up_to : 'above 700' }}</span>
                <input v-model.number="s.rate" type="number" step="0.01" class="input pl-20 pr-16 text-right font-semibold" />
                <span class="unit">Rs</span>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label class="label" for="t-peak">Peak rate (ToU)</label><div class="relative"><input id="t-peak" v-model.number="config.tariff_residential.tou.peak_rate" type="number" step="0.01" class="input pr-20" /><span class="unit">Rs / unit</span></div></div>
            <div><label class="label" for="t-off">Off-peak rate (ToU)</label><div class="relative"><input id="t-off" v-model.number="config.tariff_residential.tou.offpeak_rate" type="number" step="0.01" class="input pr-20" /><span class="unit">Rs / unit</span></div></div>
            <div><label class="label" for="t-tax">Taxes</label><div class="relative"><input id="t-tax" v-model.number="config.tariff_residential.calibration.tax_percent" type="number" step="0.1" class="input pr-10" /><span class="unit">%</span></div></div>
            <div><label class="label text-on-secondary-container" for="t-buy">Buyback rate (per unit sold)</label><div class="relative"><input id="t-buy" v-model.number="config.net_billing.buyback_rate_per_unit" type="number" step="0.01" class="input pr-20 bg-secondary-container/20" /><span class="unit text-on-secondary-container">Rs / unit</span></div></div>
            <div><label class="label" for="t-mul">Unprotected adjustment</label><div class="relative"><input id="t-mul" v-model.number="config.tariff_residential.calibration.unprotected_multiplier" type="number" step="0.01" class="input pr-10" /><span class="unit">×</span></div></div>
            <div><label class="label" for="t-extra">Protected extra</label><div class="relative"><input id="t-extra" v-model.number="config.tariff_residential.calibration.protected_extra_per_month" type="number" class="input pr-20" /><span class="unit">Rs / month</span></div></div>
          </div>
        </div>

        <!-- Solar yield -->
        <div class="card lg:col-span-2">
          <div class="flex items-center justify-between mb-1">
            <h2 class="card-title">Solar output: units per kW per month</h2>
            <span class="icon text-on-tertiary-container">wb_sunny</span>
          </div>
          <p class="text-body-sm text-on-surface-variant mb-4">{{ config.solar.yield_source }}</p>
          <div class="grid grid-cols-3 sm:grid-cols-6 lg:grid-cols-12 gap-2">
            <div v-for="(name, i) in MONTHS" :key="name" class="p-2 rounded-lg bg-surface shadow-sm">
              <label class="text-label-md font-semibold block mb-1" :for="'y' + i">{{ name }}</label>
              <input :id="'y' + i" v-model.number="config.solar.yield_per_kw_month[i + 1]" type="number" class="w-full bg-surface-container-lowest font-display text-[16px] font-bold py-1 px-2 rounded focus:outline-none focus:bg-surface-container-high" />
            </div>
          </div>
        </div>
      </fieldset>

      <!-- Actions -->
      <div v-if="token" class="card flex flex-col sm:flex-row items-center justify-between gap-4">
        <div class="flex items-center gap-1.5 text-on-surface-variant text-body-sm">
          <span class="icon text-[18px]">history</span>Saving changes the prices used for every new plan. Plans already made stay the same.
        </div>
        <div class="flex items-center gap-3 w-full sm:w-auto">
          <button class="btn-light w-1/2 sm:w-auto px-6" @click="resetDefaults">Reset to defaults</button>
          <button class="btn w-1/2 sm:w-auto px-10" @click="save"><span class="icon text-[18px]">save</span>Save</button>
        </div>
      </div>
    </template>
  </div>

  <!-- Toast -->
  <Transition enter-from-class="translate-y-24 opacity-0" leave-to-class="translate-y-24 opacity-0">
    <div v-if="toast" class="fixed bottom-6 right-6 z-50 transition-all duration-300">
      <div class="p-4 rounded-xl bg-primary text-on-primary shadow-xl flex items-center gap-2">
        <span class="icon text-secondary-fixed">verified</span><span class="text-label-md font-semibold">{{ toast }}</span>
      </div>
    </div>
  </Transition>
</template>
