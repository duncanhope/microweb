/*
 * Google Maps as a Leaflet 0.7 layer (L.Google), and the event maps' base
 * layers (L.Google.addBaseLayers). The Google Maps JavaScript API comes from
 * google_maps_loader.html, which loads it on demand: L.Google.load.
 */
L.Google = L.Class.extend({
  includes: L.Mixin.Events,

  options: {
    minZoom: 0,
    maxZoom: 18,
    tileSize: 256,
    subdomains: 'abc',
    errorTileUrl: '',
    attribution: '',
    opacity: 1,
    continuousWorld: false,
    noWrap: false,
  },

  // Possible types: SATELLITE, ROADMAP, HYBRID
  initialize: function(type, options) {
    L.Util.setOptions(this, options);

    this._type = google.maps.MapTypeId[type || 'SATELLITE'];
  },

  onAdd: function(map, insertAtTheBottom) {
    this._map = map;
    this._insertAtTheBottom = insertAtTheBottom;

    // create a container div for tiles
    this._initContainer();
    this._initMapObject();

    // set up events
    map.on('viewreset', this._resetCallback, this);

    this._limitedUpdate = L.Util.limitExecByInterval(this._update, 150, this);
    map.on('move', this._update, this);
    //map.on('moveend', this._update, this);

    this._reset();
    this._update();
  },

  onRemove: function(map) {
    this._map._container.removeChild(this._container);
    //this._container = null;

    this._map.off('viewreset', this._resetCallback, this);

    this._map.off('move', this._update, this);
    //this._map.off('moveend', this._update, this);
  },

  getAttribution: function() {
    return this.options.attribution;
  },

  setOpacity: function(opacity) {
    this.options.opacity = opacity;
    if (opacity < 1) {
      L.DomUtil.setOpacity(this._container, opacity);
    }
  },

  _initContainer: function() {
    var tilePane = this._map._container
      first = tilePane.firstChild;

    if (!this._container) {
      this._container = L.DomUtil.create('div', 'leaflet-google-layer leaflet-top leaflet-left');
      this._container.id = "_GMapContainer";
    }

    if (true) {
      tilePane.insertBefore(this._container, first);

      this.setOpacity(this.options.opacity);
      var size = this._map.getSize();
      this._container.style.width = size.x + 'px';
      this._container.style.height = size.y + 'px';
      this._container.style.zIndex = 0;
    }
  },

  _initMapObject: function() {
    this._google_center = new google.maps.LatLng(0, 0);
    // Leaflet owns panning and zooming; Google only draws.
    var map = new google.maps.Map(this._container, {
        center: this._google_center,
        zoom: 0,
        mapTypeId: this._type,
        disableDefaultUI: true,
        keyboardShortcuts: false,
        gestureHandling: 'none',
        clickableIcons: false
    });

    var _this = this;
    this._reposition = google.maps.event.addListenerOnce(map, "center_changed",
      function() { _this.onReposition(); });

    this._google = map;
  },

  _resetCallback: function(e) {
    this._reset(e.hard);
  },

  _reset: function(clearOldContainer) {
    this._initContainer();
  },

  _update: function() {
    this._resize();

    var bounds = this._map.getBounds();
    var ne = bounds.getNorthEast();
    var sw = bounds.getSouthWest();
    var google_bounds = new google.maps.LatLngBounds(
      new google.maps.LatLng(sw.lat, sw.lng),
      new google.maps.LatLng(ne.lat, ne.lng)
    );
    var center = this._map.getCenter();
    var _center = new google.maps.LatLng(center.lat, center.lng);

    this._google.setCenter(_center);
    this._google.setZoom(this._map.getZoom());
    //this._google.fitBounds(google_bounds);
  },

  // Google's map follows its container's size by itself.
  _resize: function() {
    var size = this._map.getSize();
    this._container.style.width = size.x + 'px';
    this._container.style.height = size.y + 'px';
  },

  onReposition: function() {
    //google.maps.event.trigger(this._google, "resize");
  }
});

// Loads the Google Maps JavaScript API through google_maps_loader.html's
// google.maps.importLibrary. Resolves true once L.Google can draw, and false
// when the loader is missing or the API cannot load.
L.Google.load = function() {
  var maps = window.google && window.google.maps;
  if (!maps || !maps.importLibrary) {
    return Promise.resolve(false);
  }
  return Promise.all([maps.importLibrary('core'), maps.importLibrary('maps')])
    .then(function() { return true; }, function() { return false; });
};

// The event maps' tile layers: Thunderforest's OpenCycleMap and Landscape
// when there is a key (settings.THUNDERFOREST_API_KEY), which they need, and
// OpenStreetMap's standard tiles when there is not.
L.Google.tileLayers = function(thunderforestKey) {
  if (thunderforestKey) {
    var thunderforest = {
      attribution: 'Maps &copy; <a href="https://www.thunderforest.com">Thunderforest</a>, Data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 22,
      apikey: thunderforestKey
    };
    return {
      'Open Cycle Map': L.tileLayer('https://tile.thunderforest.com/cycle/{z}/{x}/{y}.png?apikey={apikey}', thunderforest),
      'Landscape': L.tileLayer('https://tile.thunderforest.com/landscape/{z}/{x}/{y}.png?apikey={apikey}', thunderforest)
    };
  }
  return {
    'OpenStreetMap': L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    })
  };
};

// Gives an event map its base layers and the control to choose one. Google's
// road map is the default once its API loads; if it cannot load, or Google
// refuses the key on this domain, the first tile layer stands in.
L.Google.addBaseLayers = function(map, thunderforestKey) {
  var layers = L.Google.tileLayers(thunderforestKey),
      names = Object.keys(layers),
      fallback = layers[names[0]],
      control = L.control.layers(layers).addTo(map),
      googleLayer = null,
      refused = false;

  function useFallback() {
    if (googleLayer) {
      map.removeLayer(googleLayer);
      control.removeLayer(googleLayer);
      googleLayer = null;
    }
    map.addLayer(fallback);
  }

  // Google calls this when the key is not allowed on this domain, and draws
  // an error in place of the map.
  window.gm_authFailure = function() {
    refused = true;
    useFallback();
  };

  L.Google.load().then(function(loaded) {
    var chosen = names.some(function(name) { return map.hasLayer(layers[name]); });
    if (chosen) {
      return;
    }
    if (!loaded || refused) {
      useFallback();
      return;
    }
    googleLayer = new L.Google('ROADMAP');
    control.addBaseLayer(googleLayer, 'Google Maps');
    map.addLayer(googleLayer);
  });
  return control;
};
