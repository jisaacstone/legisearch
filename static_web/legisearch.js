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
  renterDelay: 250,
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

const makeFilters = () => {
  const filterEl = document.getElementById('filters');
  filterEl.innerHTML = '';
  const filterhead = document.createElement('h2');
  filterhead.textContent = 'meeting bodies';
  filterhead.classList.add('filterhead');
  filterhead.addEventListener('click', () => filterEl.classList.toggle('open'));
  filterEl.appendChild(filterhead);
  const bodyFilter = document.createElement('div');
  bodyFilter.className = 'filterlist';
  const filterAll = document.createElement('div');
  filterAll.className = 'filter allFilter rslts';
  filterAll.textContent = 'All Meeting Bodies';
  if (settings.bodyIds.size === 0) {
    filterAll.classList.add('checked');
  }
  filterAll.addEventListener('click', () => {
    if (!filterAll.classList.contains('checked')) {
      Array.prototype.forEach.call(bodyFilter.children, (child) => {
        child.classList.remove('checked');
      });
      settings.bodyIds.clear();
      filterAll.classList.add('checked');
      onType();
    }
  });
  bodyFilter.appendChild(filterAll);
  const allBodies = new Set(Object.values(db.events).map(e => e.body_id));
  const sorted = Array.from(allBodies).toSorted((a, b) => db.bodies[a].localeCompare(db.bodies[b]));
  settings.bodyFilters = {};
  sorted.forEach((bodyId) => {
    const filter = document.createElement('div');
    filter.className = `filter b-${bodyId}`;
    filter.textContent = db.bodies[bodyId];
    if (settings.bodyIds.has(bodyId)) {
      filter.classList.add('checked');
    }
    filter.onclick = () => {
      if (filter.classList.contains('checked')) {
        filter.classList.remove('checked');
        settings.bodyIds.delete(bodyId);
        if (settings.bodyIds.size === 0) {
          filterAll.classList.add('checked');
        }
      } else {
        filter.classList.add('checked');
        settings.bodyIds.add(bodyId);
        filterAll.classList.remove('checked');
      }
      onType();
    };
    bodyFilter.appendChild(filter);
    settings.bodyFilters[bodyId] = filter;
  });
  filterEl.appendChild(bodyFilter);
};

// This is a bit garbage. TODO: cleanup, use library? make it faster
const makeResultElement = (res) => {
  const result = document.createElement('div');
  result.className = 'result';

  //meeting info
  const doctype = document.createElement('div');
  doctype.className = 'meetinginfo';
  const bodyel = document.createElement('div');
  bodyel.textContent = res.b_name;
  bodyel.className = 'body b-' + res.b_id;
  doctype.appendChild(bodyel);
  const datetime = document.createElement('div');
  datetime.textContent = res.meeting_time.substring(0, 10);
  doctype.appendChild(datetime);
  result.appendChild(doctype);

  //matter info
  const matters = document.createElement('div');
  matters.className = 'matter';
  if (res.matter_type) {
    const mtype = document.createElement('div');
    mtype.textContent = res.matter.type;
    mtype.className = 'mtype ' + res.matter.type.toLowerCase().replaceAll(' ', '-');
    matters.appendChild(mtype);
    const mstatus = document.createElement('div');
    mstatus.textContent = res.matter.status;
    mstatus.className = 'mstatus ' + res.matter.status.toLowerCase().replaceAll(' ', '-');
    matters.appendChild(mstatus);
  }
  result.appendChild(matters);

  //meeting links
  const links = document.createElement('div');
  links.className = 'resultLinks';
  if (res.agenda) {
    const ext = res.agenda.slice(-5);
    const alink = document.createElement('a');
    alink.setAttribute('href', res.agenda);
    alink.textContent = ext[0] === '.' ? `${ext} agenda` : 'agenda';
    links.appendChild(alink);
  }

  if (res.minutes) {
    const ext = res.minutes.slice(-5);
    const mlink = document.createElement('a');
    mlink.setAttribute('href', res.minutes);
    mlink.textContent = ext[0] === '.' ? `${ext} minutes` : 'minutes';
    links.appendChild(mlink);
  }
  const ilink = document.createElement('a');
  ilink.setAttribute('href', res.insite);
  ilink.textContent = 'info';
  links.appendChild(ilink);

  result.appendChild(links);

  var title = res.title;
  var text = res.text;
  if (!text && title.length > 100) {
    // action text has been subsumed into a very long title. Let's split it back out
    const firstdot = title.indexOf('.', 10);
    const splitAt = firstdot < 10 ? 100 : firstdot;
    title = res.title.slice(0, splitAt);
    text = res.title.split(splitAt);
  }

  //title
  const titleEl = document.createElement('div');
  titleEl.className = 'resultTitle';
  titleEl.innerHTML = `<div class="iagenda">${res.a_num}</div><div class="ititle">${title}</div>`;
  result.appendChild(titleEl);

  //attachments
  const atts = Object.keys(res.matter.attach);

  if (atts.length > 0) {
    const atta = document.createElement('div');
    atta.className = 'attachments';
    atts.forEach((name) => {
      const link = document.createElement('a');
      link.textContent = '\u{1F4CE}' + name;
      link.setAttribute('href', atts[name]);
      atta.appendChild(link);
    });
    result.appendChild(atta);
  }

  //description
  if (text) {
    const desc = document.createElement('div');
    const lines = text.split('\n');
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

const postFetch = () => {
  db.search = new MiniSearch({
    fields: ['title', 'action_text', 'b_name'],
    storeFields: ['text', 'attachments', 'title',
      'a_num', 'matter', 'meeting_time', 'year', 'month',
      'b_id', 'b_name', 'agenda', 'minutes', 'insite']
  });
  db.search.addAll(db.items);
};

const loadData = (jurisdiction) => {
  const resEl = document.getElementById('results');
  // 'items' is left and an array, because fuse expects that
  // others are changed to a key-value mapping for faster lookup
  return Promise.all([
    fetch(`${jurisdiction}.items.json`)
      .then((resp) => resp.json())
      .then((itjson) => {
        db.items = itjson;
      }),
    fetch(`${jurisdiction}.bodies.json`)
      .then((resp) => resp.json())
      .then((bjson) => {
        db.bodies = bjson.reduce((o, b) => {o[b.id] = b.name; return o; }, {});
      })
  ]).then(() => {
    postFetch();
    onType();
  });
};

const loadJurisdictions = () => {
  const jEl = document.getElementById('jurisdiction');
  jEl.addEventListener('change', onNsChange);
  return fetch('jurisdictions.json')
    .then((resp) => resp.json())
    .then((jurisdictions) => {
      //jEl.innerHTML = '';
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
  const result = makeResultElement(res);
  if (result) {
    toRender -= 1;
    timeout = settings.renderDelay;
    resEl.appendChild(result);

    // expand/close action - needs to be added to document before can check overflow
    if (result.scrollHeight > result.clientHeight) {
      result.classList.add('long');
      result.onclick = () => result.classList.toggle('open');
    }
  }

  settings.renderTimer = setTimeout(() => renderResults(resEl, toRender), timeout);
};

const filterResult = (result) => {
  if (settings.bodyIds.size > 0) {
    if (!settings.bodyIds.has(result.b_id)) {
      return false;
    }
  }
  return true;
};

const onType = () => {
  const acEl = document.getElementById('autoComplete');
  const resEl = document.getElementById('results');
  const value = acEl.value.trim();
  resEl.innerHTML = '';
  if (value.length <= 2) {
    return;
  }
  clearTimeout(settings.renderTimer);
  // TODO: configurable limit, lazy load, pagination, or similar
  // so more results are available
  //const results = settings.fuse.search(value, { limit: settings.maxSearch });
  const results = db.search.search(value);
  setFilterStats(results);
  settings.renderQueue = results.filter(filterResult);
  renderResults(resEl, settings.maxResults);
};

const setFilterStats = (results) => {
  const bodyIds = new Set();
  for (const res of results) {
    bodyIds.add(res.b_id.toString());
  }
  for (const id in settings.bodyFilters) {
    if (bodyIds.has(id)) {
      settings.bodyFilters[id].classList.add('rslts');
    } else {
      settings.bodyFilters[id].classList.remove('rslts');
    }
  }
};

const onload = () => {
  loadJurisdictions()
    .finally(onNsChange())
    .then(() => {
    const acEl = document.getElementById('autoComplete');
    acEl.addEventListener('input', delay(onType, settings.renderDelay));
  });
};

window.onload = () => {
  onload();
};
