import json
import time
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from .services.openproject_client import OpenProjectClient
from .services.validator import validate_and_parse_file, get_sample_json_bytes, get_sample_csv_bytes
from .services.importer import run_bulk_import


@ensure_csrf_cookie
def index_view(request):
    """Main view rendering the OpenProject Bulk Uploader interactive SPA wizard."""
    context = {
        'connected': 'openproject_token' in request.session,
        'openproject_url': request.session.get('openproject_url', ''),
        'user_name': request.session.get('user_name', ''),
        'css_version': int(time.time())
    }
    return render(request, 'uploader/index.html', context)


def test_connection_view(request):
    """AJAX endpoint to test connection credentials and save them in session memory."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        url = data.get('url', '').strip()
        token = data.get('token', '').strip()

        if not url or not token:
            return JsonResponse({'success': False, 'error': 'OpenProject URL and API Token are required.'})

        client = OpenProjectClient(url, token)
        conn_res = client.test_connection()

        if not conn_res.get('success'):
            return JsonResponse({'success': False, 'error': conn_res.get('error', 'Unable to connect to OpenProject.')})

        # Save credentials in session memory ONLY
        request.session['openproject_url'] = url
        request.session['openproject_token'] = token
        request.session['auth_mode'] = conn_res.get('auth_mode', 'bearer')
        request.session['user_name'] = conn_res.get('name', 'User')

        # Fetch projects list
        proj_res = client.get_projects()

        return JsonResponse({
            'success': True,
            'user': conn_res,
            'projects': proj_res.get('projects', []) if proj_res.get('success') else []
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Unexpected error: {str(e)}"})


def project_details_view(request):
    """Fetches work package types and statuses for a selected project."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    url = request.session.get('openproject_url')
    token = request.session.get('openproject_token')
    auth_mode = request.session.get('auth_mode', 'bearer')

    if not url or not token:
        return JsonResponse({'success': False, 'error': 'Session expired. Please reconnect.'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        project_id = data.get('project_id')

        client = OpenProjectClient(url, token, auth_mode=auth_mode)
        types_res = client.get_types(project_id)
        statuses_res = client.get_statuses()
        users_res = client.get_users(project_id)
        wps_res = client.get_project_work_packages(project_id)

        return JsonResponse({
            'success': True,
            'types': types_res.get('types', []) if types_res.get('success') else [],
            'statuses': statuses_res.get('statuses', []) if statuses_res.get('success') else [],
            'users': users_res.get('users', []) if users_res.get('success') else [],
            'existing_tasks': wps_res.get('work_packages', []) if wps_res.get('success') else []
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def upload_preview_view(request):
    """Processes uploaded JSON/CSV file, validates records, scans for duplicates, and returns preview."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    uploaded_file = request.FILES.get('file')
    pasted_json_text = request.POST.get('json_text', '').strip()

    if not uploaded_file and not pasted_json_text:
        return JsonResponse({'success': False, 'error': 'Please select a file or paste JSON content in the text area.'})

    project_id = request.POST.get('project_id')

    if uploaded_file:
        content = uploaded_file.read()
        filename = uploaded_file.name
    else:
        content = pasted_json_text.encode('utf-8')
        filename = 'pasted_input.json'

    parse_res = validate_and_parse_file(content, filename)

    if not parse_res.get('success'):
        return JsonResponse(parse_res)

    records = parse_res.get('records', [])
    url = request.session.get('openproject_url')
    token = request.session.get('openproject_token')
    auth_mode = request.session.get('auth_mode', 'bearer')

    # Duplicate pre-scanning if project selected and credentials exist
    duplicate_count = 0
    if url and token and project_id:
        client = OpenProjectClient(url, token, auth_mode=auth_mode)
        for rec in records:
            dup = client.find_existing_work_package(project_id, rec['title'], rec['date'])
            rec['is_duplicate'] = dup.get('exists', False)
            if rec['is_duplicate']:
                rec['existing_wp_id'] = dup.get('id')
                duplicate_count += 1
            else:
                rec['existing_wp_id'] = None

    parse_res['duplicate_count'] = duplicate_count
    request.session['pending_records'] = records

    return JsonResponse(parse_res)


def execute_import_view(request):
    """Triggers the bulk import process into OpenProject."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    url = request.session.get('openproject_url')
    token = request.session.get('openproject_token')
    auth_mode = request.session.get('auth_mode', 'bearer')

    if not url or not token:
        return JsonResponse({'success': False, 'error': 'Session expired. Please reconnect to OpenProject.'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        project_id = data.get('project_id')
        type_id = data.get('type_id')
        status_id = data.get('status_id')
        assignee_id = data.get('assignee_id')
        accountable_id = data.get('accountable_id')
        records = data.get('records') or request.session.get('pending_records')

        if not project_id or not records:
            return JsonResponse({'success': False, 'error': 'Missing project selection or import records.'})

        results = run_bulk_import(
            openproject_url=url,
            api_token=token,
            project_id=project_id,
            default_type_id=type_id,
            default_status_id=status_id,
            records=records,
            default_assignee_id=assignee_id,
            default_accountable_id=accountable_id,
            auth_mode=auth_mode
        )

        return JsonResponse({'success': True, 'results': results})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def download_sample_view(request, format_type):
    """Provides downloadable sample JSON and CSV template files."""
    if format_type == 'json':
        response = HttpResponse(get_sample_json_bytes(), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="sample_tasks.json"'
        return response
    elif format_type == 'csv':
        response = HttpResponse(get_sample_csv_bytes(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sample_tasks.csv"'
        return response
    else:
        return HttpResponse("Invalid format", status=400)


def disconnect_view(request):
    """Clears connection session state."""
    request.session.flush()
    return JsonResponse({'success': True})
