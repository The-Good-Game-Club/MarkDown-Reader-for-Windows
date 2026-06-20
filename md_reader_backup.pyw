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


class MarkdownReader:
    MODES = ("view", "edit")

    def __init__(self, root):
        self.root = root
        self.root.title("Markdown Reader")
        self.root.geometry("1920x1600+0+0")
        self.font_size = 20
        self._current_content = ""
        self._file_path = None
        self._mode = "view"  # "view" | "edit"

        # ── Top toolbar ──────────────────────────────────────────
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

        self._save_btn = tk.Label(
            toolbar, text="💾 Save",
            font=("Segoe UI", 10),
            bg="#d4d4d4", fg="#333",
            padx=12, pady=2, cursor="hand2"
        )
        self._save_btn.pack(side=tk.LEFT, padx=(6, 0), pady=4)
        self._save_btn.bind("<Button-1>", self._save_file)
        self._save_btn.pack_forget()  # hidden in view mode

        self._file_label = tk.Label(
            toolbar, text="", font=("Segoe UI", 10),
            bg="#e0e0e0", fg="#666", anchor=tk.W
        )
        self._file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # ── Menubar ──────────────────────────────────────────────
        menubar = tk.Menu(root)
        root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file_dialog, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Reset Zoom", command=self.zoom_reset, accelerator="Ctrl+0")

        # ── Main text widget ─────────────────────────────────────
        self.text = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, font=("Segoe UI", self.font_size),
            bg="#ffffff", fg="#1a1a1a", padx=20, pady=20,
            relief=tk.FLAT, borderwidth=0
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        self.text.bind("<<Modified>>", self._on_modified)

        # Global keyboard shortcuts (always active)
        for w in [root, self.text]:
            w.bind("<Control-Key-equal>", lambda e: self.zoom_in())
            w.bind("<Control-Key-plus>", lambda e: self.zoom_in())
            w.bind("<Control-KP_Add>", lambda e: self.zoom_in())
            w.bind("<Control-Key-minus>", lambda e: self.zoom_out())
            w.bind("<Control-KP_Subtract>", lambda e: self.zoom_out())
            w.bind("<Control-Key-0>", lambda e: self.zoom_reset())
            w.bind("<Control-Key-o>", lambda e: self.open_file_dialog())
            w.bind("<Control-Key-s>", lambda e: self._save_file())

        self._block_key_id = self.text.bind("<Key>", self._block_key, "+")

        self._setup_tags()

        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.open_file(sys.argv[1])

    # ── Mode toggle ──────────────────────────────────────────────

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

        # Show raw markdown in editable form
        raw = self._current_content
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", raw)
        # Remove all tags so it's plain text
        for tag in self.text.tag_names():
            if tag != "sel":
                self.text.tag_delete(tag)
        self.text.configure(wrap=tk.WORD, state=tk.NORMAL)
        self.text.unbind("<Key>", self._block_key_id)
        # Re-bind key check for Ctrl shortcuts only
        self.text.bind("<Key>", self._edit_key_handler, "+")

    def _switch_to_view(self):
        self._mode = "view"
        self.mode_btn.config(text="VIEW MODE", bg="#2d6a4f")
        self._save_btn.pack_forget()
        self._file_label.config(fg="#666")

        # Re-render from edited content
        raw = self.text.get("1.0", tk.END) if self.text.get("1.0", tk.END).strip() else self._current_content
        # Trim trailing newlines that .get() adds
        raw = raw.rstrip("\n") + "\n" if raw.strip() else raw
        self._current_content = raw
        self.render(raw)
        self.text.unbind("<Key>", self._block_key_id)
        self._block_key_id = self.text.bind("<Key>", self._block_key, "+")

    def _edit_key_handler(self, event):
        # Allow Ctrl+ shortcuts to pass through; block nothing else
        if event.state & 0x4:
            return  # Ctrl held → let through
        return None  # normal typing

    # ── Save ─────────────────────────────────────────────────────

    def _save_file(self, event=None):
        if not self._file_path:
            path = filedialog.asksaveasfilename(
                title="Save Markdown File",
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), (All := "All files", "*.*")]
            )
            if not path:
                return
            self._file_path = path
        try:
            content = self.text.get("1.0", tk.END)
            # Normalise line endings
            content = content.replace("\r\n", "\n").rstrip("\n") + "\n"
            with open(self._file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._current_content = content
            self.root.title(f"Markdown Reader - {os.path.basename(self._file_path)}")
            self._file_label.config(text=os.path.basename(self._file_path))
            self.text.edit_modified(False)
            messagebox.showinfo("Saved", f"Saved ✓")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{str(e)}")

    # ── Modified flag ────────────────────────────────────────────

    def _on_modified(self, event=None):
        # Clear modified flag so it re-fires on next change
        self.text.edit_modified(False)

    # ── Markdown rendering (view mode) ──────────────────────────

    def _setup_tags(self):
        fs = self.font_size
        self.text.tag_configure("h1", font=("Segoe UI", int(fs * 2.2), "bold"), spacing1=int(fs * 0.8), spacing3=int(fs * 0.4))
        self.text.tag_configure("h2", font=("Segoe UI", int(fs * 1.7), "bold"), spacing1=int(fs * 0.6), spacing3=int(fs * 0.3))
        self.text.tag_configure("h3", font=("Segoe UI", int(fs * 1.4), "bold"), spacing1=int(fs * 0.4), spacing3=int(fs * 0.25))
        self.text.tag_configure("h4", font=("Segoe UI", int(fs * 1.15), "bold"), spacing1=int(fs * 0.2), spacing3=int(fs * 0.15))
        self.text.tag_configure("bold", font=("Segoe UI", fs, "bold"))
        self.text.tag_configure("italic", font=("Segoe UI", fs, "italic"))
        self.text.tag_configure("bold_italic", font=("Segoe UI", fs, "bold italic"))
        self.text.tag_configure("code", font=("Consolas", int(fs * 0.85)), background="#f0f0f0", foreground="#d63384")
        self.text.tag_configure("codeblock", font=("Consolas", int(fs * 0.85)), background="#f6f8fa", foreground="#333",
                                lmargin1=20, lmargin2=20, spacing1=int(fs * 0.25), spacing3=int(fs * 0.25), wrap=tk.NONE)
        self.text.tag_configure("blockquote", foreground="#666", font=("Segoe UI", fs, "italic"),
                                lmargin1=30, lmargin2=30, spacing1=int(fs * 0.15), spacing3=int(fs * 0.15))
        self.text.tag_configure("hr", foreground="#ccc")
        self.text.tag_configure("bullet", lmargin1=20, lmargin2=30)
        self.text.tag_configure("link", foreground="#0366d6", underline=True)
        self.text.tag_configure("image", foreground="#666", font=("Segoe UI", int(fs * 0.85), "italic"))
        self.text.tag_configure("table", font=("Consolas", int(fs * 0.9)), background="#f8f9fa",
                                lmargin1=10, lmargin2=10, spacing1=1, spacing3=1, wrap=tk.NONE)
        self.text.tag_configure("table_header", font=("Consolas", int(fs * 0.9), "bold"), background="#e9ecef",
                                lmargin1=10, lmargin2=10, spacing1=1, spacing3=1, wrap=tk.NONE)

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
        self.text.configure(font=("Segoe UI", self.font_size))
        self._setup_tags()
        if self._current_content and self._mode == "view":
            self.render(self._current_content)

    def _block_key(self, event):
        # Block text entry except when Ctrl is held (for shortcuts)
        if event.state & 0x4:
            return
        return "break"

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
            self.root.title(f"Markdown Reader - {os.path.basename(path)}")
            self._file_label.config(text=os.path.basename(path))
            if self._mode == "edit":
                # If currently in edit mode, show raw text
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", content)
            else:
                self.render(content)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{str(e)}")

    def render(self, content):
        self.text.delete("1.0", tk.END)
        lines = content.split("\n")
        in_code_block = False
        code_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.strip().startswith("```"):
                if in_code_block:
                    code_text = "\n".join(code_lines)
                    self.text.insert(tk.END, code_text + "\n", "codeblock")
                    code_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            if line.strip().startswith("|"):
                table_rows = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_rows.append(lines[i])
                    i += 1
                self._render_table(table_rows)
                self.text.insert(tk.END, "\n")
                continue

            if re.match(r"^[-*_]{3,}\s*$", line.strip()):
                self.text.insert(tk.END, " " + "\u2500" * 70 + "\n", "hr")
                i += 1
                continue

            h_match = re.match(r"^(#{1,4})\s+(.+)$", line)
            if h_match:
                level = len(h_match.group(1))
                text = h_match.group(2)
                start = self.text.index(tk.END)
                self._insert_inline(text)
                self.text.insert(tk.END, "\n")
                self.text.tag_add(f"h{level}", start, tk.END)
                i += 1
                continue

            if line.strip().startswith(">"):
                start = self.text.index(tk.END)
                bq_text = re.sub(r"^>\s?", "", line)
                self._insert_inline(bq_text)
                end = self.text.index(tk.END)
                self.text.insert(tk.END, "\n")
                self.text.tag_add("blockquote", start, end)
                i += 1
                continue

            if re.match(r"^\s*[-*+]\s+", line) or re.match(r"^\s*\d+[.)]\s+", line):
                start = self.text.index(tk.END)
                list_match = re.match(r"^(\s*(?:[-*+]|\d+[.)])\s+)", line)
                if list_match:
                    self.text.insert(tk.END, list_match.group(1), "bullet")
                    self._insert_inline(line[list_match.end():])
                else:
                    self._insert_inline(line)
                end = self.text.index(tk.END)
                self.text.insert(tk.END, "\n")
                self.text.tag_add("bullet", start, end)
                i += 1
                continue

            if line.strip() == "":
                self.text.insert(tk.END, "\n")
                i += 1
                continue

            self._insert_inline(line)
            self.text.insert(tk.END, "\n\n")
            i += 1

        if code_lines:
            self.text.insert(tk.END, "\n".join(code_lines) + "\n", "codeblock")

    def _insert_inline(self, text):
        parts = re.split(r"(`[^`]+`)|(!\[.*?\]\(.*?\))|(\[.*?\]\(.*?\))", text)
        for part in parts:
            if part is None:
                continue
            if part.startswith("`") and part.endswith("`"):
                self.text.insert(tk.END, part[1:-1], "code")
            elif part.startswith("![") and "]" in part and "(" in part:
                alt = part[2:part.index("]")]
                url = part[part.index("(") + 1:part.index(")")]
                self.text.insert(tk.END, f"[Image: {alt}] ({url})", "image")
            elif part.startswith("[") and "]" in part and "(" in part:
                link_text = part[1:part.index("]")]
                url = part[part.index("(") + 1:part.index(")")]
                self.text.insert(tk.END, link_text, "link")
            else:
                self._insert_formatted(part)

    def _insert_formatted(self, text):
        pattern = r"(\*\*\*(?!\s).+?(?<!\s)\*\*\*|___(?!\s).+?(?<!\s)___|\*\*(?!\s).+?(?<!\s)\*\*|__(?!\s).+?(?<!\s)__|\*(?!\s).+?(?<!\s)\*|_(?!\s).+?(?<!\s)_)"
        parts = re.split(pattern, text)
        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                self.text.insert(tk.END, part[3:-3], "bold_italic")
            elif part.startswith("___") and part.endswith("___"):
                self.text.insert(tk.END, part[3:-3], "bold_italic")
            elif part.startswith("**") and part.endswith("**"):
                self.text.insert(tk.END, part[2:-2], "bold")
            elif part.startswith("__") and part.endswith("__"):
                self.text.insert(tk.END, part[2:-2], "bold")
            elif part.startswith("*") and part.endswith("*"):
                self.text.insert(tk.END, part[1:-1], "italic")
            elif part.startswith("_") and part.endswith("_"):
                self.text.insert(tk.END, part[1:-1], "italic")
            else:
                self.text.insert(tk.END, part)

    def _strip_inline(self, text):
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"___(.+?)___", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        return text

    def _render_table(self, rows):
        parsed = []
        for row in rows:
            s = row.strip()
            if s.startswith("|"):
                s = s[1:]
            if s.endswith("|"):
                s = s[:-1]
            cells = [self._strip_inline(c.strip()) for c in s.split("|")]
            parsed.append(cells)

        if len(parsed) < 2:
            return

        data_start = 1
        if all(re.match(r"^[-:\s]+$", c) for c in parsed[1]):
            data_start = 2

        num_cols = max(len(r) for r in parsed)
        col_widths = [0] * num_cols
        for row in parsed:
            for i, c in enumerate(row):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], len(c))
        col_widths = [w + 2 for w in col_widths]

        def render_row(cells, tag):
            padded = []
            for i in range(num_cols):
                c = cells[i] if i < len(cells) else ""
                padded.append(" " + c.ljust(col_widths[i] - 2) + " ")
            self.text.insert(tk.END, " │ ".join(padded) + " \n", tag)

        render_row(parsed[0], "table_header")

        if data_start == 2:
            sep = "─" * (sum(col_widths) + (num_cols - 1) * 3 + 2)
            self.text.insert(tk.END, sep + "\n", "table")

        for row in parsed[data_start:]:
            render_row(row, "table")


if __name__ == "__main__":
    root = tk.Tk()
    MarkdownReader(root)
    root.mainloop()
