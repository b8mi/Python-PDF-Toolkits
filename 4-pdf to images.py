import fitz
from pathlib import Path


def get_pdf():
    while True:
        path = Path(input("Enter PDF path: ").strip().strip('"'))

        if path.is_file() and path.suffix.lower() == ".pdf":
            return path

        print("Invalid PDF path.")


def get_dpi():
    print("\nImage quality:")
    print("1. Standard (150 DPI)")
    print("2. High (300 DPI)")
    print("3. Custom DPI")
    print("4. Adaptive DPI")

    while True:
        choice = input("Select quality: ").strip()

        if choice == "1":
            return 150

        if choice == "2":
            return 300

        if choice == "3":
            while True:
                try:
                    dpi = int(input("Enter DPI (72-600): "))

                    if 72 <= dpi <= 600:
                        return dpi

                    print("DPI must be between 72 and 600.")

                except ValueError:
                    print("Enter a valid integer.")

        if choice == "4":
            return None

        print("Invalid option.")


def get_adaptive_dpi(page):
    longest_side = max(page.rect.width, page.rect.height)
    dpi = int(3000 * 72 / longest_side)

    return max(72, min(600, dpi))


def get_format():
    while True:
        image_format = input("Image format (PNG/JPG) [PNG]: ").strip().lower() or "png"

        if image_format in ("png", "jpg", "jpeg"):
            return image_format

        print("Unsupported image format.")


def get_pages(total):
    print(f"\nTotal pages: {total}")

    while True:
        selection = input("Enter pages (1,3,5-8) or all [all]: ").strip().lower()

        if selection in ("", "all"):
            return list(range(total))

        try:
            pages = set()

            for part in selection.split(","):
                part = part.strip()

                if "-" in part:
                    start, end = map(int, part.split("-"))

                    if not 1 <= start <= end <= total:
                        raise ValueError

                    pages.update(range(start - 1, end))

                else:
                    page = int(part)

                    if not 1 <= page <= total:
                        raise ValueError

                    pages.add(page - 1)

            return sorted(pages)

        except ValueError:
            print("Invalid page selection.")


def get_output_folder(pdf_path):
    default = pdf_path.parent / f"{pdf_path.stem}_images"

    while True:
        raw = input(f"Output folder [{default}]: ").strip().strip('"')
        folder = Path(raw) if raw else default

        try:
            folder.mkdir(parents=True, exist_ok=True)
            return folder

        except OSError as error:
            print(f"Cannot create folder: {error}")


def convert_pdf(pdf_path, document, output_folder, pages, dpi, image_format):
    completed = 0

    for index, page_number in enumerate(pages, start=1):
        try:
            page = document[page_number]
            resolution = dpi if dpi is not None else get_adaptive_dpi(page)

            pixmap = page.get_pixmap(dpi=resolution, colorspace=fitz.csRGB, alpha=False)

            filename = f"{pdf_path.stem}_page_{page_number + 1:03d}.{image_format}"
            output_path = output_folder / filename

            if image_format in ("jpg", "jpeg"):
                pixmap.save(str(output_path), jpg_quality=95)
            else:
                pixmap.save(str(output_path))

            completed += 1

            print(f"[{index}/{len(pages)}] Page {page_number + 1} saved at {resolution} DPI")

        except Exception as error:
            print(f"Failed to convert page {page_number + 1}: {error}")

    return completed


def main():
    pdf_path = get_pdf()

    try:
        with fitz.open(str(pdf_path)) as document:
            if document.needs_pass:
                password = input("Enter PDF password: ")

                if not document.authenticate(password):
                    print("Incorrect password.")
                    return

            dpi = get_dpi()
            image_format = get_format()
            pages = get_pages(len(document))
            output_folder = get_output_folder(pdf_path)

            completed = convert_pdf(pdf_path, document, output_folder, pages, dpi, image_format)

            print("\nConversion completed!")
            print(f"Converted: {completed}/{len(pages)} pages")
            print(f"Output: {output_folder}")

    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
