#!/bin/bash
# GNOME Desktop wrapper for Workspace Launcher
# Uses native GTK4/libadwaita selector

CONFIG_DIR="$HOME/.config/workspace-launcher"

exec python3 "$CONFIG_DIR/workspace-selector.py"
