async function loadBodies(namespace) {
  const response = await fetch(
    "/b/" + namespace,
    {headers: {"Accept": "application/json"}}
  );
  if (response.status != 200) {
    console.log(response);
    return {};
  } else {
    bodies = await response.json();
    return bodies;
  }
}

async function bodySelect(namespace, parentEl) {
  const bodies = await loadBodies(namespace);
  for (let bodyName in bodies) {
    const input = document.createElement('input');
    input.setAttribute('type', 'checkbox');
    ['name', 'id', 'value'].forEach((id) => input.setAttribute(id, bodies[bodyName]));
    parentEl.appendChild(input);
    const label = document.createElement('label');
    lable.textContent = bodyName;
    label.setAttribute('for', bodies[bodyName]);
    parentEl.appendChild(label);
  }
}
