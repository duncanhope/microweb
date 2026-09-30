// The parts of the event form (BS5-12), ported from js/eventFormClasses.js,
// js/peopleWidget.js and the form's inline script without jQuery, Moment,
// moment-timezone, jsTimezoneDetect or the datepicker. eventForm.js puts
// them together on forms/event.html.
//
// The form posts what it posted on Bootstrap 3, which core/forms/forms.py
// parses unchanged:
// - when: the event's wall-clock start with a Z, "2026-10-10T19:00:00Z",
//   whatever the browser's own time zone; tz says where that clock is.
// - duration: minutes from the start to the finish, an hour when the finish
//   is not after the start (as before).
// - lat, lon, and the map's north, east, south and west when the pin was
//   placed.
// - invite: the invited profile ids, comma separated; inviteObject: the same
//   people as JSON, so the form shows them again after an error.

import { addBaseLayers } from './eventMap.js';
import { ProfileSearch } from './mentions.js';

const { L } = window;

// ---------------------------------------------------------------------------
// When: native date and time inputs

const DATE_TYPE = { TBD: '0', SINGLE: '1', MULTIPLE: '2' };
const MINUTE = 60000;
const QUARTER_HOUR = 15 * MINUTE;

// Wall clocks are kept as UTC milliseconds, so arithmetic on them never
// meets a summer-time change in the browser's own zone.
export function composeWhen(date, time) {
  return `${date}T${time.slice(0, 5)}:00Z`;
}

function splitWhen(ms) {
  const iso = new Date(ms).toISOString();
  return { date: iso.slice(0, 10), time: iso.slice(11, 16) };
}

// The browser's wall clock now, rounded up to the quarter hour: a new event's start.
function nextQuarterHour(now = new Date()) {
  const wall = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes());
  return Math.ceil(wall / QUARTER_HOUR) * QUARTER_HOUR;
}

function durationMinutes(start, end) {
  const minutes = Math.round((end - start) / MINUTE);
  return minutes > 0 ? minutes : 60;
}

// The date type radios (single day, multiple days, to be decided), the start
// and finish, and the hidden when and duration they fill.
export class EventDates {
  constructor(fieldset, form) {
    this.radios = [...fieldset.querySelectorAll('input[name=date-type]')];
    this.panel = fieldset.querySelector('[data-mw-when]');
    this.startDate = fieldset.querySelector('#mw-event-start-date');
    this.startTime = fieldset.querySelector('#mw-event-start-time');
    this.endDate = fieldset.querySelector('#mw-event-end-date');
    this.endTime = fieldset.querySelector('#mw-event-end-time');
    this.when = form.elements.namedItem('when');
    this.duration = form.elements.namedItem('duration');

    const start = Date.parse(this.when.value);
    let type = DATE_TYPE.SINGLE;
    if (Number.isNaN(start)) {
      // An event saved without a date stays to be decided.
      if (form.hasAttribute('data-edit')) type = DATE_TYPE.TBD;
      const begin = nextQuarterHour();
      this.set(begin, begin + 60 * MINUTE);
    } else {
      const end = start + (parseInt(this.duration.value, 10) || 60) * MINUTE;
      this.set(start, end);
      if (this.endDate.value !== this.startDate.value) type = DATE_TYPE.MULTIPLE;
    }
    this.radios.find((radio) => radio.value === type).checked = true;
    this.show();

    fieldset.addEventListener('change', (event) => {
      if (event.target.name === 'date-type') this.show();
    });
    this.panel.addEventListener('input', () => this.update());
  }

  get type() {
    return this.radios.find((radio) => radio.checked)?.value ?? DATE_TYPE.SINGLE;
  }

  set(start, end) {
    ({ date: this.startDate.value, time: this.startTime.value } = splitWhen(start));
    ({ date: this.endDate.value, time: this.endTime.value } = splitWhen(end));
  }

  // To be decided hides the dates, and they are neither checked nor sent.
  // The time zone stays: the form needs one either way.
  show() {
    const { type } = this;
    this.panel.hidden = type === DATE_TYPE.TBD;
    for (const input of [this.startDate, this.startTime, this.endTime]) input.disabled = type === DATE_TYPE.TBD;
    this.endDate.hidden = this.endDate.disabled = type !== DATE_TYPE.MULTIPLE;
    this.update();
  }

  update() {
    const { type } = this;
    if (type === DATE_TYPE.SINGLE) this.endDate.value = this.startDate.value;
    this.endDate.min = this.startDate.value;
    const values = [this.startDate, this.startTime, this.endDate, this.endTime].map((input) => input.value);
    if (type === DATE_TYPE.TBD || values.some((value) => !value)) {
      this.when.value = this.duration.value = '';
      return;
    }
    const [startDate, startTime, endDate, endTime] = values;
    this.when.value = composeWhen(startDate, startTime);
    this.duration.value = durationMinutes(Date.parse(this.when.value), Date.parse(composeWhen(endDate, endTime)));
  }
}

// ---------------------------------------------------------------------------
// The time zone list, from Intl

// "+05:30" for a zone at a moment; "" for a name Intl does not know.
function utcOffset(zone, at = new Date()) {
  try {
    const name = new Intl.DateTimeFormat('en-US', { timeZone: zone, timeZoneName: 'longOffset' })
      .formatToParts(at).find((part) => part.type === 'timeZoneName').value;
    return name === 'GMT' ? '+00:00' : name.slice(3);
  } catch {
    return '';
  }
}

const offsetMinutes = (offset) => (offset ? (offset[0] === '-' ? -1 : 1) * (Number(offset.slice(1, 3)) * 60 + Number(offset.slice(4))) : 0);

// Every zone the browser knows, plus any in extra, west to east, as the
// Bootstrap 3 list was: [{ name, offset }].
function timeZones(extra = [], at = new Date()) {
  const names = new Set([...Intl.supportedValuesOf('timeZone'), ...extra.filter(Boolean)]);
  return [...names]
    .map((name) => ({ name, offset: utcOffset(name, at) }))
    .sort((a, b) => offsetMinutes(a.offset) - offsetMinutes(b.offset) || a.name.localeCompare(b.name));
}

function browserTimeZone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// Fill the select, choosing the zone it came with (an edit, or a form sent
// back with errors), or else the browser's own.
export function fillTimeZones(select) {
  const chosen = select.value || browserTimeZone();
  select.replaceChildren(...timeZones([chosen]).map(({ name, offset }) =>
    new Option(offset ? `(GMT ${offset}) ${name}` : name, name)));
  select.value = chosen;
}

// ---------------------------------------------------------------------------
// Where: the map and the location search

const WORLD = [[75.8451685402704, -121.640625], [-48.9224992637582, 153.984375]];
const PLACE_FIELDS = ['lat', 'lon', 'north', 'east', 'south', 'west'];

// The map: click it to place the pin. Its hidden fields are lat and lon for
// the pin, and the map's bounds (kept when the map is dragged) for north,
// east, south and west. The Leaflet map is kept on the element as el.mwMap.
export class EventFormMap {
  constructor(el, form) {
    this.form = form;
    this.marker = null;
    this.map = L.map(el, { zoomAnimation: false }).setMaxBounds([[-90, -180], [90, 180]]);
    el.mwMap = this.map;

    const [lat, lon, north, east, south, west] = PLACE_FIELDS.map((name) => {
      const value = form.elements.namedItem(name).value;
      return value === '' ? NaN : Number(value);
    });
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      this.map.fitBounds(WORLD);
    } else {
      if ([north, east, south, west].some(Number.isNaN)) {
        this.map.setView([lat, lon], 15);
      } else {
        this.map.fitBounds([[north, west], [south, east]]);
        // fitBounds lands one level too far out; without this every edit zooms out.
        this.map.zoomIn();
      }
      this.pin(L.latLng(lat, lon));
    }
    addBaseLayers(this.map, el.dataset.thunderforestKey);

    this.map.on('click', (event) => this.drop(event.latlng));
    this.map.on('dragend', () => this.saveBounds());
  }

  pin(latlng) {
    if (this.marker) this.marker.setLatLng(latlng);
    else this.marker = L.marker(latlng).addTo(this.map);
  }

  drop(latlng) {
    this.pin(latlng);
    this.save({ lat: latlng.lat, lon: latlng.lng });
    this.saveBounds();
  }

  // A place from the location search: fit its box and drop the pin.
  showPlace(place) {
    const [south, north, west, east] = place.boundingbox.map(Number);
    this.map.fitBounds([[south, west], [north, east]]);
    this.drop(L.latLng(Number(place.lat), Number(place.lon)));
  }

  saveBounds() {
    const bounds = this.map.getBounds();
    this.save({ north: bounds.getNorth(), east: bounds.getEast(), south: bounds.getSouth(), west: bounds.getWest() });
  }

  save(values) {
    for (const [name, value] of Object.entries(values)) this.form.elements.namedItem(name).value = value;
  }

  reset() {
    this.save(Object.fromEntries(PLACE_FIELDS.map((name) => [name, ''])));
    if (this.marker) this.map.removeLayer(this.marker);
    this.marker = null;
  }
}

// The location search: the Site's /geocode/ (events/views.py geocode), which
// passes the query to the API's geocoder. The place it finds, with lat, lon
// and boundingbox ([south, north, west, east]), or null.
export async function geocode(query) {
  try {
    const response = await fetch('/geocode/?q=' + encodeURIComponent(query), { credentials: 'same-origin' });
    if (!response.ok) return null;
    const data = await response.json();
    const place = Array.isArray(data) ? data[0] : data;
    return place?.place_id && place.boundingbox ? place : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// The RSVP limit: the number is sent only when "Max number" is chosen.

export function attendeeLimit(fieldset) {
  const field = fieldset.querySelector('input[type=number]');
  const apply = (focus) => {
    const limited = fieldset.querySelector('input[name=attendee-limit-option][value="1"]').checked;
    field.disabled = !limited;
    field.required = limited;
    if (!limited) {
      field.value = 0;
      field.classList.remove('is-invalid');
    } else if (focus) {
      if (field.value === '0') field.value = '';
      field.focus();
    }
  };
  apply(false);
  fieldset.addEventListener('change', (event) => {
    if (event.target.name === 'attendee-limit-option') apply(true);
  });
}

// ---------------------------------------------------------------------------
// Invite people: a combobox of members, and the people chosen

const DEBOUNCE_MS = 150;

// A person as the form keeps them: { id, profileName, avatar, sticky }. The
// edit form's people are sticky: they have an RSVP already, and stay.
function readPeople(json) {
  try {
    const people = JSON.parse(json || '[]');
    return Array.isArray(people) ? people.filter((person) => person && person.id) : [];
  } catch {
    return [];
  }
}

export class InvitePeople {
  constructor(root, { apiBase = '' } = {}) {
    this.apiBase = apiBase;
    this.searches = new ProfileSearch(apiBase);
    this.input = root.querySelector('input[type=text]');
    this.chosen = root.querySelector('.mw-event-form-invited');
    this.ids = root.querySelector('input[name=invite]');
    this.json = root.querySelector('input[name=inviteObject]');
    this.people = readPeople(root.dataset.mwInvited);
    this.results = [];
    this.active = -1;

    const id = this.input.id + '-results';
    this.list = document.createElement('ul');
    Object.assign(this.list, { id, className: 'dropdown-menu mw-mentions mw-event-form-results' });
    this.list.setAttribute('role', 'listbox');
    this.list.setAttribute('aria-label', 'Members');
    this.status = document.createElement('div');
    this.status.className = 'visually-hidden';
    this.status.setAttribute('role', 'status');
    // After the input group, so the input keeps its rounded corners.
    this.input.parentElement.after(this.list, this.status);
    this.input.setAttribute('role', 'combobox');
    this.input.setAttribute('aria-autocomplete', 'list');
    this.input.setAttribute('aria-expanded', 'false');
    this.input.setAttribute('aria-controls', id);

    this.input.addEventListener('input', () => {
      clearTimeout(this.timer);
      this.timer = setTimeout(() => this.search(), DEBOUNCE_MS);
    });
    this.input.addEventListener('keydown', (event) => this.onKeydown(event));
    this.input.addEventListener('blur', () => this.close());
    // Keep focus in the box while the pointer picks a member.
    this.list.addEventListener('mousedown', (event) => event.preventDefault());
    this.list.addEventListener('click', (event) => {
      const option = event.target.closest('[role=option]');
      if (option) this.add(Number(option.dataset.index));
    });
    this.chosen.addEventListener('click', (event) => {
      const button = event.target.closest('[data-mw-uninvite]');
      if (button) this.remove(Number(button.dataset.mwUninvite));
    });
    this.render();
  }

  get isOpen() {
    return this.list.classList.contains('show');
  }

  async search() {
    const term = this.input.value.trim();
    if (!term) {
      this.close();
      return;
    }
    let found;
    try {
      found = await this.searches.search(term);
    } catch {
      this.hide();
      return;
    }
    if (!found) return;
    const invited = new Set(this.people.map((person) => person.id));
    this.results = found.filter((profile) => !invited.has(profile.id));
    this.open(term);
  }

  avatar(person) {
    const img = document.createElement('img');
    img.alt = '';
    img.width = img.height = 20;
    img.src = new URL(person.avatar || '/static/img/avatar.gif', this.apiBase || location.href).href;
    return img;
  }

  open(term) {
    if (!this.results.length) {
      const empty = document.createElement('li');
      empty.className = 'dropdown-item-text';
      empty.textContent = 'No results';
      this.list.replaceChildren(empty);
      this.status.textContent = `No members found for ${term}`;
    } else {
      this.list.replaceChildren(...this.results.map((profile, index) => {
        const option = document.createElement('li');
        option.id = `${this.list.id}-${index}`;
        option.className = 'dropdown-item';
        option.dataset.index = String(index);
        option.setAttribute('role', 'option');
        option.append(this.avatar(profile), document.createTextNode(profile.profileName));
        return option;
      }));
      this.status.textContent = `${this.results.length} member${this.results.length === 1 ? '' : 's'} found, use up and down to choose`;
    }
    this.list.classList.add('show');
    this.input.setAttribute('aria-expanded', 'true');
    this.setActive(this.results.length ? 0 : -1);
  }

  // Stop any search, and hide the list.
  close() {
    clearTimeout(this.timer);
    this.searches.cancel();
    this.hide();
  }

  // Hide the list only: a search typed since may still be on its way.
  hide() {
    this.list.classList.remove('show');
    this.list.replaceChildren();
    this.input.setAttribute('aria-expanded', 'false');
    this.input.removeAttribute('aria-activedescendant');
    this.results = [];
    this.active = -1;
  }

  setActive(index) {
    const options = [...this.list.querySelectorAll('[role=option]')];
    if (!options.length) {
      this.active = -1;
      return;
    }
    this.active = (index + options.length) % options.length;
    for (const [i, option] of options.entries()) {
      option.classList.toggle('active', i === this.active);
      option.setAttribute('aria-selected', String(i === this.active));
    }
    this.input.setAttribute('aria-activedescendant', options[this.active].id);
  }

  onKeydown(event) {
    if (event.isComposing) return;
    // Enter never sends the form from here: it picks a member or does nothing.
    if (event.key === 'Enter') event.preventDefault();
    if (!this.isOpen) return;
    switch (event.key) {
      case 'ArrowDown':
        this.setActive(this.active + 1);
        break;
      case 'ArrowUp':
        this.setActive(this.active - 1);
        break;
      case 'Enter':
        if (this.active > -1) this.add(this.active);
        break;
      case 'Escape':
        this.close();
        break;
      default:
        return;
    }
    event.preventDefault();
  }

  add(index) {
    const profile = this.results[index];
    if (!profile) return;
    this.people.push({ id: profile.id, profileName: profile.profileName, avatar: profile.avatar || '' });
    this.input.value = '';
    this.close();
    this.render();
    this.status.textContent = `${profile.profileName} invited`;
  }

  remove(id) {
    const person = this.people.find((p) => p.id === id);
    if (!person || person.sticky) return;
    this.people = this.people.filter((p) => p !== person);
    this.render();
    this.status.textContent = `${person.profileName} removed`;
    this.input.focus();
  }

  render() {
    this.chosen.replaceChildren(...this.people.map((person) => {
      const item = document.createElement('li');
      item.className = 'mw-event-form-person';
      item.append(this.avatar(person), document.createTextNode(person.profileName));
      if (!person.sticky) {
        const button = document.createElement('button');
        Object.assign(button, { type: 'button', className: 'btn-close' });
        button.dataset.mwUninvite = String(person.id);
        button.setAttribute('aria-label', `Remove ${person.profileName}`);
        item.append(button);
      }
      return item;
    }));
    this.chosen.hidden = !this.people.length;
    this.ids.value = this.people.map((person) => person.id).join(',');
    this.json.value = this.people.length ? JSON.stringify(this.people) : '';
  }
}
