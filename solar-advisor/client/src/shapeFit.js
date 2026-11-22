// Cleans up hand-drawn pencil strokes (points in screen pixels, {x, y}):
// a wobbly line becomes straight, and a rough loop becomes a rectangle, circle, triangle or a polygon
// with straight edges. Roofs are mostly rectangles, so rectangles are tried hard (any rotation).

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)

function pathLength(pts) {
  let len = 0
  for (let i = 1; i < pts.length; i++) len += dist(pts[i - 1], pts[i])
  return len
}

export function polygonArea(pts) {
  let a = 0
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) a += (pts[j].x + pts[i].x) * (pts[j].y - pts[i].y)
  return Math.abs(a) / 2
}

function bboxDiagonal(pts) {
  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  return Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys))
}

// Ramer-Douglas-Peucker: keep only the points where the line really turns
function simplify(pts, eps) {
  if (pts.length < 3) return pts
  const [a, b] = [pts[0], pts.at(-1)]
  let maxD = 0
  let idx = 0
  for (let i = 1; i < pts.length - 1; i++) {
    const d = distToSegment(pts[i], a, b)
    if (d > maxD) { maxD = d; idx = i }
  }
  if (maxD <= eps) return [a, b]
  return [...simplify(pts.slice(0, idx + 1), eps).slice(0, -1), ...simplify(pts.slice(idx), eps)]
}

function distToSegment(p, a, b) {
  const l2 = (b.x - a.x) ** 2 + (b.y - a.y) ** 2
  if (!l2) return dist(p, a)
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y)) / l2))
  return dist(p, { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) })
}

// Closed loop simplified: the first point of the stroke is not a real corner, so simplify from the far point
function simplifyClosed(pts, eps) {
  let far = 0
  pts.forEach((p, i) => { if (dist(p, pts[0]) > dist(pts[far], pts[0])) far = i })
  const a = simplify(pts.slice(0, far + 1), eps)
  const b = simplify([...pts.slice(far), pts[0]], eps)
  const ring = [...a.slice(0, -1), ...b.slice(0, -1)]
  // Drop corners that are almost straight (angle close to 180 degrees)
  return ring.filter((p, i) => {
    const prev = ring[(i - 1 + ring.length) % ring.length]
    const next = ring[(i + 1) % ring.length]
    const v1 = { x: p.x - prev.x, y: p.y - prev.y }
    const v2 = { x: next.x - p.x, y: next.y - p.y }
    const cos = (v1.x * v2.x + v1.y * v2.y) / (Math.hypot(v1.x, v1.y) * Math.hypot(v2.x, v2.y) || 1)
    return cos < 0.96
  })
}

// Convex hull (monotone chain)
function hull(pts) {
  const p = [...pts].sort((a, b) => a.x - b.x || a.y - b.y)
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
  const lower = []
  for (const q of p) { while (lower.length >= 2 && cross(lower.at(-2), lower.at(-1), q) <= 0) lower.pop(); lower.push(q) }
  const upper = []
  for (const q of p.reverse()) { while (upper.length >= 2 && cross(upper.at(-2), upper.at(-1), q) <= 0) upper.pop(); upper.push(q) }
  return [...lower.slice(0, -1), ...upper.slice(0, -1)]
}

// Smallest rectangle (any rotation) around the points: one of its sides lies along a hull edge
function minAreaRect(pts) {
  const h = hull(pts)
  let best = null
  for (let i = 0; i < h.length; i++) {
    const a = h[i]
    const b = h[(i + 1) % h.length]
    const len = dist(a, b) || 1
    const ux = (b.x - a.x) / len
    const uy = (b.y - a.y) / len
    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity
    for (const p of h) {
      const u = p.x * ux + p.y * uy
      const v = -p.x * uy + p.y * ux
      minU = Math.min(minU, u); maxU = Math.max(maxU, u); minV = Math.min(minV, v); maxV = Math.max(maxV, v)
    }
    const area = (maxU - minU) * (maxV - minV)
    if (!best || area < best.area) best = { area, ux, uy, minU, maxU, minV, maxV }
  }
  const { ux, uy, minU, maxU, minV, maxV } = best
  const at = (u, v) => ({ x: u * ux - v * uy, y: u * uy + v * ux })
  return { area: best.area, corners: [at(minU, minV), at(maxU, minV), at(maxU, maxV), at(minU, maxV)] }
}

function circleFrom(pts) {
  const c = { x: pts.reduce((s, p) => s + p.x, 0) / pts.length, y: pts.reduce((s, p) => s + p.y, 0) / pts.length }
  const radii = pts.map((p) => dist(p, c))
  const mean = radii.reduce((s, r) => s + r, 0) / radii.length
  const sd = Math.sqrt(radii.reduce((s, r) => s + (r - mean) ** 2, 0) / radii.length)
  const ring = Array.from({ length: 48 }, (_, i) => ({
    x: c.x + mean * Math.cos((2 * Math.PI * i) / 48), y: c.y + mean * Math.sin((2 * Math.PI * i) / 48),
  }))
  return { spread: sd / mean, ring }
}

// Even out the spacing of a stroke so slow and fast parts of the drawing count the same
function resample(pts, n = 64) {
  const total = pathLength(pts)
  if (!total) return pts
  const step = total / n
  const out = [pts[0]]
  let acc = 0
  for (let i = 1; i < pts.length; i++) {
    let a = pts[i - 1]
    let d = dist(a, pts[i])
    while (acc + d >= step) {
      const t = (step - acc) / d
      a = { x: a.x + t * (pts[i].x - a.x), y: a.y + t * (pts[i].y - a.y) }
      out.push(a)
      d = dist(a, pts[i])
      acc = 0
    }
    acc += d
  }
  return out
}

/**
 * Decide what a stroke is.
 * Returns { kind: 'line', points: [a, b] }            a straight line (not closed)
 *      or { kind: 'rectangle' | 'circle' | 'triangle' | 'polygon', points: [...] }  a closed shape
 *      or { kind: 'scribble' }                          an open, curvy stroke: nothing to make of it
 */
export function recognise(raw) {
  if (raw.length < 2) return { kind: 'scribble' }
  const len = pathLength(raw)
  const gap = dist(raw[0], raw.at(-1))
  const size = bboxDiagonal(raw)

  // Open and nearly straight: a line
  if (gap > 0.6 * size && gap / len > 0.85) return { kind: 'line', points: [raw[0], raw.at(-1)] }
  // Ends far apart and not straight: neither a line nor a loop
  if (gap > 0.35 * size) return { kind: 'scribble' }

  const pts = resample(raw)
  const shapeArea = polygonArea(pts)
  if (shapeArea < 50) return { kind: 'scribble' }

  const circle = circleFrom(pts)
  if (circle.spread < 0.09) return { kind: 'circle', points: circle.ring }

  const rect = minAreaRect(pts)
  if (shapeArea / rect.area > 0.8) return { kind: 'rectangle', points: rect.corners }

  const corners = simplifyClosed(pts, 0.08 * size)
  if (corners.length === 3) return { kind: 'triangle', points: corners }
  const edges = simplifyClosed(pts, 0.04 * size)
  return { kind: 'polygon', points: edges.length >= 3 ? edges : rect.corners }
}

// For a chain of straight lines: turn a line so it is parallel or at a right angle to the first one,
// when it is already within `snapDeg` degrees of that
export function snapAngle(start, end, refAngle, snapDeg = 12) {
  const len = dist(start, end)
  const ang = Math.atan2(end.y - start.y, end.x - start.x)
  const quarter = Math.PI / 2
  const turns = Math.round((ang - refAngle) / quarter)
  const target = refAngle + turns * quarter
  if (Math.abs(ang - target) > (snapDeg * Math.PI) / 180) return end
  return { x: start.x + len * Math.cos(target), y: start.y + len * Math.sin(target) }
}

// A closed chain of lines that is almost a rectangle becomes an exact rectangle
export function squareUp(corners) {
  if (corners.length !== 4) return corners
  const rect = minAreaRect(corners)
  return polygonArea(corners) / rect.area > 0.9 ? rect.corners : corners
}

export { dist }
