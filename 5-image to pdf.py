import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image

class ImagesToPDFApp:
    def __init__(self, root):
        self.root = root
        root.title("Images → PDF (GUI)")
        root.geometry("600x400")

        # Keep full image paths here; the listbox only shows the filenames.
        self.images = []

        frame = tk.Frame(root)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0,8))

        tk.Button(btn_frame, text="Add Images", command=self.add_images).pack(side="left")
        tk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Move Up", command=self.move_up).pack(side="left")
        tk.Button(btn_frame, text="Move Down", command=self.move_down).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Clear List", command=self.clear_list).pack(side="left")
        tk.Button(btn_frame, text="Export", command=self.export_pdf, fg="white", bg="#2a8fbd").pack(side="right")


        lb_frame = tk.Frame(frame)
        lb_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(lb_frame, selectmode="extended")
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(lb_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        inst = ("Add images (you can select multiple). Use Move Up / Move Down to set the order.\n"
                "When ready click Export — you'll be asked for an output folder, then a PDF name.")
        tk.Label(root, text=inst, anchor="w", justify="left").pack(fill="x", padx=10, pady=(0,10))

    def add_images(self):
        types = [
            ("Image files", ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff", "*.gif")),
            ("All files", "*.*")
        ]
        paths = filedialog.askopenfilenames(title="Select images (in any order)", filetypes=types)
        if not paths:
            return
        for p in paths:
            self.images.append(p)
            self.listbox.insert("end", os.path.basename(p))


    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            messagebox.showinfo("Remove Selected", "No items selected.")
            return
        # Delete from the end so earlier indexes do not shift during removal.
        for i in reversed(sel):
            del self.images[i]
            self.listbox.delete(i)

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        for i in sel:
            if i == 0:
                continue
            self.images[i-1], self.images[i] = self.images[i], self.images[i-1]
            name_i = self.listbox.get(i)
            name_prev = self.listbox.get(i-1)
            self.listbox.delete(i-1, i)
            self.listbox.insert(i-1, name_i)
            self.listbox.insert(i, name_prev)
        self.listbox.selection_clear(0, "end")
        for i in [max(0, x-1) for x in sel]:
            self.listbox.selection_set(i)


    def move_down(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        last_index = self.listbox.size() - 1
        # Move the lower selected rows first to preserve their relative order.
        for i in reversed(sel):
            if i == last_index:
                continue
            self.images[i+1], self.images[i] = self.images[i], self.images[i+1]
            name_i = self.listbox.get(i)
            name_next = self.listbox.get(i+1)
            self.listbox.delete(i, i+1)
            self.listbox.insert(i, name_next)
            self.listbox.insert(i+1, name_i)
        self.listbox.selection_clear(0, "end")
        for i in [min(last_index, x+1) for x in sel]:
            self.listbox.selection_set(i)

    def clear_list(self):
        if messagebox.askyesno("Clear", "Clear all images from the list?"):
            self.images.clear()
            self.listbox.delete(0, "end")

    def export_pdf(self):
        if not self.images:
            messagebox.showwarning("No images", "Add some images first.")
            return


        out_dir = filedialog.askdirectory(title="Select output folder")
        if not out_dir:
            return

        name = simpledialog.askstring("PDF name", "Enter PDF file name (without extension):")
        if not name:
            return
        # Add the extension only when the user has not typed it already.
        if not name.lower().endswith(".pdf"):
            name = name + ".pdf"

        dest = os.path.join(out_dir, name)

        try:
            opened = []
            # Convert everything to RGB because Pillow cannot save every image mode as PDF.
            for p in self.images:
                img = Image.open(p)
                if img.mode in ("RGBA", "LA") or (hasattr(img, "mode") and img.mode != "RGB"):
                    img = img.convert("RGB")
                opened.append(img)

            first, rest = opened[0], opened[1:]
            # The first image starts the PDF; the others are appended as later pages.
            first.save(dest, "PDF", save_all=True, append_images=rest)
            messagebox.showinfo("Done", f"PDF created:\n{dest}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create PDF:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImagesToPDFApp(root)
    root.mainloop()
