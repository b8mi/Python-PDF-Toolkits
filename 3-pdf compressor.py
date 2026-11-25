import os
import shutil
import tempfile
from pathlib import Path
from dataclasses import dataclass

try:
    import fitz
except ImportError:
    fitz = None


PROFILES = {
    "fast": {
        "garbage": 2,
        "deflate": True
    },
    "standard": {
        "garbage": 4,
        "deflate": True,
        "clean": True
    },
    "thorough": {
        "garbage": 4,
        "deflate": True,
        "clean": True,
        "deflate_images": True,
        "deflate_fonts": True
    }
}


@dataclass
class CompressionResult:
    source: Path
    destination: Path
    before: int
    after: int
    original_kept: bool

    @property
    def savings(self):
        return (1 - self.after / self.before) * 100 if self.before else 0

    @property
    def saved_bytes(self):
        return self.before - self.after


def clean_path(value):
    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]

    return value


def format_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)

    for unit in units:
        if abs(value) < 1024 or unit == "TB":
            return f"{value:.2f} {unit}"

        value /= 1024


def collect_files():
    files = []

    while True:
        raw = clean_path(input("enter PDF path (ENTER to finish): "))

        if not raw:
            break

        path = Path(raw).expanduser()

        if not path.is_file() or path.suffix.lower() != ".pdf":
            print("  [!] invalid PDF path.\n")
            continue

        path = path.resolve()

        if path in files:
            print("  [!] file already queued.\n")
            continue

        files.append(path)
        print(f"  [+] {path.name} ({format_size(path.stat().st_size)})\n")

    return files


def choose_output_folder():
    raw = clean_path(input("destination folder: "))

    if not raw:
        return None

    folder = Path(raw).expanduser()
    folder.mkdir(parents=True, exist_ok=True)

    return folder.resolve()


def choose_profile():
    names = list(PROFILES)

    print("\n--- compression profiles ---")
    print("1 : fast      - light optimization")
    print("2 : standard  - balanced optimization")
    print("3 : thorough  - additional stream compression")

    while True:
        choice = input("profile [2]: ").strip().lower()

        if not choice:
            return "standard"

        if choice in names:
            return choice

        if choice in ("1", "2", "3"):
            return names[int(choice) - 1]

        print("Invalid compression profile.")


def choose_size_guard():
    while True:
        choice = input("smart size protection [Y/n]: ").strip().lower()

        if choice in ("", "y", "yes"):
            return True

        if choice in ("n", "no"):
            return False

        print("Enter Y or N.")


def unique_destination(folder, name):
    base = folder / name
    counter = 0

    while True:
        if counter == 0:
            suffix = ""
        elif counter == 1:
            suffix = "_compressed"
        else:
            suffix = f"_compressed_{counter}"

        candidate = base.with_name(f"{base.stem}{suffix}{base.suffix}")

        try:
            with candidate.open("xb"):
                pass

            return candidate

        except FileExistsError:
            counter += 1


def create_temp_file(folder):
    fd, name = tempfile.mkstemp(prefix=".compress_", suffix=".pdf", dir=folder)
    os.close(fd)

    return Path(name)


def verify_pdf(path, expected_pages):
    with fitz.open(str(path)) as doc:
        if not doc.is_pdf:
            raise ValueError("Output is not a valid PDF.")

        if doc.page_count != expected_pages:
            raise RuntimeError("Unexpected change in page count.")

        if doc.needs_pass:
            raise RuntimeError("Unable to verify encrypted output.")


def create_candidate(source, temp, profile):
    with fitz.open(str(source)) as doc:
        if not doc.is_pdf or doc.needs_pass:
            raise ValueError("Invalid or password-protected PDF.")

        pages = doc.page_count
        doc.save(str(temp), encryption=fitz.PDF_ENCRYPT_KEEP, **PROFILES[profile])

    verify_pdf(temp, pages)


def evaluate_candidate(source, temp, size_guard):
    original_size = source.stat().st_size
    compressed_size = temp.stat().st_size

    # Keep the original if compression produces a larger file.
    if size_guard and compressed_size >= original_size:
        shutil.copyfile(source, temp)
        return True

    return False


def compress_pdf(source, folder, profile="standard", size_guard=True):
    source = Path(source)
    folder = Path(folder)

    before = source.stat().st_size
    temp = create_temp_file(folder)
    destination = None

    try:
        create_candidate(source, temp, profile)
        original_kept = evaluate_candidate(source, temp, size_guard)

        after = temp.stat().st_size
        destination = unique_destination(folder, source.name)

        os.replace(temp, destination)

        return CompressionResult(source, destination, before, after, original_kept)

    except Exception:
        if destination is not None:
            destination.unlink(missing_ok=True)

        raise

    finally:
        temp.unlink(missing_ok=True)


def compression_bar(before, after, width=25):
    if before <= 0:
        return "-" * width

    ratio = max(0, min(1, after / before))
    filled = round(ratio * width)

    return "#" * filled + "-" * (width - filled)


def print_result(result):
    status = "ORIGINAL KEPT" if result.original_kept else "SUCCESS"
    before = format_size(result.before)
    after = format_size(result.after)

    print(f"  [{status}] {result.destination.name}")
    print(f"  {before} -> {after}")
    print(f"  [{compression_bar(result.before, result.after)}]")
    print(f"  savings: {result.savings:.1f}%")


def process_batch(files, folder, profile, size_guard):
    results = []
    errors = []

    for index, path in enumerate(files, 1):
        print(f"\n[{index}/{len(files)}] {path.name}")

        try:
            result = compress_pdf(path, folder, profile, size_guard)
            results.append(result)
            print_result(result)

        except Exception as e:
            errors.append((path, str(e)))
            print(f"  [ERROR] {e}")

    return results, errors


def analyze_results(results):
    before = sum(result.before for result in results)
    after = sum(result.after for result in results)
    originals = sum(result.original_kept for result in results)
    savings = (1 - after / before) * 100 if before else 0

    return {
        "before": before,
        "after": after,
        "originals": originals,
        "savings": savings,
        "saved_bytes": before - after
    }


def print_summary(results, errors):
    stats = analyze_results(results)

    print("\n" + "=" * 35)
    print("         compression summary")
    print("=" * 35)

    print(f"processed      : {len(results)}")
    print(f"originals kept : {stats['originals']}")
    print(f"failed         : {len(errors)}")
    print(f"total before   : {format_size(stats['before'])}")
    print(f"total after    : {format_size(stats['after'])}")
    print(f"space saved    : {format_size(stats['saved_bytes'])}")
    print(f"compression    : {stats['savings']:.1f}%")

    if errors:
        print("\n--- failed files ---")

        for path, error in errors:
            print(f"{path.name}: {error}")

    print("=" * 35)


def print_queue(files):
    total = sum(path.stat().st_size for path in files)

    print("\n--- processing queue ---")

    for i, path in enumerate(files, 1):
        print(f"{i}. {path.name}")

    print(f"\n{len(files)} files | {format_size(total)}")


def main():
    print("--- CLI compressor ---\n")

    if fitz is None:
        print("Install PyMuPDF: pip install pymupdf")
        return 1

    files = collect_files()

    if not files:
        print("No PDF files queued.")
        return 0

    print_queue(files)

    try:
        folder = choose_output_folder()
    except OSError as e:
        print(f"Failed to create folder: {e}")
        return 1

    if folder is None:
        print("No output folder selected.")
        return 0

    profile = choose_profile()
    size_guard = choose_size_guard()

    print(f"\ncompressing using '{profile}' profile...")
    print(f"size protection: {'enabled' if size_guard else 'disabled'}")

    results, errors = process_batch(files, folder, profile, size_guard)
    print_summary(results, errors)

    print("\nAll processing complete!")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
