import { defineStore } from 'pinia'

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const emptyMeter = () => ({ months: Object.fromEntries(MONTHS.map((_, i) => [i + 1, null])) })

export const usePlanStore = defineStore('plan', {
  state: () => ({
    meters: [emptyMeter()],
    house: { house_size_marla: null, people: null, sanctioned_load_kw: null },
    appliances: {}, // counts of known appliances by key, filled from appliancesText by the parser
    applianceItems: [], // every appliance line, with optional watts / hours (also unknown appliances)
    appliancesText: '',
    roof: { type: 'concrete', area_sqft: null },
    hasSolar: false,
    consent: false,
    result: null,
    submissionId: null,
  }),
  getters: {
    monthsEntered: (s) => s.meters.reduce((n, m) => n + Object.values(m.months).filter((u) => u > 0).length, 0),
    acTotal: (s) =>
      Object.entries(s.appliances).filter(([k]) => k.startsWith('ac_')).reduce((n, [, v]) => n + (v || 0), 0),
  },
  actions: {
    addMeter() { this.meters.push(emptyMeter()) },
    removeMeter(i) { this.meters.splice(i, 1) },
    payload() {
      return {
        meters: this.meters.map((m) => ({
          months: Object.fromEntries(Object.entries(m.months).filter(([, u]) => u !== null && u !== '')),
        })),
        house: {
          ...this.house, ac_total: this.acTotal, appliances: this.appliances,
          appliance_items: this.applianceItems.map(({ key, label, count, watts, hours, ton }) => ({ key, label, count, watts, hours, ton })),
        },
        roof: this.roof,
        hasSolar: this.hasSolar,
        consent: this.consent,
      }
    },
  },
})
