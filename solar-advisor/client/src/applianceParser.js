// Turns free text like "2 AC 1.5 ton inverter, 5 pankhe, fridge, air purifier 50W 8 hours" into appliance
// lines the ML service understands. Understands English and common Roman Urdu spellings.
//
// Every line is kept:
//  - an appliance we know (fan, fridge, AC...) gets its key, so typical watts and hours are used;
//  - any other appliance is kept as "custom" with the name the user wrote.
// The power (W, kW, HP, amps, AC tons) and hours per day are optional: when given, they replace the
// typical figures.

// Checked in order: the first rule whose words appear in an item wins (more specific rules first)
const RULES = [
  { key: 'air_purifier', words: ['air purifier', 'air filter'] },
  { key: 'ac', words: ['ac', 'a.c', 'air conditioner', 'aircon', 'split'] }, // type and ton decided below
  { key: 'exhaust_fan', words: ['exhaust', 'exhaust fan'] },
  { key: 'fans_inverter', words: ['dc fan', 'inverter fan', 'dc pankha', 'dc pankhe', 'dc phanka', 'dc phanke'] },
  { key: 'fans', words: ['fan', 'pankha', 'pankhe', 'pankhay', 'phanka', 'phanke', 'phankay', 'ceiling'] },
  { key: 'deep_freezer', words: ['freezer', 'deep freezer'] },
  { key: 'fridge', words: ['fridge', 'frige', 'frij', 'refrigerator', 'refrigrator'] }, // inverter decided below
  { key: 'water_dispenser', words: ['dispenser', 'dispancer', 'dispensor'] },
  { key: 'washing_machine', words: ['washing', 'wasing', 'washer', 'kapre dhone'] },
  { key: 'microwave', words: ['microwave', 'oven'] },
  { key: 'electric_stove', words: ['stove', 'chulha', 'hot plate', 'hotplate', 'cooktop'] },
  { key: 'geyser', words: ['geyser', 'geaser', 'geser', 'gyser', 'gizer', 'water heater'] },
  { key: 'room_heater', words: ['heater'] },
  { key: 'motor', words: ['motor', 'motar', 'pump', 'pani wali'] },
  { key: 'hair_dryer', words: ['hair dryer', 'hair drier', 'dryer', 'straightener'] },
  { key: 'iron', words: ['iron', 'istri', 'istari'] },
  { key: 'kettle', words: ['kettle', 'ketli'] },
  { key: 'toaster', words: ['toaster', 'sandwich maker'] },
  { key: 'blender', words: ['blender', 'juicer', 'grinder', 'chopper', 'mixer'] },
  { key: 'vacuum', words: ['vacuum', 'vacuum cleaner'] },
  { key: 'laptop', words: ['laptop'] },
  { key: 'computer', words: ['computer', 'pc', 'desktop'] },
  { key: 'router', words: ['router', 'wifi', 'wi-fi', 'modem'] },
  { key: 'treadmill', words: ['treadmill'] },
  { key: 'led_tv', words: ['tv', 't.v', 'television', 'led tv', 'lcd'] },
  { key: 'air_cooler', words: ['cooler', 'kooler'] },
  { key: 'ups', words: ['ups', 'u.p.s'] },
  { key: 'lights', words: ['bulb', 'light', 'tube', 'tubelight', 'led', 'saver', 'fanoos', 'chandelier'] },
]

// "two fans" / "do pankhe": small number words in English and Roman Urdu
const NUMBER_WORDS = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  aik: 1, ek: 1, do: 2, teen: 3, char: 4, chaar: 4, panch: 5, paanch: 5, chay: 6, che: 6, saat: 7, aath: 8, nau: 9, das: 10,
}

// Whole word, plural allowed ("fan" matches "fans", "box" would match "boxes")
const hasWord = (text, word) => new RegExp(`(^|[^a-z])${word.replace('.', '\\.')}(s|es)?($|[^a-z])`).test(text)
const NON_INVERTER = /non[\s-]?inverter/
const LIGHT_WORDS = ['bulb', 'light', 'tube', 'tubelight', 'saver', 'fanoos', 'chandelier']

// Sizes and hours the user may write next to an appliance ("50w", "1.5 kw", "1 hp", "5 amp", "8 hours")
const NUM = '(\\d+(?:\\.\\d+)?)'
const SPECS = {
  kw: new RegExp(`${NUM}\\s*(?:kw|kilowatts?)\\b`),
  w: new RegExp(`${NUM}\\s*(?:w|watts?|wat)\\b`),
  hp: new RegExp(`${NUM}\\s*(?:hp|horse\\s?power)\\b`),
  amp: new RegExp(`${NUM}\\s*(?:amps?\\b|amperes?\\b|a(?![.\\w]))`), // "5 a" but not "1 a.c"
  ton: new RegExp(`${NUM}\\s*(?:tons?|tan)\\b`),
  hours: new RegExp(`${NUM}\\s*(?:h|hrs?|hours?|ghante|ghanta|ghantay|ghantey)\\b`),
}
const VOLTS = 230 // Pakistan mains, for amps -> watts
const ANY_SPEC = new RegExp(Object.values(SPECS).map((r) => r.source).join('|'), 'g')
const FILLER = /\b(per day|a day|daily|roz|rozana|each|of|x|nos?|pcs?|pieces?)\b|[×*()]/g

function specs(text) {
  const num = (re) => { const m = text.match(re); return m ? parseFloat(m[1]) : null }
  let watts = null
  if (num(SPECS.kw) != null) watts = num(SPECS.kw) * 1000
  else if (num(SPECS.w) != null) watts = num(SPECS.w)
  else if (num(SPECS.hp) != null) watts = num(SPECS.hp) * 746
  else if (num(SPECS.amp) != null) watts = num(SPECS.amp) * VOLTS
  const hours = num(SPECS.hours)
  return {
    watts: watts > 0 ? Math.round(watts) : null,
    hours: hours > 0 && hours <= 24 ? hours : null,
    ton: num(SPECS.ton),
  }
}

function count(text) {
  // Remove sizes and hours so "1.5 ton" or "8 hours" is not read as a count
  const clean = text.replace(ANY_SPEC, ' ')
  const digits = clean.match(/\d+/)
  if (digits) return Math.max(1, parseInt(digits[0], 10))
  for (const [word, n] of Object.entries(NUMBER_WORDS)) if (hasWord(clean, word)) return n
  return 1
}

// The name of an appliance we don't know, from what the user wrote ("2 air fryers 1500w" -> "Air fryers")
function customName(text) {
  let name = text.replace(ANY_SPEC, ' ').replace(FILLER, ' ').replace(/\d+(\.\d+)?/g, ' ')
  for (const word of Object.keys(NUMBER_WORDS)) name = name.replace(new RegExp(`(^|\\s)${word}(?=\\s|$)`, 'g'), ' ')
  name = name.replace(/\s+/g, ' ').trim()
  return name ? name[0].toUpperCase() + name.slice(1) : ''
}

function acKey(text) {
  const inverter = !NON_INVERTER.test(text) && (hasWord(text, 'inverter') || hasWord(text, 'dc'))
  const oneTon = /\b1(\.0)?\s*(ton|tan)\b/.test(text) || hasWord(text, 'one ton') || hasWord(text, 'aik ton')
  if (oneTon) return inverter ? 'ac_1ton_inverter' : 'ac_1ton_noninverter'
  return inverter ? 'ac_inverter' : 'ac_noninverter' // 1.5 ton, 2 ton or not said: the 1.5 ton figures, scaled by tons
}

// Returns
//   items:   every appliance line { key, label, count, watts, hours, ton, custom }
//   counts:  { key: count } for the appliances we know (training data and the AC count use these)
//   unknown: lines with no appliance name at all (e.g. just "5"), left out
export function parseAppliances(text, labels = {}) {
  const counts = {}
  const items = []
  const unknown = []
  const lines = (text || '').toLowerCase().split(/[,\n;]+|\band\b|\baur\b/).map((s) => s.trim()).filter(Boolean)
  for (const line of lines) {
    const rule = RULES.find((r) => r.words.some((w) => hasWord(line, w)))
    const n = count(line)
    const { watts, hours, ton } = specs(line)
    if (!rule) {
      const name = customName(line)
      if (!name) {
        unknown.push(line)
        continue
      }
      items.push({ key: 'custom', label: name, count: n, watts, hours, ton: null, custom: true })
      continue
    }
    let key = rule.key
    if (key === 'ac') key = acKey(line)
    if (key === 'fridge' && hasWord(line, 'inverter') && !NON_INVERTER.test(line)) key = 'fridge_inverter'
    // In Pakistan a bare "LED" usually means an LED TV; "LED light / bulb" is a light
    if (key === 'lights' && hasWord(line, 'led') && !LIGHT_WORDS.some((w) => hasWord(line, w))) key = 'led_tv'
    counts[key] = (counts[key] || 0) + n
    items.push({ key, label: labels[key] || key, count: n, watts, hours, ton: key.startsWith('ac_') ? ton : null, custom: false })
  }
  return { items, counts, unknown, recognised: items }
}
