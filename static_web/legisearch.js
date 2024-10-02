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
  renderTimer: 0,
  renterDelay: 250,
};
const db = {};
const state = {
  results: {
    items: [],
    bodyIds: new Set(),
    years: new Set(),
  },
};

// delay search for a few milliseconds, so it only executes when there is a pause in typing
const delay = (callback, ms) => {
  let timer = 0;
  return function() {
    let context = this, args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () {
      callback.apply(context, args);
    }, ms || 0);
  };
};


const filters = (() => {
  const bodyIds = new Set(),
        years = new Set();
  let  hasAttachment = false;

  const makeElements = (results) => {
    const bids = new Set(),
          yrs = new Set(),
          bEl = document.getElementById('body-filter'),
          yEl = document.getElementById('year-filter');
    bEl.innerHTML = '';
    yEl.innerHTML = '';
    for (const res of results) {
      bids.add(res.b_id);
      yrs.add(+res.year);
    }
    for (const yr of Array.from(yrs).toSorted()) {
      makeFilterEl(years, yEl, yr.toString());
    }
    for (const bid of bids) {
      makeFilterEl(bodyIds, bEl, bid, db.bodies[bid]);
    }
  };

  const makeFilterEl = (filterSet, parentEl, id, text) => {
    const filterEl = document.createElement('div');
    if (!text) {
      text = id;
    }
    filterEl.classList.add('filter');
    filterEl.textContent = text;
    filterEl.onclick = () => {
      if (filterEl.classList.contains('checked')) {
        filterEl.classList.remove('checked');
        filterSet.delete(id);
      } else {
        filterEl.classList.add('checked');
        filterSet.add(id);
      }
      onFilterChange();
    };
    parentEl.appendChild(filterEl);
  };

  const filterResult = (result) => {
    if (bodyIds.size > 0) {
      if (!bodyIds.has(result.b_id)) {
        return false;
      }
    }
    if (years.size > 0) {
      if (!years.has(result.year)) {
        return false;
      }
    }
    if (hasAttachment) {
      if (Object.keys(result.matter.attach).length == 0) {
        return false;
      }
    }
    return true;
  };

  return {
    makeElements: makeElements,
    run: filterResult
  };
})();


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
  datetime.textContent = res.meeting_time ? res.meeting_time.substring(0, 10) : '';
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

  let title = res.title;
  let text = res.text || '';
  if (title.length > 100) {
    const match = title.substring(10).match(/[.;?]\s/);
    const splitAt = match ? match.index + 10 : title.indexOf(' ', 100);
    // action text has been subsumed into a very long title. Let's split it back out
    title = res.title.slice(0, splitAt);
    text = res.title.slice(splitAt) + '\n' + text;
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
      link.setAttribute('href', res.matter.attach[name]);
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

const jurisdictions = (() => {
  let selectedJurisdiction = 'mountainview';

  const loadData = (jurisdiction) => {
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
    // not loading anymore, so state is cached by browser
    // and I don't have to deal with the history api
    const jEl = document.getElementById('jurisdiction');
    jEl.addEventListener('change', onJChange);
    return onJChange();
  };

  onJChange = () => {
    const ns = document.getElementById('jurisdiction').value;
    selectedJurisdiction = ns;
    return loadData(settings.jurisdiction);
  };

  return { load: loadJurisdictions };
})();

const renderResults = (resEl, toRender) => {
  const res = state.renderQueue.shift();
  let timeout = 0;
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

const onType = () => {
  const acEl = document.getElementById('autoComplete');
  const resEl = document.getElementById('results');
  const value = acEl.value.trim();
  clearTimeout(settings.renderTimer);
  resEl.innerHTML = '';
  if (value.length <= 2) {
    return;
  }
  const results = db.search.search(value);
  filters.makeElements(results);
  state.results.items = results;
  onFilterChange();
};

const onFilterChange = () => {
  const resEl = document.getElementById('results');
  resEl.innerHTML = '';
  state.renderQueue = state.results.items.filter(filters.run);
  renderResults(resEl, settings.maxResults);
};

const onload = () => {
  jurisdictions.load().then(() => {
    const acEl = document.getElementById('autoComplete');
    acEl.addEventListener('input', delay(onType, settings.renderDelay));
  });
};

window.onload = () => {
  onload();
};
