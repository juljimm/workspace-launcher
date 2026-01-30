#!/bin/bash
# GNOME Desktop wrapper for Workspace Launcher
# Shows a selector GUI with icons when multiple templates exist

TEMPLATES_DIR="$HOME/.config/workspace-launcher/templates"
WORKSPACE_CMD="$HOME/.config/workspace-launcher/workspace.py"
CONFIG_DIR="$HOME/.config/workspace-launcher"
ICON_CACHE_DIR="/tmp/workspace-launcher-icons"

# Create icon cache directory
mkdir -p "$ICON_CACHE_DIR"

# Function to generate icon with initial letter
generate_initial_icon() {
    local name="$1"
    local output="$2"
    local initial="${name:0:1}"
    initial="${initial^^}"  # uppercase

    if command -v convert >/dev/null; then
        convert -size 48x48 xc:"#3584e4" -fill white -gravity center \
                -pointsize 32 -annotate 0 "$initial" "$output" 2>/dev/null
        return 0
    fi
    return 1
}

# Function to get icon for a template
get_template_icon() {
    local tmpl="$1"
    local file="$TEMPLATES_DIR/$tmpl.yml"
    local cached_icon="$ICON_CACHE_DIR/$tmpl.png"

    # Check if template has custom icon defined
    local custom_icon=$(grep -m1 "^icon:" "$file" 2>/dev/null | sed 's/^icon:[[:space:]]*//')

    if [[ -n "$custom_icon" ]] && [[ -f "$custom_icon" ]]; then
        # Use custom icon, resize if needed
        if command -v convert >/dev/null; then
            convert "$custom_icon" -background none -resize 48x48 "$cached_icon" 2>/dev/null && echo "$cached_icon" && return
        fi
        echo "$custom_icon"
        return
    fi

    # Generate icon with initial letter
    if [[ ! -f "$cached_icon" ]] || [[ "$file" -nt "$cached_icon" ]]; then
        if generate_initial_icon "$tmpl" "$cached_icon"; then
            echo "$cached_icon"
            return
        fi
    elif [[ -f "$cached_icon" ]]; then
        echo "$cached_icon"
        return
    fi

    # Fallback: no icon
    echo ""
}

# Get available templates
templates=()
for file in "$TEMPLATES_DIR"/*.yml; do
    [[ -f "$file" ]] && templates+=("$(basename "${file%.yml}")")
done

count=${#templates[@]}

# Case: 0 templates
if [[ $count -eq 0 ]]; then
    zenity --info --title="Workspace Launcher" \
           --text="No hay templates disponibles.\n\nCrea templates en:\n$TEMPLATES_DIR/" \
           --width=300
    exit 0
fi

# Case: 1 template - execute directly
if [[ $count -eq 1 ]]; then
    exec python3 "$WORKSPACE_CMD" "${templates[0]}"
fi

# Case: N templates - show zenity selector with icons
# Check if ImageMagick is available for icon generation
has_imagemagick=false
command -v convert >/dev/null && has_imagemagick=true

if $has_imagemagick; then
    # Build list with icons (icon, name, description)
    list_items=()
    for tmpl in "${templates[@]}"; do
        file="$TEMPLATES_DIR/$tmpl.yml"
        # Get icon
        icon=$(get_template_icon "$tmpl")
        # Extract description from YAML
        desc=$(grep -m1 "^description:" "$file" 2>/dev/null | sed 's/^description:[[:space:]]*//')
        [[ -z "$desc" ]] && desc="(sin descripcion)"
        list_items+=("$icon" "$tmpl" "$desc")
    done

    selected=$(zenity --list \
        --imagelist \
        --title="Workspace Launcher" \
        --text="Selecciona un template:" \
        --column="" --column="Template" --column="Descripcion" \
        --hide-column=1 --print-column=2 \
        --width=500 --height=350 \
        "${list_items[@]}" 2>/dev/null)
else
    # Fallback: simple list without icons
    list_items=()
    for tmpl in "${templates[@]}"; do
        file="$TEMPLATES_DIR/$tmpl.yml"
        desc=$(grep -m1 "^description:" "$file" 2>/dev/null | sed 's/^description:[[:space:]]*//')
        [[ -z "$desc" ]] && desc="(sin descripcion)"
        list_items+=("$tmpl" "$desc")
    done

    selected=$(zenity --list \
        --title="Workspace Launcher" \
        --text="Selecciona un template:" \
        --column="Template" --column="Descripcion" \
        --width=500 --height=300 \
        "${list_items[@]}" 2>/dev/null)
fi

# Execute selected template
if [[ -n "$selected" ]]; then
    exec python3 "$WORKSPACE_CMD" "$selected"
fi
