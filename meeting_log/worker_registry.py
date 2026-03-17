"""Module-level worker registry shared across Streamlit pages.

This dict survives Streamlit reruns and must NOT live inside a page module,
because Streamlit may reload page modules on navigation.
"""

import threading

active_workers: dict[str, threading.Thread] = {}
