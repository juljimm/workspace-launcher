#!/usr/bin/env python3
"""
Workspace Launcher - Open workspaces defined in YAML
Usage: workspace <template-name>
       workspace --list
"""

import yaml
import subprocess
import time
import sys
import os
import re
from pathlib import Path
from fractions import Fraction

TEMPLATES_DIR = Path.home() / ".config/workspace-launcher/templates"

# Monitor configuration (auto-detected)
MONITORS = {}


def detect_monitors():
    """Detecta monitores conectados usando xrandr.
    Retorna dict con nombre de output como clave (ej: DP-1, HDMI-0).
    También añade 'primary' como alias del monitor primario."""
    monitors = {}
    primary_name = None

    result = subprocess.run(["xrandr", "--query"], capture_output=True, text=True)
    if result.returncode != 0:
        return monitors

    for line in result.stdout.splitlines():
        if " connected" not in line:
            continue

        parts = line.split()
        name = parts[0]  # ej: DP-1, HDMI-0

        is_primary = "primary" in parts

        # Buscar geometría: WxH+X+Y
        geom_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
        if not geom_match:
            continue

        w, h, x, y = map(int, geom_match.groups())

        monitors[name] = {"x": x, "y": y, "w": w, "h": h}

        if is_primary:
            primary_name = name

    # Añadir alias 'primary'
    if primary_name and primary_name in monitors:
        monitors["primary"] = monitors[primary_name]
    elif monitors:
        # Si no hay primary marcado, usar el primero
        first = list(monitors.values())[0]
        monitors["primary"] = first

    return monitors

# Predefined position shortcuts
SHORTCUTS = {
    "full": "tl w:100% h:100%",
    "left": "tl w:50% h:100%",
    "right": "tr w:50% h:100%",
    "top": "tl w:100% h:50%",
    "bottom": "bl w:100% h:50%",
    "top-left": "tl w:50% h:50%",
    "top-right": "tr w:50% h:50%",
    "bottom-left": "bl w:50% h:50%",
    "bottom-right": "br w:50% h:50%",
    "left-third": "tl w:1/3 h:100%",
    "center-third": "x:1/3 w:1/3 h:100%",
    "right-third": "x:2/3 w:1/3 h:100%",
    "top-third": "tl w:100% h:1/3",
    "middle-third": "y:1/3 w:100% h:1/3",
    "bottom-third": "y:2/3 w:100% h:1/3",
    "left-two-thirds": "tl w:2/3 h:100%",
    "right-two-thirds": "x:1/3 w:2/3 h:100%",
}


def parse_value(value_str, total):
    """Parse a value string (%, fraction, or pixels) to pixels"""
    value_str = str(value_str).strip()

    # Percentage: "50%"
    if value_str.endswith('%'):
        return int(total * float(value_str[:-1]) / 100)

    # Fraction: "1/3", "2/3"
    if '/' in value_str:
        frac = Fraction(value_str)
        return int(total * float(frac))

    # Pixels: "800"
    return int(value_str)


def parse_position(position_str, monitor):
    """Parse position string into x, y, w, h"""
    mon = MONITORS.get(monitor, MONITORS["primary"])

    # Handle dict format (absolute positioning)
    if isinstance(position_str, dict):
        return (
            position_str.get('x', mon['x']),
            position_str.get('y', mon['y']),
            position_str.get('width', mon['w']),
            position_str.get('height', mon['h'])
        )

    # Expand shortcuts
    if position_str in SHORTCUTS:
        position_str = SHORTCUTS[position_str]

    # Default values
    x_rel, y_rel = 0, 0  # Relative position within monitor (0-1)
    w_rel, h_rel = 1.0, 1.0  # Size as fraction of monitor
    anchor = "tl"

    # Parse tokens
    tokens = position_str.split()
    for token in tokens:
        if token in ['tl', 'tr', 'bl', 'br', 'c']:
            anchor = token
        elif token.startswith('x:'):
            val = token[2:]
            if '%' in val:
                x_rel = float(val.rstrip('%')) / 100
            elif '/' in val:
                x_rel = float(Fraction(val))
            else:
                x_rel = int(val) / mon['w']
        elif token.startswith('y:'):
            val = token[2:]
            if '%' in val:
                y_rel = float(val.rstrip('%')) / 100
            elif '/' in val:
                y_rel = float(Fraction(val))
            else:
                y_rel = int(val) / mon['h']
        elif token.startswith('w:'):
            val = token[2:]
            if '%' in val:
                w_rel = float(val.rstrip('%')) / 100
            elif '/' in val:
                w_rel = float(Fraction(val))
            else:
                w_rel = int(val) / mon['w']  # Absolute pixels
        elif token.startswith('h:'):
            val = token[2:]
            if '%' in val:
                h_rel = float(val.rstrip('%')) / 100
            elif '/' in val:
                h_rel = float(Fraction(val))
            else:
                h_rel = int(val) / mon['h']  # Absolute pixels

    # Calculate actual dimensions
    w = int(mon['w'] * w_rel)
    h = int(mon['h'] * h_rel)

    # Calculate position based on anchor
    if anchor == 'tl':
        x = mon['x'] + int(mon['w'] * x_rel)
        y = mon['y'] + int(mon['h'] * y_rel)
    elif anchor == 'tr':
        x = mon['x'] + mon['w'] - w - int(mon['w'] * x_rel)
        y = mon['y'] + int(mon['h'] * y_rel)
    elif anchor == 'bl':
        x = mon['x'] + int(mon['w'] * x_rel)
        y = mon['y'] + mon['h'] - h - int(mon['h'] * y_rel)
    elif anchor == 'br':
        x = mon['x'] + mon['w'] - w - int(mon['w'] * x_rel)
        y = mon['y'] + mon['h'] - h - int(mon['h'] * y_rel)
    elif anchor == 'c':
        x = mon['x'] + (mon['w'] - w) // 2 + int(mon['w'] * x_rel)
        y = mon['y'] + (mon['h'] - h) // 2 + int(mon['h'] * y_rel)
    else:
        x = mon['x'] + int(mon['w'] * x_rel)
        y = mon['y'] + int(mon['h'] * y_rel)

    return x, y, w, h


def check_dependencies():
    """Check that wmctrl and xdotool are installed"""
    missing = []
    for cmd in ["wmctrl", "xdotool"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            missing.append(cmd)
    if missing:
        print(f"Error: Missing dependencies: {' '.join(missing)}")
        print("Run: sudo apt install " + " ".join(missing))
        sys.exit(1)


def move_to_desktop(win_id, desktop, by_id=True):
    """Move window to specified desktop"""
    if by_id:
        subprocess.run(["wmctrl", "-i", "-r", win_id, "-t", str(desktop - 1)],
                       capture_output=True)
    else:
        subprocess.run(["wmctrl", "-r", win_id, "-t", str(desktop - 1)],
                       capture_output=True)


def unmaximize_window(win_id, by_id=True):
    """Desmaximiza una ventana antes de posicionarla"""
    if by_id:
        subprocess.run(["wmctrl", "-i", "-r", win_id, "-b",
                        "remove,maximized_vert,maximized_horz"], capture_output=True)
    else:
        subprocess.run(["wmctrl", "-r", win_id, "-b",
                        "remove,maximized_vert,maximized_horz"], capture_output=True)


def get_frame_extents(win_id):
    """Obtiene los frame extents (sombras/decoraciones) de una ventana GTK.
    Retorna (left, right, top, bottom) o (0, 0, 0, 0) si no existe."""
    result = subprocess.run(
        ["xprop", "-id", win_id, "_GTK_FRAME_EXTENTS"],
        capture_output=True, text=True
    )
    # Formato: _GTK_FRAME_EXTENTS(CARDINAL) = 26, 26, 23, 29
    if "=" in result.stdout:
        try:
            values = result.stdout.split("=")[1].strip()
            parts = [int(x.strip()) for x in values.split(",")]
            if len(parts) == 4:
                return tuple(parts)
        except (ValueError, IndexError):
            pass
    return (0, 0, 0, 0)


def position_window(win_id, x, y, w, h):
    """Posiciona una ventana compensando por frame extents (sombras GTK)."""
    # Obtener frame extents para compensar
    left, right, top, bottom = get_frame_extents(win_id)

    # Compensar posición (restar para mover la ventana visible al borde)
    adj_x = x - left
    adj_y = y - top
    # Compensar tamaño (añadir para que el contenido visible tenga el tamaño deseado)
    adj_w = w + left + right
    adj_h = h + top + bottom

    geom = f"{adj_x},{adj_y},{adj_w},{adj_h}"
    subprocess.run(["wmctrl", "-i", "-r", win_id, "-e", f"0,{geom}"], capture_output=True)


def open_window(window_config):
    """Open a window according to its configuration"""
    wtype = window_config["type"]
    monitor = window_config.get("monitor", "primary")
    position = window_config.get("position", "full")
    desktop = window_config.get("desktop", 1)

    x, y, w, h = parse_position(position, monitor)
    geom = f"{x},{y},{w},{h}"

    if wtype == "kitty":
        title = window_config.get("title", "Kitty")
        cmd = window_config["command"]
        subprocess.Popen(
            ["kitty", "--title", title, "-e", "bash", "-c", f"{cmd}; exec bash"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2.0)
        # Buscar ventana por nombre para obtener window ID
        result = subprocess.run(
            ["xdotool", "search", "--name", title],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            win_id = result.stdout.strip().split()[-1]
            move_to_desktop(win_id, desktop, by_id=True)
            unmaximize_window(win_id, by_id=True)
            time.sleep(0.1)
            position_window(win_id, x, y, w, h)
        else:
            # Fallback: usar título directamente
            move_to_desktop(title, desktop, by_id=False)
            unmaximize_window(title, by_id=False)
            time.sleep(0.1)
            subprocess.run(["wmctrl", "-r", title, "-e", f"0,{geom}"], capture_output=True)

    elif wtype == "app":
        cmd = window_config["command"]
        window_class = window_config.get("window_class")

        # Inferir clase de ventana del comando si no está especificada
        if not window_class:
            cmd_name = cmd.split()[0].split("/")[-1]
            window_class = cmd_name

        # Obtener ventanas existentes de esta clase ANTES de abrir
        existing = subprocess.run(
            ["xdotool", "search", "--class", window_class],
            capture_output=True, text=True
        )
        existing_ids = set(existing.stdout.strip().split()) if existing.stdout.strip() else set()

        # Abrir la aplicación
        subprocess.Popen(
            cmd.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2.5)

        # Buscar ventana nueva de esta clase
        result = subprocess.run(
            ["xdotool", "search", "--class", window_class],
            capture_output=True, text=True
        )
        current_ids = set(result.stdout.strip().split()) if result.stdout.strip() else set()
        new_ids = current_ids - existing_ids

        if new_ids:
            win_id = list(new_ids)[0]  # Tomar la primera ventana nueva
            move_to_desktop(win_id, desktop, by_id=True)
            unmaximize_window(win_id, by_id=True)
            time.sleep(0.1)
            position_window(win_id, x, y, w, h)
        elif current_ids:
            # Fallback: usar la ventana más reciente de esa clase
            win_id = list(current_ids)[-1]
            move_to_desktop(win_id, desktop, by_id=True)
            unmaximize_window(win_id, by_id=True)
            time.sleep(0.1)
            position_window(win_id, x, y, w, h)


def load_template(name):
    """Load and execute a YAML template"""
    template_file = TEMPLATES_DIR / f"{name}.yml"
    if not template_file.exists():
        template_file = TEMPLATES_DIR / name
        if not template_file.exists():
            print(f"Error: Template '{name}' not found")
            print(f"Look in: {TEMPLATES_DIR}")
            return False

    with open(template_file) as f:
        config = yaml.safe_load(f)

    name_display = config.get("name", name)
    print(f"Loading workspace: {name_display}")

    for window in config.get("windows", []):
        try:
            open_window(window)
            print(f"  ✓ {window.get('title', window.get('type'))}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("Workspace loaded.")
    return True


def list_templates():
    """List available templates"""
    if not TEMPLATES_DIR.exists():
        print(f"Templates directory not found: {TEMPLATES_DIR}")
        return

    templates = list(TEMPLATES_DIR.glob("*.yml"))
    if not templates:
        print("No templates available.")
        print(f"Create one in: {TEMPLATES_DIR}/my-template.yml")
        return

    print("Available templates:\n")
    for f in sorted(templates):
        with open(f) as file:
            try:
                config = yaml.safe_load(file)
                name = f.stem
                desc = config.get("description", "No description")
                print(f"  {name}")
                print(f"    {desc}\n")
            except yaml.YAMLError:
                print(f"  {f.stem} (read error)")


def show_help():
    """Show help"""
    print("""
Workspace Launcher - Open workspaces defined in YAML

Usage:
  workspace <name>       Load the specified template
  workspace --list       List available templates
  workspace --monitors   List detected monitors
  workspace --help       Show this help

Templates in: ~/.config/workspace-launcher/templates/

Monitor names:
  Use output names from xrandr (DP-1, HDMI-0, etc.) or "primary".
  Run 'workspace --monitors' to see available monitors.

Position syntax:
  "[anchor] [x:val] [y:val] [w:val] [h:val]"

  Anchors: tl (top-left), tr (top-right), bl, br, c (center)
  Values:  50% (percentage), 1/3 (fraction), 800 (pixels)

Examples:
  monitor: DP-1                    # Use specific monitor
  monitor: primary                 # Use primary monitor
  position: "tl w:1/3 h:100%"      # Left third
  position: "x:20% w:60% h:80%"    # Custom position
  position: left-third             # Shortcut

Shortcuts: full, left, right, top, bottom,
           top-left, top-right, bottom-left, bottom-right,
           left-third, center-third, right-third,
           left-two-thirds, right-two-thirds
""")


def list_monitors():
    """Lista los monitores detectados"""
    print("Monitores detectados:\n")
    for name, mon in MONITORS.items():
        if name == "primary":
            continue
        is_primary = " (primary)" if MONITORS.get("primary") == mon else ""
        print(f"  {name}{is_primary}")
        print(f"    Posición: {mon['x']},{mon['y']}  Tamaño: {mon['w']}x{mon['h']}\n")


def main():
    global MONITORS
    check_dependencies()
    MONITORS = detect_monitors()

    if not MONITORS:
        print("Error: No se detectaron monitores")
        sys.exit(1)

    if len(sys.argv) < 2 or sys.argv[1] in ["--list", "-l"]:
        list_templates()
        return

    if sys.argv[1] in ["--monitors", "-m"]:
        list_monitors()
        return

    if sys.argv[1] in ["--help", "-h"]:
        show_help()
        return

    load_template(sys.argv[1])


if __name__ == "__main__":
    main()
