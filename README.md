# PDF Tools Python

Five tiny Python scripts for working with PDFs. I keep them as standalone scripts because I often just need to combine a few PDFs, crop some pages, or change their format without firing up a bigger PDF editor.

The scripts are numbered **1 to 5**. Each script works independently: you just need to run the tool you want to use.

| Script | Tool | Interface | Description |
| --- | --- | --- | --- |
| [`1-pdf cropper.py`](1-pdf%20cropper.py) | PDF Cropper | Desktop GUI | Crop pages using reusable presets; delete pages you do not need |
| [`2-pdf merger.py`](2-pdf%20merger.py) | PDF Merger | Desktop GUI | Merge two or more PDFs in an order of your choosing |
| [`3-pdf compressor.py`](3-pdf%20compressor.py) | PDF Compressor | Terminal | Try to minimize PDF size by repacking its data |
| [`4-pdf to images.py`](4-pdf%20to%20images.py) | PDF to Images | Terminal | Save PDF pages as separate image files |
| [`5-image to pdf.py`](5-image%20to%20pdf.py) | Images to PDF | Desktop GUI | Combine several images into a single PDF |

## Installation

You will need **Python 3.10 or newer**. Download or clone the repository, open a terminal in the folder containing the scripts, and run:

```bash
python -m pip install -r requirements.txt
```

This installs **PyMuPDF**, **Pillow**, and **pypdf**. The GUI tools also use **Tkinter**, which comes with most Python installations. On some Linux distributions, you need to install it separately, often as `python3-tk`.

The PDF-to-images script has an optional `pdf2image` fallback, but you do not need it for a normal installation. You may also need Poppler if you use that fallback.

---

## 1. PDF Cropper — `1-pdf cropper.py`

This tool is for PDFs where different pages need different cropping areas. You can set up to **five crop rectangles**, then tell the app which pages should use each one.

**What it does:**
- Opens and previews a PDF with adjustable preview size and zoom.
- Lets you draw and reposition five reusable crop rectangles.
- Assigns one crop preset to one or multiple pages.
- Marks unwanted pages for removal.
- Leaves unassigned pages alone by default (you can disable this).
- Exports the selected pages to a new PDF.

**How to use it:**
1. Run `python "1-pdf cropper.py"`, then go to **File → Open PDF**.
2. Choose a preset, then click or drag in the preview to set the crop area. Drag the corners to resize it.
3. Select the pages in the **Pages** list, then click **Assign selected to active Preset**.
4. Repeat with another preset if other pages need a different crop area.
5. Mark pages you want to remove, then click **Save PDF**.

**Useful details:** Cropping uses PDF coordinates, so changing the preview zoom does not affect the saved crop. **Center View** resets the preview position. The WASD movement is intentionally reversed: W moves the page down, S up, A right, and D left. The script writes a local `pdfcd.log` file to help debug errors; this file may include local paths and should not be uploaded to GitHub.

![PDF Cropper window](1.png)

---

## 2. PDF Merger — `2-pdf merger.py`

A quick way to merge a couple of PDFs into **one file** without having to copy and paste pages between documents.

**What it does:**
- Lets you add multiple PDFs using a file picker.
- Displays the files in a list so you can check their order.
- Lets you drag files up or down to rearrange them.
- Removes unwanted files from the list before merging.
- Merges everything into one PDF.

**How to use it:**
1. Run `python "2-pdf merger.py"`.
2. Click **+add file+** and choose at least two PDFs.
3. Drag the filenames into the order you want, from top to bottom.
4. Remove anything unnecessary with **-remove file-**.
5. Click **>merge<** and choose where to save the finished PDF.

**Useful details:** This merges **whole PDFs**, not selected pages within them. Adding the exact same file path again is ignored. The original files stay untouched when you save the merged document to a new path.

![PDF Merger window](2.png)

---

## 3. PDF Compressor — `3-pdf compressor.py`

Attempts to shrink PDF files by cleaning and compressing the data inside them while keeping the PDF format.

**What it does:**
- Accepts several PDF paths in one run.
- Creates an output folder if needed.
- Uses PyMuPDF to remove unneeded objects and compress PDF streams.
- Displays each PDF's final file size and percentage saved.

**How to use it:**
1. Run `python "3-pdf compressor.py"`.
2. Paste a PDF path and press **Enter**. Repeat for any additional PDFs.
3. Press **Enter** on a blank line when you are finished adding files.
4. Choose a **different destination folder** for the processed documents.
5. Check the reported savings and open the exported files to verify they are correct.

**Useful details:** This script **does not lower the resolution of images** inside PDFs. It may help with uncompressed PDF data, but scanned or already-compressed PDFs may show little to no reduction. Sometimes the output can even be larger, shown as negative savings. Exported PDFs keep their original filenames, so use a separate destination folder to avoid overwriting the source files.

---

## 4. PDF to Images — `4-pdf to images.py`

Turn every page of a PDF into a separate image file. This is helpful when you want an image of each page instead of the entire document.

**What it does:**
- Exports pages as **PNG, JPG, JPEG, TIFF, BMP, or WebP**.
- Creates the destination folder if needed.
- Numbers the output files, for example `document_page_0001.png`.
- Attempts to extract a full-page embedded image at its original resolution when possible.
- Otherwise renders the PDF page as an image.
- Skips an output file if its filename already exists.

**How to use it:**
1. Run `python "4-pdf to images.py"`.
2. Paste the path to the PDF when prompted.
3. Enter the destination folder.
4. Choose the format by number or name. Press **Enter** for the default, PNG.
5. Open your chosen folder and find the numbered images.

**Useful details:** Normal PDF pages are rendered at about **72 DPI** in the current script, which may be too low for detailed documents. A page containing one full-page image may preserve that embedded image's original resolution. If you edit the PDF and export again, move or delete the older images first, because matching filenames will be skipped.

---

## 5. Images to PDF — `5-image to pdf.py`

Takes a sequence of images and assembles them into a single multi-page PDF. The order shown in the list becomes the page order.

**What it does:**
- Supports **PNG, JPG, JPEG, BMP, TIFF, and GIF**.
- Lets you select several images at once.
- Rearranges images with **Move Up** and **Move Down**.
- Removes selected images from the list or clears the entire list.
- Combines the images into one PDF.

**How to use it:**
1. Run `python "5-image to pdf.py"`.
2. Click **Add Images** and select your files.
3. Arrange them in the right order with **Move Up** and **Move Down**.
4. Click **Export**, choose the output folder, and name the new PDF.

**Useful details:** The `.pdf` extension is added automatically if needed. Images are converted to RGB when necessary, so transparency might not look the same in the final PDF. Animated GIFs are not split into multiple pages: the script uses the frame that Pillow opens.

![Images to PDF window](5.png)

---

## Repository structure

```text
PDF-Tools/
├── README.md
├── requirements.txt
├── .gitignore
├── 1-pdf cropper.py
├── 2-pdf merger.py
├── 3-pdf compressor.py
├── 4-pdf to images.py
├── 5-image to pdf.py
├── 1.png
├── 2.png
└── 5.png
```

## About This Project

These free PDF tools work directly on your computer. You do not need to connect to online PDF websites or cloud services.

Combine PDFs, crop specific pages, shrink a document, or convert between PDFs and images. You can do all of this from your own machine.

**Why use these tools?**
- **Work offline:** No Wi-Fi or internet connection required once the dependencies are installed.
- **Keep your files private:** Your documents stay on your computer instead of going to third-party websites.
- **Free to use:** No subscriptions, accounts, or paid services.
- **Easy to use:** Each script focuses on a specific task and runs independently.
- **No chitchatting:** Pick your files, process them, and save!
