import json
import time
import requests
from urllib.parse import quote, urljoin


def hours_to_iso8601_duration(hours_val):
    """Converts a numeric hours value (int/float) to ISO 8601 duration format.
    Example:
        8 -> 'PT8H'
        7.5 -> 'PT7H30M'
        0.25 -> 'PT15M'
    """
    try:
        total_minutes = int(round(float(hours_val) * 60))
    except (ValueError, TypeError):
        total_minutes = 0

    if total_minutes <= 0:
        return "PT0H"

    h = total_minutes // 60
    m = total_minutes % 60

    if h > 0 and m > 0:
        return f"PT{h}H{m}M"
    elif h > 0:
        return f"PT{h}H"
    else:
        return f"PT{m}M"


class OpenProjectClient:
    """Client for interacting with OpenProject REST API v3."""

    def __init__(self, base_url, api_token, auth_mode='bearer'):
        clean_url = base_url.strip().rstrip('/')
        if not clean_url.endswith('/api/v3'):
            clean_url = f"{clean_url}/api/v3"
        self.api_url = clean_url
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'application/hal+json',
            'Content-Type': 'application/json'
        })
        self.auth_mode = auth_mode  # 'bearer' or 'basic'

    def _request(self, method, endpoint, payload=None, params=None, max_retries=3):
        """Helper to send HTTP requests with retry/backoff logic for temporary errors."""
        url = endpoint if endpoint.startswith('http') else f"{self.api_url}{endpoint}"

        backoff = 1
        for attempt in range(1, max_retries + 1):
            try:
                # If basic auth mode is active, set session.auth
                if self.auth_mode == 'basic':
                    auth = ('apikey', self.api_token)
                    headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'authorization'}
                    response = requests.request(
                        method=method,
                        url=url,
                        json=payload,
                        params=params,
                        headers=headers,
                        auth=auth,
                        timeout=15
                    )
                else:
                    response = self.session.request(
                        method=method,
                        url=url,
                        json=payload,
                        params=params,
                        timeout=15
                    )

                # Automatic fallback from bearer to basic auth on 401/403
                if response.status_code in (401, 403) and self.auth_mode == 'bearer':
                    self.auth_mode = 'basic'
                    auth = ('apikey', self.api_token)
                    headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'authorization'}
                    response = requests.request(
                        method=method,
                        url=url,
                        json=payload,
                        params=params,
                        headers=headers,
                        auth=auth,
                        timeout=15
                    )

                # Retry on temporary server errors (429, 500, 502, 503, 504)
                if response.status_code in [429, 500, 502, 503, 504] and attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                return response
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise exc

    def test_connection(self):
        """Verifies API connection and token validity by fetching current user info, automatically trying Bearer and Basic apikey auth."""
        try:
            # First try default (Bearer token)
            self.auth_mode = 'bearer'
            resp = self._request('GET', '/users/me')

            if resp.status_code in (401, 403):
                # Fallback to OpenProject standard API Key Basic Auth: username='apikey', password=api_token
                self.auth_mode = 'basic'
                resp = self._request('GET', '/users/me')

            if resp.status_code == 200:
                data = resp.json()
                return {
                    'success': True,
                    'user_id': data.get('id'),
                    'name': data.get('name'),
                    'email': data.get('email', ''),
                    'auth_mode': self.auth_mode
                }
            elif resp.status_code in (401, 403):
                return {'success': False, 'error': 'Authentication failed. Please verify your OpenProject API token and permissions.'}
            elif resp.status_code == 404:
                return {'success': False, 'error': 'OpenProject API endpoint not found. Please check your OpenProject URL (e.g. https://pms.company.com).'}
            else:
                return {'success': False, 'error': f'Server returned HTTP {resp.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}


    def get_projects(self):
        """Retrieves list of accessible projects including parent-child hierarchy info."""
        try:
            resp = self._request('GET', '/projects?pageSize=500')
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('_embedded', {}).get('elements', [])
                projects = []
                for item in elements:
                    parent_link = item.get('_links', {}).get('parent', {})
                    parent_href = parent_link.get('href') if parent_link else None
                    parent_title = parent_link.get('title') if parent_link else None
                    parent_id = None
                    if parent_href:
                        try:
                            parent_id = int(parent_href.rstrip('/').split('/')[-1])
                        except (ValueError, IndexError):
                            parent_id = None

                    projects.append({
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'identifier': item.get('identifier'),
                        'parent_id': parent_id,
                        'parent_name': parent_title,
                        'href': item.get('_links', {}).get('self', {}).get('href')
                    })
                return {'success': True, 'projects': projects}
            return {'success': False, 'error': f'Failed to fetch projects. HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_types(self, project_id=None):
        """Retrieves available work package types (e.g. Task, Milestone, Bug)."""
        try:
            endpoint = f'/projects/{project_id}/types' if project_id else '/types'
            resp = self._request('GET', endpoint)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('_embedded', {}).get('elements', [])
                types_list = []
                for item in elements:
                    types_list.append({
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'is_default': item.get('isDefault', False),
                        'href': item.get('_links', {}).get('self', {}).get('href')
                    })
                return {'success': True, 'types': types_list}
            # Fallback to general types
            if project_id:
                return self.get_types(project_id=None)
            return {'success': False, 'error': f'Failed to fetch types. HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_statuses(self):
        """Retrieves available work package statuses (e.g. New, In progress, Closed)."""
        try:
            resp = self._request('GET', '/statuses')
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('_embedded', {}).get('elements', [])
                statuses = []
                for item in elements:
                    statuses.append({
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'is_default': item.get('isDefault', False),
                        'is_closed': item.get('isClosed', False),
                        'href': item.get('_links', {}).get('self', {}).get('href')
                    })
                return {'success': True, 'statuses': statuses}
            return {'success': False, 'error': f'Failed to fetch statuses. HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def find_existing_work_package(self, project_id, title, date_str):
        """Checks if a work package with matching subject and date already exists for duplicate detection."""
        try:
            # Construct OpenProject API v3 filter query
            filters = [
                {"subject": {"operator": "=", "values": [title]}}
            ]
            filters_json = json.dumps(filters)
            endpoint = f'/projects/{project_id}/work_packages?filters={quote(filters_json)}&pageSize=50'
            resp = self._request('GET', endpoint)

            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('_embedded', {}).get('elements', [])
                for wp in elements:
                    wp_subject = wp.get('subject', '').strip().lower()
                    wp_start = wp.get('startDate')
                    wp_due = wp.get('dueDate')

                    if wp_subject == title.strip().lower():
                        # Match date if specified on either start date or due date or if unspecified
                        if not date_str or wp_start == date_str or wp_due == date_str:
                            return {
                                'exists': True,
                                'id': wp.get('id'),
                                'subject': wp.get('subject'),
                                'href': wp.get('_links', {}).get('self', {}).get('href')
                            }

            return {'exists': False}
        except Exception:
            return {'exists': False}

    def get_users(self, project_id=None):
        """Retrieves available users/members for a project space."""
        try:
            endpoint = f'/projects/{project_id}/available_assignees' if project_id else '/users?pageSize=500'
            resp = self._request('GET', endpoint)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('_embedded', {}).get('elements', [])
                users = []
                for item in elements:
                    users.append({
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'email': item.get('email', ''),
                        'href': item.get('_links', {}).get('self', {}).get('href')
                    })
                return {'success': True, 'users': users}
            if project_id:
                return self.get_users(project_id=None)
            return {'success': False, 'error': f'Failed to fetch users. HTTP {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def resolve_status_id(self, status_val):
        """Resolves status ID whether status_val is an integer ID or string name (e.g. 'In progress', 'Closed', 'New')."""
        if not status_val:
            return None
        s_str = str(status_val).strip()
        if s_str.isdigit() or s_str.startswith('/'):
            return s_str

        res = self.get_statuses()
        if res.get('success'):
            statuses = res.get('statuses', [])
            s_lower = s_str.lower()
            for st in statuses:
                if st['name'].lower() == s_lower:
                    return st['id']
            for st in statuses:
                if s_lower in st['name'].lower():
                    return st['id']

        return None

    def resolve_type_id(self, type_val, project_id=None):
        """Resolves type ID whether type_val is an integer ID or string name (e.g. 'Task', 'Bug', 'Feature')."""
        if not type_val:
            return None
        t_str = str(type_val).strip()
        if t_str.isdigit() or t_str.startswith('/'):
            return t_str

        res = self.get_types(project_id=project_id)
        if res.get('success'):
            types_list = res.get('types', [])
            t_lower = t_str.lower()
            for tp in types_list:
                if tp['name'].lower() == t_lower:
                    return tp['id']
            for tp in types_list:
                if t_lower in tp['name'].lower():
                    return tp['id']

        return None

    def create_work_package(self, project_id, title, description=None, type_id=None, status_id=None, start_date=None, due_date=None, assignee_id=None, accountable_id=None):
        """Creates a new work package in OpenProject via REST API v3."""
        try:
            payload = {
                'subject': title,
                'description': {
                    'format': 'markdown',
                    'raw': description or ''
                }
            }

            if start_date:
                payload['startDate'] = start_date
            if due_date:
                payload['dueDate'] = due_date

            links = {
                'project': {
                    'href': f'/api/v3/projects/{project_id}' if not str(project_id).startswith('/') else project_id
                }
            }

            if type_id:
                resolved_type = self.resolve_type_id(type_id, project_id=project_id)
                if resolved_type:
                    type_href = str(resolved_type) if str(resolved_type).startswith('/') else f'/api/v3/types/{resolved_type}'
                    links['type'] = {'href': type_href}

            if status_id:
                resolved_status = self.resolve_status_id(status_id)
                if resolved_status:
                    status_href = str(resolved_status) if str(resolved_status).startswith('/') else f'/api/v3/statuses/{resolved_status}'
                    links['status'] = {'href': status_href}

            if assignee_id:
                assignee_href = str(assignee_id) if str(assignee_id).startswith('/') else f'/api/v3/users/{assignee_id}'
                links['assignee'] = {'href': assignee_href}

            if accountable_id:
                accountable_href = str(accountable_id) if str(accountable_id).startswith('/') else f'/api/v3/users/{accountable_id}'
                links['responsible'] = {'href': accountable_href}

            payload['_links'] = links

            endpoint = f'/projects/{project_id}/work_packages'
            resp = self._request('POST', endpoint, payload=payload)

            if resp.status_code in [200, 201]:
                data = resp.json()
                return {
                    'success': True,
                    'id': data.get('id'),
                    'subject': data.get('subject'),
                    'href': data.get('_links', {}).get('self', {}).get('href')
                }
            else:
                error_msg = f"HTTP {resp.status_code}"
                try:
                    err_json = resp.json()
                    if 'message' in err_json:
                        error_msg += f": {err_json['message']}"
                    elif '_embedded' in err_json and 'errors' in err_json['_embedded']:
                        errs = [e.get('message', '') for e in err_json['_embedded']['errors']]
                        error_msg += f": {', '.join(errs)}"
                except Exception:
                    pass
                return {'success': False, 'status_code': resp.status_code, 'error': error_msg}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_time_entry(self, project_id, work_package_id, date_str, hours, comment=None):
        """Creates a time entry associated with a work package via REST API v3."""
        try:
            iso_hours = hours_to_iso8601_duration(hours)

            wp_href = str(work_package_id) if str(work_package_id).startswith('/') else f'/api/v3/work_packages/{work_package_id}'
            proj_href = str(project_id) if str(project_id).startswith('/') else f'/api/v3/projects/{project_id}'

            payload = {
                'spentOn': date_str,
                'hours': iso_hours,
                'comment': {
                    'format': 'markdown',
                    'raw': comment or ''
                },
                '_links': {
                    'workPackage': {'href': wp_href},
                    'project': {'href': proj_href}
                }
            }

            resp = self._request('POST', '/time_entries', payload=payload)

            if resp.status_code in [200, 201]:
                data = resp.json()
                return {
                    'success': True,
                    'id': data.get('id'),
                    'hours': hours,
                    'spentOn': date_str
                }
            else:
                error_msg = f"HTTP {resp.status_code}"
                try:
                    err_json = resp.json()
                    if 'message' in err_json:
                        error_msg += f": {err_json['message']}"
                except Exception:
                    pass
                return {'success': False, 'status_code': resp.status_code, 'error': error_msg}

        except Exception as e:
            return {'success': False, 'error': str(e)}
