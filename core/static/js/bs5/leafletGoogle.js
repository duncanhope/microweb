// Google Maps as a Leaflet 0.7 layer (BS5-11), ported from js/leaflet.js
// (L.Google) without globals of its own. Leaflet is a classic script the page
// loads first, so it is window.L here. The Google Maps JavaScript API comes
// from google_maps_loader.html, which defines google.maps.importLibrary and
// loads nothing until loadGoogleMaps() calls it. The event page's map uses
// it, and the event form can.
//
// Leaflet owns the map: it pans and zooms, and this layer keeps a Google map
// underneath it at the same centre and zoom.

const { L } = window;

// Resolves true once GoogleLayer can draw, and false when the loader is
// missing (blocked or offline) or the API cannot load.
export async function loadGoogleMaps() {
  const maps = window.google?.maps;
  if (!maps?.importLibrary) return false;
  try {
    await Promise.all([maps.importLibrary('core'), maps.importLibrary('maps')]);
    return true;
  } catch {
    return false;
  }
}

export const GoogleLayer = L.Class.extend({
  includes: L.Mixin.Events,

  // type: ROADMAP, SATELLITE, HYBRID or TERRAIN.
  initialize(type = 'ROADMAP') {
    this.type = window.google.maps.MapTypeId[type];
  },

  onAdd(map) {
    this.map = map;
    this.container = L.DomUtil.create('div', 'leaflet-google-layer leaflet-top leaflet-left');
    this.container.style.zIndex = 0;
    map.getContainer().prepend(this.container);
    this.resize();
    // Leaflet takes the gestures; Google only draws.
    this.google = new window.google.maps.Map(this.container, {
      center: new window.google.maps.LatLng(0, 0),
      zoom: 0,
      mapTypeId: this.type,
      disableDefaultUI: true,
      keyboardShortcuts: false,
      gestureHandling: 'none',
      clickableIcons: false,
    });
    map.on('move', this.update, this);
    this.update();
  },

  onRemove(map) {
    this.container.remove();
    map.off('move', this.update, this);
  },

  // Google's map follows its container's size by itself.
  resize() {
    const size = this.map.getSize();
    this.container.style.width = size.x + 'px';
    this.container.style.height = size.y + 'px';
  },

  update() {
    this.resize();
    const center = this.map.getCenter();
    this.google.setCenter(new window.google.maps.LatLng(center.lat, center.lng));
    this.google.setZoom(this.map.getZoom());
  },
});
