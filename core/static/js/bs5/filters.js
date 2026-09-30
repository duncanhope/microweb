// A list's filters in the metabar (BS5-09): a GET form marked data-mw-filters,
// on the people list (profiles.html), and on Today and search (BS5-10).
// Ported from js/filters.js without jQuery. Any change loads the list again
// with the form's values, empty ones left out, so the URL carries the
// filters: ?online=true&top=true.
// Without scripts the form's own button does the same, empty values and all.

export function filterUrl(form) {
  const url = new URL(form.action, location.href);
  const params = new URLSearchParams();
  for (const [name, value] of new FormData(form)) {
    if (typeof value === 'string' && value.trim()) params.append(name, value.trim());
  }
  url.search = params.toString();
  return url.href;
}

for (const form of document.querySelectorAll('form[data-mw-filters]')) {
  const go = (event) => {
    event.preventDefault();
    location.assign(filterUrl(form));
  };
  form.addEventListener('change', go);
  form.addEventListener('submit', go);
}
