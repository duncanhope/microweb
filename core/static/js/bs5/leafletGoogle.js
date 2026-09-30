// Google Maps as a Leaflet 0.7 layer (BS5-11), ported from js/leaflet.js
// (L.Google) without globals of its own. Leaflet and the Google Maps API are
// classic scripts the page loads first, so they are window.L and
// window.google here. The event page's map uses it, and the event form can.
//
// Leaflet owns the map: it pans and zooms, and this layer keeps a Google map
// underneath it at the same centre and zoom.

const { L } = window;

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
    this.google = new window.google.maps.Map(this.container, {
      center: new window.google.maps.LatLng(0, 0),
      zoom: 0,
      mapTypeId: this.type,
      disableDefaultUI: true,
      keyboardShortcuts: false,
      draggable: false,
      disableDoubleClickZoom: true,
      scrollwheel: false,
      streetViewControl: false,
    });
    map.on('move', this.update, this);
    this.update();
  },

  onRemove(map) {
    this.container.remove();
    map.off('move', this.update, this);
  },

  resize() {
    const size = this.map.getSize();
    const [width, height] = [size.x + 'px', size.y + 'px'];
    if (this.container.style.width === width && this.container.style.height === height) return false;
    this.container.style.width = width;
    this.container.style.height = height;
    return true;
  },

  update() {
    if (this.resize()) window.google.maps.event.trigger(this.google, 'resize');
    const center = this.map.getCenter();
    this.google.setCenter(new window.google.maps.LatLng(center.lat, center.lng));
    this.google.setZoom(this.map.getZoom());
  },
});
