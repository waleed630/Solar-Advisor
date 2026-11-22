import 'dotenv/config'
import { readFile } from 'node:fs/promises'
import express from 'express'
import cors from 'cors'
import mongoose from 'mongoose'
import api from './routes/api.js'
import { Settings } from './models/index.js'

const app = express()
app.use(cors({ origin: ['http://localhost:5173'] }))
app.use(express.json({ limit: '1mb' }))
app.use('/api', api)

// Copy every key of `defaults` that `target` does not have yet; existing values (admin edits) stay
function addMissing(target, defaults) {
  let added = 0
  for (const [k, v] of Object.entries(defaults)) {
    if (!(k in target)) {
      target[k] = v
      added++
    } else if (v && typeof v === 'object' && !Array.isArray(v) && target[k] && typeof target[k] === 'object') {
      added += addMissing(target[k], v)
    }
  }
  return added
}

// First start: copy default prices and tariff from config/pakistan.json into the database.
// Later starts: add any new settings from the file without touching values an admin has edited.
async function seedSettings() {
  const file = new URL('../../config/pakistan.json', import.meta.url)
  const defaults = JSON.parse(await readFile(file, 'utf8'))
  const existing = await Settings.findOne({ key: 'pricing' })
  if (!existing) {
    await Settings.create({ key: 'pricing', config: defaults })
    console.log('Seeded prices and tariff from config/pakistan.json')
    return
  }
  const config = existing.config
  const added = addMissing(config, defaults)
  if (added) {
    await Settings.updateOne({ key: 'pricing' }, { config })
    console.log(`Added ${added} new settings from config/pakistan.json`)
  }
}

await mongoose.connect(process.env.MONGO_URI)
console.log('MongoDB connected')
await seedSettings()

const port = process.env.PORT || 5000
app.listen(port, () => console.log(`Server on http://localhost:${port}`))
