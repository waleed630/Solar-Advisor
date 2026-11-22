// Turns free text like "2 AC 1.5 ton inverter, 5 pankhe, fridge, motor" into appliance counts
// that the ML service understands ({ ac_inverter: 2, fans: 5, fridge: 1, motor: 1 }).
// Understands English and common Roman Urdu spellings.

// Checked in order: the first rule whose words appear in an item wins (more specific rules first)
const RULES = [
  { key: 'ac', words: ['ac', 'a.c', 'air conditioner', 'aircon', 'split'] }, // type and ton decided below
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
  { key: 'iron', words: ['iron', 'istri', 'istari'] },
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

function count(text) {
  // Remove sizes so "1.5 ton" or "100 watt" is not read as a count
  const clean = text.replace(/\d+(\.\d+)?\s*(ton|tons|tan|kw|watt|watts|w|hp|litre|liter|l)\b/g, ' ')
  const digits = clean.match(/\d+/)
  if (digits) return Math.max(1, parseInt(digits[0], 10))
  for (const [word, n] of Object.entries(NUMBER_WORDS)) if (hasWord(clean, word)) return n
  return 1
}

function acKey(text) {
  const inverter = !NON_INVERTER.test(text) && (hasWord(text, 'inverter') || hasWord(text, 'dc'))
  const oneTon = /\b1(\.0)?\s*(ton|tan)\b/.test(text) || hasWord(text, 'one ton') || hasWord(text, 'aik ton')
  if (oneTon) return inverter ? 'ac_1ton_inverter' : 'ac_1ton_noninverter'
  return inverter ? 'ac_inverter' : 'ac_noninverter' // 1.5 ton, 2 ton or not said: the 1.5 ton figures
}

export function parseAppliances(text, labels = {}) {
  const counts = {}
  const recognised = []
  const unknown = []
  const items = (text || '').toLowerCase().split(/[,\n;]+|\band\b|\baur\b/).map((s) => s.trim()).filter(Boolean)
  for (const item of items) {
    const rule = RULES.find((r) => r.words.some((w) => hasWord(item, w)))
    if (!rule) {
      unknown.push(item)
      continue
    }
    let key = rule.key
    if (key === 'ac') key = acKey(item)
    if (key === 'fridge' && hasWord(item, 'inverter') && !NON_INVERTER.test(item)) key = 'fridge_inverter'
    // In Pakistan a bare "LED" usually means an LED TV; "LED light / bulb" is a light
    if (key === 'lights' && hasWord(item, 'led') && !LIGHT_WORDS.some((w) => hasWord(item, w))) key = 'led_tv'
    const n = count(item)
    counts[key] = (counts[key] || 0) + n
    recognised.push({ text: item, key, count: n, label: labels[key] || key })
  }
  return { counts, recognised, unknown }
}
