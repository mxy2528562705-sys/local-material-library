---
name: local-material-library
description: Turn a local folder of PDFs, images, Word documents and notes into a searchable local library with editable categories, tags, page previews and resumable OCR. Use for personal archives, research materials and large mixed file collections.
---

# 文史社科类资料整理流程包

Build a working local library using the bundled application, not a newly invented dashboard. Run from this skill directory; paths below are relative to it. Read `references/workflow.md` for OCR, migration, backup or troubleshooting.

## Inputs

Use the user's source folder and a separate writable data folder. Ask only for a missing source folder; suggest a sibling `material-library-data` for derived data. Never point the source at an entire home directory by default. Preserve the user's language and library title.

## Run

Requires Python 3.10 or newer. Execute:

```sh
python scripts/run.py --source "/absolute/path/to/materials" --data "/absolute/path/to/material-library-data" --title "我的资料库"
```

The runner creates an isolated environment, installs pinned dependencies and starts a loopback-only server. First start scans all supported files automatically; subsequent updates use the refresh button. Read the actual printed URL (a busy port is handled automatically) and give it to the user. Keep the server running using the host's supported long-running terminal mechanism. Do not deploy publicly or modify system startup settings as part of this skill.

For an isolated demonstration, first run `python scripts/demo.py --output /tmp/material-library-demo` with the environment's Python, then use that folder as the source. Never substitute the demo for the user's actual import.

## Invariants

- Source files are read-only. Categories, tags, notes and hidden duplicate entries live in SQLite. Hiding is reversible and never deletes originals.
- Scan all PDF pages, retaining page locators. Report OCR candidates, completed OCR pages and failures separately. A successful sample is not a fully recognized book.
- Rescanning preserves stable IDs and annotations. Changed files invalidate derived page text; missing files are marked missing, not deleted. Identical SHA-256 hashes indicate exact duplicates; similar names do not.
- Results are paginated by document, not dominated by multiple chunks of a single book. Test a word that occurs inside a PDF, not just its filename.
- The original PDF page is the visual reference. DOCX is extracted text, not a layout-faithful preview. OCR text can contain errors; this version does not overlay exact keyword positions on scans.
- Never package real documents, personal contact information, databases, credentials or machine paths for GitHub.

## Verify Before Hand-off

Run `python -m unittest discover -s tests -v` from the repository root when modifying the bundled application. If only the installed skill folder is available, use the demo checks; the test suite belongs to the full repository. For ordinary use, check counts and errors after scanning, search a known interior-page phrase, open a later PDF page, save a tag, and confirm that refreshing preserves it. Inspect the interface at desktop and narrow widths when changing UI.

Provide the actual local URL, source/data locations, how to restart, and any unsupported files or incomplete OCR. Do not describe pending jobs as complete. Do not claim that untested operating systems were tested.
