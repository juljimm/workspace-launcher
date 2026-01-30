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
from concurrent.futures import ThreadPoolExecutor, as_completed

TEMPLATES_DIR = Path.home() / ".config/workspace-launcher/templates"
DESKTOP_DIR = Path.home() / ".local/share/applications"
CONFIG_DIR = Path.home() / ".config/workspace-launcher"
ICON_NAME = "workspace-launcher"

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
    left, right, top, bottom = get_frame_extents(win_id)
    adj_x = x - left
    adj_y = y - top
    adj_w = w + left + right
    adj_h = h + top + bottom
    geom = f"{adj_x},{adj_y},{adj_w},{adj_h}"
    subprocess.run(["wmctrl", "-i", "-r", win_id, "-e", f"0,{geom}"], capture_output=True)


def get_window_ids_by_name(name):
    """Obtiene IDs de ventanas por nombre usando xdotool."""
    result = subprocess.run(
        ["xdotool", "search", "--name", name],
        capture_output=True, text=True
    )
    return set(result.stdout.strip().split()) if result.stdout.strip() else set()


def get_window_ids_by_class(window_class):
    """Obtiene IDs de ventanas por clase usando xdotool."""
    result = subprocess.run(
        ["xdotool", "search", "--class", window_class],
        capture_output=True, text=True
    )
    return set(result.stdout.strip().split()) if result.stdout.strip() else set()


def wait_for_window_by_name(name, existing_ids, timeout=5.0, poll_interval=0.1):
    """Espera hasta que aparezca una ventana nueva con el nombre dado."""
    start = time.time()
    while time.time() - start < timeout:
        current_ids = get_window_ids_by_name(name)
        new_ids = current_ids - existing_ids
        if new_ids:
            return list(new_ids)[-1]  # Última ventana (más reciente)
        time.sleep(poll_interval)
    return None


def wait_for_window_by_class(window_class, existing_ids, timeout=5.0, poll_interval=0.1):
    """Espera hasta que aparezca una ventana nueva con la clase dada."""
    start = time.time()
    while time.time() - start < timeout:
        current_ids = get_window_ids_by_class(window_class)
        new_ids = current_ids - existing_ids
        if new_ids:
            return list(new_ids)[0]  # Primera ventana nueva
        time.sleep(poll_interval)
    return None


def open_window(window_config):
    """Open a window according to its configuration"""
    wtype = window_config["type"]
    monitor = window_config.get("monitor", "primary")
    position = window_config.get("position", "full")
    desktop = window_config.get("desktop", 1)

    x, y, w, h = parse_position(position, monitor)

    if wtype == "kitty":
        title = window_config.get("title", "Kitty")
        cmd = window_config["command"]

        # Obtener ventanas existentes ANTES de abrir
        existing_ids = get_window_ids_by_name(title)

        subprocess.Popen(
            ["kitty", "--title", title, "-e", "bash", "-c", f"{cmd}; exec bash"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Esperar a que aparezca la ventana
        win_id = wait_for_window_by_name(title, existing_ids, timeout=5.0)

        if win_id:
            move_to_desktop(win_id, desktop, by_id=True)
            unmaximize_window(win_id, by_id=True)
            time.sleep(0.1)
            position_window(win_id, x, y, w, h)
            return (True, title)
        return (False, title)

    elif wtype == "app":
        cmd = window_config["command"]
        window_class = window_config.get("window_class")

        if not window_class:
            cmd_name = cmd.split()[0].split("/")[-1]
            window_class = cmd_name

        # Obtener ventanas existentes ANTES de abrir
        existing_ids = get_window_ids_by_class(window_class)

        subprocess.Popen(
            cmd.split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Esperar a que aparezca la ventana
        win_id = wait_for_window_by_class(window_class, existing_ids, timeout=5.0)

        if win_id:
            move_to_desktop(win_id, desktop, by_id=True)
            unmaximize_window(win_id, by_id=True)
            time.sleep(0.1)
            position_window(win_id, x, y, w, h)
            return (True, window_class)
        return (False, window_class)

    return (False, "unknown")


def get_window_group_key(window_config):
    """Obtiene la clave de agrupación para evitar race conditions.

    Ventanas del mismo grupo se procesan secuencialmente.
    Ventanas de grupos diferentes se procesan en paralelo.
    """
    wtype = window_config["type"]
    if wtype == "kitty":
        # Cada kitty tiene título único, pueden ir en paralelo
        return ("kitty", window_config.get("title", "Kitty"))
    elif wtype == "app":
        # Agrupar por clase de ventana (ej: múltiples librewolf)
        window_class = window_config.get("window_class")
        if not window_class:
            cmd = window_config["command"]
            window_class = cmd.split()[0].split("/")[-1]
        return ("app", window_class)
    return ("unknown", "unknown")


def process_window_group(windows_in_group):
    """Procesa un grupo de ventanas del mismo tipo secuencialmente.

    Para ventanas que comparten la misma clase (ej: múltiples librewolf),
    las procesa una por una para evitar race conditions.

    Returns:
        list of (success, window_title) tuples
    """
    results = []
    for window_config in windows_in_group:
        try:
            success, title = open_window(window_config)
            results.append((success, title))
        except Exception as e:
            results.append((False, f"{window_config.get('title', 'unknown')}: {e}"))
    return results


def load_template(name):
    """Load and execute a YAML template with parallel window launching"""
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
    windows = config.get("windows", [])

    if not windows:
        print(f"Workspace '{name_display}' has no windows defined.")
        return True

    print(f"Loading workspace: {name_display}")

    # Agrupar ventanas por ejecutable
    # Ventanas del mismo grupo (ej: 2 librewolf) se procesan secuencialmente
    # Grupos diferentes (kitty, librewolf, code) se procesan en paralelo
    groups = {}
    for window in windows:
        key = get_window_group_key(window)
        if key not in groups:
            groups[key] = []
        groups[key].append(window)

    # Procesar grupos en paralelo, ventanas dentro de cada grupo secuencialmente
    all_results = []
    with ThreadPoolExecutor(max_workers=len(groups)) as executor:
        futures = {
            executor.submit(process_window_group, group_windows): key
            for key, group_windows in groups.items()
        }

        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"  ✗ Error processing group: {e}")

    # Mostrar resultados
    for success, title in all_results:
        if success:
            print(f"  ✓ {title}")
        else:
            print(f"  ✗ {title}")

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


# =============================================================================
# Shortcut (.desktop) management functions
# =============================================================================

def sanitize_filename(name):
    """Convierte un nombre en uno seguro para usar como nombre de archivo.

    Args:
        name: Nombre del template

    Returns:
        Nombre sanitizado (lowercase, sin espacios ni caracteres especiales)
    """
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', name.lower())
    sanitized = re.sub(r'-+', '-', sanitized)
    return sanitized.strip('-')


def get_template_metadata(template_path):
    """Extrae metadatos de un archivo de template YAML.

    Args:
        template_path: Path al archivo .yml

    Returns:
        dict con keys: name, description, shortcut (bool)
        Retorna None si hay error al leer
    """
    try:
        with open(template_path) as f:
            config = yaml.safe_load(f)
            return {
                "name": config.get("name", template_path.stem),
                "description": config.get("description", ""),
                "shortcut": config.get("shortcut", True)
            }
    except (yaml.YAMLError, IOError):
        return None


def generate_desktop_entry(template_name, metadata):
    """Genera el contenido de un archivo .desktop para un template.

    Args:
        template_name: Nombre del archivo de template (sin extensión)
        metadata: dict con name, description

    Returns:
        String con el contenido del archivo .desktop
    """
    display_name = metadata.get("name", template_name)
    description = metadata.get("description", f"Workspace: {display_name}")

    return f"""[Desktop Entry]
Version=1.0
Type=Application
Name=WS: {display_name}
Comment={description}
Exec=python3 {CONFIG_DIR}/workspace.py '{template_name}'
Icon={ICON_NAME}
Terminal=false
Categories=Utility;System;
Keywords=workspace;layout;windows;{template_name};
StartupNotify=false
"""


def get_desktop_filename(template_name):
    """Genera el nombre del archivo .desktop para un template."""
    safe_name = sanitize_filename(template_name)
    return DESKTOP_DIR / f"workspace-launcher-{safe_name}.desktop"


def install_template_shortcut(template_name, metadata=None):
    """Instala un archivo .desktop para un template.

    Args:
        template_name: Nombre del archivo de template (sin extensión)
        metadata: Metadatos del template (opcional, se lee si no se provee)

    Returns:
        True si se instaló correctamente, False en caso contrario
    """
    if metadata is None:
        template_path = TEMPLATES_DIR / f"{template_name}.yml"
        metadata = get_template_metadata(template_path)
        if metadata is None:
            return False

    if not metadata.get("shortcut", True):
        return False

    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    desktop_content = generate_desktop_entry(template_name, metadata)
    desktop_file = get_desktop_filename(template_name)

    try:
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        return True
    except IOError:
        return False


def remove_template_shortcut(template_name):
    """Elimina el archivo .desktop de un template."""
    desktop_file = get_desktop_filename(template_name)
    try:
        if desktop_file.exists():
            desktop_file.unlink()
        return True
    except IOError:
        return False


def sync_shortcuts():
    """Sincroniza los shortcuts .desktop con los templates existentes.

    - Crea shortcuts para templates con shortcut: true (o sin campo)
    - Elimina shortcuts de templates con shortcut: false
    - Elimina shortcuts huérfanos (templates eliminados)

    Returns:
        dict con estadísticas: created, removed, errors
    """
    stats = {"created": 0, "removed": 0, "errors": 0}

    if not TEMPLATES_DIR.exists():
        return stats

    current_templates = {}
    for template_file in TEMPLATES_DIR.glob("*.yml"):
        template_name = template_file.stem
        metadata = get_template_metadata(template_file)
        if metadata:
            current_templates[template_name] = metadata

    existing_shortcuts = set()
    if DESKTOP_DIR.exists():
        for desktop_file in DESKTOP_DIR.glob("workspace-launcher-*.desktop"):
            name_part = desktop_file.stem.replace("workspace-launcher-", "", 1)
            existing_shortcuts.add(name_part)

    templates_with_shortcuts = set()
    for template_name, metadata in current_templates.items():
        safe_name = sanitize_filename(template_name)
        should_have_shortcut = metadata.get("shortcut", True)

        if should_have_shortcut:
            templates_with_shortcuts.add(safe_name)
            if install_template_shortcut(template_name, metadata):
                if safe_name not in existing_shortcuts:
                    stats["created"] += 1
            else:
                stats["errors"] += 1
        else:
            if safe_name in existing_shortcuts:
                if remove_template_shortcut(template_name):
                    stats["removed"] += 1
                else:
                    stats["errors"] += 1

    orphan_shortcuts = existing_shortcuts - templates_with_shortcuts
    for safe_name in orphan_shortcuts:
        desktop_file = DESKTOP_DIR / f"workspace-launcher-{safe_name}.desktop"
        try:
            if desktop_file.exists():
                desktop_file.unlink()
                stats["removed"] += 1
        except IOError:
            stats["errors"] += 1

    return stats


def list_shortcuts():
    """Lista los shortcuts .desktop instalados."""
    if not DESKTOP_DIR.exists():
        print("No hay shortcuts instalados.")
        return

    shortcuts = list(DESKTOP_DIR.glob("workspace-launcher-*.desktop"))
    if not shortcuts:
        print("No hay shortcuts instalados.")
        return

    print("Shortcuts instalados:\n")
    for desktop_file in sorted(shortcuts):
        try:
            with open(desktop_file) as f:
                content = f.read()
                name_match = re.search(r'^Name=(.+)$', content, re.MULTILINE)
                name = name_match.group(1) if name_match else desktop_file.stem
                print(f"  {name}")
                print(f"    {desktop_file}\n")
        except IOError:
            print(f"  {desktop_file.stem} (error de lectura)")


def show_help():
    """Show help"""
    print("""
Workspace Launcher - Open workspaces defined in YAML

Usage:
  workspace <name>           Load the specified template
  workspace --list           List available templates
  workspace --monitors       List detected monitors
  workspace --sync-shortcuts Sync .desktop shortcuts with templates
  workspace --list-shortcuts List installed shortcuts
  workspace --help           Show this help

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

Template options:
  shortcut: true/false   Create/skip .desktop shortcut (default: true)
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

    # Opciones que no requieren detectar monitores
    if len(sys.argv) >= 2:
        if sys.argv[1] in ["--sync-shortcuts"]:
            stats = sync_shortcuts()
            if stats["created"] or stats["removed"]:
                print(f"Shortcuts: {stats['created']} creados, {stats['removed']} eliminados")
            return

        if sys.argv[1] in ["--list-shortcuts"]:
            list_shortcuts()
            return

        if sys.argv[1] in ["--help", "-h"]:
            show_help()
            return

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

    load_template(sys.argv[1])


if __name__ == "__main__":
    main()
