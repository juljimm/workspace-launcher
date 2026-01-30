#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$HOME/.config/workspace-launcher"
BIN_DIR="$HOME/bin"

echo "=== Installing Workspace Launcher ==="

# 1. Install system dependencies
echo "Checking system dependencies..."
MISSING=()
command -v wmctrl >/dev/null || MISSING+=("wmctrl")
command -v xdotool >/dev/null || MISSING+=("xdotool")

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "Installing: ${MISSING[*]}"
    sudo apt install -y "${MISSING[@]}"
fi

# 2. Install pyyaml
echo "Checking pyyaml..."
python3 -c "import yaml" 2>/dev/null || pip install --user pyyaml

# 3. Detect monitors
echo "Detecting monitors..."
MONITORS_INFO=""
PRIMARY_MONITOR=""
FIRST_MONITOR=""

while IFS= read -r line; do
    if [[ "$line" =~ ^([A-Za-z0-9-]+)\ connected ]]; then
        name="${BASH_REMATCH[1]}"
        [[ -z "$FIRST_MONITOR" ]] && FIRST_MONITOR="$name"

        # Extract geometry WxH+X+Y
        if [[ "$line" =~ ([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+) ]]; then
            w="${BASH_REMATCH[1]}"
            h="${BASH_REMATCH[2]}"
            x="${BASH_REMATCH[3]}"
            y="${BASH_REMATCH[4]}"

            is_primary=""
            if [[ "$line" =~ " primary " ]]; then
                PRIMARY_MONITOR="$name"
                is_primary=" (primary)"
            fi

            MONITORS_INFO+="#   - $name: ${w}x${h} at position ${x},${y}${is_primary}\n"
        fi
    fi
done < <(xrandr --query)

# Use first monitor as default if no primary
[[ -z "$PRIMARY_MONITOR" ]] && PRIMARY_MONITOR="$FIRST_MONITOR"

# 4. Create config directory
echo "Creating config directory..."
mkdir -p "$CONFIG_DIR/templates"

# 5. Copy main script
echo "Installing workspace script..."
cp "$SCRIPT_DIR/workspace.py" "$CONFIG_DIR/workspace.py"
chmod +x "$CONFIG_DIR/workspace.py"

# 6. Generate example template with detected monitors
if [[ ! -f "$CONFIG_DIR/templates/example.yml" ]]; then
    echo "Creating example template..."
    cat > "$CONFIG_DIR/templates/example.yml" << TEMPLATE
# Example template for Workspace Launcher
# Copy and modify as needed

name: Example
description: Example template showing different window types and positions

# Detected monitors (run 'workspace --monitors' to update):
$(echo -e "$MONITORS_INFO")
#   - primary: Alias for the primary monitor

# Position syntax: "[anchor] [x:val] [y:val] [w:val] [h:val]"
#   Anchors: tl (top-left), tr (top-right), bl, br, c (center)
#   Values: 50% (percentage), 1/3 (fraction), 800 (pixels)
#
# Shortcuts: full, left, right, top, bottom,
#            top-left, top-right, bottom-left, bottom-right,
#            left-third, center-third, right-third

windows:
  # Kitty terminal - left third of primary monitor
  - type: kitty
    title: "Main Terminal"
    command: "echo 'Hello from Workspace Launcher!'; exec bash"
    monitor: ${PRIMARY_MONITOR}
    position: "tl w:1/3 h:100%"
    desktop: 1

  # Example: Browser in center two-thirds
  # - type: app
  #   command: "firefox https://github.com"
  #   monitor: ${PRIMARY_MONITOR}
  #   position: "x:1/3 w:2/3 h:100%"

  # Example: Small terminal in corner
  # - type: kitty
  #   title: "Logs"
  #   command: "tail -f /var/log/syslog"
  #   monitor: ${PRIMARY_MONITOR}
  #   position: "br w:25% h:30%"
TEMPLATE
fi

# 7. Copy other templates (without overwriting)
for template in "$SCRIPT_DIR"/templates/*.yml; do
    name=$(basename "$template")
    [[ "$name" == "example.yml" ]] && continue
    if [[ ! -f "$CONFIG_DIR/templates/$name" ]]; then
        cp "$template" "$CONFIG_DIR/templates/"
    fi
done

# 8. Create symlink in ~/bin
echo "Creating symlink..."
mkdir -p "$BIN_DIR"
ln -sf "$CONFIG_DIR/workspace.py" "$BIN_DIR/workspace"

# 9. Install GNOME desktop integration
echo "Installing GNOME desktop integration..."
cp "$SCRIPT_DIR/workspace-launcher.sh" "$CONFIG_DIR/workspace-launcher.sh"
chmod +x "$CONFIG_DIR/workspace-launcher.sh"

# Install icon following freedesktop.org spec
ICON_NAME="workspace-launcher"
if [[ -f "$SCRIPT_DIR/workspace_launcher.svg" ]]; then
    echo "Installing icon..."
    mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"
    cp "$SCRIPT_DIR/workspace_launcher.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/${ICON_NAME}.svg"
    # Update icon cache
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
else
    ICON_NAME="utilities-terminal"
fi

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/workspace-launcher.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Workspace Launcher
Comment=Open predefined window layouts
Exec=$CONFIG_DIR/workspace-launcher.sh
Icon=$ICON_NAME
Terminal=false
Categories=Utility;System;
DESKTOP

# Check zenity
if ! command -v zenity >/dev/null; then
    echo "Nota: Instala zenity para selector GUI: sudo apt install zenity"
fi

# 10. Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "NOTE: Add ~/bin to your PATH if you haven't:"
    echo '  echo '\''export PATH="$HOME/bin:$PATH"'\'' >> ~/.bashrc'
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Detected monitors:"
echo -e "$MONITORS_INFO" | sed 's/^#//'
echo ""
echo "Usage: workspace <template-name>"
echo "       workspace --monitors    # List monitors"
echo "       workspace --list        # List templates"
echo ""
echo "GNOME: Search 'Workspace Launcher' in Activities"
echo ""
echo "Templates in: $CONFIG_DIR/templates/"
