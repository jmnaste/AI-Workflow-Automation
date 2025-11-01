async function call(path, opts={}) {
  const out = document.getElementById('out');
  out.textContent = 'Loading…';
  try {
    const res = await fetch(path, { headers: { 'Accept': 'application/json', ...(opts.headers||{}) } });
    const text = await res.text();
    out.textContent = text;
  } catch (e) {
    out.textContent = 'Error: ' + e.message;
  }
}

document.getElementById('btn-health').addEventListener('click', () => call('/api/health'));
