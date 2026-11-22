import { Router } from 'express'
import axios from 'axios'
import multer from 'multer'
import jwt from 'jsonwebtoken'
import { Settings, Submission, Lead } from '../models/index.js'

const router = Router()
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (req, file, cb) => cb(null, file.mimetype.startsWith('image/')),
})
const ml = () => axios.create({ baseURL: process.env.ML_SERVICE_URL, timeout: 60000 })

const getConfig = async () => (await Settings.findOne({ key: 'pricing' })).config

function requireAdmin(req, res, next) {
  const token = (req.headers.authorization || '').replace('Bearer ', '')
  try {
    jwt.verify(token, process.env.JWT_SECRET)
    next()
  } catch {
    res.status(401).json({ error: 'Login required' })
  }
}

// Pass ML service errors through with a readable message
function mlError(res, e) {
  const detail = e.response?.data?.detail
  // FastAPI validation errors come as a list: [{loc, msg}, ...]
  let text
  if (Array.isArray(detail)) text = detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
  else if (detail) text = detail
  else if (e.response) text = `ML service error ${e.response.status}`
  else if (e.code === 'ECONNABORTED' || e.code === 'ETIMEDOUT') text = 'The ML service took too long to answer. Please try again.'
  else text = 'The ML service is not running or is still starting. Wait a few seconds and try again.'
  res.status(e.response?.status || 502).json({ error: text })
}

router.get('/health', (req, res) => res.json({ ok: true }))

// ---------- Prices and tariff ----------
router.get('/settings', async (req, res) => {
  const s = await Settings.findOne({ key: 'pricing' })
  res.json({ config: s.config, updatedAt: s.updatedAt })
})

router.post('/admin/login', (req, res) => {
  if (req.body.password !== process.env.ADMIN_PASSWORD) return res.status(401).json({ error: 'Wrong password' })
  res.json({ token: jwt.sign({ role: 'admin' }, process.env.JWT_SECRET, { expiresIn: '8h' }) })
})

// Lets the Prices screen check that a saved login is still valid
router.get('/admin/check', requireAdmin, (req, res) => res.json({ ok: true }))

router.put('/settings', requireAdmin, async (req, res) => {
  const config = req.body.config
  if (!config?.prices || !config?.tariff_residential || !config?.solar) {
    return res.status(400).json({ error: 'config must include prices, tariff_residential and solar' })
  }
  config.last_updated = new Date().toISOString().slice(0, 10)
  const s = await Settings.findOneAndUpdate({ key: 'pricing' }, { config, updatedBy: 'admin' }, { new: true })
  res.json({ config: s.config, updatedAt: s.updatedAt })
})

router.post('/admin/reset-settings', requireAdmin, async (req, res) => {
  const { data } = await ml().get('/config/default')
  const s = await Settings.findOneAndUpdate({ key: 'pricing' }, { config: data }, { new: true })
  res.json({ config: s.config, updatedAt: s.updatedAt })
})

// ---------- Plan ----------
router.get('/options', async (req, res) => {
  try {
    res.json((await ml().get('/options')).data)
  } catch (e) {
    mlError(res, e)
  }
})

router.post('/plan', async (req, res) => {
  const { meters = [], house = {}, roof = {}, hasSolar = false, consent = false } = req.body
  try {
    const config = await getConfig()
    const { data } = await ml().post('/plan', { meters, house, roof, config })
    const rec = data.plan.recommended
    const submission = await Submission.create({
      meters, house, roof, hasSolar, consent,
      summary: { yearlyUnits: data.plan.yearly_units, kw: rec.kw, panels: rec.panels, cost: rec.cost,
                 paybackYears: rec.payback_years, basis: data.basis },
    })

    // With consent, a complete bill from a home without solar becomes training data
    let training = null
    if (consent && !hasSolar && meters.length) {
      try {
        training = (await ml().post('/bills/add', { meters, house, submission_id: String(submission._id) })).data
        if (training.added) await Submission.updateOne({ _id: submission._id }, { addedToTraining: true })
      } catch (e) {
        training = { added: false, reason: e.response?.data?.detail || 'could not add' }
      }
    }
    res.json({ ...data, submissionId: submission._id, training })
  } catch (e) {
    mlError(res, e)
  }
})

// ---------- Bill OCR ----------
router.post('/ocr', upload.single('bill'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'Please upload a photo of the bill (jpg or png)' })
  try {
    const form = new FormData()
    form.append('file', new Blob([req.file.buffer], { type: req.file.mimetype }), req.file.originalname)
    const { data } = await ml().post('/ocr', form, { timeout: 120000 }) // reading a photo can take up to a minute
    res.json(data)
  } catch (e) {
    mlError(res, e)
  }
})

// ---------- Leads ----------
router.post('/leads', async (req, res) => {
  const { name, phone, city, note, submissionId } = req.body
  if (!name || !phone) return res.status(400).json({ error: 'Name and phone are required' })
  const lead = await Lead.create({ name, phone, city, note, submission: submissionId })
  res.status(201).json({ id: lead._id })
})

router.get('/admin/leads', requireAdmin, async (req, res) => {
  res.json(await Lead.find().sort({ createdAt: -1 }).populate('submission', 'summary').limit(200))
})

// ---------- Model ----------
router.get('/model', async (req, res) => {
  try {
    res.json((await ml().get('/model')).data)
  } catch (e) {
    mlError(res, e)
  }
})

router.post('/admin/retrain', requireAdmin, async (req, res) => {
  try {
    res.json((await ml().post('/retrain')).data)
  } catch (e) {
    mlError(res, e)
  }
})

export default router
