// Minimal client-side renderer for JSON fields + live rules
document.addEventListener('DOMContentLoaded', () => {
  if (!window.__SCHEMA__) return;
  const schema = window.__SCHEMA__;
  const data = Object.assign({}, window.__DEFAULTS__ || {});
  const form = document.getElementById('dynForm');
  const holder = document.getElementById('formFields');

  function renderField(f){
    const wrap = document.createElement('div');
    wrap.style.minWidth = '280px';
    if (f.ui && f.ui.header){
      const h = document.createElement('h3');
      h.textContent = f.ui.header;
      h.style.margin = '16px 0 8px';
      holder.appendChild(h);
    }
    const label = document.createElement('label');
    label.textContent = f.label || f.name;
    wrap.appendChild(label);
    let input;
    switch(f.type){
      case 'textarea':
        input = document.createElement('textarea');
        if (f.ui && f.ui.rows) input.rows = f.ui.rows;
        break;
      case 'select':
        input = document.createElement('select');
        (f.options || []).forEach(opt => {
          const o = document.createElement('option');
          o.value = typeof opt === 'string' ? opt : opt.value;
          o.textContent = typeof opt === 'string' ? opt : (opt.label || opt.value);
          input.appendChild(o);
        });
        break;
      case 'checkbox':
        input = document.createElement('input'); input.type = 'checkbox';
        break;
      case 'number':
        input = document.createElement('input'); input.type = 'number';
        break;
      case 'date':
        input = document.createElement('input'); input.type = 'date';
        break;
      default:
        input = document.createElement('input'); input.type = 'text';
    }
    input.name = f.name;
    if (data[f.name] != null){
      if (input.type === 'checkbox') input.checked = !!data[f.name];
      else input.value = data[f.name];
    }
    if (f.ui && f.ui.placeholder) input.placeholder = f.ui.placeholder;
    wrap.appendChild(input);
    holder.appendChild(wrap);
  }

  // initial render
  (schema.fields || []).forEach(renderField);

  async function refreshRules(){
    try{
      const payload = Object.assign({}, data);
      const res = await fetch(`/rules/${schema.slug}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      const rules = await res.json();
      // show/hide
      (schema.fields || []).forEach(f => {
        const fieldWrap = [...holder.children].find(el => el.querySelector(`[name="${f.name}"]`));
        if (!fieldWrap) return;
        if (rules.hide && rules.hide.includes(f.name)) fieldWrap.style.display = 'none';
        else fieldWrap.style.display = '';
        const input = fieldWrap.querySelector(`[name="${f.name}"]`);
        if (!input) return;
        const locked = rules.lock && rules.lock.includes(f.name);
        input.disabled = !!locked;
        // show implies display but not required changes here
      });
    }catch(e){ console.warn('Rule refresh failed', e); }
  }

  holder.addEventListener('input', (ev) => {
    const t = ev.target;
    if (!t.name) return;
    data[t.name] = t.type === 'checkbox' ? t.checked : t.value;
    refreshRules();
  });

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const payload = {};
    (schema.fields || []).forEach(f => {
      const el = form.querySelector(`[name="${f.name}"]`);
      if (!el) return;
      payload[f.name] = (el.type === 'checkbox') ? el.checked : el.value;
    });
    const res = await fetch(window.__SAVE_URL__, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if (res.ok){
      alert('Saved');
      window.location.reload();
    } else {
      alert('Save error');
    }
  });

  refreshRules();
});
