# Workspace Launcher

A Python CLI tool that automates opening and positioning windows on Linux desktops using YAML configuration templates.

> Coded with AI (Claude), designed and orchestrated by the author.

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
workspace <template>    # Load a template
workspace --list        # List available templates
workspace --monitors    # Show detected monitors
workspace --help        # Show help
```

## Templates

Templates are YAML files stored in `~/.config/workspace-launcher/templates/`.

### Example Template

```yaml
name: Development
description: My development workspace

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
    window_class: firefox
    monitor: DP-2
    position: full
    desktop: 2
```

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

## License

MIT License - see [LICENSE](LICENSE) file.
