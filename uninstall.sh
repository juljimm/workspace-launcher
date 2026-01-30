#!/bin/bash
echo "Removing workspace..."
rm -f "$HOME/bin/workspace"
rm -f "$HOME/.config/workspace-launcher/workspace.py"
rm -f "$HOME/.config/workspace-launcher/workspace-launcher.sh"
rm -f "$HOME/.local/share/applications/workspace-launcher.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/workspace-launcher.svg"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo ""
echo "Uninstall complete."
echo "Note: Templates in ~/.config/workspace-launcher/templates/ were preserved."
echo "To remove everything: rm -rf ~/.config/workspace-launcher/"
