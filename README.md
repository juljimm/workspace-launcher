# Workspace Launcher

A Python CLI tool that automates opening and positioning windows on Linux desktops using YAML configuration templates.

> Coded with AI (Claude), designed and orchestrated by the author.

## Features

- **Parallel window launching**: Different window types open simultaneously for faster workspace setup
- **Smart polling**: Windows are positioned as soon as they appear (no fixed delays)
- **Multi-monitor support**: Auto-detects monitors via xrandr
- **Flexible positioning**: Percentages, fractions, pixels, and preset shortcuts
- **GNOME integration**: Desktop shortcuts for quick access from Activities

## Requirements

- Python 3
- pyyaml
- wmctrl
- xdotool

Install dependencies on Debian/Ubuntu:

```bash
sudo apt install wmctrl xdotool python3-yaml
```

## Installation

```bash
./install.sh
```

To uninstall:

```bash
./uninstall.sh
```

## Usage

```bash
workspace <template>        # Load a template
workspace --list            # List available templates
workspace --monitors        # Show detected monitors
workspace --sync-shortcuts  # Sync .desktop shortcuts with templates
workspace --list-shortcuts  # List installed shortcuts
workspace --help            # Show help
```

## Templates

Templates are YAML files stored in `~/.config/workspace-launcher/templates/`.

### Example Template

```yaml
name: Development
description: My development workspace
shortcut: true  # Create .desktop shortcut (default: true)

windows:
  - type: kitty
    title: "Editor"
    command: "nvim ."
    monitor: primary
    position: left-two-thirds
    desktop: 1

  - type: kitty
    title: "Terminal"
    command: ""
    monitor: primary
    position: right-third
    desktop: 1

  - type: app
    command: firefox
    monitor: DP-2
    position: full
    desktop: 2
```

### Template Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | filename | Display name for the workspace |
| `description` | string | - | Description shown in listings |
| `shortcut` | bool | true | Create .desktop shortcut for GNOME |

## Window Types

| Type | Description | Required Fields | Optional |
|------|-------------|-----------------|----------|
| `kitty` | Kitty terminal | command | title |
| `app` | Generic application | command | window_class |

## Position Syntax

```yaml
position: "[anchor] [x:val] [y:val] [w:val] [h:val]"
```

### Anchors

- `tl` - top-left (default)
- `tr` - top-right
- `bl` - bottom-left
- `br` - bottom-right
- `c` - center

### Values

- Percentage: `50%`, `33%`, `100%`
- Fraction: `1/2`, `1/3`, `2/3`, `1/4`
- Pixels: `800`, `1920`

### Examples

```yaml
position: "tl w:1/3 h:100%"       # Left third, full height
position: "x:20% w:60% h:80%"     # 60% wide starting at 20%
position: "tr w:50% h:50%"        # Top-right quarter
position: "c w:800 h:600"         # Centered, 800x600 pixels
position: "x:1/3 w:1/3 h:100%"    # Center third (column)
```

### Shortcuts

| Shortcut | Description |
|----------|-------------|
| `full` | Full screen |
| `left` | Left half |
| `right` | Right half |
| `top` | Top half |
| `bottom` | Bottom half |
| `top-left` | Top-left quarter |
| `top-right` | Top-right quarter |
| `bottom-left` | Bottom-left quarter |
| `bottom-right` | Bottom-right quarter |
| `left-third` | Left third |
| `center-third` | Center third |
| `right-third` | Right third |
| `left-two-thirds` | Left two-thirds |
| `right-two-thirds` | Right two-thirds |

## Monitor Configuration

Monitors are auto-detected using `xrandr`. Use the output names (e.g., `DP-1`, `HDMI-0`, `eDP-1`) or `primary` for the primary monitor.

```bash
workspace --monitors    # Show detected monitors
```

Example monitor usage in templates:

```yaml
windows:
  - type: kitty
    command: htop
    monitor: DP-1        # Specific monitor
    position: full

  - type: app
    command: firefox
    monitor: primary     # Primary monitor
    position: left
```

## GNOME Integration

Workspace Launcher integrates with GNOME desktop:

- **Main launcher**: Search "Workspace Launcher" in Activities to open the template selector
- **Template shortcuts**: Each template with `shortcut: true` gets its own .desktop entry (prefixed with "WS:")

Sync shortcuts after adding/removing templates:

```bash
workspace --sync-shortcuts
```

## Performance

Windows are launched in parallel by type:
- Different types (kitty, firefox, code) open simultaneously
- Same type (multiple firefox windows) open sequentially to avoid conflicts
- Active polling detects windows as soon as they appear (100ms intervals)

Typical improvement: 4+ windows load in ~3-4s instead of ~10s.

## License

MIT License - see [LICENSE](LICENSE) file.
