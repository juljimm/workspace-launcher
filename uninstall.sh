#!/bin/bash
echo "Removing workspace..."
rm -f "$HOME/bin/workspace"
rm -f "$HOME/.config/workspace-launcher/workspace.py"
echo ""
echo "Uninstall complete."
echo "Note: Templates in ~/.config/workspace-launcher/templates/ were preserved."
echo "To remove everything: rm -rf ~/.config/workspace-launcher/"
