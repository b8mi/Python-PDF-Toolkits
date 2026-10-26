# Python PDF Tools

Five small Python tools for working with PDF files. I made them as separate scripts because sometimes I just need to merge a few documents, crop some pages, or convert files without opening a larger PDF editor.

The scripts are numbered **1 to 5**. Each one works independently: you only need to run the tool you want to use.

| Script | Tool | Interface | Description |
| --- | --- | --- | --- |
| [`1-pdf cropper.py`](1-pdf%20cropper.py) | PDF Cropper | Desktop GUI | Crop selected pages using reusable presets; remove unwanted pages |
| [`2-pdf merger.py`](2-pdf%20merger.py) | PDF Merger | Desktop GUI | Combine multiple PDFs in a chosen order |
| [`3-pdf compressor.py`](3-pdf%20compressor.py) | PDF Compressor | Terminal | Try to reduce PDF size by repacking its data |
| [`4-pdf to images.py`](4-pdf%20to%20images.py) | PDF to Images | Terminal | Save PDF pages as separate image files |
| [`5-image to pdf.py`](5-image%20to%20pdf.py) | Images to PDF | Desktop GUI | Put multiple images into one PDF |

## Installation

You need **Python 3.10 or newer**. Download or clone the repository, then open a terminal in the folder containing the scripts and run:

```bash
python -m pip install -r requirements.txt
```

This installs **PyMuPDF**, **Pillow**, and **pypdf**. The graphical tools also use **Tkinter**, which is included with most Python installations. On some Linux distributions it must be installed separately, often as `python3-tk`.

The PDF-to-images script has an optional `pdf2image` fallback, but you don't need it for the normal installation. If you use that fallback, you may also need Poppler.

---

## 1. PDF Cropper — `1-pdf cropper.py`

This is for PDFs where different pages need different cropping areas. Instead of cropping every page to the same rectangle, you can define up to **five presets**, then decide which pages use each one.

**What it does:**
- Opens and previews a PDF, with adjustable preview size and zoom.
- Lets you draw and adjust five reusable crop rectangles.
- Assigns a crop preset to one page or several pages at once.
- Marks unwanted pages for removal.
- Keeps unassigned pages unchanged by default (you can turn this off).
- Exports the selected pages to a new PDF.

**How to use it:**
1. Start it with `python "1-pdf cropper.py"`, then go to **File → Open PDF**.
2. Select a preset and click or drag on the preview to define the crop area. Drag its corners to adjust it.
3. Select the pages in the **Pages** list and click **Assign selected to active Preset**.
4. Repeat with another preset if other pages need a different crop area.
5. Mark pages for removal if necessary, then choose **Save PDF**.

**Useful details:** Cropping uses PDF coordinates, so changing the preview zoom doesn't change the saved crop. **Center View** resets the preview position. The WASD movement is intentionally reversed: W moves the page down, S up, A right, and D left. The script writes a local `pdfcd.log` file to help debug errors; that file can include local paths and shouldn't be uploaded to GitHub.

![PDF Cropper window](1.png)

---

## 2. PDF Merger — `2-pdf merger.py`

A simple way to put several PDFs into **one file**, without having to manually copy pages between documents.

**What it does:**
- Adds multiple PDF files through a file picker.
- Shows the files in a list so you can check their order.
- Lets you drag files up or down to rearrange them.
- Removes files you don't want in the final document.
- Merges everything into one PDF.

**How to use it:**
1. Run `python "2-pdf merger.py"`.
2. Click **+add file+** and select at least two PDFs.
3. Drag the filenames into the order you want (top to bottom).
4. Remove anything unnecessary with **-remove file-**.
5. Click **>merge<** and select where to save the finished PDF.

**Useful details:** This combines **whole PDFs**, not selected pages within each PDF. Adding the exact same path again is ignored. The original files are left alone when you save the merged result to a new path.

![PDF Merger window](2.png)

---

## 3. PDF Compressor — `3-pdf compressor.py`

Attempts to reduce PDF file sizes by cleaning up and compressing their internal data, while keeping the PDF format.

**What it does:**
- Accepts several PDF paths in one run.
- Creates an output folder if needed.
- Uses PyMuPDF to remove unneeded objects and compress PDF streams.
- Reports the final file size and percentage saved for each PDF.

**How to use it:**
1. Run `python "3-pdf compressor.py"`.
2. Paste a PDF path and press **Enter**; repeat for any additional PDFs.
3. Press **Enter** on a blank line when you're done adding files.
4. Enter a **different destination folder** for the processed documents.
5. Check the reported savings and open the exported files to make sure they're correct.

**Useful details:** This script **does not lower the resolution of images** inside PDFs. It can help with uncompressed PDF data, but scanned or already-compressed PDFs may barely change in size. Sometimes the output is actually larger (shown as negative savings). The exported PDFs keep their original filenames, so use a separate destination folder to avoid overwriting your originals.

---

## 4. PDF to Images — `4-pdf to images.py`

Converts a PDF into individual image files. It is useful when you need an image of each page rather than the complete document.

**What it does:**
- Exports pages as **PNG, JPG, JPEG, TIFF, BMP, or WebP**.
- Creates the destination folder if it doesn't already exist.
- Numbers the output files, such as `document_page_0001.png`.
- Tries to extract a full-page embedded image at its original resolution when possible.
- Otherwise renders the PDF page into an image.
- Skips an output file if that filename already exists.

**How to use it:**
1. Run `python "4-pdf to images.py"`.
2. Paste the path to the PDF when prompted.
3. Enter the destination folder.
4. Pick the format by number or name. Press **Enter** for the default, PNG.
5. Find the numbered images in your chosen folder.

**Useful details:** Ordinary PDF pages are rendered at approximately **72 DPI** in the current script, which may be too low for some detailed documents. A page that consists of one full-page image may keep that embedded image's original resolution. If you edit the PDF and export again, move or delete old images first, since matching filenames are skipped.

---

## 5. Images to PDF — `5-image to pdf.py`

Takes multiple images and puts them into a single multi-page PDF. The order you see in the list becomes the page order.

**What it does:**
- Accepts **PNG, JPG, JPEG, BMP, TIFF, and GIF** files.
- Allows multiple images to be selected at once.
- Reorders images with **Move Up** and **Move Down**.
- Removes selected images or clears the list.
- Exports the images together as one PDF.

**How to use it:**
1. Run `python "5-image to pdf.py"`.
2. Click **Add Images** and choose your files.
3. Arrange them in the correct order with **Move Up** and **Move Down**.
4. Click **Export**, choose the output folder, and enter the new PDF's name.

**Useful details:** The `.pdf` extension is added automatically if needed. Images are converted to RGB when necessary, so transparency may not look the same in the final PDF. Animated GIFs are not expanded into multiple pages: the script uses the frame that Pillow opens.

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

This project provides five simple Python tools for working with PDF files directly on your computer, without relying on online PDF websites or cloud services.

Whether you need to merge multiple PDFs, crop specific pages, compress a document, or convert between PDFs and images, these tools let you do everything locally.

**Why use these tools?**
- **Works offline:** No Wi-Fi or internet connection required after installing the dependencies.
- **Privacy:** Your documents stay on your computer instead of being uploaded to third-party websites.
- **Free to use:** No subscriptions, accounts, or paid services.
- **Simple:** Each script focuses on a specific task and can be used independently.
- **No unnecessary steps:** Select your files, process them, and save the result!

## AI Assistance

AI was used to explain parts of the code for easier debugging and to assist with documentation. Each script includes an AI disclosure at the top.
