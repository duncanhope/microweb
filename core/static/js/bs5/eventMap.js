// The event page's map (BS5-11), ported from js/eventMap.js and the inline
// script in event.html without jQuery. event_header_small.html renders
//
//   <div id="map-canvas" data-mw-event-map data-lat data-lon
//        data-north data-west data-south data-east data-thunderforest-key></div>
//
// and this module draws a Leaflet 0.7 map on it, fitted to the place's bounds,
// with a marker on the place: Google's road map once its API loads, and
// tile layers to choose from. The tile layers are Thunderforest's
// OpenCycleMap and Landscape when there is a key
// (settings.THUNDERFOREST_API_KEY), which they need, and OpenStreetMap's
// standard tiles when there is not. The Leaflet map is kept on the element as
// el.mwMap. Leaflet draws its own light UI, so _base.scss keeps
// .leaflet-container in color-scheme: light in every Color mode.

import { GoogleLayer, loadGoogleMaps } from './leafletGoogle.js';

const { L } = window;

const THUNDERFOREST = {
  attribution: 'Maps &copy; <a href="https://www.thunderforest.com">Thunderforest</a>, Data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 22,
};
const OPENSTREETMAP = {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
};

export function tileLayers(thunderforestKey) {
  if (thunderforestKey) {
    const options = { ...THUNDERFOREST, apikey: thunderforestKey };
    return {
      'Open Cycle Map': L.tileLayer('https://tile.thunderforest.com/cycle/{z}/{x}/{y}.png?apikey={apikey}', options),
      Landscape: L.tileLayer('https://tile.thunderforest.com/landscape/{z}/{x}/{y}.png?apikey={apikey}', options),
    };
  }
  return { OpenStreetMap: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', OPENSTREETMAP) };
}

// Google's road map is the default once its API loads. If it cannot load
// (blocked or offline), or Google refuses the key on this domain, the first
// tile layer stands in.
async function addBaseLayers(map, thunderforestKey) {
  const layers = tileLayers(thunderforestKey);
  const fallback = Object.values(layers)[0];
  const control = L.control.layers(layers).addTo(map);
  let google = null;
  let refused = false;
  const useFallback = () => {
    if (google) {
      map.removeLayer(google);
      control.removeLayer(google);
      google = null;
    }
    map.addLayer(fallback);
  };
  // Google calls this when the key is not allowed on this domain, and draws
  // an error in place of the map.
  window.gm_authFailure = () => {
    refused = true;
    useFallback();
  };

  const loaded = await loadGoogleMaps();
  if (Object.values(layers).some((layer) => map.hasLayer(layer))) return;
  if (!loaded || refused) {
    useFallback();
    return;
  }
  google = new GoogleLayer('ROADMAP');
  control.addBaseLayer(google, 'Google Maps');
  map.addLayer(google);
}

export function drawEventMap(el) {
  const number = (name) => (el.dataset[name] === '' ? NaN : Number(el.dataset[name]));
  const [lat, lon, north, west, south, east] = ['lat', 'lon', 'north', 'west', 'south', 'east'].map(number);
  if (Number.isNaN(lat) || Number.isNaN(lon)) return null;

  const map = L.map(el, { zoomAnimation: false }).setMaxBounds([[-90, -180], [90, 180]]);
  if ([north, west, south, east].some(Number.isNaN)) {
    map.setView([lat, lon], 15);
  } else {
    map.fitBounds([[north, west], [south, east]]);
    // fitBounds lands one level too far out, as the old script noted.
    map.zoomIn();
  }
  L.marker([lat, lon]).addTo(map);
  addBaseLayers(map, el.dataset.thunderforestKey);
  el.mwMap = map;
  return map;
}

const el = document.querySelector('[data-mw-event-map]');
if (el && L) drawEventMap(el);
