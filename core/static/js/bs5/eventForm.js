// The event form's page script (BS5-12): forms/event.html, marked
// data-mw-event-form. Ported from js/eventForm.js and the form's inline
// script without jQuery. The parts are in eventFormClasses.js:
// - the time zone list and the start and finish (EventDates);
// - the location: "Enter a location" or to be decided, the location search
//   (Show on map) and the map (EventFormMap);
// - the RSVP limit.
// The people invited are peopleWidget.js's, wired when it is imported.
// The first comment's box and the check before posting are the comment
// box's (simpleEditor.js initEditors).

import { initEditors } from './simpleEditor.js';
import {
  EventDates, EventFormMap, attendeeLimit, fillTimeZones, geocode,
} from './eventFormClasses.js';
import './peopleWidget.js';

// "Enter a location" or to be decided. To be decided hides the location and
// the map and clears them, as before.
function wherePart(fieldset, map) {
  const panel = fieldset.querySelector('[data-mw-where]');
  const where = fieldset.querySelector('textarea');
  const status = fieldset.querySelector('[data-mw-locate-status]');

  fieldset.addEventListener('change', (event) => {
    if (event.target.name !== 'location-type') return;
    const decided = event.target.value === '1';
    panel.hidden = !decided;
    if (decided) {
      map?.map.invalidateSize();
    } else {
      where.value = '';
      status.textContent = '';
      map?.reset();
    }
  });

  fieldset.querySelector('#locate').addEventListener('click', async () => {
    const query = where.value.replace(/\s+/g, ' ').trim();
    if (!query || !map) return;
    status.textContent = 'Searching...';
    const place = await geocode(query);
    if (place) {
      map.showPlace(place);
      status.textContent = '';
    } else {
      status.textContent = 'That place was not found. Click the map to place the pin.';
    }
  });
}

const form = document.querySelector('[data-mw-event-form]');
if (form) {
  fillTimeZones(form.querySelector('[data-mw-tz]'));
  new EventDates(form.querySelector('[data-mw-event-dates]'), form);
  const mapEl = form.querySelector('[data-mw-event-form-map]');
  const map = mapEl && window.L ? new EventFormMap(mapEl, form) : null;
  wherePart(form.querySelector('[data-mw-event-place]'), map);
  attendeeLimit(form.querySelector('[data-mw-rsvp-limit]'));
  form.dataset.mwReady = '';
}
initEditors();
