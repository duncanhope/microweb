// The event page's map (BS5-11), ported from js/eventMap.js and the inline
// script in event.html without jQuery. event_header_small.html renders
//
//   <div id="map-canvas" data-mw-event-map data-lat data-lon
//        data-north data-west data-south data-east></div>
//
// and this module draws a Leaflet 0.7 map on it: Google's road map, with
// OpenCycleMap and Landscape to choose from, fitted to the place's bounds,
// with a marker on the place. The Leaflet map is kept on the element as
// el.mwMap. Leaflet draws its own light UI, so _base.scss keeps
// .leaflet-container in color-scheme: light in every Color mode.

import { GoogleLayer } from './leafletGoogle.js';

const { L } = window;

const THUNDERFOREST = {
  attribution: 'Maps &copy; <a href="http://www.thunderforest.com">Thunderforest</a>, Data &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
  maxZoom: 22,
};

export function drawEventMap(el) {
  const number = (name) => (el.dataset[name] === '' ? NaN : Number(el.dataset[name]));
  const [lat, lon, north, west, south, east] = ['lat', 'lon', 'north', 'west', 'south', 'east'].map(number);
  if (Number.isNaN(lat) || Number.isNaN(lon)) return null;

  const map = L.map(el, { zoomAnimation: false }).setMaxBounds([[-90, -180], [90, 180]]);
  const layers = {
    'Open Cycle Map': L.tileLayer('https://a.tile.thunderforest.com/cycle/{z}/{x}/{y}.png', THUNDERFOREST),
    Landscape: L.tileLayer('https://a.tile.thunderforest.com/landscape/{z}/{x}/{y}.png', THUNDERFOREST),
  };
  // Google's road map is the default, as today; without the Google script
  // (blocked or offline) OpenCycleMap stands in.
  let base = layers['Open Cycle Map'];
  if (window.google?.maps) {
    base = new GoogleLayer('ROADMAP');
    layers['Google Maps'] = base;
  }
  map.addLayer(base);
  map.addControl(L.control.layers(layers));

  if ([north, west, south, east].some(Number.isNaN)) {
    map.setView([lat, lon], 15);
  } else {
    map.fitBounds([[north, west], [south, east]]);
    // fitBounds lands one level too far out, as the old script noted.
    map.zoomIn();
  }
  L.marker([lat, lon]).addTo(map);
  el.mwMap = map;
  return map;
}

const el = document.querySelector('[data-mw-event-map]');
if (el && L) drawEventMap(el);
