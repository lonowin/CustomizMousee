import os
import json


def config_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "CustomizeMousee")


def default_config() -> dict:
    return {
        "cursor_type":        "Custom Cursor",
        "enable_trails":      True,
        "halo_enabled":       True,
        "opacity":            220,
        "trail_length":       30,
        "halo_radius":        24,
        "trail_color":        [255, 30, 67],
        "halo_color":         [40, 230, 80],
        "theme":              "Dark",
        "run_background":     False,
        "ui_scale":           100,
        "trail_width":        7,
        "trail_texture_path": "",
    }


def load_config() -> dict:
    path = os.path.join(config_dir(), "settings.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = default_config()
            cfg.update(data)      # fill missing keys with defaults
            return cfg
        except Exception:
            pass
    # Automatically create settings.json with default values if it doesn't exist
    cfg = default_config()
    try:
        save_config(cfg)
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(config_dir(), exist_ok=True)
    path = os.path.join(config_dir(), "settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
