import os
import sys
import traceback
import logging
import math


# Put errors next to the script, useful when the GUI closes unexpectedly.
LOGFILE = os.path.join(os.path.dirname(__file__), "pdfcd.log")
logging.basicConfig(filename=LOGFILE, level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def fatal_messagebox(title, text):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    except Exception:
        print(title, text)

try:
    logging.info("Starting imports...")
    import fitz
    from PIL import Image, ImageTk
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    logging.info("Imports successful.")
except Exception as e:
    logging.exception("Import error")
    fatal_messagebox("Missing dependency", f"{e}\nInstall: pip install pymupdf pillow")
    sys.exit(1)



# Canvas size and zoom are separate so resizing the preview does not change the PDF itself.
PREVIEW_BASE_W = 700
PREVIEW_BASE_H = 600
POINT_RADIUS = 6
NEAR_DIST = 14
PRESET_COLORS = ["#00A2FF", "#FF7F00", "#2ECC71", "#D6336C", "#8E44AD"]
ACTIVE_BTN_BG = "#0078D7"
ACTIVE_BTN_FG = "white"

PREVIEW_MIN_PCT = 15
PREVIEW_MAX_PCT = 55
PREVIEW_DEFAULT_PCT = 50

ZOOM_MIN_PCT = 40
ZOOM_MAX_PCT = 60
ZOOM_DEFAULT_PCT = 60

PAN_STEP_PX = 5


class PDFCropperGUI:
    def __init__(self, root):
        logging.info("Initializing GUI...")
        self.root = root
        root.title("PDF Cropper (:")
        self.doc = None
        self.input_path = None
        self.page_index = 0


        self.preview_pct = PREVIEW_DEFAULT_PCT
        self.zoom_pct = 100

        self.render_scale = 1.0
        self.image_pix_width = 0
        self.image_pix_height = 0

        self.center_offset_x = 0
        self.center_offset_y = 0
        self.pan_x = 0
        self.pan_y = 0

        # Presets store PDF coordinates; assignments link page numbers to those presets.
        self.presets = {i: None for i in range(1,6)}
        self.page_assignments = {}
        self.active_preset = 1
        self.dragging = None
        self.removed_pages = set()

        self._build_ui()

        self.root.bind("<Key>", self.on_key_press)

        logging.info("GUI initialized.")

    def _build_ui(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=False)
        filemenu.add_command(label="Open PDF...", command=self.open_pdf)
        filemenu.add_command(label="Save Output PDF...", command=self.save_output)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)


        main = ttk.Frame(self.root, padding=6)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(main, width=360)
        right.pack(side="right", fill="y")

        control_row = ttk.Frame(left)
        control_row.pack(fill="x", pady=4, padx=4)

        ttk.Label(control_row, text="Preview size:").pack(side="left", padx=(0,6))
        self.preview_scale = ttk.Scale(control_row, from_=PREVIEW_MIN_PCT, to=PREVIEW_MAX_PCT,
                                       orient="horizontal", command=self.on_preview_scale_change)
        self.preview_scale.set(PREVIEW_DEFAULT_PCT)
        self.preview_scale.pack(side="left", fill="x", expand=True, padx=(0,8))
        self.preview_pct_label = ttk.Label(control_row, text=f"{PREVIEW_DEFAULT_PCT}%")
        self.preview_pct_label.pack(side="left", padx=(0,8))

        ttk.Label(control_row, text="PDF zoom:").pack(side="left", padx=(0,6))
        self.zoom_scale = ttk.Scale(control_row, from_=ZOOM_MIN_PCT, to=ZOOM_MAX_PCT,
                                    orient="horizontal", command=self.on_zoom_change)
        self.zoom_scale.set(ZOOM_DEFAULT_PCT)
        self.zoom_scale.pack(side="left", fill="x", expand=False)
        self.zoom_pct_label = ttk.Label(control_row, text="100%")
        self.zoom_pct_label.pack(side="left", padx=(6,0))


        preview_frame = ttk.LabelFrame(left, text="Preview (PDF)")
        preview_frame.pack(fill="both", expand=False, padx=4, pady=4)
        cw = int(PREVIEW_BASE_W * PREVIEW_DEFAULT_PCT / 100)
        ch = int(PREVIEW_BASE_H * PREVIEW_DEFAULT_PCT / 100)
        self.canvas = tk.Canvas(preview_frame, width=cw, height=ch, background="gray")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_down)
        self.canvas.bind("<B1-Motion>", self.on_canvas_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_up)
        self.canvas.focus_set()
        self.tk_img = None

        nav = ttk.Frame(left)
        nav.pack(fill="x", pady=4)
        ttk.Button(nav, text="<< Prev", command=self.prev_page).pack(side="left")
        ttk.Button(nav, text="Next >>", command=self.next_page).pack(side="left")
        self.page_label = ttk.Label(nav, text="No file loaded")
        self.page_label.pack(side="left", padx=10)
        ttk.Button(nav, text="Center View", command=self.reset_pan_and_render).pack(side="right")

        presets_frame = ttk.LabelFrame(left, text="Presets")
        presets_frame.pack(fill="x", padx=4, pady=6)

        self.preset_buttons = []
        self.preset_btn_orig_colors = []
        for i in range(1,6):
            b = tk.Button(presets_frame, text=f"Preset {i}", command=lambda i=i: self.select_preset(i), relief='raised')
            b.pack(side="left", padx=4, pady=4)
            self.preset_buttons.append(b)
            self.preset_btn_orig_colors.append((b.cget("bg"), b.cget("fg")))


        info_frame = ttk.Frame(left)
        info_frame.pack(fill="x", padx=4)
        self.active_label = ttk.Label(info_frame, text="Active: Preset 1", font=("Segoe UI", 10, "bold"))
        self.active_label.pack(side="left")
        ttk.Button(info_frame, text="Clear Preset", command=self.clear_active_preset).pack(side="left", padx=8)

        preset_coords_frame = ttk.Frame(left)
        preset_coords_frame.pack(fill="x", padx=4, pady=4)
        ttk.Label(preset_coords_frame, text="Active coords").pack(side="left")
        self.coords_label = ttk.Label(preset_coords_frame, text="Not set")
        self.coords_label.pack(side="left", padx=8)

        pages_frame = ttk.LabelFrame(right, text="Pages")
        pages_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.pages_listbox = tk.Listbox(pages_frame, selectmode="extended", width=34)
        self.pages_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(pages_frame, orient="vertical", command=self.pages_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.pages_listbox.config(yscrollcommand=scrollbar.set)

        # The list supports selecting several pages for the same crop preset.
        self.pages_listbox.bind("<<ListboxSelect>>", self.on_page_select)

        assign_frame = ttk.Frame(right)
        assign_frame.pack(fill="x", padx=4, pady=6)
        ttk.Button(assign_frame, text="Assign selected to active Preset", command=self.assign_selection_active).pack(fill="x", pady=2)
        ttk.Button(assign_frame, text="Unassign selected", command=self.unassign_selection).pack(fill="x", pady=2)
        ttk.Button(assign_frame, text="Mark selected for removal", command=self.mark_selected_removed).pack(fill="x", pady=2)
        ttk.Button(assign_frame, text="Unmark selected removal", command=self.unmark_selected_removed).pack(fill="x", pady=2)


        mapping_frame = ttk.LabelFrame(right, text="Mapping preview")
        mapping_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.mapping_text = tk.Text(mapping_frame, height=10, width=36)
        self.mapping_text.pack(fill="both", expand=True)

        options_frame = ttk.Frame(right)
        options_frame.pack(fill="x", padx=4, pady=6)
        self.keep_unassigned = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Keep unassigned pages unchanged", variable=self.keep_unassigned).pack(anchor="w")

        process_frame = ttk.Frame(right)
        process_frame.pack(fill="x", padx=4, pady=6)
        ttk.Button(process_frame, text="Save PDF...", command=self.save_output).pack(fill="x", pady=2)
        ttk.Button(process_frame, text="Clear all", command=self.clear_all_assignments).pack(fill="x", pady=2)
        ttk.Button(process_frame, text="Help", command=self.show_help).pack(fill="x", pady=2)

        self.update_preset_button_styles()

    def on_preview_scale_change(self, val):
        try:
            pct = int(float(val))
        except Exception:
            pct = PREVIEW_DEFAULT_PCT
        self.preview_pct = pct
        self.preview_pct_label.config(text=f"{pct}%")
        new_w = int(PREVIEW_BASE_W * pct / 100)
        new_h = int(PREVIEW_BASE_H * pct / 100)
        self.canvas.config(width=new_w, height=new_h)
        self.clamp_pan()
        self.render_page()


    def on_zoom_change(self, val):
        try:
            slider = float(val)
        except Exception:
            slider = ZOOM_DEFAULT_PCT

        slider = max(ZOOM_MIN_PCT, min(ZOOM_MAX_PCT, slider))
        # 40 means 10% zoom, while 60 means 100% zoom.
        self.zoom_pct = 10 + (slider - ZOOM_MIN_PCT) * 90 / (ZOOM_MAX_PCT - ZOOM_MIN_PCT)
        self.zoom_pct_label.config(text=f"{self.zoom_pct:.0f}%")
        self.clamp_pan()
        self.render_page()


    def show_help(self):
        messagebox.showinfo("Help",
            "Controls:\n"
            "- Preview size slider: reduces the canvas area so the UI fits on small screens.\n"
            "- PDF zoom slider: zooms the page inside the preview.\n"
            "- Click the preview to focus it, then use W/A/S/D to pan when zoomed in.\n"
            "- Click a page in the Pages list to jump to it. Next/Prev still work.\n"
            "\nNote: WASD are inverted per your request: W\u2191\u2193 and A\u2190\u2192."
        )

    def select_preset(self, idx):
        self.active_preset = idx
        self.active_label.config(text=f"Active: Preset {idx}")
        self.update_preset_button_styles()
        self.render_page()


    def update_preset_button_styles(self):
        for i, btn in enumerate(self.preset_buttons, start=1):
            orig_bg, orig_fg = self.preset_btn_orig_colors[i-1]
            if i == self.active_preset:
                btn.config(bg=ACTIVE_BTN_BG, fg=ACTIVE_BTN_FG, relief='sunken')
            else:
                btn.config(bg=orig_bg, fg=orig_fg, relief='raised')

    def clear_active_preset(self):
        self.presets[self.active_preset] = None
        self.coords_label.config(text="Not set")
        self.render_page()

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            logging.info("Open PDF cancelled.")
            return
        try:
            self.doc = fitz.open(path)
        except Exception as e:
            logging.exception("Cannot open PDF")
            messagebox.showerror("Error", f"Cannot open PDF: {e}")
            return
        self.input_path = path
        self.pages_listbox.delete(0, tk.END)
        for i in range(len(self.doc)):
            self.pages_listbox.insert(tk.END, f"Page {i+1}")
        self.page_index = 0
        # A new file should not inherit crop assignments or removed pages from the last one.
        self.page_assignments.clear()
        self.presets = {i: None for i in range(1,6)}
        self.coords_label.config(text="Not set")
        self.removed_pages.clear()
        logging.info(f"Opened PDF: {path} ({len(self.doc)} pages)")
        self.reset_pan()
        self.select_preset(1)
        try:
            self.canvas.focus_set()
        except Exception:
            pass
        self.render_page()


    def on_page_select(self, event):
        if not self.doc:
            return
        sel = self.pages_listbox.curselection()
        if sel:
            idx = sel[0]
            if idx != self.page_index:
                self.page_index = idx
                self.clamp_pan()
                self.render_page()


    def reset_pan(self):
        self.pan_x = 0
        self.pan_y = 0

    def reset_pan_and_render(self):
        self.reset_pan()
        self.render_page()

    def clamp_pan(self):
        """Keep the page from being dragged outside the visible area."""
        canvas_w = int(self.canvas.cget("width"))
        canvas_h = int(self.canvas.cget("height"))
        center_x = (canvas_w - self.image_pix_width) // 2
        center_y = (canvas_h - self.image_pix_height) // 2


        min_off_x = min(0, canvas_w - self.image_pix_width)
        max_off_x = max(0, canvas_w - self.image_pix_width)
        min_off_y = min(0, canvas_h - self.image_pix_height)
        max_off_y = max(0, canvas_h - self.image_pix_height)

        # Convert canvas boundaries into limits for the pan offsets.
        pan_min_x = min_off_x - center_x
        pan_max_x = max_off_x - center_x
        pan_min_y = min_off_y - center_y
        pan_max_y = max_off_y - center_y

        self.pan_x = max(pan_min_x, min(pan_max_x, self.pan_x))
        self.pan_y = max(pan_min_y, min(pan_max_y, self.pan_y))

    def compute_offsets(self, canvas_w, canvas_h):
        """Combine centering with the current pan and keep it inside the canvas."""
        center_x = (canvas_w - self.image_pix_width) // 2
        center_y = (canvas_h - self.image_pix_height) // 2
        off_x = center_x + int(self.pan_x)
        off_y = center_y + int(self.pan_y)

        min_off_x = min(0, canvas_w - self.image_pix_width)
        max_off_x = max(0, canvas_w - self.image_pix_width)
        min_off_y = min(0, canvas_h - self.image_pix_height)
        max_off_y = max(0, canvas_h - self.image_pix_height)
        # Small pages stay centered; larger pages can be panned but not lost offscreen.
        off_x = max(min_off_x, min(max_off_x, off_x))
        off_y = max(min_off_y, min(max_off_y, off_y))
        self.center_offset_x = center_x
        self.center_offset_y = center_y
        self.pan_x = off_x - center_x
        self.pan_y = off_y - center_y
        return off_x, off_y


    def render_page(self):
        if not self.doc:
            return
        try:
            page = self.doc.load_page(self.page_index)
            rect = page.rect
            canvas_w = int(self.canvas.cget("width"))
            canvas_h = int(self.canvas.cget("height"))
            fit_x = canvas_w / rect.width
            fit_y = canvas_h / rect.height
            base = min(fit_x, fit_y)

            # Fit the page first, then apply the extra zoom from the slider.
            scale = base * (self.zoom_pct / 100.0)
            scale = min(scale, 10.0)
            self.render_scale = scale

            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.tk_img = ImageTk.PhotoImage(img)

            self.image_pix_width = pix.width
            self.image_pix_height = pix.height

            off_x, off_y = self.compute_offsets(canvas_w, canvas_h)


            self.canvas.delete("all")
            self.canvas.create_rectangle(0, 0, canvas_w, canvas_h, fill="#7f7f7f", outline="")
            self.canvas.create_image(off_x, off_y, anchor="nw", image=self.tk_img, tags=("pdfimage",))
            self.page_label.config(text=f"{os.path.basename(self.input_path)} — Page {self.page_index+1}/{len(self.doc)}")
            self.update_mapping_text()

            # Draw saved crop boxes on top of the preview so each one stays visible.
            for idx in range(1,6):
                preset = self.presets.get(idx)
                color = PRESET_COLORS[(idx-1) % len(PRESET_COLORS)]
                if preset:
                    (x0_pdf,y0_pdf),(x1_pdf,y1_pdf) = preset
                    x0_i = x0_pdf * self.render_scale + off_x
                    y0_i = y0_pdf * self.render_scale + off_y
                    x1_i = x1_pdf * self.render_scale + off_x
                    y1_i = y1_pdf * self.render_scale + off_y
                    if idx == self.active_preset:
                        self.canvas.create_rectangle(x0_i, y0_i, x1_i, y1_i, outline=color, width=3, tags=("preset",))
                    else:
                        self.canvas.create_rectangle(x0_i, y0_i, x1_i, y1_i, outline=color, dash=(4,3), width=2, tags=("preset",))
                    r = POINT_RADIUS if idx != self.active_preset else POINT_RADIUS+2
                    self.canvas.create_oval(x0_i-r, y0_i-r, x0_i+r, y0_i+r, fill=color, outline="black", tags=("point",))
                    self.canvas.create_oval(x1_i-r, y1_i-r, x1_i+r, y1_i+r, fill=color, outline="black", tags=("point",))

            active = self.presets.get(self.active_preset)
            if active:
                (xa,ya),(xb,yb) = active
                self.coords_label.config(text="%.1f,%.1f -> %.1f,%.1f" % (xa,ya,xb,yb))
            else:
                self.coords_label.config(text="Not set")


            try:
                self.canvas.focus_set()
            except Exception:
                pass
        except Exception:
            logging.exception("render_page failed")
            messagebox.showerror("Render error", "Failed rendering page. See log.")

    def canvas_to_image(self, cx, cy):
        # Mouse positions are on the canvas; remove the image offset before converting.
        ix = cx - (self.center_offset_x + int(self.pan_x))
        iy = cy - (self.center_offset_y + int(self.pan_y))
        ix = max(0, min(self.image_pix_width - 1, ix))
        iy = max(0, min(self.image_pix_height - 1, iy))
        return ix, iy

    def image_to_pdf(self, ix, iy):
        return ix / self.render_scale, iy / self.render_scale

    def pdf_to_image(self, xp, yp):
        return xp * self.render_scale, yp * self.render_scale

    def find_nearest_corner(self, ix, iy, preset_points_img=None):
        if preset_points_img is None:
            return None
        (x0,y0),(x1,y1) = preset_points_img
        d0 = math.hypot(ix-x0, iy-y0)
        d1 = math.hypot(ix-x1, iy-y1)
        if d0 <= NEAR_DIST and d0 <= d1:
            return 0
        if d1 <= NEAR_DIST and d1 < d0:
            return 1
        return None



    def on_canvas_down(self, event):
        try:
            self.canvas.focus_set()
        except Exception:
            pass

        if not self.doc:
            return
        cx, cy = event.x, event.y
        ix = cx - (self.center_offset_x + int(self.pan_x))
        iy = cy - (self.center_offset_y + int(self.pan_y))
        ix = max(0, min(self.image_pix_width-1, ix))
        iy = max(0, min(self.image_pix_height-1, iy))

        preset = self.presets.get(self.active_preset)
        preset_img = None
        if preset:
            (x0p,y0p),(x1p,y1p) = preset
            preset_img = (self.pdf_to_image(x0p,y0p), self.pdf_to_image(x1p,y1p))
        # Click near a corner to drag it, or use the closer corner if clicking elsewhere.
        nearest = self.find_nearest_corner(ix, iy, preset_img)
        if nearest is not None:
            self.dragging = (self.active_preset, nearest)
            logging.debug(f"Start dragging preset {self.active_preset} corner {nearest}")
        else:
            if preset is None:
                xp, yp = self.image_to_pdf(ix, iy)
                self.presets[self.active_preset] = ((xp, yp), (xp, yp))
                self.dragging = (self.active_preset, 1)
            else:
                (x0i,y0i),(x1i,y1i) = preset_img
                d0 = math.hypot(ix-x0i, iy-y0i)
                d1 = math.hypot(ix-x1i, iy-y1i)
                target = 0 if d0 <= d1 else 1
                xp, yp = self.image_to_pdf(ix, iy)
                pts = list(map(list, self.presets[self.active_preset]))
                pts[target] = [xp, yp]
                self.presets[self.active_preset] = (tuple(pts[0]), tuple(pts[1]))
                self.dragging = (self.active_preset, target)
        self.render_page()


    def on_canvas_move(self, event):
        if not self.doc or not self.dragging:
            return
        cx, cy = event.x, event.y
        ix = cx - (self.center_offset_x + int(self.pan_x))
        iy = cy - (self.center_offset_y + int(self.pan_y))
        ix = max(0, min(self.image_pix_width-1, ix))
        iy = max(0, min(self.image_pix_height-1, iy))
        xp, yp = self.image_to_pdf(ix, iy)
        preset_idx, corner_idx = self.dragging
        pts = list(map(list, self.presets[preset_idx]))
        pts[corner_idx] = [xp, yp]
        self.presets[preset_idx] = (tuple(pts[0]), tuple(pts[1]))
        self.render_page()

    def on_canvas_up(self, event):
        if not self.doc:
            return
        if self.dragging:
            logging.debug(f"Stop dragging {self.dragging}")
        self.dragging = None
        self.render_page()


    def on_key_press(self, event):
        focused = self.root.focus_get()
        if focused != self.canvas:
            return
        key = event.keysym.lower()
        if key not in ('w','a','s','d'):
            return


        step = PAN_STEP_PX
        # These key directions move the view opposite to the usual WASD camera controls.
        if key == 'w':
            self.pan_y += step
        elif key == 's':
            self.pan_y -= step
        elif key == 'd':
            self.pan_x -= step
        elif key == 'a':
            self.pan_x += step
        self.clamp_pan()
        self.render_page()

    def assign_selection_active(self):
        if not self.doc:
            messagebox.showwarning("No PDF", "Open a PDF first.")
            return
        sel = self.pages_listbox.curselection()
        if not sel:
            messagebox.showwarning("No pages selected", "Select page(s) to assign.")
            return
        if self.presets.get(self.active_preset) is None:
            if not messagebox.askyesno("Preset not set", "Active preset not set. Are you sure want to assign anyway?"):
                return
        for idx in sel:
            if idx in self.removed_pages:
                self.removed_pages.discard(idx)
            self.page_assignments[idx] = self.active_preset
        logging.info(f"Assigned pages {sel} -> preset {self.active_preset}")
        self.update_mapping_text()


    def unassign_selection(self):
        if not self.doc:
            return
        sel = self.pages_listbox.curselection()
        for idx in sel:
            if idx in self.page_assignments:
                del self.page_assignments[idx]
        self.update_mapping_text()

    def mark_selected_removed(self):
        if not self.doc:
            messagebox.showwarning("No PDF", "Open a PDF first.")
            return
        sel = self.pages_listbox.curselection()
        if not sel:
            messagebox.showwarning("No pages selected", "Select page(s) to mark for removal.")
            return
        for idx in sel:

            if idx in self.page_assignments:
                del self.page_assignments[idx]
            self.removed_pages.add(idx)
        logging.info(f"Marked pages {sel} for removal")
        self.update_mapping_text()
        self.render_page()


    def unmark_selected_removed(self):
        if not self.doc:
            return
        sel = self.pages_listbox.curselection()
        for idx in sel:
            if idx in self.removed_pages:
                self.removed_pages.remove(idx)
        logging.info(f"Unmarked pages {sel} from removal")
        self.update_mapping_text()
        self.render_page()

    def update_mapping_text(self):
        self.mapping_text.delete("1.0", tk.END)
        lines = []
        for i in range(len(self.doc)) if self.doc else []:
            p = i+1

            # Removal wins over any crop assignment when showing the page mapping.
            if i in self.removed_pages:
                lines.append(f"Page {p}: Removed")
                continue
            preset = self.page_assignments.get(i)
            if preset:
                lines.append(f"Page {p}: Preset {preset}")
            else:
                lines.append(f"Page {p}: (unassigned)")
        self.mapping_text.insert(tk.END, "\n".join(lines))


    def prev_page(self):
        if not self.doc: return
        if self.page_index > 0:
            self.page_index -= 1
            try:
                self.pages_listbox.selection_clear(0, tk.END)
                self.pages_listbox.selection_set(self.page_index)
                self.pages_listbox.see(self.page_index)
            except Exception:
                pass
            self.clamp_pan()
            self.render_page()

    def next_page(self):
        if not self.doc: return
        if self.page_index < len(self.doc)-1:
            self.page_index += 1
            try:
                self.pages_listbox.selection_clear(0, tk.END)
                self.pages_listbox.selection_set(self.page_index)
                self.pages_listbox.see(self.page_index)
            except Exception:
                pass
            self.clamp_pan()
            self.render_page()


    def clear_all_assignments(self):
        self.page_assignments.clear()
        self.removed_pages.clear()
        self.update_mapping_text()
        self.render_page()


    def save_output(self):
        if not self.doc:
            messagebox.showwarning("No PDF", "Open a PDF")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not out_path:
            logging.info("Save cancelled ):")
            return

        outdoc = fitz.open()
        total = len(self.doc)
        pages_written = 0
        logging.info(f"Starting export at: {out_path} ...")
        try:
            # Export one page at a time so removed and unchanged pages keep their original order.
            for pno in range(total):
                if pno in self.removed_pages:
                    logging.debug(f"Skipping page {pno+1} because it's marked removed")
                    continue


                preset_idx = self.page_assignments.get(pno)
                if preset_idx:
                    rect = self.presets.get(preset_idx)
                    if rect is None:
                        if self.keep_unassigned.get():
                            outdoc.insert_pdf(self.doc, from_page=pno, to_page=pno)
                            pages_written += 1
                        else:
                            pass
                    else:
                        (x0,y0),(x1,y1) = rect
                        w = abs(x1 - x0)
                        h = abs(y1 - y0)
                        if w <= 0 or h <= 0:
                            logging.warning(f"Skipping page {pno+1}: invalid preset rect {rect}")
                            continue
                        np = outdoc.new_page(width=w, height=h)
                        clip = fitz.Rect(min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1))
                        # Copy the clipped PDF area into a new page without turning it into an image.
                        np.show_pdf_page(fitz.Rect(0,0,w,h), self.doc, pno, clip=clip)
                        pages_written += 1
                else:
                    if self.keep_unassigned.get():
                        outdoc.insert_pdf(self.doc, from_page=pno, to_page=pno)
                        pages_written += 1
                    else:
                        pass


            outdoc.save(out_path)
            outdoc.close()
            logging.info(f"Saved {pages_written} to: {out_path}")
            messagebox.showinfo("Saved", f"Saved {pages_written} to:\n{out_path}")
        except Exception:
            logging.exception("Failed during save_output")
            messagebox.showerror("Error saving PDF", f"Failed to save. See log: {LOGFILE}")

def run_app():
    try:
        root = tk.Tk()
        root.minsize(600, 400)
        root.geometry("660x660+0+0")
        app = PDFCropperGUI(root)
        logging.info("Entering mainloop (:")
        root.mainloop()
        logging.info("Mainloop exited (:")
    except Exception:
        logging.exception("Unhandled exception in run_app")
        tb = traceback.format_exc()
        fatal_messagebox("error", f"An unexpected error occurred:\n\n{tb}\n\nSee log: {LOGFILE}")

if __name__ == "__main__":
    logging.info("TOOL started.")
    run_app()
    logging.info("TOOL finished.")

