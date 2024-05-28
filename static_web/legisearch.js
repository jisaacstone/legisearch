const settings = {
  options: {
    keys: [{ name: 'title', weight: 0.7 }, { name: 'action_text', weight: 0.6 }],
    includeScore: true,
    distance: 10000,
    threshold: 0.9
  },
  maxSearch: 500,
  maxResults: 50,
  jurisdiction: 'mountainview',
  bodyIds: new Set(),
  renderTimer: 0,
  renderQueue: []
};
const db = {};

// delay search for a few milliseconds, so it only executes when there is a pause in typing
function delay(callback, ms) {
  var timer = 0;
  return function() {
    var context = this, args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () {
      callback.apply(context, args);
    }, ms || 0);
  };
}

// TODO: cleanup and enable
const makeFilters = () => {
  const filterEl = document.getElementById('filters');
  filterEl.innerHTML = '';
  const filterhead = document.createElement('h2');
  filterhead.textContent = 'filters';
  filterhead.addEventListener('click', () => filterEl.toggleClass('open'));
  filterEl.appendChild(filterhead);
  const bodyFilter = document.createElement('div');
  bodyFilter.className = 'filterlist';
  const allBodies = new Set(Object.values(db.events).map(e => e.body_id));
  allBodies.forEach((bodyId) => {
    const filter = document.createElement('div');
    filter.className = 'filter';
    filter.textContent = db.bodies[bodyId];
    if (settings.bodyIds.has(bodyId)) {
      filter.classList.add('checked');
    }
    filter.onclick = () => {
      if (filter.classList.contains('checked')) {
        filter.classList.remove('checked');
        settings.bodyIds.delete(bodyId);
      } else {
        filter.classList.add('checked');
        settings.bodyIds.add(bodyId);
      }
      onType();
    };
    bodyFilter.appendChild(filter);
  });
  filterEl.appendChild(bodyFilter);
};

// This is a bit garbage. TODO: cleanup, use library? make it faster
const makeResultElement = (res) => {
  const event = db.events[res.event_id];
  if (!event) {
    return null;
  }
  // filter
  if (settings.bodyIds.has(event.body_id)) {
    return null;
  }

  const body = db.bodies[event.body_id];
  const result = document.createElement('div');
  result.className = 'result';

  //meeting info
  const doctype = document.createElement('div');
  doctype.className = 'meetinginfo';
  const bodyel = document.createElement('div');
  bodyel.textContent = body;
  bodyel.className = 'body b-' + event.body_id;
  doctype.appendChild(bodyel);
  const datetime = document.createElement('div');
  datetime.textContent = event.meeting_time.substring(0, 10);
  doctype.appendChild(datetime);
  result.appendChild(doctype);
  //matter info
  const matters = document.createElement('div');
  matters.className = 'matter';
  if (res.matter_type) {
    const mtype = document.createElement('div');
    mtype.textContent = res.matter_type;
    mtype.className = 'mtype ' + res.matter_type.toLowerCase().replaceAll(' ', '-');
    matters.appendChild(mtype);
    const mstatus = document.createElement('div');
    mstatus.textContent = res.matter_status;
    mstatus.className = 'mstatus ' + res.matter_status.toLowerCase().replaceAll(' ', '-');
    matters.appendChild(mstatus);
  }
  result.appendChild(matters);

  //meeting links
  const links = document.createElement('div');
  links.className = 'resultLinks';
  const ilink = document.createElement('a');
  ilink.setAttribute('href', event.insite_url);
  ilink.textContent = 'info';
  links.appendChild(ilink);

  var alink;
  if (event.agenda_url) {
    alink = document.createElement('a');
    alink.setAttribute('href', event.agenda_url);
  } else {
    alink = document.createElement('span');
    alink.className = 'not-available';
  }
  alink.textContent = 'agenda';
  links.appendChild(alink);

  var mlink;
  if (event.minutes_url) {
    mlink = document.createElement('a');
    mlink.setAttribute('href', event.minutes_url);
  } else {
    mlink = document.createElement('span');
    mlink.className = 'not-available';
  }
  mlink.textContent = 'minutes';
  links.appendChild(mlink);

  result.appendChild(links);

  //title
  const title = document.createElement('div');
  title.className = 'resultTitle';
  title.innerHTML = `<div class="iagenda">${res.agenda_number}</div><div class="ititle">${res.title}</div>`;
  result.appendChild(title);

  //attachments
  if (res.matter_attachments !== '{}') {
    const attachments = JSON.parse(res.matter_attachments);
    const atta = document.createElement('div');
    atta.className = 'attachments';
    Object.keys(attachments).forEach((name) => {
      const link = document.createElement('a');
      link.textContent = '\u{1F4CE}' + name;
      link.setAttribute('href', attachments[name]);
      atta.appendChild(link);
    });
    result.appendChild(atta);
  }

  //description
  if (res.action_text) {
    const desc = document.createElement('div');
    const lines = res.action_text.split('\n');
    desc.className = 'resultDescription';
    lines.forEach((line) => {
        const p = document.createElement('p');
        p.textContent = line;
        desc.appendChild(p);
    });
    result.appendChild(desc);
  }
  return result;
};

const loadData = (jurisdiction) => {
  // 'items' is left and an array, because fuse expects that
  // others are changed to a key-value mapping for faster lookup
  return Promise.all([
    fetch(`${jurisdiction}.events.json`)
      .then((resp) => resp.json())
      .then((evtjson) => {
        db.events = evtjson.reduce((o, e) => {o[e.id] = e; return o; }, {});
      }),
    fetch(`${jurisdiction}.items.json`)
      .then((resp) => resp.json())
      .then((itjson) => {
        db.items = itjson;
        settings.fuse = new Fuse(itjson, settings.options);
      }),
    fetch(`${jurisdiction}.bodies.json`)
      .then((resp) => resp.json())
      .then((bjson) => {
        db.bodies = bjson.reduce((o, b) => {o[b.id] = b.name; return o; }, {});
      })
  ]).then(() => onType()); //call immediatly, so page refresh pulls results
};

const loadJurisdictions = () => {
  const jEl = document.getElementById('jurisdiction');
  jEl.addEventListener('change', onNsChange);
  return fetch('jurisdictions.json')
    .then((resp) => resp.json())
    .then((jurisdictions) => {
      jEl.innerHTML = '';
      for (const [name, jur] of Object.entries(jurisdictions)) {
        const opt = document.createElement('option');
        opt.value = jur;
        opt.innerHTML = name;
        jEl.appendChild(opt);
      }
    })
    .then(() => jEl.dispatchEvent(new Event('change')));
};

onNsChange = () => {
  const ns = document.getElementById('jurisdiction').value;
  settings.jurisdiction = ns;
  return loadData(settings.jurisdiction).then(makeFilters);
};

const renderResults = (resEl, toRender) => {
  const res = settings.renderQueue.shift();
  var timeout = 0;
  if (!res) {
    return;
  }
  const result = makeResultElement(res.item);
  if (result) {
    toRender -= 1;
    timeout = 250;
    resEl.appendChild(result);

    // expand/close action - needs to be added to document before can check overflow
    if (result.scrollHeight > result.clientHeight) {
      result.classList.add('long');
      result.onclick = () => result.classList.toggle('open');
    }
  }

  settings.renderTimer = setTimeout(() => renderResults(resEl, toRender), timeout);
};

const onType = () => {
  const acEl = document.getElementById('autoComplete');
  const resEl = document.getElementById('results');
  const value = acEl.value.trim();
  resEl.innerHTML = '';
  if (value.length <= 1) {
    return;
  }
  // TODO: configurable limit, lazy load, pagination, or similar
  // so more results are available
  const results = settings.fuse.search(value, { limit: settings.maxSearch });
  clearTimeout(settings.renderTimer);
  settings.renderQueue = results;
  renderResults(resEl, settings.maxResults);
};

const onload = () => {
  loadJurisdictions()
    .finally(onNsChange())
    .then(() => {
    const acEl = document.getElementById('autoComplete');
    // TODO: small delay, so it only does search after a pause
    // or: only after a certain number of characters?
    acEl.addEventListener('input', delay(onType, 250));
  });
};

window.onload = () => {
  const filEl = document.getElementById('filters');
  onload();
};
