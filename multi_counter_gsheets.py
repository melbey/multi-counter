#!/usr/bin/env python3
"""
Multi Counter Clicker - Instant browser UI + Google Apps Script sync

This version avoids Streamlit reruns for +1/-1/reset/delete.
Counting happens instantly in the browser, then syncs to Google Sheets in the background.

Important:
- This app embeds APPS_SCRIPT_URL and APPS_SCRIPT_TOKEN into the browser page so JavaScript can sync directly.
- That means anyone who can open the public app can potentially inspect/use the token.
- For a private counter tool this is usually acceptable, but do not use this pattern for sensitive data.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components


APP_TITLE = "Multi Counter Clicker"
APP_VERSION = "instant-browser-v1"
SWEDEN_TZ = ZoneInfo("Europe/Stockholm")


def sweden_now_str() -> str:
    return datetime.now(SWEDEN_TZ).replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1rem;
            max-width: 100%;
        }
        [data-testid="stStatusWidget"] {
            display: none !important;
        }
        iframe {
            border: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def app_html(apps_script_url: str, apps_script_token: str) -> str:
    # JSON-encode so values are safely inserted into JavaScript.
    url_js = json.dumps(apps_script_url)
    token_js = json.dumps(apps_script_token)
    now_js = json.dumps(sweden_now_str())

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root {{
  color-scheme: light dark;
  --bg: #0e1117;
  --panel: #161b22;
  --panel2: #1f2630;
  --text: #f0f3f6;
  --muted: #9ca3af;
  --border: rgba(255,255,255,.12);
  --accent: #ff4b4b;
  --good: #2ecc71;
  --danger: #ef4444;
  --button: #262d38;
  --button-hover: #303847;
}}

* {{
  box-sizing: border-box;
}}

html, body {{
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

body {{
  padding: 10px 12px 40px;
}}

.header {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}}

h1 {{
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 .25rem;
}}

.subtitle {{
  color: var(--muted);
  font-size: .9rem;
}}

.toolbar {{
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
  align-items: center;
  justify-content: flex-end;
}}

button {{
  border: 1px solid var(--border);
  background: var(--button);
  color: var(--text);
  padding: .55rem .75rem;
  border-radius: .55rem;
  cursor: pointer;
  font-weight: 650;
  min-height: 38px;
}}

button:hover {{
  background: var(--button-hover);
}}

button.primary {{
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}}

button.danger {{
  color: #fecaca;
}}

.status {{
  color: var(--muted);
  font-size: .86rem;
  min-height: 1.4rem;
}}

.add-panel {{
  display: flex;
  gap: .6rem;
  margin: 1rem 0;
  align-items: center;
}}

input {{
  background: var(--panel);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: .55rem;
  padding: .65rem .75rem;
  font-size: 1rem;
  min-height: 42px;
}}

.add-panel input {{
  flex: 1;
}}

.counter-list {{
  display: flex;
  flex-direction: column;
  gap: .65rem;
}}

.counter {{
  display: grid;
  grid-template-columns: minmax(160px, 1fr) 88px repeat(6, auto);
  gap: .45rem;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: .8rem;
  padding: .7rem;
}}

.counter-name {{
  width: 100%;
  font-weight: 650;
}}

.count {{
  text-align: center;
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
}}

.small {{
  padding: .45rem .55rem;
  min-width: 52px;
}}

.empty {{
  color: var(--muted);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: .8rem;
  padding: 1rem;
}}

.footer {{
  margin-top: 1rem;
  color: var(--muted);
  font-size: .85rem;
}}

@media (max-width: 850px) {{
  .header {{
    display: block;
  }}

  .toolbar {{
    justify-content: flex-start;
    margin-top: .75rem;
  }}

  .counter {{
    grid-template-columns: 1fr 74px;
  }}

  .counter-name {{
    grid-column: 1 / span 2;
  }}

  .count {{
    text-align: left;
    font-size: 2.4rem;
    padding-left: .2rem;
  }}

  .counter button {{
    min-height: 42px;
  }}
}}
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Multi Counter Clicker</h1>
      <div class="subtitle">{html.escape(APP_VERSION)} · Sweden time: <span id="swedenTime"></span></div>
    </div>
    <div class="toolbar">
      <button id="reloadBtn">Reload</button>
      <button id="saveBtn" class="primary">Save now</button>
      <button id="exportBtn">Export JSON</button>
      <button id="importBtn">Import JSON</button>
      <input id="importFile" type="file" accept=".json,application/json" style="display:none" />
    </div>
  </div>

  <div id="status" class="status">Starting...</div>

  <div class="add-panel">
    <input id="newCounterName" placeholder="New counter name, e.g. GFP-positive cells" />
    <button id="addBtn" class="primary">Add counter</button>
  </div>

  <div id="counterList" class="counter-list"></div>

  <div class="footer">
    Counts update instantly in the browser. Changes are saved to Google Sheets automatically in the background.
  </div>

<script>
const APPS_SCRIPT_URL = {url_js};
const APPS_SCRIPT_TOKEN = {token_js};
let counters = [];
let saveTimer = null;
let saving = false;
let lastSavedJson = "";
let dirty = false;

function uuid() {{
  if (crypto && crypto.randomUUID) return crypto.randomUUID();
  return "counter-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
}}

function swedenTimestamp() {{
  // Browser-local timestamp is only for display/update metadata.
  // Google Sheet storage does not depend on this for counter math.
  const d = new Date();
  return d.toISOString();
}}

function setStatus(text, kind="") {{
  const el = document.getElementById("status");
  el.textContent = text;
  el.style.color = kind === "error" ? "#f87171" : kind === "ok" ? "#86efac" : "var(--muted)";
}}

function normalizeCounter(item) {{
  return {{
    id: String(item.id || uuid()),
    name: String(item.name || "Counter"),
    count: Number(item.count || 0),
    updated_at: String(item.updated_at || "")
  }};
}}

async function api(action, payload={{}}) {{
  const res = await fetch(APPS_SCRIPT_URL, {{
    method: "POST",
    headers: {{ "Content-Type": "text/plain;charset=utf-8" }},
    body: JSON.stringify({{
      action,
      token: APPS_SCRIPT_TOKEN,
      ...payload
    }})
  }});

  if (!res.ok) throw new Error("HTTP " + res.status);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "Unknown backend error");
  return data;
}}

async function loadCounters() {{
  try {{
    setStatus("Loading from Google Sheets...");
    const data = await api("load");
    counters = (data.counters || []).map(normalizeCounter);
    lastSavedJson = JSON.stringify(counters);
    dirty = false;
    render();
    setStatus("Loaded. Ready.", "ok");
  }} catch (err) {{
    setStatus("Could not load: " + err.message, "error");
    render();
  }}
}}

async function saveCounters(force=false) {{
  if (saving) return;
  const currentJson = JSON.stringify(counters);

  if (!force && currentJson === lastSavedJson) {{
    dirty = false;
    return;
  }}

  saving = true;
  setStatus("Saving...");
  try {{
    const payloadCounters = counters.map(c => ({{
      ...c,
      updated_at: swedenTimestamp()
    }}));
    await api("save", {{ counters: payloadCounters }});
    lastSavedJson = JSON.stringify(counters);
    dirty = false;
    setStatus("Saved.", "ok");
  }} catch (err) {{
    setStatus("Save failed: " + err.message, "error");
  }} finally {{
    saving = false;
  }}
}}

function scheduleSave() {{
  dirty = true;
  setStatus("Changed locally. Saving soon...");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveCounters(false), 450);
}}

function render() {{
  const root = document.getElementById("counterList");
  root.innerHTML = "";

  if (counters.length === 0) {{
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No counters yet. Add one above.";
    root.appendChild(empty);
    return;
  }}

  counters.forEach((counter, index) => {{
    const row = document.createElement("div");
    row.className = "counter";

    const name = document.createElement("input");
    name.className = "counter-name";
    name.value = counter.name;
    name.title = "Rename counter";
    name.addEventListener("input", () => {{
      counter.name = name.value.trim() || "Counter";
      scheduleSave();
    }});

    const count = document.createElement("div");
    count.className = "count";
    count.textContent = counter.count;

    const minus = button("-1", "small", () => {{
      counter.count -= 1;
      count.textContent = counter.count;
      scheduleSave();
    }});

    const plus = button("+1", "small primary", () => {{
      counter.count += 1;
      count.textContent = counter.count;
      scheduleSave();
    }});

    const reset = button("Reset", "small", () => {{
      if (confirm(`Reset “${{counter.name}}” to 0?`)) {{
        counter.count = 0;
        render();
        scheduleSave();
      }}
    }});

    const up = button("↑", "small", () => {{
      if (index > 0) {{
        [counters[index - 1], counters[index]] = [counters[index], counters[index - 1]];
        render();
        scheduleSave();
      }}
    }});

    const down = button("↓", "small", () => {{
      if (index < counters.length - 1) {{
        [counters[index + 1], counters[index]] = [counters[index], counters[index + 1]];
        render();
        scheduleSave();
      }}
    }});

    const del = button("Delete", "small danger", () => {{
      if (confirm(`Delete “${{counter.name}}”?`)) {{
        counters = counters.filter(c => c.id !== counter.id);
        render();
        scheduleSave();
      }}
    }});

    row.appendChild(name);
    row.appendChild(count);
    row.appendChild(minus);
    row.appendChild(plus);
    row.appendChild(reset);
    row.appendChild(up);
    row.appendChild(down);
    row.appendChild(del);
    root.appendChild(row);
  }});
}}

function button(text, cls, onClick) {{
  const b = document.createElement("button");
  b.textContent = text;
  b.className = cls || "";
  b.addEventListener("click", onClick);
  return b;
}}

function addCounter() {{
  const input = document.getElementById("newCounterName");
  const name = input.value.trim();
  if (!name) {{
    input.focus();
    return;
  }}
  counters.push({{
    id: uuid(),
    name,
    count: 0,
    updated_at: swedenTimestamp()
  }});
  input.value = "";
  render();
  scheduleSave();
}}

function exportJson() {{
  const blob = new Blob([JSON.stringify(counters, null, 2)], {{ type: "application/json" }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "multi_counter_backup.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}}

function importJsonFile(file) {{
  const reader = new FileReader();
  reader.onload = () => {{
    try {{
      let data = JSON.parse(reader.result);
      if (data && !Array.isArray(data) && Array.isArray(data.counters)) data = data.counters;
      if (!Array.isArray(data)) throw new Error("JSON must be a list of counters or an object with a counters list.");
      const imported = data.map(normalizeCounter);
      if (confirm(`Replace current counters with ${{imported.length}} imported counter(s)?`)) {{
        counters = imported;
        render();
        scheduleSave();
      }}
    }} catch (err) {{
      alert("Import failed: " + err.message);
    }}
  }};
  reader.readAsText(file);
}}

document.getElementById("addBtn").addEventListener("click", addCounter);
document.getElementById("newCounterName").addEventListener("keydown", (e) => {{
  if (e.key === "Enter") addCounter();
}});
document.getElementById("reloadBtn").addEventListener("click", () => {{
  if (dirty && !confirm("You have unsaved local changes. Reload anyway?")) return;
  loadCounters();
}});
document.getElementById("saveBtn").addEventListener("click", () => saveCounters(true));
document.getElementById("exportBtn").addEventListener("click", exportJson);
document.getElementById("importBtn").addEventListener("click", () => document.getElementById("importFile").click());
document.getElementById("importFile").addEventListener("change", (e) => {{
  if (e.target.files && e.target.files[0]) importJsonFile(e.target.files[0]);
  e.target.value = "";
}});

window.addEventListener("beforeunload", (e) => {{
  if (dirty) {{
    saveCounters(true);
  }}
}});

function updateSwedenClock() {{
  const formatter = new Intl.DateTimeFormat("sv-SE", {{
    timeZone: "Europe/Stockholm",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }});
  document.getElementById("swedenTime").textContent = formatter.format(new Date());
}}

setInterval(updateSwedenClock, 15000);
updateSwedenClock();
loadCounters();
</script>
</body>
</html>
"""


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    inject_css()

    apps_script_url = get_secret("APPS_SCRIPT_URL", "").strip()
    apps_script_token = get_secret("APPS_SCRIPT_TOKEN", "").strip()

    if not apps_script_url:
        st.error("Missing APPS_SCRIPT_URL in Streamlit secrets.")
        st.stop()

    if not apps_script_token:
        st.error("Missing APPS_SCRIPT_TOKEN in Streamlit secrets.")
        st.stop()

    components.html(
        app_html(apps_script_url, apps_script_token),
        height=900,
        scrolling=True,
    )


if __name__ == "__main__":
    main()
