#!/usr/bin/env python3
"""
Markdown Reader v3 — basic markdown rendering by default, optional LaTeX math

v3 升級：
  - Default view: markdown→HtmlFrame (fast, no LaTeX), basic MD formatting out-of-box
  - [Enable LaTeX] toggle: on-demand LaTeX math rendering (lazy import)
  - HtmlFrame also lazy-imported — fast app startup
  - Copy / Paste / Select All buttons + Edit menu + keyboard shortcuts
"""

import sys
import os
import re
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import markdown


# ── CSS template (用 .replace() 避免同 {} 衝突) ──────────────

CSS_STYLE = '''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
  body {
    font-family: 'Segoe UI', 'Noto Sans CJK', system-ui, sans-serif;
    font-size: 34px;
    line-height: 1.7;
    color: #1a1a1a;
    padding: 20px 32px;
    background: #ffffff;
  }
  h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 6px; }
  h2 { font-size: 1.5em; margin-top: 1.5em; }
  h3 { font-size: 1.2em; color: #444; }
  h4 { font-size: 1.1em; color: #555; }
  code {
    font-family: 'Cascadia Code', 'Consolas', monospace;
    background: #f0f0f0; padding: 2px 6px; border-radius: 3px;
    font-size: 0.9em;
  }
  pre code {
    display: block; padding: 12px 16px; overflow-x: auto;
    background: #f6f8fa; border-radius: 6px;
  }
  blockquote {
    margin: 12px 0; padding: 8px 16px; border-left: 4px solid #ddd;
    color: #555; background: #fafafa;
  }
  table { border-collapse: collapse; margin: 12px 0; width: 100%; }
  th, td { border: 1px solid #ddd; padding: 6px 12px; text-align: left; }
  th { background: #f0f0f0; font-weight: bold; }
  img { max-width: 100%; height: auto; }
  a { color: #0366d6; text-decoration: none; }
  a:hover { text-decoration: underline; }
  hr { border: none; border-top: 1px solid #ddd; margin: 24px 0; }
  details {
    margin: 8px 0; padding: 8px 12px;
    background: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;
  }
  details summary { cursor: pointer; font-weight: bold; color: #2d6a4f; }
  details[open] { background: #ffffff; }
  math { font-size: 1.1em; }
  [display="block"] math { display: block; text-align: center; margin: 12px 0; }
</style>
</head>
<body>
{html}
</body>
</html>'''


# ── Render functions ─────────────────────────────────────────

def markdown_to_html_basic(md_text):
    """Fast markdown→HTML. No LaTeX processing."""
    html = markdown.markdown(
        md_text,
        extensions=['extra', 'codehilite', 'toc', 'sane_lists'],
    )
    return CSS_STYLE.replace('{html}', html)


def markdown_to_html_with_latex(md_text):
    """Markdown→HTML + LaTeX math → MathML conversion (lazy import)."""
    # Lazy import — only load latex2mathml when user clicks Enable LaTeX
    from latex2mathml.converter import convert as tex2mathml

    LATEX_INLINE_RE = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)')
    LATEX_DISPLAY_RE = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)

    def _replace_inline(m):
        try:
            return tex2mathml(m.group(1), display='inline')
        except Exception:
            return f'<code>${m.group(1)}$</code>'

    def _replace_display(m):
        try:
            return tex2mathml(m.group(1), display='block')
        except Exception:
            return f'<pre><code>$${m.group(1)}$$</code></pre>'

    html = LATEX_DISPLAY_RE.sub(_replace_display, md_text)
    html = LATEX_INLINE_RE.sub(_replace_inline, html)
    html = markdown.markdown(
        html,
        extensions=['extra', 'codehilite', 'toc', 'sane_lists'],
    )
    return CSS_STYLE.replace('{html}', html)


# ── 主應用 ──────────────────────────────────────────────────

class MarkdownReader:
    MODES = ("view", "edit")

    def __init__(self, root):
        self.root = root
        self.root.title("Markdown Reader")
        self.root.geometry("1920x1600+0+0")
        self.font_size = 20
        self._current_content = ""
        self._file_path = None
        self._mode = "view"
        self._latex_enabled = False       # default: basic markdown only
        self._html_frame = None           # lazy-created on first view

        # ── Toolbar ───────────────────────────────────────────
        toolbar = tk.Frame(root, bg="#e0e0e0", height=36)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        self.mode_btn = tk.Label(
            toolbar, text="VIEW MODE",
            font=("Segoe UI", 11, "bold"),
            bg="#2d6a4f", fg="white",
            padx=14, pady=2, cursor="hand2"
        )
        self.mode_btn.pack(side=tk.LEFT, padx=(8, 0), pady=4)
        self.mode_btn.bind("<Button-1>", self._toggle_mode)

        # LaTeX toggle (default: OFF)
        self._latex_btn = tk.Label(
            toolbar, text="Enable LaTeX",
            font=("Segoe UI", 10),
            bg="#d4d4d4", fg="#333",
            padx=12, pady=2, cursor="hand2"
        )
        self._latex_btn.pack(side=tk.LEFT, padx=(6, 0), pady=4)
        self._latex_btn.bind("<Button-1>", self._toggle_latex)

        # Edit action buttons
        self._copy_btn = tk.Label(
            toolbar, text="\U0001f4cb Copy",
            font=("Segoe UI", 10),
            bg="#d4d4d4", fg="#333",
            padx=8, pady=2, cursor="hand2"
        )
        self._copy_btn.pack(side=tk.LEFT, padx=(6, 0), pady=4)
        self._copy_btn.bind("<Button-1>", lambda e: self.copy_text())

        self._paste_btn = tk.Label(
            toolbar, text="\U0001f4cc Paste",
            font=("Segoe UI", 10),
            bg="#d4d4d4", fg="#333",
            padx=8, pady=2, cursor="hand2"
        )
        self._paste_btn.pack(side=tk.LEFT, padx=(3, 0), pady=4)
        self._paste_btn.bind("<Button-1>", lambda e: self.paste_text())

        self._select_all_btn = tk.Label(
            toolbar, text="\U0001f532 Select All",
            font=("Segoe UI", 10),
            bg="#d4d4d4", fg="#333",
            padx=8, pady=2, cursor="hand2"
        )
        self._select_all_btn.pack(side=tk.LEFT, padx=(3, 0), pady=4)
        self._select_all_btn.bind("<Button-1>", lambda e: self.select_all())

        # Save button (hidden by default, shown in edit mode)
        self._save_btn = tk.Label(
            toolbar, text="\U0001f4be Save",
            font=("Segoe UI", 10),
            bg="#d4d4d4", fg="#333",
            padx=12, pady=2, cursor="hand2"
        )
        self._save_btn.pack(side=tk.LEFT, padx=(12, 0), pady=4)
        self._save_btn.bind("<Button-1>", self._save_file)
        self._save_btn.pack_forget()

        # File name label
        self._file_label = tk.Label(
            toolbar, text="", font=("Segoe UI", 10),
            bg="#e0e0e0", fg="#666", anchor=tk.W
        )
        self._file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # ── Menubar ───────────────────────────────────────────
        menubar = tk.Menu(root)
        root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file_dialog, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo",   command=self.undo,         accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo",   command=self.redo,         accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy",   command=self.copy_text,    accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste",  command=self.paste_text,   accelerator="Ctrl+V")
        edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In",  command=self.zoom_in,  accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Reset Zoom", command=self.zoom_reset, accelerator="Ctrl+0")

        # ── Edit frame (ScrolledText, hidden by default) ──────
        self._edit_text = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Segoe UI", self.font_size),
            bg="#ffffff", fg="#1a1a1a", padx=20, pady=20,
            relief=tk.FLAT, borderwidth=0, undo=True
        )
        self._edit_text.bind("<<Modified>>", self._on_modified)
        self._modified = False  # track unsaved changes

        # ── Keyboard shortcuts (bind to root + edit_text) ─────
        for w in [root, self._edit_text]:
            w.bind("<Control-Key-equal>",      lambda e: self.zoom_in())
            w.bind("<Control-Key-plus>",       lambda e: self.zoom_in())
            w.bind("<Control-KP_Add>",         lambda e: self.zoom_in())
            w.bind("<Control-Key-minus>",      lambda e: self.zoom_out())
            w.bind("<Control-KP_Subtract>",    lambda e: self.zoom_out())
            w.bind("<Control-Key-0>",          lambda e: self.zoom_reset())
            w.bind("<Control-Key-o>",          lambda e: self.open_file_dialog())
            w.bind("<Control-Key-c>",          lambda e: self.copy_text())
            w.bind("<Control-Key-a>",          lambda e: self.select_all())

        # Single-source bindings (on _edit_text only, with break)
        self._edit_text.bind("<Control-Key-v>", lambda e: self.paste_text() or "break")
        self._edit_text.bind("<Control-Key-s>", lambda e: self._save_file() or "break")
        self._edit_text.bind("<Control-Key-z>", lambda e: self.undo() or "break")
        self._edit_text.bind("<Control-Key-y>", lambda e: self.redo() or "break")
        # Disable tkinter's built-in <<Paste>> to avoid double-paste
        self._edit_text.bind_class("Text", "<<Paste>>", lambda e: "break")

        # Window close → check unsaved changes
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.open_file(sys.argv[1])

    # ── Lazy HtmlFrame loader ─────────────────────────────────

    def _ensure_html_frame(self):
        """Create HtmlFrame on first use (lazy import)."""
        if self._html_frame is None:
            from tkinterweb import HtmlFrame
            self._html_frame = HtmlFrame(self.root, messages_enabled=False)
        return self._html_frame

    # ── LaTeX toggle ─────────────────────────────────────────

    def _toggle_latex(self, event=None):
        """Toggle LaTeX math rendering on/off."""
        if self._mode != "view":
            return
        self._latex_enabled = not self._latex_enabled
        if self._latex_enabled:
            self._latex_btn.config(text="Disable LaTeX", bg="#b13e3e", fg="white")
        else:
            self._latex_btn.config(text="Enable LaTeX", bg="#d4d4d4", fg="#333")
        if self._current_content.strip():
            self._render_current()

    # ── Mode toggle ──────────────────────────────────────────

    def _toggle_mode(self, event=None):
        if self._mode == "view":
            self._switch_to_edit()
        else:
            self._switch_to_view()

    def _switch_to_edit(self):
        self._mode = "edit"
        self.mode_btn.config(text="EDIT MODE", bg="#b13e3e")
        self._save_btn.pack(side=tk.LEFT, padx=(6, 0), pady=4)
        self._file_label.config(fg="#999")

        if self._html_frame:
            self._html_frame.pack_forget()
        self._edit_text.pack(fill=tk.BOTH, expand=True)
        self._edit_text.delete("1.0", tk.END)
        self._edit_text.insert("1.0", self._current_content)
        self._edit_text.edit_modified(False)
        self._modified = False

    def _switch_to_view(self):
        self._mode = "view"
        self.mode_btn.config(text="VIEW MODE", bg="#2d6a4f")
        self._save_btn.pack_forget()
        self._file_label.config(fg="#666")

        # Save edits
        if hasattr(self, '_edit_text'):
            raw = self._edit_text.get("1.0", tk.END).rstrip("\n") + "\n"
            if raw.strip():
                self._current_content = raw

        self._edit_text.pack_forget()
        hf = self._ensure_html_frame()
        hf.pack(fill=tk.BOTH, expand=True)
        if self._current_content.strip():
            self._render_current()

    # ── Render ───────────────────────────────────────────────

    def _render_current(self):
        """Re-render current content with current LaTeX setting."""
        fs = self.font_size
        try:
            if self._latex_enabled:
                html = markdown_to_html_with_latex(self._current_content)
            else:
                html = markdown_to_html_basic(self._current_content)
            html = html.replace(
                'font-size: 34px;',
                f'font-size: {int(fs * 1.7)}px;'
            )
            hf = self._ensure_html_frame()
            hf.load_html(html)
        except Exception as e:
            hf = self._ensure_html_frame()
            hf.load_html(
                f'<html><body><h2>Render Error</h2>'
                f'<pre style="color:red">{str(e)}</pre>'
                f'<hr><pre>{self._current_content[:500]}</pre></body></html>'
            )

    # ── Copy / Paste / Select All ────────────────────────────

    def _active_widget(self):
        w = self.root.focus_get()
        if w and hasattr(w, 'get') and hasattr(w, 'insert'):
            return w
        return None

    def copy_text(self):
        w = self._active_widget()
        if not w:
            return
        try:
            if hasattr(w, 'selection_get'):
                sel = w.selection_get()
            else:
                sel = w.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
        except (tk.TclError, Exception):
            pass

    def paste_text(self):
        w = self._active_widget()
        if not w:
            return
        try:
            text = self.root.clipboard_get()
            w.insert(tk.INSERT, text)
        except Exception:
            pass

    def select_all(self):
        w = self._active_widget()
        if not w:
            return
        try:
            w.tag_add(tk.SEL, "1.0", tk.END)
            w.mark_set(tk.INSERT, "1.0")
            w.see(tk.INSERT)
        except Exception:
            pass

    # ── Save ─────────────────────────────────────────────────

    def _save_file(self, event=None):
        if not self._file_path:
            path = filedialog.asksaveasfilename(
                title="Save Markdown File",
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
            )
            if not path:
                return
            self._file_path = path
        try:
            content = self._edit_text.get("1.0", tk.END)
            content = content.replace("\r\n", "\n").rstrip("\n") + "\n"
            with open(self._file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._current_content = content
            self._modified = False
            self.root.title(f"Markdown Reader - {os.path.basename(self._file_path)}")
            self._file_label.config(text=os.path.basename(self._file_path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{str(e)}")

    def _on_modified(self, event=None):
        self._modified = True
        self._edit_text.edit_modified(False)

    def undo(self):
        """Safe undo — prevents Windows empty-stack wipe bug."""
        try:
            before = self._edit_text.get("1.0", tk.END)
            self._edit_text.edit_undo()
            after = self._edit_text.get("1.0", tk.END)
            # Windows bug: edit_undo on empty stack wipes everything
            if not after.strip() and before.strip():
                self._edit_text.delete("1.0", tk.END)
                self._edit_text.insert("1.0", before)
        except tk.TclError:
            pass

    def redo(self):
        """Safe redo — prevents Windows empty-stack wipe bug."""
        try:
            before = self._edit_text.get("1.0", tk.END)
            self._edit_text.edit_redo()
            after = self._edit_text.get("1.0", tk.END)
            if not after.strip() and before.strip():
                self._edit_text.delete("1.0", tk.END)
                self._edit_text.insert("1.0", before)
        except tk.TclError:
            pass

    def _on_close(self):
        """Close window, ask to save if modified."""
        if self._modified:
            if messagebox.askyesno("Unsaved Changes", "Save changes before closing?"):
                self._save_file()
        self.root.destroy()

    # ── Zoom ─────────────────────────────────────────────────

    def zoom_in(self):
        if self.font_size < 72:
            self.font_size += 2
            self._apply_zoom()

    def zoom_out(self):
        if self.font_size > 8:
            self.font_size -= 2
            self._apply_zoom()

    def zoom_reset(self):
        self.font_size = 20
        self._apply_zoom()

    def _apply_zoom(self):
        if self._mode == "edit":
            self._edit_text.configure(font=("Segoe UI", self.font_size))
        else:
            self._render_current()

    # ── File handling ────────────────────────────────────────

    def open_file_dialog(self):
        path = filedialog.askopenfilename(
            title="Open Markdown File",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if path:
            self.open_file(path)

    def open_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self._file_path = path
            self._current_content = content
            self._modified = False
            self.root.title(f"Markdown Reader - {os.path.basename(path)}")
            self._file_label.config(text=os.path.basename(path))

            # Switch to view + render
            self._mode = "view"
            self.mode_btn.config(text="VIEW MODE", bg="#2d6a4f")
            self._save_btn.pack_forget()
            self._edit_text.pack_forget()
            hf = self._ensure_html_frame()
            hf.pack(fill=tk.BOTH, expand=True)
            self._render_current()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    MarkdownReader(root)
    root.mainloop()
