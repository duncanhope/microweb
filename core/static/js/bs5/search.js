// The search page (BS5-10). Its options are a GET form marked data-mw-filters,
// which filters.js reloads on every change. A new search typed into the
// navbar keeps those options, as js/filters.js's formSubmit did, so title
// matching and the sort order carry over to the new words.

import { filterUrl } from './filters.js';

const options = document.querySelector('form[data-mw-filters]');
const navbar = document.getElementById('navbar-search-input')?.form;

if (options && navbar) {
  navbar.addEventListener('submit', (event) => {
    const words = navbar.elements.q.value.trim();
    if (!words) return;
    event.preventDefault();
    options.elements.q.value = words;
    location.assign(filterUrl(options));
  });
}
