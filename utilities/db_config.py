"""
Database configuration settings.

Connection settings now live in an external config.json file
(next to the .exe / app folder) instead of being hardcoded here.
This means an IP change just requires editing that JSON file —
no recompiling, no redistributing the app.
"""

import json
import os
import sys

# Default values used ONLY if config.json doesn't exist yet
# (e.g. first run, or fresh install on a new PC)
DEFAULT_CONFIG = {
    'dbname': 'rvs_dbase',
    'user': 'postgres',
    'password': 'cod34food',
    'host': '192.168.254.119',
    'port': '5432'
}


def _get_config_path():
    """
    Returns the path to config.json.
    Works whether running as a normal .py script or as a
    PyInstaller-compiled .exe.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe -> use the folder the .exe is in
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as a normal .py script
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, 'config.json')


def _load_config():
    config_path = _get_config_path()

    if not os.path.exists(config_path):
        # First run: create config.json using the defaults
        _save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Config file is corrupted/unreadable -> fall back to defaults
        # so the app doesn't crash on launch
        return DEFAULT_CONFIG.copy()


def _save_config(config_dict):
    config_path = _get_config_path()
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=4)


def update_config(new_values: dict):
    """
    Call this to update connection settings at runtime
    (e.g. from a 'Server Settings' dialog in the app).
    Updates both the in-memory POSTGRES_CONFIG and config.json.
    """
    global POSTGRES_CONFIG
    POSTGRES_CONFIG.update(new_values)
    _save_config(POSTGRES_CONFIG)


# This is what every other module imports — same name, same shape,
# so nothing else in the app needs to change.
POSTGRES_CONFIG = _load_config()
