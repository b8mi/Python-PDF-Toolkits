import os
import tempfile
import tkinter as tk

from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk

from pathlib import Path
from dataclasses import dataclass
from pypdf import PdfReader, PdfWriter


@dataclass
class PDFEntry:
    path: Path
    page_count: int
    size: int
    selection: str = "all"

    @property
    def pages(self):
        return parse_pages(
            self.selection,
            self.page_count
        )


def parse_pages(spec, count):

    if not spec.strip() or spec.strip().lower() == "all":
        return list(range(count))

    result = []
    seen = set()

    for token in spec.split(","):

        parts = token.strip().split("-")

        if len(parts) not in (1, 2) or any(
            not p.strip().isdigit()
            for p in parts
        ):
            raise ValueError(
                "Use page numbers and ranges, e.g. 1,3-5."
            )

        start = int(parts[0])
        end = int(parts[-1])

        if not 1 <= start <= end <= count:
            raise ValueError(
                f"Page ranges must be within 1-{count}, "
                "in ascending order."
            )

        for page in range(start - 1, end):

            if page not in seen:
                seen.add(page)
                result.append(page)

    return result


def inspect_pdf(path):
    # Analyze documents before adding them to the queue.

    path = Path(path).resolve()

    with path.open("rb") as source:

        reader = PdfReader(source)

        if reader.is_encrypted:
            raise ValueError(
                "Password-protected PDFs are not supported."
            )

        count = len(reader.pages)

        if count == 0:
            raise ValueError("PDF contains no pages.")

    return PDFEntry(
        path=path,
        page_count=count,
        size=path.stat().st_size
    )


def format_size(size):

    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.2f} MB"

    return f"{size / 1024:.1f} KB"


def queue_summary(entries):

    file_count = len(entries)

    page_count = sum(
        len(entry.pages) for entry in entries
    )

    total_size = sum(
        entry.size for entry in entries
    )

    return file_count, page_count, total_size


def merge_entries(entries, destination):

    if len(entries) < 2:
        raise ValueError("Add at least two PDF files.")

    destination = Path(destination).resolve()

    # Prevent the merger from replacing an input document.

    if any(
        destination == entry.path
        or (
            destination.exists()
            and os.path.samefile(destination, entry.path)
        )
        for entry in entries
    ):
        raise ValueError(
            "Choose a destination different from your input PDFs."
        )

    expected = sum(
        len(entry.pages) for entry in entries
    )

    fd, name = tempfile.mkstemp(
        prefix=".merge_",
        suffix=".pdf",
        dir=destination.parent
    )

    os.close(fd)

    temp = Path(name)

    writer = PdfWriter()

    try:

        for entry in entries:

            current = inspect_pdf(entry.path)

            # Detect changes made to queued documents.

            if current.page_count != entry.page_count:
                raise ValueError(
                    f"{entry.path.name} changed page count. "
                    "Remove and add it again."
                )

            writer.append(
                str(entry.path),
                pages=entry.pages
            )

        with temp.open("wb") as output:
            writer.write(output)

        # Verify the final page count before saving.

        with temp.open("rb") as check:

            if len(PdfReader(check).pages) != expected:
                raise RuntimeError(
                    "Merged page count did not match the queue."
                )

        os.replace(temp, destination)

        return expected

    finally:

        writer.close()

        temp.unlink(missing_ok=True)


class PDFMergerApp:

    def __init__(self, root):

        self.root = root

        self.root.title("PDF Merger V2")

        self.root.geometry("780x470")

        self.root.minsize(560, 350)

        self.entries = []

        self.cur_index = None

        self.summary = tk.StringVar()

        self.details = tk.StringVar(
            value="Select a file to see its location."
        )

        self.status = tk.StringVar(
            value="Ready. Add PDFs to begin."
        )

        self.configure_style()

        self.build_ui()

        self.refresh_queue()


    @property
    def file_paths(self):
        return [
            str(entry.path)
            for entry in self.entries
        ]


    def configure_style(self):

        style = ttk.Style(self.root)

        style.configure(
            "Title.TLabel",
            font=("TkDefaultFont", 19, "bold")
        )

        style.configure(
            "Summary.TLabel",
            font=("TkDefaultFont", 11, "bold")
        )

        style.configure(
            "Treeview",
            rowheight=29
        )

        style.configure(
            "Action.TButton",
            padding=(12, 7)
        )


    def build_ui(self):

        frame = ttk.Frame(
            self.root,
            padding=16
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        ttk.Label(
            frame,
            text="PDF Merger",
            style="Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=(
                "Add files, drag to reorder, "
                "then choose the pages to merge."
            )
        ).pack(
            anchor="w",
            pady=(3, 12)
        )

        # Toolbar

        toolbar = ttk.Frame(frame)

        toolbar.pack(
            fill=tk.X,
            pady=(0, 8)
        )

        ttk.Button(
            toolbar,
            text="+ Add files",
            command=self.add_files
        ).pack(
            side=tk.LEFT,
            padx=(0, 5)
        )

        ttk.Button(
            toolbar,
            text="Remove",
            command=self.remove_file
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        ttk.Button(
            toolbar,
            text="↑",
            width=3,
            command=lambda: self.move_selected(-1)
        ).pack(
            side=tk.LEFT,
            padx=3
        )

        ttk.Button(
            toolbar,
            text="↓",
            width=3,
            command=lambda: self.move_selected(1)
        ).pack(
            side=tk.LEFT,
            padx=3
        )

        ttk.Button(
            toolbar,
            text="Edit page range",
            command=self.edit_pages
        ).pack(
            side=tk.RIGHT
        )

        # Intelligent file table

        table_frame = ttk.Frame(frame)

        table_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        columns = (
            "file",
            "pages",
            "selected",
            "size"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        labels = (
            "File",
            "Total pages",
            "Selected pages",
            "File size"
        )

        widths = (260, 85, 165, 90)

        for column, label, width in zip(
            columns,
            labels,
            widths
        ):

            self.tree.heading(
                column,
                text=label
            )

            self.tree.column(
                column,
                width=width,
                minwidth=65,
                stretch=column == "file",
                anchor=(
                    "w"
                    if column in ("file", "selected")
                    else "center"
                )
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        # Mouse interactions

        self.tree.bind(
            "<Button-1>",
            self.on_click
        )

        self.tree.bind(
            "<B1-Motion>",
            self.on_drag
        )

        self.tree.bind(
            "<ButtonRelease-1>",
            self.on_release
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

        self.tree.bind(
            "<Double-1>",
            self.on_double_click
        )

        # Selected file information

        ttk.Label(
            frame,
            textvariable=self.details,
            wraplength=690
        ).pack(
            fill=tk.X,
            pady=(6, 2)
        )

        # Live statistics

        ttk.Label(
            frame,
            textvariable=self.summary,
            style="Summary.TLabel"
        ).pack(
            anchor="w",
            pady=(3, 8)
        )

        bottom = ttk.Frame(frame)

        bottom.pack(fill=tk.X)

        ttk.Label(
            bottom,
            textvariable=self.status,
            wraplength=460
        ).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )

        self.merge_button = ttk.Button(
            bottom,
            text="Merge PDFs",
            style="Action.TButton",
            command=self.merge_pdfs
        )

        self.merge_button.pack(
            side=tk.RIGHT
        )


    def refresh_queue(self, select=None):

        children = self.tree.get_children()

        if children:
            self.tree.delete(*children)

        for index, entry in enumerate(self.entries):

            selected = (
                f"{len(entry.pages)} | {entry.selection}"
            )

            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    entry.path.name,
                    entry.page_count,
                    selected,
                    format_size(entry.size)
                )
            )

        if select is not None and 0 <= select < len(self.entries):

            iid = str(select)

            self.tree.selection_set(iid)

            self.tree.focus(iid)

            self.tree.see(iid)

        count, pages, size = queue_summary(
            self.entries
        )

        self.summary.set(
            f"{count} files  |  "
            f"{pages} output pages  |  "
            f"{format_size(size)} input size"
        )

        # Automatically enable or disable the merge button.

        self.merge_button.configure(
            state="normal" if count >= 2 else "disabled"
        )

        self.on_select()


    def selected_index(self):

        selected = self.tree.selection()

        return int(selected[0]) if selected else None


    def on_select(self, event=None):

        index = self.selected_index()

        if index is not None and index < len(self.entries):

            self.details.set(
                str(self.entries[index].path)
            )

        else:

            self.details.set(
                "Select a file to see its location."
            )


    def add_files(self):

        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[
                ("PDF files", "*.pdf")
            ]
        )

        if not files:
            return

        known = {
            entry.path
            for entry in self.entries
        }

        added = 0
        errors = []

        for file in files:

            path = Path(file).resolve()

            if path in known:
                continue

            try:

                entry = inspect_pdf(path)

                self.entries.append(entry)

                known.add(path)

                added += 1

            except Exception as exc:

                errors.append(
                    f"{path.name}: {exc}"
                )

        self.refresh_queue(
            len(self.entries) - 1
            if self.entries
            else None
        )

        self.status.set(
            f"Added {added} file(s)."
        )

        if errors:

            messagebox.showwarning(
                "Some files could not be added",
                "\n".join(errors)
            )


    def remove_file(self):

        index = self.selected_index()

        if index is None:
            return

        removed = self.entries.pop(index)

        self.refresh_queue(
            min(index, len(self.entries) - 1)
        )

        self.status.set(
            f"Removed {removed.path.name}"
        )


    def move_entry(self, source, destination):

        if not (
            0 <= source < len(self.entries)
            and 0 <= destination < len(self.entries)
        ):
            return

        if source == destination:
            return

        entry = self.entries.pop(source)

        self.entries.insert(
            destination,
            entry
        )

        self.refresh_queue(destination)


    def move_selected(self, direction):

        index = self.selected_index()

        if index is not None:

            self.move_entry(
                index,
                index + direction
            )


    def on_click(self, event):

        row = self.tree.identify_row(event.y)

        self.cur_index = int(row) if row else None


    def on_drag(self, event):

        row = self.tree.identify_row(event.y)

        if self.cur_index is None or not row:
            return

        target = int(row)

        if target != self.cur_index:

            self.move_entry(
                self.cur_index,
                target
            )

            self.cur_index = target

        return "break"


    def on_release(self, event):

        self.cur_index = None


    def on_double_click(self, event):

        if self.tree.identify_row(event.y):

            self.edit_pages()


    def edit_pages(self):

        index = self.selected_index()

        if index is None:

            messagebox.showinfo(
                "Page range",
                "Select a PDF first."
            )

            return

        entry = self.entries[index]

        initial = entry.selection

        while True:

            answer = simpledialog.askstring(
                "Select pages",
                (
                    f"{entry.path.name}\n"
                    f"Available pages: 1-{entry.page_count}\n\n"
                    "Enter all or ranges such as 1,3-5.\n"
                    "Order is preserved.\n"
                    "Repeated pages are ignored."
                ),
                initialvalue=initial,
                parent=self.root
            )

            if answer is None:
                return

            try:

                parse_pages(
                    answer,
                    entry.page_count
                )

            except ValueError as exc:

                messagebox.showerror(
                    "Invalid page range",
                    str(exc)
                )

                initial = answer

                continue

            entry.selection = (
                answer.strip() or "all"
            )

            self.refresh_queue(index)

            self.status.set(
                f"Updated page range for {entry.path.name}."
            )

            return


    def merge_pdfs(self):

        if len(self.entries) < 2:

            messagebox.showwarning(
                "PDF Merger",
                "Add at least two PDF files."
            )

            return

        destination = filedialog.asksaveasfilename(
            title="Save as",
            defaultextension=".pdf",
            filetypes=[
                ("PDF files", "*.pdf")
            ]
        )

        if not destination:
            return

        self.status.set(
            "Merging selected pages..."
        )

        self.root.update_idletasks()

        try:

            pages = merge_entries(
                self.entries,
                destination
            )

            self.status.set(
                f"Merged {pages} pages successfully."
            )

            messagebox.showinfo(
                "Success",
                (
                    f"Merged {len(self.entries)} files "
                    f"({pages} pages)!\n\n"
                    f"Saved to:\n{destination}"
                )
            )

        except Exception as exc:

            self.status.set("Merge failed.")

            messagebox.showerror(
                "Error",
                str(exc)
            )


def main():

    root = tk.Tk()

    app = PDFMergerApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
