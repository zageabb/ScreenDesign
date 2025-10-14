
// Client-side renderer with layout modes: one, two, table + group 'repeatable-table' + computed fields

document.addEventListener('DOMContentLoaded', () => {
  if (!window.__SCHEMA__) return;
  const schema = window.__SCHEMA__;
  const data = Object.assign({}, window.__DEFAULTS__ || {});
  const form = document.getElementById('dynForm');
  const holder = document.getElementById('formFields');
  const tableHolder = document.getElementById('formTableHolder');

  const layout = (schema.ui && schema.ui.layout) || 'one';
  function evalCompute(expr, ctx){
    try{
      // VERY minimal and unsafe if altered; here we only allow arithmetic and names from ctx
      // You should mirror server-side safety. This is UX only; server re-computes authoritative values.
      const allowed = Object.keys(ctx).reduce((acc,k)=>{acc[k]=ctx[k];return acc;},{});
      const fn = new Function(...Object.keys(allowed), `return (${expr});`);
      return fn(...Object.values(allowed));
    }catch(e){ return null; }
  }


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

  function buildInput(f, rowObj, onRowChange){
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
    const name = rowObj ? f.name : f.name;
    input.name = rowObj ? name : f.name;
    const value = rowObj ? (rowObj[name] ?? "") : (data[name] ?? "");
    if (input.type === 'checkbox') input.checked = !!value; else input.value = value;
    if (f.ui && f.ui.placeholder) input.placeholder = f.ui.placeholder;
    input.style.width = '360px'; input.style.maxWidth = '100%'; input.style.padding = '8px';
    if (onRowChange){
      input.addEventListener('input', () => {
        onRowChange(f.name, input.type === 'checkbox' ? input.checked : input.value);
            recalcRow(field, rows[idx]);
            renderBody();
      });
    }
    return input;
  }

  
  function renderRepeatableTable(field){
    function recalcRow(field, row){
      // compute any subfields with 'compute'
      (field.fields || []).forEach(sf => {
        if (sf.compute){
          const val = evalCompute(sf.compute, row);
          if (val !== null && val !== undefined){
            row[sf.name] = val;
          }
        }
      });
    }

    const wrap = document.createElement('div');
    wrap.className = 'card card-body shadow-sm mb-3';
    wrap.dataset.field = field.name;

    const title = document.createElement('h3');
    title.textContent = field.label || field.name;
    title.className = 'h5 mb-3';
    wrap.appendChild(title);

    const tbl = document.createElement('table');
    tbl.className = 'table table-bordered align-middle';
    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    field.fields.forEach(sf => {
      const th = document.createElement('th');
      th.textContent = sf.label || sf.name;
      trh.appendChild(th);
    });
    const thAct = document.createElement('th'); thAct.textContent = 'Actions';
    trh.appendChild(thAct);
    thead.appendChild(trh);
    const tbody = document.createElement('tbody');

    tbl.appendChild(thead); tbl.appendChild(tbody);
    const responsive = document.createElement('div');
    responsive.className = 'table-responsive';
    responsive.appendChild(tbl);
    wrap.appendChild(responsive);

    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'btn btn-primary mt-3';
    addBtn.textContent = 'Add Row';
    wrap.appendChild(addBtn);

    if (!Array.isArray(data[field.name])) data[field.name] = [];
    const rows = data[field.name];

    function renderBody(){
      tbody.innerHTML = '';
      rows.forEach((row, idx) => {
        const tr = document.createElement('tr');
        field.fields.forEach(sf => {
          const td = document.createElement('td');
          const input = buildInput(sf, row, (key, val) => {
            rows[idx][key] = val;
          });
          input.style.width = '100%';
          td.appendChild(input);
          tr.appendChild(td);
        });
        const tdAct = document.createElement('td');
        const del = document.createElement('button');
        del.type = 'button';
        del.className = 'btn btn-outline-danger btn-sm';
        del.textContent = 'Delete';
        del.addEventListener('click', () => {
          rows.splice(idx, 1);
          renderBody();
        });
        tdAct.appendChild(del);
        tr.appendChild(tdAct);
        tbody.appendChild(tr);
      });
    }

    addBtn.addEventListener('click', () => {
      const newRow = {};
      field.fields.forEach(sf => { newRow[sf.name] = sf.default ?? (sf.type === 'number' ? 0 : ""); });
      rows.push(newRow);
      recalcRow(field, newRow);
      renderBody();
    });

    renderBody();
    holder.appendChild(wrap);
    return wrap;
  }

  function renderField(f){
    if (f.type === 'group' && f.mode === 'repeatable-table'){
      return renderRepeatableTable(f);
    }

    if (layout === 'table'){
      if (!tableHolder.__table){
        const tbl = document.createElement('table');
        tbl.className = 'table table-bordered align-middle';
        const thead = document.createElement('thead');
        const trh = document.createElement('tr');
        const th1 = document.createElement('th'); th1.textContent = 'Field';
        const th2 = document.createElement('th'); th2.textContent = 'Value';
        trh.appendChild(th1); trh.appendChild(th2);
        thead.appendChild(trh);
        const tbody = document.createElement('tbody');
        tbl.appendChild(thead); tbl.appendChild(tbody);
        const responsive = document.createElement('div');
        responsive.className = 'table-responsive';
        responsive.appendChild(tbl);
        tableHolder.appendChild(responsive);
        tableHolder.__table = tbl;
      }
      const input = buildInput(f);
      const row = kvRow(f.label || f.name, input);
      tableHolder.__table.querySelector('tbody').appendChild(row);
      return;
    }

    const wrap = document.createElement('div');
    wrap.style.minWidth = '280px';
    wrap.dataset.field = f.name;
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
    return wrap;
  }

  (schema.fields || []).forEach(renderField);

  async function refreshRules(){
    try{
      const payload = Object.assign({}, data);
      const res = await fetch(`/rules/${schema.slug}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      const rules = await res.json();
      (schema.fields || []).forEach(f => {
        let node = holder.querySelector(`[data-field="${f.name}"]`) || holder.querySelector(`[name="${f.name}"]`) || tableHolder.querySelector(`[name="${f.name}"]`);
        if (!node) return;
        let wrap = node.closest('div') || node.closest('tr') || node;
        if (rules.hide && rules.hide.includes(f.name)) wrap.style.display = 'none';
        else wrap.style.display = '';
        const locked = !!(rules.lock && rules.lock.includes(f.name));
        if (locked){
          wrap.querySelectorAll('input,select,textarea,button').forEach(el => el.disabled = true);
        }
      });
    }catch(e){ console.warn('Rule refresh failed', e); }
  }

  const onInput = (ev) => {
    const t = ev.target;
    if (!t.name) return;
    const isInGroup = !!t.closest('[data-field]') && schema.fields.find(f => f.name === t.closest('[data-field]').dataset.field && f.type === 'group');
    if (!isInGroup){
      data[t.name] = t.type === 'checkbox' ? t.checked : t.value;
      refreshRules();
    }
  };
  holder.addEventListener('input', onInput);
  tableHolder.addEventListener('input', onInput);

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const payload = {};
    (schema.fields || []).forEach(f => {
      if (f.type === 'group' && f.mode === 'repeatable-table'){
        payload[f.name] = data[f.name] || [];
      } else {
        const el = form.querySelector(`[name="${f.name}"]`);
        if (el){
          payload[f.name] = (el.type === 'checkbox') ? el.checked : el.value;
        }
      }
    });
    const res = await fetch(window.__SAVE_URL__, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if (res.ok){
      const result = await res.json();
      if (result.redirect){
        window.location.href = result.redirect;
      } else {
        alert('Saved');
        window.location.reload();
      }
    } else {
      alert('Save error');
    }
  });

  refreshRules();
});
