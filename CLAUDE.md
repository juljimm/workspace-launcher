# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Workspace Launcher is a Python CLI tool that automates opening and positioning windows on Linux desktops using YAML configuration templates. It uses `wmctrl` and `xdotool` for window management.

## Commands

```bash
# Install
./install.sh

# Uninstall
./uninstall.sh

# Run (after installation)
workspace --list        # List templates
workspace <template>    # Load a template
workspace --help        # Show help
```

## Architecture

Single-file Python script (`workspace.py`) with no test suite. Templates are stored in `~/.config/workspace-launcher/templates/` as YAML files.

**Key components in workspace.py:**
- `parse_position()` - Converts position strings (anchors, percentages, fractions) to pixel coordinates
- `open_window()` - Spawns windows using subprocess and positions them with wmctrl
- `load_template()` - Parses YAML template and opens all defined windows

**Window types supported:** `kitty` (terminal), `app` (generic application)

**Dependencies:** Python 3, pyyaml, wmctrl, xdotool

## Position System

Position strings follow format: `"[anchor] [x:val] [y:val] [w:val] [h:val]"`

- Anchors: `tl`, `tr`, `bl`, `br`, `c` (top-left, top-right, bottom-left, bottom-right, center)
- Values: percentages (`50%`), fractions (`1/3`), or pixels (`800`)
- Shortcuts defined in `SHORTCUTS` dict: `full`, `left`, `right`, `left-third`, etc.

## Monitor Configuration

Hardcoded in `MONITORS` dict at top of workspace.py. Currently configured for dual-monitor setup with left (1200x1920 rotated) and right (3840x2160 primary).

## Development Workflow

**Siempre que se modifique código, ejecutar la instalación para aplicar los cambios:**

```bash
./install.sh
```

Esto es necesario porque el script se copia a `~/.config/workspace-launcher/workspace.py` durante la instalación. Los cambios en el código fuente no afectan la instalación local hasta que se ejecute el instalador.

Esto aplica especialmente cuando:
- Se modifica `workspace.py`
- Se cambia la sintaxis de templates
- Se añaden nuevos shortcuts o tipos de ventana
