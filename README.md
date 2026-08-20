# OpenProject Bulk Uploader

A lightweight, zero-hosting local desktop application for bulk uploading work packages and daily time entries to OpenProject via REST API v3.

## Features

- **Double-Click Executable Launch**: Packaged as `dist/OpenProjectBulkUploader.exe`. Automatically launches local web server on `http://127.0.0.1:8000` and opens default browser.
- **Zero Database / Zero Cloud Hosting**: Runs 100% locally. Session credentials (OpenProject URL and API Token) are stored in server-side session memory only and cleared on disconnect/session close.
- **REST API v3 Integration**: OpenProject authentication, project retrieval, work package type selection, status mapping, duplicate detection, work package creation, and time entry creation with ISO 8601 duration handling.
- **JSON & CSV Support**: Upload `.json` or `.csv` files with customizable fields (`date`, `title`, `description`, `hours`, `status`, `type`).
- **Weekend Filter Option**: Toggle to automatically skip Saturday and Sunday entries.
- **Pre-Import Preview**: Displays calculated totals and flags duplicate work packages before writing to OpenProject.
- **Duplicate Detection**: Mandatory check preventing duplicate tasks on the same project with matching date and title.
- **Import Summary & Audit Logs**: Detailed breakdown of Created, Skipped, and Failed records. Timestamped audit log file generated in `logs/import_YYYYMMDD_HHMMSS.log` (sans sensitive API tokens).

---

## Quick Start (Pre-Packaged Executable)

1. Double-click **`OpenProjectBulkUploader.exe`** in the `dist/` folder.
2. The application will start locally on `http://127.0.0.1:8000` and open your default browser automatically.
3. Enter your **OpenProject URL** (e.g. `https://pms.company.com`) and your personal **API Token** (My Account → Access Tokens → API Token).
4. Select your OpenProject Project, upload your JSON or CSV task file, review the preview table, and click **Import Tasks to OpenProject**.

---

## Development Setup

If running from source:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run unit tests
python manage.py test

# 3. Start local development server
python launcher.py
```

---

## Building Executable with PyInstaller

To rebuild the single-file executable:

```bash
python -m PyInstaller OpenProjectBulkUploader.spec
```

The output executable will be created at `dist/OpenProjectBulkUploader.exe`.

---

## Security Guidelines

- **In-Memory Token Storage**: API tokens are held strictly in server-side session memory for the current session.
- **No Token Logging**: Logging functions explicitly sanitize headers and credentials.
- **Direct HTTPS Communication**: API requests communicate directly with your configured OpenProject instance.
