import os
import fitz

def clean_path(path_string):
    cleaned = path_string.strip()
    # Handle quoted paths pasted from Explorer or the terminal.
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        return cleaned[1:-1]
    return cleaned

def main():
    print("--- CLI Compressor ---\n")
    files = []

    while True:
        raw_input = input("Enter PDF path (or press ENTER when finished): ")
        path = clean_path(raw_input)


        if not path:
            break


        # Only queue actual PDF files, rather than passing invalid paths to PyMuPDF.
        if os.path.isfile(path) and path.lower().endswith('.pdf'):
            files.append(path)
            print(f"  [+] Added: {os.path.basename(path)}\n")
        else:
            print("  [!] Invalid path or file is not a .pdf. Try again.\n")


    if not files:
        print("\nNo valid PDF files were added. Exiting.")
        return


    print(f"\n{len(files)} PDF file(s) queued.")
    out_dir = input("Enter the destination path for compressed PDFs: ")
    out_dir = clean_path(out_dir)

    if not out_dir:
        print("No output folder provided. Exiting.")
        return

    # Create a destination folder if it is not there yet.
    if not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir)
            print(f"Created output directory: {out_dir}")
        except Exception as e:
            print(f"Failed to create output folder: {e}")
            return


    print("\nCompressing...")
    for path in files:
        name = os.path.basename(path)
        dest = os.path.join(out_dir, name)


        try:
            doc = fitz.open(path)


            # Repack PDF objects and streams. This does not downsample the images inside.
            doc.save(
                dest,
                garbage=4,
                deflate=True,
                clean=True
            )
            doc.close()

            before = os.path.getsize(path) / 1024
            after = os.path.getsize(dest) / 1024
            # A negative saving means the new PDF ended up larger than the original.
            savings = (100 - (after / before * 100)) if before > 0 else 0

            print(f"  [SUCCESS] {name} -> Saved {savings:.1f}% ({after:.1f} KB)")
        except Exception as e:
            print(f"  [ERROR] Failed {name}: {e}")

    print("\nAll processing complete!")

if __name__ == "__main__":
    main()
