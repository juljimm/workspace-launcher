#!/usr/bin/env python3
"""
Native GNOME template selector using GTK4 + libadwaita
Fully integrated with system theme (light/dark)
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
import os
import sys
import yaml
import subprocess

TEMPLATES_DIR = os.path.expanduser("~/.config/workspace-launcher/templates")
WORKSPACE_CMD = os.path.expanduser("~/.config/workspace-launcher/workspace.py")


class TemplateRow(Adw.ActionRow):
    """A row representing a template"""
    def __init__(self, name, description):
        super().__init__()
        self.template_name = name
        self.set_title(name)
        if description:
            self.set_subtitle(description)
        self.set_activatable(True)

        # Add arrow icon
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        arrow.add_css_class("dim-label")
        self.add_suffix(arrow)


class TemplateSelector(Adw.ApplicationWindow):
    """Main selector window"""
    def __init__(self, app, templates):
        super().__init__(application=app)
        self.templates = templates
        self.filtered_rows = []

        # Window properties
        self.set_title("Workspace Launcher")
        self.set_default_size(420, 500)
        self.set_resizable(False)

        # Center on screen after realize
        self.connect("realize", self.center_on_screen)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title="Workspace Launcher",
            subtitle=f"{len(templates)} templates"
        ))
        main_box.append(header)

        # Content with clamp for proper sizing
        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        main_box.append(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        clamp.set_child(content_box)

        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar templates...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", self.on_search_activate)
        content_box.append(self.search_entry)

        # Scrolled window for list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(300)
        content_box.append(scrolled)

        # List box in a preferences group style
        self.list_group = Adw.PreferencesGroup()
        scrolled.set_child(self.list_group)

        # Populate templates
        self.all_rows = []
        for name, desc in sorted(templates.items()):
            row = TemplateRow(name, desc)
            row.connect("activated", self.on_template_activated)
            self.list_group.add(row)
            self.all_rows.append(row)

        self.filtered_rows = self.all_rows.copy()

        # Keyboard shortcuts
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(controller)

        # Focus search on start
        self.search_entry.grab_focus()

    def on_search_changed(self, entry):
        """Filter templates based on search text"""
        search_text = entry.get_text().lower()
        self.filtered_rows = []

        for row in self.all_rows:
            name = row.template_name.lower()
            subtitle = (row.get_subtitle() or "").lower()
            matches = search_text in name or search_text in subtitle
            row.set_visible(matches)
            if matches:
                self.filtered_rows.append(row)

    def on_search_activate(self, entry):
        """Execute first visible template on Enter"""
        if self.filtered_rows:
            self.launch_template(self.filtered_rows[0].template_name)

    def on_template_activated(self, row):
        """Launch selected template"""
        self.launch_template(row.template_name)

    def on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard navigation"""
        if keyval == 65307:  # Escape
            self.close()
            return True
        return False

    def launch_template(self, name):
        """Execute workspace command with template"""
        self.close()
        subprocess.Popen(
            ["python3", WORKSPACE_CMD, name],
            start_new_session=True
        )

    def center_on_screen(self, widget):
        """Center window on screen"""
        # Schedule centering after window is mapped
        GLib.timeout_add(50, self._do_center)

    def _do_center(self):
        """Actually center the window using wmctrl"""
        try:
            # Get screen dimensions
            display = self.get_display()
            monitors = display.get_monitors()
            if monitors.get_n_items() > 0:
                # Find primary or first monitor
                monitor = None
                for i in range(monitors.get_n_items()):
                    m = monitors.get_item(i)
                    if hasattr(m, 'is_primary') and m.is_primary():
                        monitor = m
                        break
                if not monitor:
                    monitor = monitors.get_item(0)

                geometry = monitor.get_geometry()
                win_width, win_height = self.get_default_size()
                x = geometry.x + (geometry.width - win_width) // 2
                y = geometry.y + (geometry.height - win_height) // 2

                # Use wmctrl to move window
                subprocess.run(
                    ["wmctrl", "-r", ":ACTIVE:", "-e", f"0,{x},{y},{win_width},{win_height}"],
                    capture_output=True
                )
        except Exception:
            pass
        return False  # Don't repeat


class SelectorApp(Adw.Application):
    """Main application"""
    def __init__(self):
        super().__init__(
            application_id="com.workspace.launcher.selector",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.templates = {}

    def sync_shortcuts(self):
        """Sincroniza shortcuts .desktop con templates"""
        subprocess.run(
            ["python3", WORKSPACE_CMD, "--sync-shortcuts"],
            capture_output=True
        )

    def do_activate(self):
        # Sincronizar shortcuts al iniciar
        self.sync_shortcuts()

        # Load templates
        self.templates = self.load_templates()

        if not self.templates:
            self.show_no_templates_dialog()
            return

        if len(self.templates) == 1:
            # Single template - launch directly
            name = list(self.templates.keys())[0]
            subprocess.Popen(
                ["python3", WORKSPACE_CMD, name],
                start_new_session=True
            )
            self.quit()
            return

        # Multiple templates - show selector
        win = TemplateSelector(self, self.templates)
        win.present()

    def load_templates(self):
        """Load all templates from config directory"""
        templates = {}
        if not os.path.isdir(TEMPLATES_DIR):
            return templates

        for filename in os.listdir(TEMPLATES_DIR):
            if filename.endswith('.yml') or filename.endswith('.yaml'):
                name = filename.rsplit('.', 1)[0]
                filepath = os.path.join(TEMPLATES_DIR, filename)
                desc = self.get_template_description(filepath)
                templates[name] = desc

        return templates

    def get_template_description(self, filepath):
        """Extract description from template file"""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('description', '')
        except:
            return ''

    def show_no_templates_dialog(self):
        """Show message when no templates exist"""
        dialog = Adw.MessageDialog(
            heading="Sin templates",
            body=f"No hay templates disponibles.\n\nCrea templates en:\n{TEMPLATES_DIR}/"
        )
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: self.quit())
        dialog.present()


def main():
    app = SelectorApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
