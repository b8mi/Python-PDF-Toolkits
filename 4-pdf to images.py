import io
from pathlib import Path
from PIL import Image

try:
    import fitz
except ImportError:
    fitz = None

try:
    from pdf2image import convert_from_path, pdfinfo_from_path
except ImportError:
    convert_from_path = pdfinfo_from_path = None


FORMATS = ["png", "jpg", "jpeg", "tiff", "bmp", "webp"]


def clean_path(value):
    return Path(value.strip().strip('"\'')).expanduser()


def choose_format():
    print("\nIMAGE FORMATS")

    for i, fmt in enumerate(FORMATS, 1):
        print(f"  {i} : {fmt}")

    choice = input("Format [PNG]: ").strip().lower()

    if choice.isdigit():
        index = int(choice) - 1
        return FORMATS[index] if 0 <= index < len(FORMATS) else "png"

    return choice if choice in FORMATS else "png"


def parse_pages(spec, count):
    if not spec.strip() or spec.strip().lower() == "all":
        return list(range(count))

    result = []
    seen = set()

    for token in spec.split(","):
        parts = token.strip().split("-")

        if len(parts) not in (1, 2) or any(
            not p.strip().isdigit() for p in parts
        ):
            raise ValueError("Use page numbers or ranges, e.g. 1,3-5.")

        start, end = int(parts[0]), int(parts[-1])

        if not 1 <= start <= end <= count:
            raise ValueError(
                f"Page ranges must be within 1-{count}, in ascending order."
            )

        for index in range(start - 1, end):
            if index not in seen:
                seen.add(index)
                result.append(index)

    return result


def ask_pages(count):
    while True:
        try:
            return parse_pages(
                input(f"Pages (1-{count}; e.g. 1,3-5) [all]: "),
                count
            )
        except ValueError as exc:
            print(exc)


def choose_quality():
    print(
        "\nQUALITY\n"
        "  1 : Original behavior (native image or 72 DPI)\n"
        "  2 : Smart (adaptive resolution up to 300 DPI)\n"
        "  3 : Custom DPI (render the entire page)"
    )

    while True:
        choice = input("Quality [1]: ").strip()

        if choice in ("", "1"):
            return "original", 72

        if choice == "2":
            return "smart", 150

        if choice == "3":
            try:
                dpi = int(input("DPI (72-600): "))

                if 72 <= dpi <= 600:
                    return "custom", dpi

            except ValueError:
                pass

            print("Enter a DPI between 72 and 600.")

        else:
            print("Choose 1, 2 or 3.")


def save_bytes(path, data):
    # Never overwrite an existing image.
    try:
        with path.open("xb") as output:
            output.write(data)

    except FileExistsError:
        return "skipped"

    return "saved"


def save_image(img, path, fmt, dpi=None):
    options = {}

    if fmt in ("jpg", "jpeg", "webp"):
        options["quality"] = 95

    if dpi is not None and fmt != "webp":
        options["dpi"] = (dpi, dpi)

    pil_format = "JPEG" if fmt in ("jpg", "jpeg") else fmt.upper()

    with io.BytesIO() as buffer, img.convert("RGB") as rgb:
        rgb.save(buffer, format=pil_format, **options)

        return save_bytes(path, buffer.getvalue())


def native_page_image(doc, page):
    # Determine whether the page is a single complete image.
    # Avoid extraction if it would lose visible information.

    try:
        if (
            page.rotation
            or page.first_annot
            or page.first_widget
            or page.get_links()
        ):
            return None

        if page.get_text().strip():
            return None

        if [item[0] for item in page.get_bboxlog()] != ["fill-image"]:
            return None

        images = page.get_images(full=True)

        if len(images) != 1:
            return None

        xref, mask = images[0][:2]

        if not xref or mask:
            return None

        spots = page.get_image_rects(xref, transform=True)

        if len(spots) != 1:
            return None

        rect, matrix = spots[0]

        if any(
            abs(a - b) >= 2
            for a, b in zip(rect, page.rect)
        ):
            return None

        if (
            matrix.a <= 0
            or matrix.d <= 0
            or abs(matrix.b) > 0.01
            or abs(matrix.c) > 0.01
        ):
            return None

        info = doc.extract_image(xref)

        image_ratio = info["width"] / info["height"]
        page_ratio = rect.width / rect.height

        if abs(image_ratio / page_ratio - 1) > 0.01:
            return None

        if doc.xref_get_key(xref, "Decode")[0] != "null":
            return None

        return info

    except Exception:
        return None


def adaptive_dpi(page):
    # Analyze text sizes and page dimensions.
    # Higher resolution is selected for small, detailed content.

    blocks = page.get_text(
        "dict",
        flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
    )

    sizes = [
        span["size"]
        for block in blocks["blocks"]
        if block["type"] == 0
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    ]

    small_text = bool(sizes and min(sizes) < 10)
    compact_page = min(page.rect.width, page.rect.height) < 400

    dpi = 300 if small_text or compact_page else 200

    # Limit bitmap size to reduce excessive memory consumption.
    area = page.rect.width * page.rect.height

    cap = int(
        72 * (24_000_000 / max(area, 1)) ** 0.5
    )

    return max(72, min(dpi, cap))


def output_path(folder, stem, index, fmt):
    return folder / f"{stem}_page_{index + 1:04d}.{fmt}"


def convert_fitz_page(doc, index, target, fmt, mode, dpi):
    if target.exists():
        return "skipped", "existing file"

    page = doc.load_page(index)

    if mode != "custom":
        info = native_page_image(doc, page)

        if info:
            try:
                data = info["image"]
                ext = info["ext"].lower()

                if ext == fmt or {ext, fmt} == {"jpg", "jpeg"}:
                    status = save_bytes(target, data)

                else:
                    with Image.open(io.BytesIO(data)) as img:
                        status = save_image(img, target, fmt)

                return status, "native image"

            except Exception as exc:
                print(
                    f"  Native extraction unavailable: {exc}; "
                    "rendering instead."
                )

    actual_dpi = adaptive_dpi(page) if mode == "smart" else dpi

    pix = page.get_pixmap(
        dpi=actual_dpi,
        alpha=False,
        colorspace=fitz.csRGB
    )

    if fmt == "png":
        status = save_bytes(target, pix.tobytes("png"))

    else:
        with Image.frombytes(
            "RGB",
            (pix.width, pix.height),
            pix.samples
        ) as img:
            status = save_image(img, target, fmt, actual_dpi)

    return status, f"rendered at {actual_dpi} DPI"


def convert_poppler_page(path, index, target, fmt, mode, dpi):
    if target.exists():
        return "skipped", "existing file"

    actual_dpi = 200 if mode == "smart" else dpi

    images = convert_from_path(
        str(path),
        dpi=actual_dpi,
        first_page=index + 1,
        last_page=index + 1,
        thread_count=1
    )

    if not images:
        raise RuntimeError("Poppler returned no image.")

    try:
        status = save_image(images[0], target, fmt, actual_dpi)

        return status, f"Poppler at {actual_dpi} DPI"

    finally:
        for img in images:
            img.close()


def process_pages(path, folder, fmt, indices, mode, dpi, doc=None):
    totals = {
        "saved": 0,
        "skipped": 0,
        "failed": 0
    }

    for position, index in enumerate(indices, 1):
        target = output_path(folder, path.stem, index, fmt)

        try:
            if doc is not None:
                status, method = convert_fitz_page(
                    doc, index, target, fmt, mode, dpi
                )

            else:
                status, method = convert_poppler_page(
                    path, index, target, fmt, mode, dpi
                )

            totals[status] += 1

            print(
                f"[{position}/{len(indices)}] "
                f"{status.upper():7} {target.name} ({method})"
            )

        except Exception as exc:
            totals["failed"] += 1

            print(
                f"[{position}/{len(indices)}] "
                f"FAILED {target.name}: {exc}"
            )

    return totals


def print_summary(totals, folder):
    print("\n--- CONVERSION SUMMARY ---")

    for key, value in totals.items():
        print(f"{key.title():8}: {value}")

    print(f"Folder  : {folder.resolve()}")


def main():
    print("================================")
    print("       PDF TO IMAGES V2")
    print("================================")

    raw_pdf = input("PDF path: ").strip()
    raw_folder = input("Output folder path: ").strip()

    if not raw_pdf or not raw_folder:
        print("Both paths are required.")
        return 1

    path = clean_path(raw_pdf)
    folder = clean_path(raw_folder)

    if not path.is_file():
        print("PDF not found.")
        return 1

    if fitz is None and convert_from_path is None:
        print("Install PyMuPDF or pdf2image to read PDFs.")
        return 1

    try:
        folder.mkdir(parents=True, exist_ok=True)

        fmt = choose_format()

        if fitz is not None:
            with fitz.open(str(path)) as doc:

                if doc.needs_pass:
                    raise ValueError(
                        "Password-protected PDFs are not supported."
                    )

                if not doc.is_pdf or not doc.page_count:
                    raise ValueError(
                        "Choose a PDF containing at least one page."
                    )

                indices = ask_pages(doc.page_count)

                mode, dpi = choose_quality()

                totals = process_pages(
                    path, folder, fmt, indices, mode, dpi, doc
                )

        else:
            count = int(pdfinfo_from_path(str(path))["Pages"])

            if count < 1:
                raise ValueError("PDF contains no pages.")

            indices = ask_pages(count)

            mode, dpi = choose_quality()

            if mode == "smart":
                print("Poppler fallback: smart quality uses 200 DPI.")

            totals = process_pages(
                path, folder, fmt, indices, mode, dpi
            )

        print_summary(totals, folder)

        return int(totals["failed"] > 0)

    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
