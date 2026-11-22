<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import L from '../leaflet-setup'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw'
import 'leaflet-draw/dist/leaflet.draw.css'
import { area as turfArea, difference, featureCollection, union, unkinkPolygon } from '@turf/turf'
import { DEFAULT_LEVEL, LEVELS, grow, loadPatch, maskToLatLngs } from '../roofSelect'
import { dist, recognise, snapAngle, squareUp } from '../shapeFit'

const emit = defineEmits(['area'])
const mapEl = ref(null)
const query = ref('')
const searching = ref(false)
const DEFAULT_MESSAGE = 'Find your roof, then press “Select my roof” and click on it. You can also draw it with the ⬠ or ■ tool.'
const message = ref(DEFAULT_MESSAGE)
let map, drawn

const SQFT_PER_M2 = 10.7639
const MAX_HOME_ROOF_SQFT = 50000 // about 2 kanal of open roof; anything bigger is a drawing mistake
const PHOTO_ZOOM = 19 // highest zoom with real satellite photos
const MAX_ZOOM = 22 // how far the user can zoom in (photos enlarged beyond PHOTO_ZOOM)
const ROOF_ZOOM = 20 // zoom used after search / "use my location": one house fills most of the map
// Selected roof = light yellow, whether picked by click or drawn by hand. Red = cut out of the selection.
const ROOF_STYLE = { color: '#F59E0B', weight: 2, fillColor: '#FDE68A', fillOpacity: 0.55 }
const CUT_STYLE = { color: '#DC2626', weight: 2, fillColor: '#FCA5A5', fillOpacity: 0.65 }

function areaMessage(sqft, removed, picked) {
  const cut = removed ? ` (${removed.toLocaleString()} sq ft taken out with the red pencil)` : ''
  const tip = picked ? ' Not quite right? Use Smaller / Bigger, the pencils, ✏️ to move corners, or draw it by hand.' : ''
  return `Selected roof: about ${sqft.toLocaleString()} sq ft${cut}.${tip}`
}

// A hand-drawn line can cross itself; split such a shape into clean pieces so the area maths works
function pieces(layer) {
  try {
    return unkinkPolygon(layer.toGeoJSON()).features
  } catch {
    return [layer.toGeoJSON()]
  }
}

// Yellow shapes joined together (overlaps counted once), minus everything red
function selectedArea() {
  const keep = []
  const cut = []
  drawn.eachLayer((layer) => (layer.options.cut ? cut : keep).push(...pieces(layer)))
  if (!keep.length) return { sqft: 0, removed: 0 }
  let shape = keep.length > 1 ? union(featureCollection(keep)) : keep[0]
  const before = turfArea(shape)
  if (cut.length) {
    const hole = cut.length > 1 ? union(featureCollection(cut)) : cut[0]
    shape = difference(featureCollection([shape, hole]))
  }
  const after = shape ? turfArea(shape) : 0
  return { sqft: Math.round(after * SQFT_PER_M2), removed: Math.round((before - after) * SQFT_PER_M2) }
}

function update(picked = false) {
  refreshCounts()
  const { sqft, removed } = selectedArea()
  if (sqft > MAX_HOME_ROOF_SQFT) {
    message.value = `That is ${sqft.toLocaleString()} sq ft, far bigger than a home roof. Zoom in to your roof and try again.`
    emit('area', null)
    return
  }
  message.value = sqft ? areaMessage(sqft, removed, picked) : DEFAULT_MESSAGE
  emit('area', sqft || null)
}

onMounted(() => {
  map = L.map(mapEl.value, { maxZoom: MAX_ZOOM }).setView([31.5204, 74.3587], 12) // Lahore
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    // Esri has real photos up to zoom 19 in Lahore; above that it sends a "no data" tile.
    // So we load zoom-19 photos and enlarge them for zoom 20 to 22: a bit blurry, but one roof fills the map.
    maxNativeZoom: PHOTO_ZOOM,
    maxZoom: MAX_ZOOM,
    attribution: 'Imagery © Esri',
  }).addTo(map)

  drawn = new L.FeatureGroup().addTo(map)
  map.addControl(
    new L.Control.Draw({
      // showArea is off on both: leaflet-draw 1.0.4 throws "type is not defined" when it is on
      draw: {
        polygon: { showArea: false, shapeOptions: ROOF_STYLE },
        rectangle: { showArea: false, shapeOptions: ROOF_STYLE },
        polyline: false, circle: false, marker: false, circlemarker: false,
      },
      edit: { featureGroup: drawn },
    })
  )
  map.on(L.Draw.Event.CREATED, (e) => { drawn.addLayer(e.layer); update() })
  map.on(L.Draw.Event.EDITED, () => update())
  map.on(L.Draw.Event.DELETED, () => { picked = null; update() })
  map.on(L.Draw.Event.DRAWSTART, () => { setSelecting(false); setPencil(null) }) // one tool at a time
  map.on('click', (e) => selecting.value && pickRoof(e.latlng))

  // Pencil drawing with mouse, pen or finger
  const el = mapEl.value
  el.addEventListener('pointerdown', penDown)
  el.addEventListener('pointermove', penMove)
  el.addEventListener('pointerup', penUp)
  el.addEventListener('pointercancel', penUp)
})

// ---------- Pencils: yellow adds to the roof, red cuts out (water tank, stair room, shade) ----------
const pencil = ref(null) // 'add', 'cut' or null
let stroke = null // { points, line } while the pencil is down

function setPencil(mode) {
  pencil.value = pencil.value === mode ? null : mode
  clearChain() // unfinished lines belong to the pencil that drew them
  if (!map) return
  const on = !!pencil.value
  if (on) {
    map.dragging.disable() // dragging would move the map instead of drawing
    setSelecting(false)
    message.value = pencil.value === 'add'
      ? 'Yellow pencil: hold and draw around the part of the roof to add. Lift to finish.'
      : 'Red pencil: hold and draw around what to take out (water tank, stair room, shade). Lift to finish.'
  } else {
    map.dragging.enable()
  }
  mapEl.value.style.cursor = on ? 'crosshair' : ''
  mapEl.value.style.touchAction = on ? 'none' : '' // stop the page scrolling while drawing with a finger
}

function penDown(e) {
  if (!pencil.value || e.target.closest('.leaflet-control')) return
  e.preventDefault()
  mapEl.value.setPointerCapture(e.pointerId)
  const ll = map.mouseEventToLatLng(e)
  const style = pencil.value === 'add' ? ROOF_STYLE : CUT_STYLE
  stroke = { latlngs: [ll], pixels: [map.mouseEventToContainerPoint(e)], last: { x: e.clientX, y: e.clientY },
             line: L.polyline([ll], { color: style.color, weight: 3, interactive: false }).addTo(map) }
}

function penMove(e) {
  if (!stroke) return
  // Skip tiny moves: fewer points, smoother line
  if (Math.hypot(e.clientX - stroke.last.x, e.clientY - stroke.last.y) < 3) return
  stroke.last = { x: e.clientX, y: e.clientY }
  stroke.latlngs.push(map.mouseEventToLatLng(e))
  stroke.pixels.push(map.mouseEventToContainerPoint(e))
  stroke.line.setLatLngs(stroke.latlngs)
}

function penUp() {
  if (!stroke) return
  const { latlngs, pixels, line } = stroke
  stroke = null
  line.remove()
  if (latlngs.length < 3) return // a tap, not a shape
  if (!autoShapes.value) return addShape(latlngs)

  const shape = recognise(pixels)
  if (shape.kind === 'line') return addLine(shape.points[0], shape.points[1])
  if (shape.kind === 'scribble') {
    message.value = 'Could not make a shape from that. Draw a closed loop around the area, or straight lines one after another.'
    return
  }
  clearChain()
  addShape(toLatLngs(shape.points), SHAPE_NAMES[shape.kind])
}

// ---------- Auto shapes: wobbly strokes become clean rectangles, circles, triangles or straight edges ----------
const autoShapes = ref(true)
const SHAPE_NAMES = { rectangle: 'a rectangle', circle: 'a circle', triangle: 'a triangle', polygon: 'a shape with straight edges' }
const JOIN_PX = 25 // a line that starts or ends this close to the chain's end or start joins it
let chain = null // straight lines drawn one after another: { pixels: [...], refAngle, layer }

const toLatLngs = (pixels) => pixels.map((p) => map.containerPointToLatLng(L.point(p.x, p.y)))

function clearChain() {
  if (chain) chain.layer.remove()
  chain = null
  refreshCounts()
}

// ---------- Undo / clear, separately for yellow (added) and red (taken out) ----------
const yellowCount = ref(0) // shapes plus unfinished lines, so the buttons know when there is something to undo
const redCount = ref(0)

function refreshCounts() {
  if (!drawn) return
  const layers = drawn.getLayers()
  const chainFor = (cut) => (chain && chain.cut === cut ? 1 : 0)
  yellowCount.value = layers.filter((l) => !l.options.cut).length + chainFor(false)
  redCount.value = layers.filter((l) => l.options.cut).length + chainFor(true)
}

function undoLast(cut) {
  // Unfinished straight lines of this colour go first, one line at a time
  if (chain && chain.cut === cut) {
    chain.pixels.pop()
    if (chain.pixels.length < 2) clearChain()
    else { chain.layer.setLatLngs(toLatLngs(chain.pixels)); refreshCounts() }
    message.value = 'Last line removed.'
    return
  }
  const last = drawn.getLayers().filter((l) => !!l.options.cut === cut).at(-1) // layers keep the order they were added
  if (!last) return
  drawn.removeLayer(last)
  if (last === picked) picked = null
  update()
}

function clearColour(cut) {
  const layers = drawn.getLayers().filter((l) => !!l.options.cut === cut)
  const what = cut ? 'red (taken out)' : 'yellow (selected)'
  if (layers.length > 1 && !confirm(`Remove all ${layers.length} ${what} shapes?`)) return
  if (chain && chain.cut === cut) clearChain()
  for (const l of layers) {
    drawn.removeLayer(l)
    if (l === picked) picked = null
  }
  update()
}

function addLine(start, end) {
  // Join the new line to the end of the previous one when it starts near it; otherwise start a new chain
  if (chain && dist(start, chain.pixels.at(-1)) <= JOIN_PX) start = chain.pixels.at(-1)
  else { clearChain() }
  if (!chain) {
    const cut = pencil.value === 'cut'
    chain = { pixels: [start], cut, refAngle: Math.atan2(end.y - start.y, end.x - start.x),
              layer: L.polyline([], { color: (cut ? CUT_STYLE : ROOF_STYLE).color, weight: 3, dashArray: '8 6', interactive: false }).addTo(map) }
  } else {
    end = snapAngle(start, end, chain.refAngle) // parallel or at a right angle to the first line
  }
  // Ends near the first point after 2 or more lines: close the shape
  if (chain.pixels.length >= 3 && dist(end, chain.pixels[0]) <= JOIN_PX) {
    const corners = squareUp(chain.pixels)
    clearChain()
    addShape(toLatLngs(corners), corners.length === 4 ? 'a rectangle' : 'a shape with straight edges')
    return
  }
  chain.pixels.push(end)
  chain.layer.setLatLngs(toLatLngs(chain.pixels))
  refreshCounts()
  message.value = 'Line straightened. Keep drawing lines; end the last one at the first point to close the shape.'
}

function addShape(latlngs, madeInto = null) {
  const cut = pencil.value === 'cut'
  const shape = L.polygon(latlngs, { ...(cut ? CUT_STYLE : ROOF_STYLE), cut })
  drawn.addLayer(shape)
  if (cut && !drawnHasYellow()) {
    drawn.removeLayer(shape)
    message.value = 'Select or draw your roof first; the red pencil takes parts out of it.'
    return
  }
  update()
  if (madeInto) message.value = `Turned into ${madeInto}. ` + message.value
}

const drawnHasYellow = () => drawn.getLayers().some((l) => !l.options.cut)

onBeforeUnmount(() => map && map.remove())

// ---------- Click on a roof to select it ----------
const selecting = ref(false)
const working = ref(false)
const level = ref(DEFAULT_LEVEL)
let patch = null // photo around the last click, reused by Smaller / Bigger
const hasPatch = ref(false) // shows the Smaller / Bigger buttons
let picked = null // the yellow shape made by the last click

function setSelecting(on) {
  if (on && pencil.value) setPencil(null)
  selecting.value = on
  mapEl.value.style.cursor = on ? 'crosshair' : ''
  if (on) message.value = 'Click in the middle of your roof (on an open part, not on the water tank).'
}

async function pickRoof(latlng) {
  if (map.getZoom() < PHOTO_ZOOM) {
    message.value = 'Zoom in more first, until one house fills a good part of the map.'
    return
  }
  working.value = true
  message.value = 'Finding the edges of your roof…'
  try {
    patch = await loadPatch(map, latlng)
    hasPatch.value = true
    level.value = DEFAULT_LEVEL
    showSelection()
  } catch {
    message.value = 'Could not read the satellite photo here. Please draw your roof with the ⬠ tool.'
  } finally {
    working.value = false
  }
}

function showSelection() {
  const result = grow(patch, level.value, MAX_HOME_ROOF_SQFT)
  if (result.error) {
    message.value = result.error === 'too_small'
      ? 'Only a tiny spot matched. Press Bigger, or click on a plain part of the roof.'
      : 'The selection spread past your roof (the roofs around look alike). Press Smaller, or draw it with the ⬠ tool.'
    return
  }
  const latlngs = maskToLatLngs(map, patch, result.mask)
  if (!latlngs) return
  if (picked) drawn.removeLayer(picked)
  picked = L.polygon(latlngs, ROOF_STYLE)
  drawn.addLayer(picked)
  setSelecting(false)
  update(true)
}

function changeSize(step) {
  const next = level.value + step
  if (!patch || next < 0 || next >= LEVELS.length) return
  level.value = next
  showSelection()
}

// ---------- Search and "use my location" ----------
async function search() {
  if (!query.value) return
  searching.value = true
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=pk&q=${encodeURIComponent(query.value)}`
    const res = await (await fetch(url, { headers: { 'Accept-Language': 'en' } })).json()
    if (res.length) map.setView([+res[0].lat, +res[0].lon], 18) // an area, not one house: user zooms in from here
    else message.value = 'Place not found. Try a nearby landmark or road.'
  } catch {
    message.value = 'Search is not working right now. Move and zoom the map to your roof by hand.'
  } finally {
    searching.value = false
  }
}

// The phone's GPS takes the map straight to the user's roof (when they are at home)
const locating = ref(false)
let hereCircle

function locate() {
  if (!navigator.geolocation) {
    message.value = 'This browser cannot share its location. Please search your area instead.'
    return
  }
  locating.value = true
  message.value = 'Finding your location…'
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      locating.value = false
      const { latitude, longitude, accuracy } = pos.coords
      map.setView([latitude, longitude], ROOF_ZOOM)
      if (hereCircle) hereCircle.remove()
      // Shows where the phone thinks it is; not part of the roof area
      hereCircle = L.circle([latitude, longitude], {
        radius: Math.max(accuracy, 5), color: '#f59e0b', weight: 2, fill: false, dashArray: '6 6', interactive: false,
      }).addTo(map)
      message.value = accuracy > 100
        ? `Location found, but only to about ${Math.round(accuracy)} m. Look for your roof around the orange circle.`
        : 'Your roof should be inside the orange circle. Press “Select my roof” and click on it.'
    },
    (err) => {
      locating.value = false
      message.value = err.code === err.PERMISSION_DENIED
        ? 'Location permission was refused. Please search your area instead.'
        : 'Could not get your location. Please search your area instead.'
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
  )
}
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-2 mb-3">
      <div class="relative flex-1 min-w-48">
        <span class="icon text-[18px] text-on-surface-variant absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">search</span>
        <input v-model="query" class="input pl-9" placeholder="e.g. Amir Town, Lahore" @keyup.enter="search" />
      </div>
      <button class="btn-light" :disabled="searching" @click="search">Search</button>
      <button class="btn-light" :disabled="locating" title="Works best when you are at home" @click="locate">
        <span class="icon text-[18px]" :class="locating && 'animate-spin'">{{ locating ? 'sync' : 'my_location' }}</span>{{ locating ? 'Finding…' : 'Use my location' }}
      </button>
    </div>
    <div class="flex flex-wrap items-center gap-2 mb-3">
      <button
        :class="selecting ? 'btn' : 'btn-light'"
        :disabled="working"
        @click="setSelecting(!selecting)"
      >
        <span class="icon text-[18px]" :class="working && 'animate-spin'">{{ working ? 'sync' : 'touch_app' }}</span>
        {{ working ? 'Finding edges…' : selecting ? 'Click on your roof…' : 'Select my roof' }}
      </button>
      <template v-if="hasPatch">
        <button class="btn-light" :disabled="working || level === 0" @click="changeSize(-1)"><span class="icon text-[18px]">remove</span>Smaller</button>
        <button class="btn-light" :disabled="working || level === LEVELS.length - 1" @click="changeSize(1)"><span class="icon text-[18px]">add</span>Bigger</button>
      </template>
      <div class="flex items-center rounded-lg bg-tertiary-fixed/50 p-1 gap-1">
        <button
          class="btn-light"
          :class="pencil === 'add' ? '!bg-tertiary-fixed-dim ring-2 ring-on-tertiary-container' : '!bg-surface-container-lowest'"
          title="Draw around a part of the roof to add it"
          @click="setPencil('add')"
        >
          <span class="inline-block w-3 h-3 rounded-full" style="background: #F59E0B"></span>Pencil: add
        </button>
        <button class="btn-light px-2.5 !bg-transparent" title="Remove the last yellow shape or line" :disabled="!yellowCount" @click="undoLast(false)"><span class="icon text-[18px]">undo</span>Undo</button>
        <button class="btn-light px-2.5 !bg-transparent" title="Remove all yellow shapes" :disabled="!yellowCount" @click="clearColour(false)"><span class="icon text-[18px]">close</span>Clear</button>
      </div>
      <div class="flex items-center rounded-lg bg-error-container/50 p-1 gap-1">
        <button
          class="btn-light"
          :class="pencil === 'cut' ? '!bg-error-container ring-2 ring-error' : '!bg-surface-container-lowest'"
          title="Draw around a water tank, stair room or shade to take it out"
          @click="setPencil('cut')"
        >
          <span class="inline-block w-3 h-3 rounded-full" style="background: #DC2626"></span>Pencil: remove
        </button>
        <button class="btn-light px-2.5 !bg-transparent" title="Remove the last red shape or line" :disabled="!redCount" @click="undoLast(true)"><span class="icon text-[18px]">undo</span>Undo</button>
        <button class="btn-light px-2.5 !bg-transparent" title="Remove all red shapes" :disabled="!redCount" @click="clearColour(true)"><span class="icon text-[18px]">close</span>Clear</button>
      </div>
      <label class="flex items-center gap-2 text-label-md text-on-surface-variant cursor-pointer" title="Turn wobbly pencil strokes into straight lines and clean shapes">
        <input v-model="autoShapes" type="checkbox" class="w-4 h-4" />Auto shapes
      </label>
    </div>
    <div ref="mapEl" class="h-104 sm:h-136 rounded-lg overflow-hidden ring-1 ring-outline-variant/50"></div>
    <p v-if="message" class="panel mt-3 text-body-sm text-on-surface-variant flex items-start gap-1.5"><span class="icon text-[18px] text-secondary shrink-0">info</span><span>{{ message }}</span></p>
  </div>
</template>
