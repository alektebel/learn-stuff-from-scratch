const state = {
  today: null,
  selected: null,
  days: [],
  byDate: {},
  posts: new Set(),
};

const $ = (id) => document.getElementById(id);

function fmt(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function pretty(iso) {
  return fmt(iso).toLocaleDateString("en-GB", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

function renderToday(entry, iso) {
  $("today-label").textContent = pretty(iso);
  $("week-label").textContent = entry
    ? (entry.week === 0 ? "Week 0 — setup" : `Week ${String(entry.week).padStart(2, "0")} · ${entry.kind}`)
    : "Outside the plan";
  $("today-do").textContent = entry ? entry.do : "No planned work for this date.";
  $("today-project").textContent = entry ? entry.project : "";
  $("today-publish").textContent = entry
    ? entry.publish
    : "Write anyway if something is worth keeping.";
}

function renderWeek(iso) {
  const entry = state.byDate[iso];
  const week = entry ? entry.week : null;
  const list = $("week-list");
  list.innerHTML = "";
  state.days
    .filter((d) => d.week === week)
    .forEach((d) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.innerHTML = `<span class="when">${d.date} · ${d.dow.slice(0, 3)}</span>${d.publish}`;
      btn.addEventListener("click", () => select(d.date));
      li.appendChild(btn);
      list.appendChild(li);
    });
}

function renderCalendar() {
  const cal = $("calendar");
  cal.innerHTML = "";
  ["M", "T", "W", "T", "F", "S", "S"].forEach((label) => {
    const h = document.createElement("div");
    h.className = "cal-head";
    h.textContent = label;
    cal.appendChild(h);
  });

  const first = fmt(state.days[0].date);
  const last = fmt(state.days[state.days.length - 1].date);
  // Monday-first grid. JS getDay(): Sun=0.
  const pad = (first.getDay() + 6) % 7;
  for (let i = 0; i < pad; i++) {
    const empty = document.createElement("div");
    empty.className = "cal-day empty";
    cal.appendChild(empty);
  }

  for (let t = +first; t <= +last; t += 86400000) {
    const day = new Date(t);
    const iso = [
      day.getFullYear(),
      String(day.getMonth() + 1).padStart(2, "0"),
      String(day.getDate()).padStart(2, "0"),
    ].join("-");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cal-day";
    btn.textContent = String(day.getDate());
    btn.title = state.byDate[iso] ? state.byDate[iso].publish : iso;
    if (iso === state.today) btn.classList.add("today");
    if (iso === state.selected) btn.classList.add("selected");
    if (state.posts.has(iso)) btn.classList.add("has-post");
    btn.addEventListener("click", () => select(iso));
    cal.appendChild(btn);
  }
}

async function loadPost(iso) {
  const res = await fetch("/api/posts/" + iso);
  const data = await res.json();
  $("body").value = data.body || defaultBody(iso);
  $("save-state").textContent = data.exists ? "saved on disk" : "unsaved";
}

function defaultBody(iso) {
  const entry = state.byDate[iso];
  if (!entry) return `# ${pretty(iso)}\n\n`;
  return [
    `# ${pretty(iso)} — Week ${entry.week}`,
    "",
    `Expected publish: *${entry.publish}*`,
    "",
    `Project: \`${entry.project}\``,
    "",
    "## What I built",
    "",
    "",
    "## What surprised me",
    "",
    "",
    "## What I would defend differently",
    "",
    "",
  ].join("\n");
}

async function select(iso) {
  state.selected = iso;
  renderToday(state.byDate[iso], iso);
  renderWeek(iso);
  renderCalendar();
  await loadPost(iso);
}

async function save() {
  const iso = state.selected;
  $("save-state").textContent = "saving…";
  await fetch("/api/posts/" + iso, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body: $("body").value }),
  });
  state.posts.add(iso);
  $("save-state").textContent = "saved";
  renderCalendar();
}

async function boot() {
  const [curr, posts, progress] = await Promise.all([
    fetch("/api/curriculum").then((r) => r.json()),
    fetch("/api/posts").then((r) => r.json()),
    fetch("/api/progress").then((r) => r.json()),
  ]);
  state.today = curr.today;
  state.days = curr.days;
  state.byDate = Object.fromEntries(curr.days.map((d) => [d.date, d]));
  state.posts = new Set(posts.map((p) => p.date));
  $("progress").textContent = progress.text
    ? progress.text.replace(/\u001b\[[0-9;]*m/g, "").trim()
    : "progress.py did not run";
  $("save").addEventListener("click", save);
  $("body").addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "s") {
      event.preventDefault();
      save();
    }
  });
  const startOn = state.byDate[curr.today] ? curr.today : curr.days[0].date;
  await select(startOn);
}

boot();
