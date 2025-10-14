// Client-side renderer with layout modes: one, two, table
document.addEventListener('DOMContentLoaded', () => {
  if (!window.__SCHEMA__) return;
  const schema = window.__SCHEMA__;
  const data = Object.assign({}, window.__DEFAULTS__ || {});
  const form = document.getElementById('dynForm');
  const holder = document.getElementById('formFields');
  const tableHolder = document.getElementById('formTableHolder');

  const layout = (schema.ui && schema.ui.layout) || 'one';

  // Apply container styling based on layout
  if (layout === 'two'){
    holder.style.display = 'grid';
    holder.style.gridTemplateColumns = '1fr 1fr';
    holder.style.gap = '20px 24px';
  } else if (layout === 'one'){
    holder.style.display = 'block';
  } else if (layout === 'table'){
    holder.style.display = 'none';
    tableHolder.style.display = 'block';
  }

  function kvRow(labelText, inputEl){
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = labelText;
    const td = document.createElement('td');
    td.appendChild(inputEl);
    tr.appendChild(th);
    tr.appendChild(td);
    return tr;
  }

  function renderField(f){
    // Table layout: use label/value rows
    if (layout === 'table'){
      if (!tableHolder.__table){
        const tbl = document.createElement('table');
        tbl.style.borderCollapse = 'collapse';
        tbl.style.width = '100%';
        const thead = document.createElement('thead');
        const trh = document.createElement('tr');
        const th1 = document.createElement('th'); th1.textContent = 'Field'; 
        const th2 = document.createElement('th'); th2.textContent = 'Value';
        trh.appendChild(th1); trh.appendChild(th2);
        thead.appendChild(trh);
        const tbody = document.createElement('tbody');
        tbl.appendChild(thead); tbl.appendChild(tbody);
        tableHolder.appendChild(tbl);
        tableHolder.__table = tbl;
      }
      const input = buildInput(f);
      const row = kvRow(f.label || f.name, input);
      tableHolder.__table.querySelector('tbody').appendChild(row);
      return;
    }

    // One/two column cards
    const wrap = document.createElement('div');
    wrap.style.minWidth = '280px';
    if (layout === 'two'){
      const span = (f.ui && Number(f.ui.colSpan)) || 1;
      wrap.style.gridColumn = `span ${Math.min(Math.max(span,1),2)}`;
    }

    if (f.ui && f.ui.header){
      const h = document.createElement('h3');
      h.textContent = f.ui.header;
      h.style.margin = '8px 0 4px';
      h.style.gridColumn = layout === 'two' ? '1 / -1' : '';
      holder.appendChild(h);
    }

    const label = document.createElement('label');
    label.textContent = f.label || f.name;
    wrap.appendChild(label);

    const input = buildInput(f);
    wrap.appendChild(input);
    holder.appendChild(wrap);
  }

  function buildInput(f){
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
    input.style.width = '360px'; input.style.maxWidth = '100%'; input.style.padding = '8px';
    return input;
  }

  // initial render
  (schema.fields || []).forEach(renderField);

  async function refreshRules(){
    try{
      const payload = Object.assign({}, data);
      const res = await fetch(`/rules/${schema.slug}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      const rules = await res.json();
      // show/hide, lock
      (schema.fields || []).forEach(f => {
        const selector = `[name="${f.name}"]`;
        let node = holder.querySelector(selector) || tableHolder.querySelector(selector);
        if (!node) return;
        let wrap = node.closest('div') || node.closest('tr') || node;
        if (rules.hide && rules.hide.includes(f.name)) wrap.style.display = 'none';
        else wrap.style.display = '';
        node.disabled = !!(rules.lock && rules.lock.includes(f.name));
      });
    }catch(e){ console.warn('Rule refresh failed', e); }
  }

  const onInput = (ev) => {
    const t = ev.target;
    if (!t.name) return;
    data[t.name] = t.type === 'checkbox' ? t.checked : t.value;
    refreshRules();
  };
  holder.addEventListener('input', onInput);
  tableHolder.addEventListener('input', onInput);

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
