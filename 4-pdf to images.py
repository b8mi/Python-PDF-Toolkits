from pathlib import Path
import io
import sys

try:
    import fitz
except ImportError:
    fitz = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

from PIL import Image

FORMATS = ["png", "jpg", "jpeg", "tiff", "bmp", "webp"]


pdf_path = Path(input("PDF path: ").strip().strip('"'))
folder = Path(input("Output folder path: ").strip().strip('"'))

if not pdf_path.is_file():
    print("PDF not found.")
    sys.exit(1)

if fitz is None and convert_from_path is None:
    print("Install PyMuPDF or pdf2image to read PDFs.")
    sys.exit(1)

folder.mkdir(parents=True, exist_ok=True)

# A number or a format name both work; pressing Enter uses PNG.
for i, f in enumerate(FORMATS, 1):
    print(f"{i} : {f}")

choice = input(": ").strip().lower()
if choice.isdigit():
    spot = int(choice) - 1
    fmt = FORMATS[spot] if 0 <= spot < len(FORMATS) else "png"
else:
    fmt = choice if choice in FORMATS else "png"

stem = pdf_path.stem


def save_bytes(path: Path, data: bytes):
    # Leave existing page images alone if this was run before.
    if path.exists():
        print("skip", path.name)
        return True
    with open(path, "wb") as f:
        f.write(data)
    print("saved", path.name)
    return True


def save_image(img, path: Path, fmt: str):
    if path.exists():
        print("skip", path.name)
        return True
    try:
        img.convert("RGB").save(
            path,
            format="JPEG" if fmt in ("jpg", "jpeg") else fmt.upper(),
            quality=95
        )
        print("saved", path.name)
        return True
    except Exception as e:
        print("couldn't save", path.name, e)
        return False


if fitz is not None:
    with fitz.open(str(pdf_path)) as doc:
        for pno in range(doc.page_count):
            page = doc.load_page(pno)
            target = folder / f"{stem}_page_{pno+1:04d}.{fmt}"
            saved = False

            # Sometimes the whole page is one image. Extracting it keeps its original resolution.
            for item in page.get_images(full=True):
                xref = item[0]
                try:
                    spots = page.get_image_rects(xref)
                    covers = any(
                        abs(r.x0 - page.rect.x0) < 2 and
                        abs(r.y0 - page.rect.y0) < 2 and
                        abs(r.x1 - page.rect.x1) < 2 and
                        abs(r.y1 - page.rect.y1) < 2
                        for r in spots
                    )
                    if not covers:
                        continue

                    info = doc.extract_image(xref)
                    data = info["image"]
                    ext = info.get("ext", "png").lower()

                    if ext == fmt:
                        saved = save_bytes(target, data)
                    else:
                        with Image.open(io.BytesIO(data)) as img:
                            saved = save_image(img, target, fmt)
                    if saved:
                        break
                except Exception as e:
                    print("couldn't extract image:", e)

            # Regular PDF pages have text or drawings, so render those normally.
            if not saved:
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                if fmt == "png":
                    if target.exists():
                        print("skip", target.name)
                    else:
                        pix.save(str(target))
                        print("rendered", target.name)
                else:
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    save_image(img, target, fmt)

else:
    # pdf2image is a backup when PyMuPDF isn't installed (it may need Poppler).
    pages = convert_from_path(str(pdf_path), dpi=72)
    for i, img in enumerate(pages, 1):
        target = folder / f"{stem}_page_{i:04d}.{fmt}"
        save_image(img, target, fmt)
