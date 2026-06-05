#!/usr/bin/env python3
"""
Multi Counter Clicker - Streamlit + Google Apps Script backend

This app stores counters in a Google Sheet through a Google Apps Script web app.
No service account JSON key is required.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


APP_TITLE = "Multi Counter Clicker"
APP_VERSION = "online-apps-script-v1"
SWEDEN_TZ = ZoneInfo("Europe/Stockholm")


def sweden_now() -> datetime:
    return datetime.now(SWEDEN_TZ).replace(second=0, microsecond=0).replace(tzinfo=None)


def sweden_now_str() -> str:
    return sweden_now().strftime("%Y-%m-%d %H:%M")


@dataclass
class Counter:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Counter"
    count: int = 0
    updated_at: str = ""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Counter":
        raw = dict(data or {})
        counter_id = str(raw.get("id") or str(uuid.uuid4()))
        name = str(raw.get("name") or "Counter").strip() or "Counter"

        try:
            count = int(float(raw.get("count", 0) or 0))
        except Exception:
            count = 0

        updated_at = str(raw.get("updated_at") or "")
        return Counter(id=counter_id, name=name, count=count, updated_at=updated_at)


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def backend_url() -> str:
    return get_secret("APPS_SCRIPT_URL", "").strip()


def backend_token() -> str:
    return get_secret("APPS_SCRIPT_TOKEN", "").strip()


def api_call(action: str, counters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    url = backend_url()
    if not url:
        raise RuntimeError("Missing APPS_SCRIPT_URL in Streamlit secrets.")

    payload: Dict[str, Any] = {
        "action": action,
        "token": backend_token(),
    }
    if counters is not None:
        payload["counters"] = counters

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(data.get("error", "Unknown backend error."))

    return data


@st.cache_data(ttl=120, show_spinner=False)
def load_counters_cached() -> List[Dict[str, Any]]:
    return api_call("load").get("counters", [])


def force_reload_counters() -> List[Counter]:
    load_counters_cached.clear()
    counters = [Counter.from_dict(item) for item in load_counters_cached()]
    st.session_state["counters"] = counters
    return counters


def load_counters() -> List[Counter]:
    if "counters" not in st.session_state:
        st.session_state["counters"] = [Counter.from_dict(item) for item in load_counters_cached()]
    return st.session_state["counters"]


def save_counters(counters: List[Counter]) -> None:
    for counter in counters:
        counter.updated_at = sweden_now_str()
    st.session_state["counters"] = counters
    api_call("save", [asdict(c) for c in counters])
    load_counters_cached.clear()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { transition: none !important; }
        [data-testid="stStatusWidget"] { display: none !important; }
        button, input, textarea, select, [role="button"], [data-testid="stDataFrame"] {
            transition: none !important;
        }
        .counter-card {
            border: 1px solid rgba(120, 120, 120, 0.25);
            border-radius: 0.75rem;
            padding: 0.75rem 1rem;
            margin-bottom: 0.75rem;
        }
        .counter-count {
            font-size: 2.2rem;
            font-weight: 700;
            line-height: 1.1;
        }
        .muted {
            opacity: 0.7;
            font-size: 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def find_counter(counters: List[Counter], counter_id: str) -> Optional[Counter]:
    for counter in counters:
        if counter.id == counter_id:
            return counter
    return None


def move_counter(counters: List[Counter], counter_id: str, direction: int) -> List[Counter]:
    idx = next((i for i, c in enumerate(counters) if c.id == counter_id), None)
    if idx is None:
        return counters

    new_idx = idx + direction
    if new_idx < 0 or new_idx >= len(counters):
        return counters

    counters[idx], counters[new_idx] = counters[new_idx], counters[idx]
    return counters


def render_counter(counter: Counter, counters: List[Counter]) -> None:
    with st.container(border=True):
        col_name, col_count, col_minus, col_plus, col_reset, col_up, col_down, col_delete = st.columns(
            [3.5, 1, 0.75, 0.75, 1, 0.65, 0.65, 0.85],
            vertical_alignment="center",
        )

        new_name = col_name.text_input(
            "Counter name",
            value=counter.name,
            key=f"name_{counter.id}",
            label_visibility="collapsed",
        )

        if new_name.strip() and new_name.strip() != counter.name:
            counter.name = new_name.strip()
            save_counters(counters)
            st.rerun()

        col_count.markdown(f"<div class='counter-count'>{counter.count}</div>", unsafe_allow_html=True)

        if col_minus.button("-1", key=f"minus_{counter.id}", use_container_width=True):
            counter.count -= 1
            save_counters(counters)
            st.rerun()

        if col_plus.button("+1", key=f"plus_{counter.id}", use_container_width=True):
            counter.count += 1
            save_counters(counters)
            st.rerun()

        if col_reset.button("Reset", key=f"reset_{counter.id}", use_container_width=True):
            counter.count = 0
            save_counters(counters)
            st.rerun()

        if col_up.button("↑", key=f"up_{counter.id}", use_container_width=True):
            counters = move_counter(counters, counter.id, -1)
            save_counters(counters)
            st.rerun()

        if col_down.button("↓", key=f"down_{counter.id}", use_container_width=True):
            counters = move_counter(counters, counter.id, 1)
            save_counters(counters)
            st.rerun()

        if col_delete.button("Delete", key=f"delete_{counter.id}", use_container_width=True):
            st.session_state[f"confirm_delete_{counter.id}"] = True
            st.rerun()

        if st.session_state.get(f"confirm_delete_{counter.id}", False):
            st.warning(f"Delete “{counter.name}”?")
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Yes, delete", key=f"confirm_yes_{counter.id}"):
                save_counters([c for c in counters if c.id != counter.id])
                st.session_state.pop(f"confirm_delete_{counter.id}", None)
                st.rerun()
            if cancel_col.button("Cancel", key=f"confirm_no_{counter.id}"):
                st.session_state.pop(f"confirm_delete_{counter.id}", None)
                st.rerun()


def parse_imported_counters(data: Any) -> List[Counter]:
    """
    Accepts:
    - Original local JSON: [ {"name": "...", "count": 0}, ... ]
    - Online backup JSON: [ {"id": "...", "name": "...", "count": 0}, ... ]
    - Wrapped format: {"counters": [...]}
    """
    if isinstance(data, dict):
        if isinstance(data.get("counters"), list):
            data = data["counters"]
        else:
            raise ValueError("JSON object found, but it does not contain a 'counters' list.")

    if not isinstance(data, list):
        raise ValueError("JSON must be a list of counters or an object containing a 'counters' list.")

    return [Counter.from_dict(item) for item in data]


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    inject_css()

    st.title(APP_TITLE)
    st.caption(f"{APP_VERSION} · Sweden time: {sweden_now_str()}")

    try:
        counters = load_counters()
    except Exception as exc:
        st.error(f"Could not load data from Google Sheets backend: {exc}")
        st.stop()

    with st.sidebar:
        st.header("Google Sheets")
        st.write("Counters are saved to the Google Sheet configured in Streamlit secrets.")

        if st.button("Reload from Google Sheet", use_container_width=True):
            force_reload_counters()
            st.rerun()

        st.divider()
        st.header("Import / export")

        st.download_button(
            "Download JSON backup",
            data=json.dumps([asdict(c) for c in counters], indent=2),
            file_name="multi_counter_backup.json",
            mime="application/json",
            use_container_width=True,
        )

        uploaded = st.file_uploader("Import JSON backup", type=["json"])
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                imported = parse_imported_counters(data)
                st.success(f"Ready to import {len(imported)} counter(s).")

                if st.button("Replace Google Sheet counters", use_container_width=True):
                    save_counters(imported)
                    st.success("Imported.")
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not import JSON: {exc}")

        st.divider()
        st.header("Danger zone")
        if st.button("Delete all counters", use_container_width=True):
            st.session_state["confirm_delete_all"] = True

        if st.session_state.get("confirm_delete_all", False):
            st.warning("Delete all counters?")
            if st.button("Yes, delete all", use_container_width=True):
                save_counters([])
                st.session_state["confirm_delete_all"] = False
                st.rerun()
            if st.button("Cancel", use_container_width=True):
                st.session_state["confirm_delete_all"] = False
                st.rerun()

    with st.form("add_counter_form"):
        st.subheader("Add counter")
        new_name = st.text_input("New counter name", placeholder="e.g. GFP-positive cells")
        submitted = st.form_submit_button("Add New Counter")

    if submitted:
        name = new_name.strip()
        if not name:
            st.error("Please enter a counter name.")
        else:
            counters.append(Counter(name=name, count=0, updated_at=sweden_now_str()))
            save_counters(counters)
            st.rerun()

    st.header("Counters")

    if not counters:
        st.info("No counters yet. Add one above.")
    else:
        for counter in counters:
            render_counter(counter, counters)

    with st.expander("Raw data"):
        st.dataframe(pd.DataFrame([asdict(c) for c in counters]), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
