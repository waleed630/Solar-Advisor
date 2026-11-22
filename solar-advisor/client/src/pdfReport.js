// Builds a PDF of the solar plan (everything on the result screen) and shares it.
import { jsPDF } from 'jspdf'
import { autoTable } from 'jspdf-autotable'
import { MONTHS } from './store'

const GREEN = [0, 108, 74] // theme jade
const NAVY = [11, 28, 48] // theme navy
const GREY = [69, 70, 77]
const rs = (n) => (n == null ? '-' : 'Rs ' + Math.round(n).toLocaleString('en-US'))
const num = (n) => (n == null ? '-' : Math.round(n).toLocaleString('en-US'))
const STATUS = { protected: 'Protected', unprotected: 'Unprotected', tou: 'Time of use' }

export function summaryText(result) {
  const r = result.plan.recommended
  return `My solar plan from SolarAdvisor: ${r.kw} kW (${r.panels} panels), cost about ${rs(r.cost)}, ` +
    `saving about ${rs(r.monthly_saving)} a month, payback ${r.payback_years} years.`
}

// charts: { usage, bill } as JPEG data URLs from the Chart.js canvases (optional)
export function buildPdf(result, charts = {}) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const W = doc.internal.pageSize.getWidth()
  const M = 14 // margin
  const p = result.plan
  const rec = p.recommended
  const batt = p.with_battery
  let y = 18

  const heading = (text) => {
    if (y > 250) { doc.addPage(); y = 18 }
    doc.setFont('helvetica', 'bold').setFontSize(13).setTextColor(...NAVY).text(text, M, y)
    y += 3
  }
  const table = (head, body, opts = {}) => {
    autoTable(doc, {
      startY: y, head: [head], body, margin: { left: M, right: M },
      styles: { fontSize: 9, cellPadding: 1.8 }, headStyles: { fillColor: GREEN }, ...opts,
    })
    y = doc.lastAutoTable.finalY + 8
  }
  const image = (dataUrl, h) => {
    if (!dataUrl) return
    if (y + h > 280) { doc.addPage(); y = 18 }
    doc.addImage(dataUrl, 'JPEG', M, y, W - 2 * M, h)
    y += h + 6
  }

  // Title
  doc.setFont('helvetica', 'bold').setFontSize(20).setTextColor(...GREEN).text('SolarAdvisor', M, y)
  doc.setFont('helvetica', 'normal').setFontSize(10).setTextColor(...GREY)
    .text(`Your solar plan  |  ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}`, M, y + 6)
  y += 16

  heading('Summary')
  table(['', ''], [
    ['Units used in a year', `${num(p.yearly_units)} units`],
    ['System size', `${rec.kw} kW (${rec.panels} panels)`],
    ['Estimated cost', rs(rec.cost)],
    ['Saving per month', rs(rec.monthly_saving)],
    ['Payback', `${rec.payback_years} years`],
    ['Mounting structure', p.structure.name],
  ], { showHead: false, columnStyles: { 0: { fontStyle: 'bold', cellWidth: 60 } } })

  heading('Units used and what solar makes')
  image(charts.usage, 62)
  table(['Season', 'Average units per month'], ['summer', 'mild', 'winter'].map((s) => [s[0].toUpperCase() + s.slice(1), num(result.seasons[s].avg_per_month)]))

  heading('Month by month')
  table(['Month', 'Units used', 'Solar makes', 'Bill now', 'Bill with solar'],
    rec.months.map((m) => [MONTHS[m.month - 1], num(m.use), num(m.solar), rs(m.bill_before), rs(m.bill_after)]))

  heading('Monthly bill, now and with solar')
  image(charts.bill, 62)

  heading('With or without battery')
  table(['', 'Without battery', 'With battery'], [
    ['Panels / size', `${rec.panels} / ${rec.kw} kW`, `${batt?.panels} / ${batt?.kw} kW`],
    ['Battery', 'none', `${batt?.battery_kwh} kWh`],
    ['Cost', rs(rec.cost), rs(batt?.cost)],
    ['Saving per month', rs(rec.monthly_saving), rs(batt?.monthly_saving)],
    ['Payback', `${rec.payback_years} years`, `${batt?.payback_years} years`],
    ['Replacing inverter / battery in 25 years', rs(rec.replacement_cost), rs(batt?.replacement_cost)],
    ['Saving over 25 years (after all costs)', rs(rec.lifetime_net_saving), rs(batt?.lifetime_net_saving)],
    ['Tariff before -> after', `${STATUS[rec.status_before]} -> ${STATUS[rec.status_after]}`,
      `${STATUS[batt?.status_before]} -> ${STATUS[batt?.status_after]}`],
  ])

  heading('Roof and structure')
  const roofLine = p.roof.area_sqft
    ? `Panels need about ${num(p.roof.needed_sqft)} sq ft; free roof is ${num(p.roof.area_sqft)} sq ft. ${p.roof.fits ? 'It fits.' : 'It does not fit.'}`
    : `Panels need about ${num(p.roof.needed_sqft)} sq ft of free roof.`
  doc.setFont('helvetica', 'normal').setFontSize(10).setTextColor(...NAVY)
  doc.text(doc.splitTextToSize(`${roofLine} Structure: ${p.structure.name}. ${p.structure.note}`, W - 2 * M), M, y + 4)
  y += 18

  heading('Where the money goes (without battery)')
  const label = (k) => k.replace('_', ' and ').replace(/^./, (c) => c.toUpperCase()) // "wiring_protection" -> "Wiring and protection"
  table(['Part', 'Cost'], Object.entries(rec.cost_parts).filter(([, v]) => v).map(([k, v]) => [label(k), rs(v)]))

  if (result.appliances.summer) {
    heading('Which appliances use the most (summer)')
    table(['Appliance', 'Units per month', 'Share'],
      result.appliances.summer.items.map((a) => [`${a.count} x ${a.appliance}`, `~${num(a.units)}`, `${a.share_percent}%`]))
  }

  heading('Other sizes')
  table(['Panels', 'kW', 'Cost', 'Saving / year', 'Payback', 'Covers'],
    p.size_options.map((o) => [o.panels, o.kw, rs(o.cost), rs(o.yearly_saving), `${o.payback_years} yrs`, `${o.covers_percent}%`]),
    { didParseCell: (d) => { if (d.section === 'body' && p.size_options[d.row.index].panels === rec.panels) d.cell.styles.fontStyle = 'bold' } })

  // Footer note on the last page
  if (y > 265) { doc.addPage(); y = 18 }
  doc.setFont('helvetica', 'italic').setFontSize(8).setTextColor(...GREY)
  doc.text(doc.splitTextToSize(
    `Estimate based on ${result.model.based_on_houses} homes. Prices and tariffs change often; check with your installer and DISCO before buying.`,
    W - 2 * M), M, y)
  return doc
}

export function pdfFileName() {
  return `solar-plan-${new Date().toISOString().slice(0, 10)}.pdf`
}

// Phone or tablet (iPads report themselves as Macs, but have a touch screen)
export function isMobile() {
  const ua = navigator.userAgent
  return /Android|iPhone|iPad|iPod|Mobile/i.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)
}

const pdfFile = (doc) => new File([doc.output('blob')], pdfFileName(), { type: 'application/pdf' })

// Can this browser hand a file to other apps (the phone's share menu, or Windows share)?
export function canShareFile(doc) {
  return !!(navigator.canShare && navigator.canShare({ files: [pdfFile(doc)] }))
}

// Share menu with the PDF attached: the user picks WhatsApp, then the chat.
// No link can attach a file to WhatsApp, so this is the only way to send the PDF itself.
export async function sharePdfFile(doc, result) {
  if (!canShareFile(doc)) return 'unsupported'
  try {
    await navigator.share({ files: [pdfFile(doc)], title: 'My solar plan', text: summaryText(result) })
    return 'shared'
  } catch (e) {
    return e.name === 'AbortError' ? 'cancelled' : 'unsupported'
  }
}

// Open WhatsApp with the plan's summary typed in. target: 'web' (WhatsApp Web in a new tab)
// or 'app' (the installed WhatsApp app). onAppMissing runs when the app did not open.
export function openWhatsApp(target, result, onAppMissing) {
  const text = encodeURIComponent(summaryText(result))
  if (target === 'web') {
    window.open(`https://web.whatsapp.com/send?text=${text}`, '_blank', 'noopener')
    return
  }
  // If the app opens, this page loses focus; if it is still in front after 2.5 s, the app is not installed
  let left = false
  const onBlur = () => (left = true)
  window.addEventListener('blur', onBlur, { once: true })
  window.location.href = `whatsapp://send?text=${text}`
  setTimeout(() => {
    window.removeEventListener('blur', onBlur)
    if (!left && document.hasFocus() && onAppMissing) onAppMissing()
  }, 2500)
}
