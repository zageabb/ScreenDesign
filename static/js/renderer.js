
// Client-side renderer with layout modes: one, two, table + group 'repeatable-table' + computed fields

document.addEventListener('DOMContentLoaded', () => {
  if (!window.__SCHEMA__) return;
  const schema = window.__SCHEMA__;
  const data = Object.assign({}, window.__DEFAULTS__ || {});
  const form = document.getElementById('dynForm');
  const holder = document.getElementById('formFields');
  const tableHolder = document.getElementById('formTableHolder');
  const fieldRegistry = new Map();

  const layout = (schema.ui && schema.ui.layout) || 'one';
  function coerceFieldValue(field, raw){
    if (!field) return raw;
    if (field.type === 'number'){
      if (raw === '' || raw === null || raw === undefined) return null;
      const num = Number(raw);
      return Number.isFinite(num) ? num : null;
    }
    return raw;
  }
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

  const tableFields = [];
  const repeatableTables = [];

  function buildInput(f, rowObj, onRowChange){
    if (f && f.name && !rowObj){
      fieldRegistry.set(f.name, f);
    }
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
    const name = f.name;
    input.name = name;
    const source = rowObj || data;
    const value = source && Object.prototype.hasOwnProperty.call(source, name) ? source[name] : '';
    if (input.type === 'checkbox'){
      input.checked = !!value;
    } else if (value !== undefined && value !== null){
      input.value = value;
    }
    if (f.ui && f.ui.placeholder) input.placeholder = f.ui.placeholder;
    if (rowObj){
      input.style.width = '100%';
      input.style.maxWidth = '100%';
      input.style.padding = '6px';
    } else {
      input.style.width = '360px';
      input.style.maxWidth = '100%';
      input.style.padding = '8px';
    }
    if (onRowChange){
      input.addEventListener('input', () => {
        const newVal = input.type === 'checkbox' ? input.checked : coerceFieldValue(f, input.value);
        onRowChange(name, newVal);
      });
    }
    return input;
  }

  
  function renderRepeatableTable(field){
    function recalcRow(row){
      (field.fields || []).forEach(sf => {
        if (sf.type === 'number'){
          row[sf.name] = coerceFieldValue(sf, row[sf.name]);
        }
      });
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
        recalcRow(row);
        const tr = document.createElement('tr');
        const rowInputs = {};
        function updateComputedInputs(){
          field.fields.forEach(sf => {
            if (sf.compute && rowInputs[sf.name]){
              const computedVal = rows[idx][sf.name];
              const target = rowInputs[sf.name];
              if (target.type === 'checkbox') target.checked = !!computedVal;
              else target.value = computedVal ?? '';
            }
          });
        }
        field.fields.forEach(sf => {
          const td = document.createElement('td');
          const input = buildInput(sf, row, (key, val) => {
            rows[idx][key] = val;
            recalcRow(rows[idx]);
            updateComputedInputs();
          });
          rowInputs[sf.name] = input;
          td.appendChild(input);
          tr.appendChild(td);
        });
        updateComputedInputs();
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
      recalcRow(newRow);
      renderBody();
    });

    renderBody();
    const container = layout === 'table' ? tableHolder : holder;
    container.appendChild(wrap);
    repeatableTables.push({ field, rows, renderBody });
    return wrap;
  }

  function renderField(f){
    if (f.type === 'group' && f.mode === 'repeatable-table'){
      if (layout === 'table'){
        tableFields.push(f);
        return;
      }
      return renderRepeatableTable(f);
    }

    if (layout === 'table'){
      tableFields.push(f);
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

  function renderTableLayout(fields){
    tableHolder.innerHTML = '';

    const config = (schema.ui && schema.ui.tableLayout) || {};
    const columns = Math.max(1, Number(config.columns) || 1);
    const definedRows = Array.isArray(config.rows) ? config.rows.filter(row => Array.isArray(row)) : [];

    const simpleFields = [];
    const repeatableGroups = [];
    const fieldMap = new Map();

    fields.forEach(f => {
      if (f.type === 'group' && f.mode === 'repeatable-table'){
        repeatableGroups.push(f);
      } else {
        simpleFields.push(f);
        fieldMap.set(f.name, f);
      }
    });

    const table = document.createElement('table');
    table.className = 'table table-bordered align-middle form-table-layout';
    const tbody = document.createElement('tbody');
    table.appendChild(tbody);
    const responsive = document.createElement('div');
    responsive.className = 'table-responsive';
    responsive.appendChild(table);
    tableHolder.appendChild(responsive);
    tableHolder.__table = table;

    function appendRow(rowFields){
      if (!rowFields.length) return;
      const tr = document.createElement('tr');
      let remaining = columns;
      rowFields.forEach(field => {
        if (!field || remaining <= 0) return;
        let span = Math.max(1, Math.min(columns, Number(field.ui && field.ui.tableSpan) || Number(field.ui && field.ui.colSpan) || 1));
        if (span > remaining) span = remaining;
        const td = document.createElement('td');
        td.className = 'form-table-cell';
        if (span > 1) td.colSpan = span;
        const label = document.createElement('label');
        label.className = 'form-label';
        label.textContent = field.label || field.name;
        td.appendChild(label);
        const input = buildInput(field);
        input.style.width = '100%';
        input.style.maxWidth = '100%';
        input.style.boxSizing = 'border-box';
        td.appendChild(input);
        tr.appendChild(td);
        remaining -= span;
      });

      while (remaining > 0){
        const td = document.createElement('td');
        td.className = 'form-table-cell empty';
        tr.appendChild(td);
        remaining--;
      }

      tbody.appendChild(tr);
    }

    const used = new Set();

    definedRows.forEach(row => {
      const resolved = row
        .map(name => (typeof name === 'string' ? fieldMap.get(name) : null))
        .filter(Boolean);
      resolved.forEach(field => used.add(field.name));
      if (resolved.length) appendRow(resolved);
    });

    let pending = [];
    let pendingSpan = 0;

    simpleFields.forEach(field => {
      if (used.has(field.name)) return;
      const span = Math.max(1, Math.min(columns, Number(field.ui && field.ui.tableSpan) || Number(field.ui && field.ui.colSpan) || 1));
      if (pendingSpan + span > columns){
        appendRow(pending);
        pending = [];
        pendingSpan = 0;
      }
      pending.push(field);
      pendingSpan += span;
    });

    if (pending.length){
      appendRow(pending);
    }

    repeatableGroups.forEach(renderRepeatableTable);
  }

  (schema.fields || []).forEach(renderField);

  if (layout === 'table'){
    renderTableLayout(tableFields);
  }

  function collectPayload(){
    const payload = {};
    (schema.fields || []).forEach(f => {
      if (f.type === 'group' && f.mode === 'repeatable-table'){
        const rows = Array.isArray(data[f.name]) ? data[f.name].map(row => ({...row})) : [];
        payload[f.name] = rows;
      } else {
        const el = form.querySelector(`[name="${f.name}"]`);
        if (el){
          const field = fieldRegistry.get(f.name) || f;
          const raw = el.type === 'checkbox' ? el.checked : el.value;
          const value = el.type === 'checkbox' ? raw : coerceFieldValue(field, raw);
          payload[f.name] = value;
          data[f.name] = value;
        } else if (Object.prototype.hasOwnProperty.call(data, f.name)){
          payload[f.name] = data[f.name];
        }
      }
    });
    return payload;
  }

  function applyServerData(serverData){
    if (!serverData) return;
    (schema.fields || []).forEach(f => {
      if (f.type === 'group' && f.mode === 'repeatable-table'){
        const newRows = Array.isArray(serverData[f.name]) ? serverData[f.name] : [];
        const instance = repeatableTables.find(rt => rt.field.name === f.name);
        const targetRows = instance ? instance.rows : (Array.isArray(data[f.name]) ? data[f.name] : []);
        targetRows.length = 0;
        newRows.forEach(row => targetRows.push({...row}));
        data[f.name] = targetRows;
        if (instance){
          instance.renderBody();
        }
      } else if (Object.prototype.hasOwnProperty.call(serverData, f.name)){
        const value = serverData[f.name];
        data[f.name] = value;
        const el = form.querySelector(`[name="${f.name}"]`);
        if (el){
          if (el.type === 'checkbox') el.checked = !!value;
          else el.value = value ?? '';
        }
      }
    });
  }

  async function recomputeCalculated({silent=false}={}){
    if (!window.__RECOMPUTE_URL__) return null;
    const payload = collectPayload();
    try{
      const res = await fetch(window.__RECOMPUTE_URL__, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      if (json && json.data){
        applyServerData(json.data);
        await refreshRules();
      }
      return json.data;
    }catch(err){
      console.warn('Failed to recompute calculated fields', err);
      if (!silent) alert('Unable to refresh calculated fields right now.');
      return null;
    }
  }

  async function refreshRules(){
    try{
      const payload = collectPayload();
      const res = await fetch(`/rules/${schema.slug}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      const rules = await res.json();
      (schema.fields || []).forEach(f => {
        let node = holder.querySelector(`[data-field="${f.name}"]`) || holder.querySelector(`[name="${f.name}"]`) || tableHolder.querySelector(`[name="${f.name}"]`);
        if (!node) return;
        let wrap = node.closest('[data-field]') || node.closest('td') || node.closest('tr') || node.closest('div') || node;
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
      const field = fieldRegistry.get(t.name);
      if (t.type === 'checkbox') data[t.name] = t.checked;
      else data[t.name] = coerceFieldValue(field, t.value);
      refreshRules();
    }
  };
  holder.addEventListener('input', onInput);
  tableHolder.addEventListener('input', onInput);

  const recomputeBtn = document.getElementById('recomputeBtn');
  if (recomputeBtn){
    if (!window.__RECOMPUTE_URL__){
      recomputeBtn.style.display = 'none';
    } else {
      recomputeBtn.addEventListener('click', async () => {
        const originalText = recomputeBtn.textContent;
        recomputeBtn.disabled = true;
        recomputeBtn.textContent = 'Refreshing…';
        await recomputeCalculated({silent:false});
        recomputeBtn.textContent = originalText;
        recomputeBtn.disabled = false;
      });
    }
  }

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    await recomputeCalculated({silent: true});
    const payload = collectPayload();
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

  const deleteBtn = document.getElementById('deleteRecordBtn');
  if (deleteBtn && window.__DELETE_URL__){
    deleteBtn.addEventListener('click', async () => {
      if (!confirm('Delete this record?')) return;
      const res = await fetch(window.__DELETE_URL__, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
      if (res.ok){
        const result = await res.json();
        if (result.redirect){
          window.location.href = result.redirect;
        } else if (window.__LIST_URL__){
          window.location.href = window.__LIST_URL__;
        } else {
          window.location.reload();
        }
      } else {
        alert('Delete failed');
      }
    });
  }
});
