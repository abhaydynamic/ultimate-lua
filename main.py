import os
import sys
import json
import shutil
import subprocess
from io import StringIO
from lupa import LuaRuntime

from kivy.config import Config
# Emulate mobile screen ratios for accurate desktop testing
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '750')

from kivy.core.window import Window
from kivy.uix.codeinput import CodeInput
from kivy.uix.textinput import TextInput
from kivy.extras.highlight import KivyLexer
from kivy.uix.screenmanager import ScreenManager
from kivy.metrics import dp
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDList, OneLineAvatarIconListItem, IconLeftWidget, IconRightWidget
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.navigationdrawer import MDNavigationLayout, MDNavigationDrawer
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.slider import MDSlider
from kivymd.uix.label import MDLabel

# --- POLICY-COMPLIANT LOCAL ENVIRONMENT PATHS ---
WORKSPACE_DIR = os.path.join(os.path.expanduser("~"), "LuaProjectsWorkspace")
STATE_FILE = os.path.join(WORKSPACE_DIR, ".ide_session_state.json")
SETTINGS_FILE = os.path.join(WORKSPACE_DIR, ".ide_settings.json")

if not os.path.exists(WORKSPACE_DIR):
    os.makedirs(WORKSPACE_DIR)

DEFAULT_FILE = os.path.join(WORKSPACE_DIR, "main.lua")
if not os.path.exists(DEFAULT_FILE):
    with open(DEFAULT_FILE, "w", encoding="utf-8") as f:
        f.write('-- Dribbble UI Update\nlocal math_mod = "Engine Activated"\nprint(math_mod)\n\nfor i = 1, 3 do\n    print("Iteration: " .. i)\nend')

OFFLINE_DOCS = {
    "print": "print(...) -> Outputs values cleanly to the system debug console layout.",
    "local": "local var = val -> Declares a lexically scoped local variable framework.",
    "for": "for i = start, stop, step do ... end -> Standard counter loop logic configuration.",
    "if": "if condition then ... elseif cond then ... else ... end -> Execution branching path.",
    "function": "function name(args) ... end -> Declares an executable Lua block assignment.",
    "while": "while condition do ... end -> Repeats a block as long as the condition is true.",
    "return": "return val -> Exits a function and optionally passes back a value.",
    "math": "math library -> Provides standard mathematical functions.",
    "string": "string library -> Provides standard string manipulation functions.",
    "table": "table library -> Provides generic functions for table manipulation."
}

class AutoIndentCodeInput(CodeInput):
    """Custom CodeInput supporting basic auto-indentation and Kivy's native undo/redo."""
    def insert_text(self, substring, from_undo=False):
        app = MDApp.get_running_app()
        auto_indent = app.ide_settings.get("auto_indent", True) if app else True
        
        if auto_indent and substring == '\n':
            lines = self.text[:self.cursor_index()].split('\n')
            if lines:
                prev_line = lines[-1]
                indent = len(prev_line) - len(prev_line.lstrip(' \t'))
                substring += prev_line[:indent]
        super().insert_text(substring, from_undo)


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        self.labels = []
        
        self.layout = MDBoxLayout(orientation='vertical')
        
        self.toolbar = MDTopAppBar(
            title="Settings",
            anchor_title="left",
            elevation=0
        )
        self.toolbar.left_action_items = [["arrow-left", lambda x: MDApp.get_running_app().switch_to_editor()]]
        self.layout.add_widget(self.toolbar)
        
        content = MDBoxLayout(orientation='vertical', padding=dp(24), spacing=dp(24))
        
        # Dark Mode Toggle
        row_theme = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
        lbl_theme = MDLabel(text="Dark Mode", theme_text_color="Custom")
        self.labels.append(lbl_theme)
        row_theme.add_widget(lbl_theme)
        self.dark_mode_switch = MDSwitch()
        self.dark_mode_switch.bind(active=self.on_setting_change)
        row_theme.add_widget(self.dark_mode_switch)
        content.add_widget(row_theme)

        # Line Numbers Toggle
        row1 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
        lbl1 = MDLabel(text="Show Line Numbers", theme_text_color="Custom")
        self.labels.append(lbl1)
        row1.add_widget(lbl1)
        self.line_num_switch = MDSwitch()
        self.line_num_switch.bind(active=self.on_setting_change)
        row1.add_widget(self.line_num_switch)
        content.add_widget(row1)
        
        # Auto Save Toggle
        row_auto_save = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
        lbl_save = MDLabel(text="Auto Save to Disk", theme_text_color="Custom")
        self.labels.append(lbl_save)
        row_auto_save.add_widget(lbl_save)
        self.auto_save_switch = MDSwitch()
        self.auto_save_switch.bind(active=self.on_setting_change)
        row_auto_save.add_widget(self.auto_save_switch)
        content.add_widget(row_auto_save)
        
        # Auto Indent Toggle
        row_auto_indent = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
        lbl_indent = MDLabel(text="Auto Indentation", theme_text_color="Custom")
        self.labels.append(lbl_indent)
        row_auto_indent.add_widget(lbl_indent)
        self.auto_indent_switch = MDSwitch()
        self.auto_indent_switch.bind(active=self.on_setting_change)
        row_auto_indent.add_widget(self.auto_indent_switch)
        content.add_widget(row_auto_indent)

        # Font Size Slider
        row_font = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48))
        lbl_font = MDLabel(text="Font Size", size_hint_x=0.4, theme_text_color="Custom")
        self.labels.append(lbl_font)
        row_font.add_widget(lbl_font)
        self.font_slider = MDSlider(min=10, max=30, step=1, value=16, size_hint_x=0.6)
        self.font_slider.bind(value=self.on_setting_change)
        row_font.add_widget(self.font_slider)
        content.add_widget(row_font)
        
        content.add_widget(MDBoxLayout()) 
        self.layout.add_widget(content)
        self.add_widget(self.layout)

    def update_theme(self, is_dark):
        bg = (0.1, 0.1, 0.1, 1) if is_dark else (0.95, 0.95, 0.95, 1)
        text = (0.9, 0.9, 0.9, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        
        self.toolbar.md_bg_color = bg
        self.toolbar.specific_text_color = text
        self.layout.md_bg_color = bg
        
        for label in self.labels:
            label.text_color = text

    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        self.font_slider.value = app.ide_settings.get("font_size", 16)
        
        target_lines = app.ide_settings.get("show_line_numbers", True)
        target_save = app.ide_settings.get("auto_save", True)
        target_indent = app.ide_settings.get("auto_indent", True)
        target_dark = app.ide_settings.get("dark_mode", False)
        
        Clock.schedule_once(lambda dt: self._apply_switch_states(target_lines, target_save, target_indent, target_dark), 0)

    def _apply_switch_states(self, lines, save, indent, dark):
        self.line_num_switch.active = lines
        self.auto_save_switch.active = save
        self.auto_indent_switch.active = indent
        self.dark_mode_switch.active = dark

    def on_setting_change(self, *args):
        app = MDApp.get_running_app()
        app.ide_settings["show_line_numbers"] = self.line_num_switch.active
        app.ide_settings["auto_save"] = self.auto_save_switch.active
        app.ide_settings["auto_indent"] = self.auto_indent_switch.active
        app.ide_settings["dark_mode"] = self.dark_mode_switch.active
        app.ide_settings["font_size"] = int(self.font_slider.value)
        app.save_settings()
        app.apply_settings()


class EditorScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'editor'
        self.save_event = None
        
        layout = MDBoxLayout(orientation='vertical')
        
        self.toolbar = MDTopAppBar(title="main.lua", anchor_title="left", elevation=0)
        self.toolbar.left_action_items = [["menu", lambda x: MDApp.get_running_app().toggle_nav_drawer()]]
        self.toolbar.right_action_items = [
            ["cog", lambda x: MDApp.get_running_app().switch_to_settings()],
            ["book-open-variant", lambda x: self.show_offline_documentation_dialog()],
            ["play-circle", lambda x: MDApp.get_running_app().execute_lua_script()]
        ]
        layout.add_widget(self.toolbar)
        
        self.editor_container = MDBoxLayout(orientation='horizontal')
        
        self.line_numbers = TextInput(
            text="1\n",
            readonly=True,
            size_hint_x=None,
            width=dp(35),
            font_size=16,
            padding=(dp(4), dp(12)),
            halign="right"
        )
        
        self.editor_input = AutoIndentCodeInput(
            lexer=KivyLexer(),
            font_size=16,
            cursor_color=(0, 0.6, 0.3, 1),
            padding=(dp(12), dp(12)),
            size_hint_x=1
        )
        self.editor_input.bind(text=self.on_text_change)
        self.editor_input.bind(scroll_y=self.sync_scroll)
        
        self.editor_container.add_widget(self.line_numbers)
        self.editor_container.add_widget(self.editor_input)
        layout.add_widget(self.editor_container)
        
        self.macro_scroller = MDScrollView(size_hint_y=None, height=dp(48), do_scroll_y=False, do_scroll_x=True)
        self.macro_bar = MDBoxLayout(orientation='horizontal', size_hint_x=None, padding=dp(4), spacing=dp(4))
        self.macro_bar.bind(minimum_width=self.macro_bar.setter('width'))
        
        quick_glyphs = ["Undo", "Redo", "Tabs", "{", "}", "[", "]", "(", ")", "=", '"', "_", "←", "→"]
        for glyph in quick_glyphs:
            btn = MDFlatButton(
                text=glyph,
                theme_text_color="Custom",
                font_size=14,
                size_hint_x=None,
                width=dp(50) if len(glyph) < 4 else dp(65)
            )
            btn.bind(on_release=self.process_macro_insertion)
            self.macro_bar.add_widget(btn)
            
        self.macro_scroller.add_widget(self.macro_bar)
        
        self.bottom_container = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(48))
        self.bottom_container.add_widget(self.macro_scroller)
        layout.add_widget(self.bottom_container)
        
        self.add_widget(layout)

    def update_theme(self, is_dark):
        bg = (0.1, 0.1, 0.1, 1) if is_dark else (0.95, 0.95, 0.95, 1)
        text = (0.9, 0.9, 0.9, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        ed_bg = (0.05, 0.05, 0.05, 1) if is_dark else (1, 1, 1, 1)
        ed_fg = (0.9, 0.9, 0.9, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        line_bg = (0.08, 0.08, 0.08, 1) if is_dark else (0.95, 0.95, 0.95, 1)
        
        self.toolbar.md_bg_color = bg
        self.toolbar.specific_text_color = text
        self.line_numbers.background_color = line_bg
        self.line_numbers.foreground_color = (0.4, 0.4, 0.4, 1) if is_dark else (0.5, 0.5, 0.5, 1)
        self.editor_input.background_color = ed_bg
        self.editor_input.foreground_color = ed_fg
        
        self.bottom_container.md_bg_color = bg
        self.macro_scroller.md_bg_color = bg
        for btn in self.macro_bar.children:
            btn.md_bg_color = (0.15, 0.15, 0.15, 1) if is_dark else (0.9, 0.9, 0.9, 1)
            btn.text_color = (0.8, 0.8, 0.8, 1) if is_dark else (0.2, 0.2, 0.2, 1)

    def on_text_change(self, instance, text_content):
        lines = text_content.count('\n') + 1
        self.line_numbers.text = '\n'.join(str(i) for i in range(1, lines + 1)) + '\n'
        
        app = MDApp.get_running_app()
        state_data = {
            "last_active_file": app.current_open_file,
            "buffer_cache": text_content
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f)
        except IOError:
            pass

        if app.ide_settings.get("auto_save", True):
            if self.save_event:
                self.save_event.cancel()
            self.save_event = Clock.schedule_once(self.trigger_auto_save, 2.0)

    def trigger_auto_save(self, dt):
        MDApp.get_running_app().save_active_buffer_to_disk()

    def sync_scroll(self, instance, value):
        self.line_numbers.scroll_y = value

    def apply_settings(self, settings):
        font_size = settings.get("font_size", 16)
        self.editor_input.font_size = font_size
        self.line_numbers.font_size = font_size
        
        show_lines = settings.get("show_line_numbers", True)
        self.editor_container.clear_widgets()
        if show_lines:
            self.editor_container.add_widget(self.line_numbers)
        self.editor_container.add_widget(self.editor_input)

    def process_macro_insertion(self, instance):
        token = instance.text
        if token == "Undo":
            self.editor_input.do_undo()
        elif token == "Redo":
            self.editor_input.do_redo()
        elif token == "Tabs":
            self.editor_input.insert_text("    ")
        elif token == "←":
            self.editor_input.do_cursor_movement('cursor_left')
        elif token == "→":
            self.editor_input.do_cursor_movement('cursor_right')
        else:
            pairs = {"{": "}", "[": "]", "(": ")", '"': '"'}
            if token in pairs:
                self.editor_input.insert_text(f"{token}{pairs[token]}")
                self.editor_input.do_cursor_movement('cursor_left')
            else:
                self.editor_input.insert_text(token)

    def show_offline_documentation_dialog(self):
        current_selection = self.editor_input.selection_text.strip()
        
        if not current_selection:
            text = self.editor_input.text
            cursor_idx = self.editor_input.cursor_index()
            
            start = cursor_idx
            while start > 0 and (text[start-1].isalnum() or text[start-1] == '_'):
                start -= 1
                
            end = cursor_idx
            while end < len(text) and (text[end].isalnum() or text[end] == '_'):
                end += 1
                
            current_selection = text[start:end].strip()

        if not current_selection:
            title = "Lua Docs"
            doc_text = "Place your cursor inside or highlight a valid keyword (like 'print', 'local', 'for') to view docs."
        else:
            title = f"Lua Docs: '{current_selection}'"
            doc_text = OFFLINE_DOCS.get(
                current_selection,
                f"No short docs available for '{current_selection}'. Try standard Lua keywords."
            )
            
        self.doc_dialog = MDDialog(
            title=title,
            text=doc_text,
            buttons=[MDFlatButton(text="DISMISS", on_release=lambda x: self.doc_dialog.dismiss())]
        )
        self.doc_dialog.open()


class ConsoleScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'console'
        self.repl_mode = "LUA"
        self.lua_runtime = LuaRuntime(unpack_returned_tuples=True)
        self.lua_runtime.execute("print = python.builtins.print")
        
        layout = MDBoxLayout(orientation='vertical')
        
        self.toolbar = MDTopAppBar(
            title="Terminal & REPL",
            anchor_title="left",
            elevation=0
        )
        self.toolbar.left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().switch_to_editor()]]
        self.toolbar.right_action_items=[["trash-can-outline", lambda x: self.clear_terminal()]]
        layout.add_widget(self.toolbar)
        
        self.terminal_output = MDTextField(
            text="Type below to interact directly with the interpreter or shell.\n",
            multiline=True,
            readonly=True,
            font_name="RobotoMono-Regular",
            font_size=14,
            mode="fill"
        )
        self.scroller = MDScrollView()
        self.scroller.add_widget(self.terminal_output)
        layout.add_widget(self.scroller)
        
        self.input_area = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(100))
        
        self.macro_scroller = MDScrollView(size_hint_y=None, height=dp(40), do_scroll_y=False, do_scroll_x=True)
        self.macro_bar = MDBoxLayout(orientation='horizontal', size_hint_x=None, padding=dp(2), spacing=dp(4))
        self.macro_bar.bind(minimum_width=self.macro_bar.setter('width'))
        for glyph in ["Tabs", "←", "→", "-", "/", "*", "(", ")", '"', "'"]:
            btn = MDFlatButton(
                text=glyph, theme_text_color="Custom", 
                font_size=12, size_hint_x=None, width=dp(45)
            )
            btn.bind(on_release=self.process_terminal_macro)
            self.macro_bar.add_widget(btn)
        self.macro_scroller.add_widget(self.macro_bar)
        self.input_area.add_widget(self.macro_scroller)
        
        cmd_box = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), padding=dp(8), spacing=dp(8))
        
        self.mode_btn = MDRaisedButton(text="LUA", size_hint_x=None, width=dp(60))
        self.mode_btn.bind(on_release=self.toggle_repl_mode)
        cmd_box.add_widget(self.mode_btn)
        
        self.cmd_input = MDTextField(
            hint_text="Enter command...",
            multiline=False,
            mode="round"
        )
        self.cmd_input.bind(on_text_validate=self.execute_repl_command)
        cmd_box.add_widget(self.cmd_input)
        
        self.send_btn = MDIconButton(icon="send", theme_text_color="Custom")
        self.send_btn.bind(on_release=self.execute_repl_command)
        cmd_box.add_widget(self.send_btn)
        
        self.input_area.add_widget(cmd_box)
        layout.add_widget(self.input_area)
        
        self.add_widget(layout)

    def update_theme(self, is_dark):
        bg = (0.1, 0.1, 0.1, 1) if is_dark else (0.95, 0.95, 0.95, 1)
        text = (1, 1, 1, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        term_bg = (0.05, 0.05, 0.05, 1) if is_dark else (1, 1, 1, 1)
        
        self.toolbar.md_bg_color = bg
        self.toolbar.specific_text_color = text
        self.terminal_output.fill_color_normal = term_bg
        self.terminal_output.fill_color_focus = term_bg
        self.terminal_output.text_color_normal = (0, 0.9, 0.4, 1) if is_dark else (0, 0.5, 0.2, 1)
        self.terminal_output.text_color_focus = (0, 0.9, 0.4, 1) if is_dark else (0, 0.5, 0.2, 1)
        
        self.scroller.md_bg_color = bg
        self.input_area.md_bg_color = (0.1, 0.1, 0.1, 1) if is_dark else (0.92, 0.92, 0.92, 1)
        
        self.cmd_input.fill_color_normal = (0.15, 0.15, 0.15, 1) if is_dark else (1, 1, 1, 1)
        self.cmd_input.fill_color_focus = (0.2, 0.2, 0.2, 1) if is_dark else (1, 1, 1, 1)
        self.cmd_input.text_color_normal = (1, 1, 1, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        self.send_btn.text_color = (0, 0.9, 0.4, 1) if is_dark else (0, 0.6, 0.3, 1)
        
        for btn in self.macro_bar.children:
            btn.md_bg_color = (0.15, 0.15, 0.15, 1) if is_dark else (0.85, 0.85, 0.85, 1)
            btn.text_color = (0.8, 0.8, 0.8, 1) if is_dark else (0.2, 0.2, 0.2, 1)

    def toggle_repl_mode(self, instance):
        self.repl_mode = "BASH" if self.repl_mode == "LUA" else "LUA"
        self.mode_btn.text = self.repl_mode

    def process_terminal_macro(self, instance):
        token = instance.text
        if token == "Tabs":
            self.cmd_input.insert_text("    ")
        elif token == "←":
            self.cmd_input.do_cursor_movement('cursor_left')
        elif token == "→":
            self.cmd_input.do_cursor_movement('cursor_right')
        else:
            self.cmd_input.insert_text(token)

    def execute_repl_command(self, *args):
        cmd = self.cmd_input.text.strip()
        if not cmd:
            return
            
        self.cmd_input.text = ""
        prefix = f"\n[{self.repl_mode}]> {cmd}\n"
        self.terminal_output.text += prefix
        
        if self.repl_mode == "LUA":
            old_stdout = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output
            try:
                res = self.lua_runtime.execute(cmd)
                out = redirected_output.getvalue()
                if out:
                    self.terminal_output.text += out
                elif res is not None:
                    self.terminal_output.text += str(res) + "\n"
            except Exception as e:
                self.terminal_output.text += f"Error: {str(e)}\n"
            finally:
                sys.stdout = old_stdout
        else:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout:
                    self.terminal_output.text += result.stdout
                if result.stderr:
                    self.terminal_output.text += result.stderr
            except Exception as e:
                self.terminal_output.text += f"Shell Error: {str(e)}\n"

    def clear_terminal(self):
        self.terminal_output.text = "Terminal cleared.\n"


class LuaStudioIDEApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Green"
        
        self.current_open_file = DEFAULT_FILE
        self.load_settings()
        
        self.nav_layout = MDNavigationLayout()
        
        self.sm = ScreenManager()
        self.editor_screen = EditorScreen()
        self.console_screen = ConsoleScreen()
        self.settings_screen = SettingsScreen()
        
        self.sm.add_widget(self.editor_screen)
        self.sm.add_widget(self.console_screen)
        self.sm.add_widget(self.settings_screen)
        
        self.nav_drawer = MDNavigationDrawer()
        drawer_layout = MDBoxLayout(orientation="vertical", padding=dp(8))
        
        self.drawer_header = MDTopAppBar(
            title="File Manager",
            elevation=0,
            right_action_items=[["file-plus-outline", lambda x: self.prompt_asset_creation_dialog()]]
        )
        drawer_layout.add_widget(self.drawer_header)
        
        self.file_list_view = MDList()
        scroller = MDScrollView()
        scroller.add_widget(self.file_list_view)
        drawer_layout.add_widget(scroller)
        
        self.nav_drawer.add_widget(drawer_layout)
        self.nav_layout.add_widget(self.sm)
        self.nav_layout.add_widget(self.nav_drawer)
        
        self.apply_settings()
        self.refresh_project_workspace_tree()
        self.recover_interrupted_session()
        
        return self.nav_layout

    def load_settings(self):
        self.ide_settings = {"show_line_numbers": True, "font_size": 16, "auto_save": True, "auto_indent": True, "dark_mode": False}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self.ide_settings.update(json.load(f))
            except Exception:
                pass

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.ide_settings, f)
        except Exception:
            pass

    def apply_settings(self):
        self.editor_screen.apply_settings(self.ide_settings)
        is_dark = self.ide_settings.get("dark_mode", False)
        self.theme_cls.theme_style = "Dark" if is_dark else "Light"
        
        # Apply themes locally to override hardcoded elements
        self.editor_screen.update_theme(is_dark)
        self.console_screen.update_theme(is_dark)
        self.settings_screen.update_theme(is_dark)
        
        # Update Nav Drawer
        bg = (0.12, 0.12, 0.12, 1) if is_dark else (0.95, 0.95, 0.95, 1)
        text = (1, 1, 1, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        self.nav_drawer.md_bg_color = bg
        self.drawer_header.md_bg_color = bg
        self.drawer_header.specific_text_color = text
        self.refresh_project_workspace_tree()

    def toggle_nav_drawer(self):
        self.nav_drawer.set_state("open")

    def switch_to_editor(self):
        self.sm.transition.direction = 'right'
        self.sm.current = 'editor'

    def switch_to_console(self):
        self.sm.transition.direction = 'left'
        self.sm.current = 'console'
        
    def switch_to_settings(self):
        self.sm.transition.direction = 'left'
        self.sm.current = 'settings'

    def refresh_project_workspace_tree(self):
        self.file_list_view.clear_widgets()
        is_dark = self.ide_settings.get("dark_mode", False)
        text_color = (0.9, 0.9, 0.9, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        icon_color = (0.5, 0.5, 0.5, 1) if is_dark else (0.4, 0.4, 0.4, 1)

        for filename in sorted(os.listdir(WORKSPACE_DIR)):
            if filename.endswith(".lua"):
                item = OneLineAvatarIconListItem(
                    text=filename,
                    theme_text_color="Custom",
                    text_color=text_color,
                    on_release=lambda x, f=filename: self.switch_active_project_file(f)
                )
                item.add_widget(IconLeftWidget(
                    icon="file-code-outline",
                    theme_icon_color="Custom",
                    icon_color=icon_color
                ))
                
                opt_btn = IconRightWidget(
                    icon="dots-vertical",
                    theme_icon_color="Custom",
                    icon_color=icon_color,
                    on_release=lambda x, f=filename: self.prompt_file_options(f)
                )
                item.add_widget(opt_btn)
                self.file_list_view.add_widget(item)

    def switch_active_project_file(self, filename):
        self.save_active_buffer_to_disk()
        target_path = os.path.join(WORKSPACE_DIR, filename)
        self.current_open_file = target_path
        self.editor_screen.toolbar.title = filename
        self.load_active_buffer_from_disk(target_path)
        self.nav_drawer.set_state("close")

    def load_active_buffer_from_disk(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                self.editor_screen.editor_input.text = f.read()
                
    def save_active_buffer_to_disk(self):
        if self.current_open_file:
            with open(self.current_open_file, "w", encoding="utf-8") as f:
                f.write(self.editor_screen.editor_input.text)

    def prompt_file_options(self, filename):
        self.file_opt_dialog = MDDialog(
            title=f"Options: {filename}",
            type="simple",
            items=[
                OneLineAvatarIconListItem(text="Rename", on_release=lambda x: self.prompt_rename_file(filename)),
                OneLineAvatarIconListItem(text="Export to Downloads", on_release=lambda x: self.export_file(filename)),
                OneLineAvatarIconListItem(text="Duplicate (Copy/Paste)", on_release=lambda x: self.duplicate_file(filename)),
                OneLineAvatarIconListItem(text="Delete", theme_text_color="Error", on_release=lambda x: self.delete_file(filename)),
            ],
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.file_opt_dialog.dismiss())]
        )
        self.file_opt_dialog.open()

    def prompt_rename_file(self, filename):
        self.file_opt_dialog.dismiss()
        input_field = MDTextField(text=filename, hint_text="New file name")
        self.rename_dialog = MDDialog(
            title="Rename File",
            type="custom",
            content_cls=input_field,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.rename_dialog.dismiss()),
                MDRaisedButton(text="RENAME", on_release=lambda x: self.commit_rename_file(filename, input_field.text))
            ]
        )
        self.rename_dialog.open()

    def commit_rename_file(self, old_name, new_name):
        self.rename_dialog.dismiss()
        if not new_name.endswith(".lua"):
            new_name += ".lua"
            
        src = os.path.join(WORKSPACE_DIR, old_name)
        dest = os.path.join(WORKSPACE_DIR, new_name)
        
        if os.path.exists(src) and not os.path.exists(dest):
            os.rename(src, dest)
            if self.current_open_file == src:
                self.current_open_file = dest
                self.editor_screen.toolbar.title = new_name
            self.refresh_project_workspace_tree()

    def export_file(self, filename):
        self.file_opt_dialog.dismiss()
        src = os.path.join(WORKSPACE_DIR, filename)
        
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_dir):
            try:
                os.makedirs(downloads_dir)
            except Exception:
                pass
                
        dest = os.path.join(downloads_dir, filename)
        try:
            shutil.copy(src, dest)
            self.export_alert = MDDialog(
                title="Export Successful",
                text=f"File successfully exported to:\n\n{dest}",
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.export_alert.dismiss())]
            )
            self.export_alert.open()
        except Exception as e:
            self.export_alert = MDDialog(
                title="Export Failed",
                text=str(e),
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.export_alert.dismiss())]
            )
            self.export_alert.open()

    def duplicate_file(self, filename):
        self.file_opt_dialog.dismiss()
        src = os.path.join(WORKSPACE_DIR, filename)
        dest = os.path.join(WORKSPACE_DIR, "copy_" + filename)
        try:
            shutil.copy(src, dest)
            self.refresh_project_workspace_tree()
        except Exception:
            pass

    def delete_file(self, filename):
        self.file_opt_dialog.dismiss()
        target_path = os.path.join(WORKSPACE_DIR, filename)
        if os.path.exists(target_path):
            os.remove(target_path)
            if self.current_open_file == target_path:
                self.editor_screen.editor_input.text = ""
                self.editor_screen.toolbar.title = "No File Opened"
            self.refresh_project_workspace_tree()

    def execute_lua_script(self):
        self.save_active_buffer_to_disk()
        self.switch_to_console()
        
        old_stdout = sys.stdout
        redirected_output = StringIO()
        sys.stdout = redirected_output
        
        console = self.console_screen.terminal_output
        console.text += f"\n>>> Running: {os.path.basename(self.current_open_file)}\n"
        
        try:
            lua_engine = LuaRuntime(unpack_returned_tuples=True)
            lua_engine.execute("print = python.builtins.print")
            with open(self.current_open_file, "r", encoding="utf-8") as f:
                script_content = f.read()
            lua_engine.execute(script_content)
            console.text += redirected_output.getvalue() + "\n[Finished]\n"
        except Exception as err:
            console.text += f"❌ EXCEPTION:\n{str(err)}\n"
        finally:
            sys.stdout = old_stdout

    def prompt_asset_creation_dialog(self):
        input_field = MDTextField(hint_text="filename.lua", text="script.lua")
        self.dialog = MDDialog(
            title="New File",
            type="custom",
            content_cls=input_field,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="CREATE", on_release=lambda x: self.commit_new_asset_node(input_field.text))
            ]
        )
        self.dialog.open()

    def commit_new_asset_node(self, target_name):
        self.dialog.dismiss()
        if not target_name.endswith(".lua"):
            target_name += ".lua"
        new_file_path = os.path.join(WORKSPACE_DIR, target_name)
        if not os.path.exists(new_file_path):
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(f"-- {target_name}\nprint('Hello World')")
        self.refresh_project_workspace_tree()

    def recover_interrupted_session(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    cached_state = json.load(f)
                target_file = cached_state.get("last_active_file", DEFAULT_FILE)
                if os.path.exists(target_file):
                    self.current_open_file = target_file
                    self.editor_screen.toolbar.title = os.path.basename(target_file)
                    self.editor_screen.editor_input.text = cached_state.get("buffer_cache", "")
            except Exception:
                self.load_active_buffer_from_disk(self.current_open_file)
        else:
            self.load_active_buffer_from_disk(self.current_open_file)

if __name__ == '__main__':
    LuaStudioIDEApp().run()
