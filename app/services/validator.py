import csv
import io
import json
from datetime import datetime


def parse_date_str(date_input):
    """Normalizes arbitrary date strings into standard YYYY-MM-DD format."""
    if isinstance(date_input, datetime):
        return date_input.strftime('%Y-%m-%d')

    s = str(date_input).strip()
    if not s:
        return None

    # Try common formats
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d.%m.%Y',
        '%Y.%m.%d'
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


def validate_and_parse_file(file_content, filename):
    """Parses JSON or CSV content and returns structured record list and validation errors."""
    records = []
    errors = []

    filename_lower = filename.lower()

    raw_items = []

    try:
        if filename_lower.endswith('.json'):
            text = file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content
            parsed = json.loads(text)
            if isinstance(parsed, list):
                raw_items = parsed
            elif isinstance(parsed, dict):
                raw_items = [parsed]
            else:
                return {'success': False, 'errors': ['JSON file must contain an array of task objects.']}

        elif filename_lower.endswith('.csv'):
            text = file_content.decode('utf-8-sig') if isinstance(file_content, bytes) else file_content
            reader = csv.DictReader(io.StringIO(text))
            raw_items = list(reader)

        else:
            return {'success': False, 'errors': ['Unsupported file format. Please upload a .json or .csv file.']}

    except json.JSONDecodeError as e:
        return {'success': False, 'errors': [f'Invalid JSON syntax: {str(e)}']}
    except Exception as e:
        return {'success': False, 'errors': [f'Failed to parse file: {str(e)}']}

    if not raw_items:
        return {'success': False, 'errors': ['Uploaded file is empty.']}

    total_hours = 0.0

    for idx, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            errors.append(f"Row {idx}: Record is not a valid object/dictionary.")
            continue

        # Extract date
        raw_date = item.get('date') or item.get('Date') or item.get('DATE')
        normalized_date = parse_date_str(raw_date)

        if not normalized_date:
            errors.append(f"Row {idx}: Missing or invalid date '{raw_date}'.")
            continue

        # Extract title
        title = item.get('title') or item.get('Title') or item.get('TITLE') or item.get('subject') or item.get('Subject')
        if not title or not str(title).strip():
            errors.append(f"Row {idx}: Missing task title.")
            continue
        title = str(title).strip()

        # Extract description
        description = item.get('description') or item.get('Description') or item.get('comment') or ''
        description = str(description).strip()

        # Extract hours
        raw_hours = item.get('hours') or item.get('Hours') or item.get('HOURS') or item.get('time')
        hours = None
        if raw_hours is not None and str(raw_hours).strip() != '':
            try:
                hours = float(raw_hours)
                if hours < 0:
                    errors.append(f"Row {idx} ('{title}'): Hours cannot be negative.")
                    continue
                total_hours += hours
            except ValueError:
                errors.append(f"Row {idx} ('{title}'): Invalid hours value '{raw_hours}'. Must be numeric.")
                continue

        # Extract optional status and type
        status = item.get('status') or item.get('Status')
        task_type = item.get('type') or item.get('Type')

        records.append({
            'row_id': idx,
            'date': normalized_date,
            'title': title,
            'description': description,
            'hours': hours,
            'status': str(status).strip() if status else None,
            'type': str(task_type).strip() if task_type else None
        })

    return {
        'success': len(records) > 0,
        'records': records,
        'errors': errors,
        'total_tasks': len(records),
        'total_hours': round(total_hours, 2)
    }


def get_sample_json_bytes():
    """Generates sample JSON file bytes for downloadable template."""
    sample = [
        {
            "date": "2026-06-15",
            "title": "Staff Performance Report",
            "description": "Implemented staff performance report API and endpoint optimization",
            "hours": 8,
            "status": "Closed",
            "type": "Task"
        },
        {
            "date": "2026-06-16",
            "title": "Holiday Report",
            "description": "Implemented organization holiday report filter and export",
            "hours": 7,
            "status": "Closed",
            "type": "Task"
        },
        {
            "date": "2026-06-17",
            "title": "CSV Export",
            "description": "Fixed CSV export date formatting and column alignment",
            "hours": 8,
            "status": "Closed",
            "type": "Task"
        }
    ]
    return json.dumps(sample, indent=2).encode('utf-8')


def get_sample_csv_bytes():
    """Generates sample CSV file bytes for downloadable template."""
    sample_csv = (
        "date,title,description,hours,type,status\n"
        "2026-06-15,Staff Performance Report,Implemented staff performance report API,8,Task,Closed\n"
        "2026-06-16,Holiday Report,Implemented organization holiday report,7,Task,Closed\n"
        "2026-06-17,CSV Export,Fixed CSV export date formatting,8,Task,Closed\n"
    )
    return sample_csv.encode('utf-8')
