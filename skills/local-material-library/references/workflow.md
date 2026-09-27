# Import, OCR and maintenance

## Import contract

PDF, DOCX, TXT, MD, CSV and common raster images are indexed. Other file types are counted as skipped. DOCX paragraphs and tables are searchable but page numbers are not available. PDF page numbers are physical file pages, including covers. Text files are decoded as UTF-8 (including BOM), then GB18030; undecodable files report an error. There is no truncation or page sampling.

Folders become initial categories. Changes in the UI are virtual; they do not move source files. A rescan preserves annotations and IDs for unchanged relative paths. A unique missing file with the same hash can be reconciled after an external move. Ambiguous copies stay separate. A changed file keeps annotations but is re-extracted. SHA-256 is calculated on every scan to detect same-size replacements.

The data folder is bound to one resolved source root. To move a collection to another machine, copy both folders, then run `library.py rebind --source NEW_ROOT --data DATA` before scanning. Never merge a different collection into an existing data folder by rebinding it.

## OCR

Stop the web server before running CLI scan/OCR/rebind commands against the same data folder. Within the web UI, import and OCR are serialized automatically.

OCR uses an optional local Tesseract executable, no paid API. Install it and the required language packs:

- macOS with Homebrew: `brew install tesseract tesseract-lang`
- Ubuntu/Debian: `sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra`
- Windows: install a Tesseract distribution listed in the official documentation, add it to PATH and install Chinese language data.

Verify `tesseract --list-langs` includes the requested languages. The UI runs `chi_sim+eng`; CLI `--lang` can change this. Missing software or languages is an error, not successful OCR.

```sh
python scripts/library.py ocr --source SOURCE --data DATA --batch 50 --lang chi_sim+eng
```

This processes up to 50 candidate pages and commits each page immediately. Repeat to resume. Pages with fewer than 20 non-whitespace extracted characters are candidates; this heuristic cannot detect every damaged text layer. For an image-heavy book with a partial text layer, explicitly run `--id DOCUMENT_ID --all-pages`; already successful OCR pages are retained. `--retry` retries failed pages. Blank pages can legitimately finish with zero recognized characters. OCR never replaces an original file. Inspect difficult historical text visually.

## Search and scale

Literal, case-insensitive substring search supports short Chinese phrases without tokenization. Search spans filename, path, category, tags, notes and all extracted pages. Results have server-side pagination and one row per document. The reader has a separately paginated list of matching pages. This design favors recall over ranking. SQLite substring scans may become slow for hundreds of thousands of pages; measure first and replace the search layer when needed. Do not claim benchmark results not measured.

## Backup and recovery

Stop the server before copying the data folder, or use the `export` command for a consistent SQLite backup plus portable JSON metadata:

```sh
python scripts/library.py export --data DATA --output BACKUP_DIRECTORY
```

The backup excludes originals; back up the source separately. Restoring `library.sqlite` restores categories, notes, hidden states and page text. Rebind the source on a new machine if necessary. The hidden-items filter can restore an accidentally hidden record. Rescanning an unchanged extraction error retries it.

## Local boundaries

The server binds only to 127.0.0.1, rejects foreign Host/Origin values, requires a per-process token for mutations, exposes only indexed supported originals and serves original documents as downloads. HTML is not indexed or served as active content. There are no upload, shell-command, delete-source or cloud endpoints. Other processes running as the same OS user are outside this boundary. Keep document-parser dependencies updated for untrusted files.

Troubleshoot the actual printed URL and actual data folder, not another running copy. Scan errors, OCR failures and unavailable originals remain visible. Preview errors must not silently show a cover in place of a requested page.
