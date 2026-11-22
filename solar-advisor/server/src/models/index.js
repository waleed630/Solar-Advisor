import mongoose from 'mongoose'

// Prices, tariff and solar yield. One document, edited from the Prices screen.
const settingsSchema = new mongoose.Schema(
  {
    key: { type: String, unique: true, default: 'pricing' },
    config: { type: mongoose.Schema.Types.Mixed, required: true },
    updatedBy: String,
  },
  { timestamps: true, minimize: false }
)

// Every plan a user makes. Bills are kept for training only when consent is true.
const submissionSchema = new mongoose.Schema(
  {
    meters: [{ months: { type: Map, of: Number } }],
    house: mongoose.Schema.Types.Mixed,
    roof: mongoose.Schema.Types.Mixed,
    hasSolar: Boolean,
    consent: { type: Boolean, default: false },
    addedToTraining: { type: Boolean, default: false },
    summary: mongoose.Schema.Types.Mixed,
  },
  { timestamps: true, minimize: false }
)

// "Get quotes from installers"
const leadSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    phone: { type: String, required: true },
    city: String,
    note: String,
    submission: { type: mongoose.Schema.Types.ObjectId, ref: 'Submission' },
    status: { type: String, enum: ['new', 'sent', 'closed'], default: 'new' },
  },
  { timestamps: true }
)

export const Settings = mongoose.model('Settings', settingsSchema)
export const Submission = mongoose.model('Submission', submissionSchema)
export const Lead = mongoose.model('Lead', leadSchema)
