// "Magic wand" roof selection: the user clicks their roof on the satellite map, and we grow a region of
// similar colour from that point until it hits the roof's edge (walls and shadows are a different colour).
// Works on the real zoom-19 photo pixels, whatever zoom the map shows.
import { contours } from 'd3-contour'
import { area as turfArea, convex, featureCollection, point, simplify, polygon as turfPolygon } from '@turf/turf'
import L from './leaflet-setup'

const ZOOM = 19 // highest zoom with real photos (see RoofMap.vue)
const TILE = 256
const SIZE = TILE * 3 // we read a 3 x 3 block of tiles around the click (about 190 m across)
const tileUrl = (x, y) =>
  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${ZOOM}/${y}/${x}`

// How different a pixel's colour may be from the clicked colour (RGB distance). Smaller = tighter selection.
export const LEVELS = [14, 20, 27, 35, 45, 58]
export const DEFAULT_LEVEL = 2
const HULL_LIMIT = 1.3 // use the neat outer outline only if it adds at most 30%

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous' // the tile server allows this, so we may read the pixels
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('Could not load the satellite photo'))
    img.src = url
  })
}

// Load the photo around the click once; growing with a different level reuses it
export async function loadPatch(map, latlng) {
  const p = map.project(latlng, ZOOM) // pixel position on the whole zoom-19 world map
  const tx = Math.floor(p.x / TILE)
  const ty = Math.floor(p.y / TILE)
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  const jobs = []
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      jobs.push(loadImage(tileUrl(tx + dx, ty + dy)).then((img) => ctx.drawImage(img, (dx + 1) * TILE, (dy + 1) * TILE)))
    }
  }
  await Promise.all(jobs)

  // A slight blur hides photo noise, so small specks on the roof don't stop the fill
  const smooth = document.createElement('canvas')
  smooth.width = smooth.height = SIZE
  const sctx = smooth.getContext('2d', { willReadFrequently: true })
  sctx.filter = 'blur(1.2px)'
  sctx.drawImage(canvas, 0, 0)

  const origin = L.point((tx - 1) * TILE, (ty - 1) * TILE)
  return {
    pixels: sctx.getImageData(0, 0, SIZE, SIZE).data,
    origin,
    seed: { x: Math.floor(p.x - origin.x), y: Math.floor(p.y - origin.y) },
    metresPerPixel: (156543.03392 * Math.cos((latlng.lat * Math.PI) / 180)) / 2 ** ZOOM,
  }
}

// Average colour of the 5 x 5 pixels around the click (one pixel can be a speck)
function seedColour({ pixels, seed }) {
  let r = 0, g = 0, b = 0, n = 0
  for (let y = seed.y - 2; y <= seed.y + 2; y++) {
    for (let x = seed.x - 2; x <= seed.x + 2; x++) {
      const i = (y * SIZE + x) * 4
      r += pixels[i]; g += pixels[i + 1]; b += pixels[i + 2]; n++
    }
  }
  return [r / n, g / n, b / n]
}

// Grow the region; returns null with a reason when it does not look like one roof
export function grow(patch, level, maxSqft) {
  const { pixels, seed, metresPerPixel } = patch
  const tol2 = LEVELS[level] ** 2
  const [sr, sg, sb] = seedColour(patch)
  const maxPixels = (maxSqft / 10.7639) / metresPerPixel ** 2

  const mask = new Uint8Array(SIZE * SIZE)
  const stack = [seed.y * SIZE + seed.x]
  mask[stack[0]] = 1
  let count = 0
  while (stack.length) {
    const idx = stack.pop()
    count++
    if (count > maxPixels) return { error: 'too_big' }
    const x = idx % SIZE
    const y = (idx - x) / SIZE
    if (x === 0 || y === 0 || x === SIZE - 1 || y === SIZE - 1) return { error: 'too_big' }
    for (const n of [idx - 1, idx + 1, idx - SIZE, idx + SIZE]) {
      if (mask[n]) continue
      const i = n * 4
      const dr = pixels[i] - sr, dg = pixels[i + 1] - sg, db = pixels[i + 2] - sb
      if (dr * dr + dg * dg + db * db <= tol2) {
        mask[n] = 1
        stack.push(n)
      }
    }
  }
  const sqft = count * metresPerPixel ** 2 * 10.7639
  if (sqft < 150) return { error: 'too_small' }
  return { mask, sqft }
}

// Turn the selected pixels into a map polygon (outline traced, small holes ignored, corners simplified)
export function maskToLatLngs(map, patch, mask) {
  const values = Float32Array.from(mask)
  const [shape] = contours().size([SIZE, SIZE]).thresholds([0.5])(values)
  // Several pieces can come back; keep the biggest outer ring (the roof itself)
  let best = null
  let bestArea = 0
  for (const poly of shape.coordinates) {
    const ring = poly[0]
    let a = 0
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1])
    if (Math.abs(a) > bestArea) { bestArea = Math.abs(a); best = ring }
  }
  if (!best) return null
  const ring = best[0][0] === best.at(-1)[0] && best[0][1] === best.at(-1)[1] ? best : [...best, best[0]]
  const lngLat = ring.map(([x, y]) => {
    const ll = map.unproject(L.point(patch.origin.x + x, patch.origin.y + y), ZOOM)
    return [ll.lng, ll.lat]
  })
  let shapePoly = turfPolygon([lngLat])
  // Most roofs are rectangles, but shade and stains leave a ragged edge. If the outer outline (convex hull)
  // is only a little bigger than what we found, use it: neater, and closer to the real roof.
  // An L-shaped roof makes the hull much bigger, so it keeps the traced shape.
  const hull = convex(featureCollection(lngLat.map((c) => point(c))))
  if (hull && turfArea(hull) <= HULL_LIMIT * turfArea(shapePoly)) shapePoly = hull
  // About 0.5 m of tolerance turns the pixel staircase into straight roof edges
  const simple = simplify(shapePoly, { tolerance: 0.000005, highQuality: true })
  return simple.geometry.coordinates[0].map(([lng, lat]) => [lat, lng])
}
