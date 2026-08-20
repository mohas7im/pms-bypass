import os
import logging
from datetime import datetime
from django.conf import settings
from .openproject_client import OpenProjectClient


def setup_import_logger():
    """Sets up a file logger in logs/ directory without leaking credentials."""
    log_dir = getattr(settings, 'BASE_DIR', os.getcwd()) / 'logs'
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"import_{timestamp}.log"

    logger = logging.getLogger(f"import_{timestamp}")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger, str(log_file)


def run_bulk_import(openproject_url, api_token, project_id, default_type_id, default_status_id, records, default_assignee_id=None, default_accountable_id=None, auth_mode='bearer'):
    """Executes bulk import of tasks and time entries into OpenProject with duplicate checking."""
    logger, log_file_path = setup_import_logger()
    logger.info(f"Starting OpenProject Bulk Import for Project ID: {project_id}")
    logger.info(f"Target URL: {openproject_url}")
    logger.info(f"Total Records to Process: {len(records)}")

    client = OpenProjectClient(openproject_url, api_token, auth_mode=auth_mode)

    results = {
        'created_work_packages': 0,
        'created_time_entries': 0,
        'skipped_duplicates': 0,
        'failed_count': 0,
        'total_hours': 0.0,
        'records_details': [],
        'log_file': log_file_path
    }

    for record in records:
        date_str = record['date']
        title = record['title']
        description = record['description']
        hours = record['hours']
        record_type_id = record.get('type') or default_type_id
        record_status_id = record.get('status') or default_status_id
        record_assignee_id = record.get('assignee') or default_assignee_id
        record_accountable_id = record.get('accountable') or default_accountable_id

        detail = {
            'date': date_str,
            'title': title,
            'hours': hours,
            'status': 'PENDING',
            'wp_created': False,
            'time_entry_created': False,
            'wp_id': None,
            'reason': ''
        }

        logger.info(f"Processing Task: '{title}' ({date_str}) - Hours: {hours}")

        # Step 1: Duplicate Detection
        dup_check = client.find_existing_work_package(project_id, title, date_str)
        if dup_check.get('exists'):
            wp_id = dup_check.get('id')
            detail['status'] = 'SKIPPED'
            detail['reason'] = f"Existing work package (ID: #{wp_id})"
            detail['wp_id'] = wp_id
            results['skipped_duplicates'] += 1
            logger.info(f"SKIPPED '{title}' ({date_str}): {detail['reason']}")
            results['records_details'].append(detail)
            continue

        # Step 2: Work Package Creation
        wp_res = client.create_work_package(
            project_id=project_id,
            title=title,
            description=description,
            type_id=record_type_id,
            status_id=record_status_id,
            start_date=date_str,
            due_date=date_str,
            assignee_id=record_assignee_id,
            accountable_id=record_accountable_id
        )

        if not wp_res.get('success'):
            detail['status'] = 'FAILED'
            detail['reason'] = f"Work package creation failed: {wp_res.get('error')}"
            results['failed_count'] += 1
            logger.error(f"FAILED '{title}' ({date_str}): {detail['reason']}")
            results['records_details'].append(detail)
            continue

        wp_id = wp_res.get('id')
        detail['wp_created'] = True
        detail['wp_id'] = wp_id
        results['created_work_packages'] += 1
        logger.info(f"CREATED Work Package #{wp_id} for '{title}'")

        # Step 3: Time Entry Creation (if hours specified)
        if hours and float(hours) > 0:
            te_res = client.create_time_entry(
                project_id=project_id,
                work_package_id=wp_id,
                date_str=date_str,
                hours=hours,
                comment=description or title
            )

            if te_res.get('success'):
                detail['time_entry_created'] = True
                results['created_time_entries'] += 1
                results['total_hours'] += float(hours)
                logger.info(f"CREATED Time Entry ({hours}h) for Work Package #{wp_id}")
            else:
                detail['time_entry_error'] = te_res.get('error')
                logger.warning(f"Time Entry failed for Work Package #{wp_id}: {te_res.get('error')}")

        detail['status'] = 'SUCCESS'
        results['records_details'].append(detail)

    results['total_hours'] = round(results['total_hours'], 2)
    logger.info("Bulk Import Completed.")
    logger.info(f"Summary: Created WPs={results['created_work_packages']}, Created Time Entries={results['created_time_entries']}, Skipped={results['skipped_duplicates']}, Failed={results['failed_count']}")

    return results
