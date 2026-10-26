import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pypdf import PdfWriter

class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("merger")
        self.root.geometry("450x400")

        self.file_paths = []

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        add_btn = tk.Button(btn_frame, text="+add file+", command=self.add_files, width=15)
        add_btn.grid(row=0, column=0, padx=5)

        remove_btn = tk.Button(btn_frame, text="-remove file-", command=self.remove_file, width=15)
        remove_btn.grid(row=0, column=1, padx=5)

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, yscrollcommand=scrollbar.set, font=("Arial", 11))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Drag-and-drop should update the list on screen and the file order together.
        self.listbox.bind('<Button-1>', self.on_click)
        self.listbox.bind('<B1-Motion>', self.on_drag)
        self.cur_index = None

        merge_btn = tk.Button(self.root, text=">merge<", command=self.merge_pdfs, width=20, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        merge_btn.pack(pady=15)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF Files", "*.pdf")]
        )

        # Ignore duplicates, otherwise the same PDF could be merged twice by accident.
        for file in files:
            if file not in self.file_paths:
                self.file_paths.append(file)
                self.listbox.insert(tk.END, os.path.basename(file))

    def remove_file(self):
        sel = self.listbox.curselection()
        if not sel:
            return


        index = sel[0]
        self.listbox.delete(index)
        self.file_paths.pop(index)

    def on_click(self, event):
        self.cur_index = self.listbox.nearest(event.y)

    def on_drag(self, event):
        if self.cur_index is None:
            return

        spot = self.listbox.nearest(event.y)

        # The listbox is only the display; the matching path needs moving too.
        if spot != self.cur_index:
            item = self.listbox.get(self.cur_index)
            self.listbox.delete(self.cur_index)
            self.listbox.insert(spot, item)

            path = self.file_paths.pop(self.cur_index)
            self.file_paths.insert(spot, path)

            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(spot)

            self.cur_index = spot


    def merge_pdfs(self):
        if len(self.file_paths) < 2:
            messagebox.showwarning("!", " add at least 2 PDF files.")
            return

        dest = filedialog.asksaveasfilename(
            title="Save as",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not dest:
            return

        try:
            # PdfWriter appends pages in the same order the files appear in the list.
            merger = PdfWriter()

            for path in self.file_paths:
                merger.append(path)

            with open(dest, "wb") as output_file:
                merger.write(output_file)

            messagebox.showinfo("Success", f"successfully merged {len(self.file_paths)} files!\n\nand saved to:\n{dest}")


        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFMergerApp(root)
    root.mainloop()
