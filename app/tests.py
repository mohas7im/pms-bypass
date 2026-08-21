import json
import io
from unittest.mock import MagicMock, patch
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from app.services.openproject_client import hours_to_iso8601_duration, OpenProjectClient
from app.services.validator import validate_and_parse_file, get_sample_json_bytes, get_sample_csv_bytes
from app.services.importer import run_bulk_import


class OpenProjectClientTests(TestCase):

    def test_hours_to_iso8601_duration(self):
        self.assertEqual(hours_to_iso8601_duration(8), 'PT8H')
        self.assertEqual(hours_to_iso8601_duration(7.5), 'PT7H30M')
        self.assertEqual(hours_to_iso8601_duration(0.25), 'PT15M')
        self.assertEqual(hours_to_iso8601_duration(0), 'PT0H')
        self.assertEqual(hours_to_iso8601_duration(None), 'PT0H')

    @patch('requests.Session.request')
    def test_test_connection_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'}
        mock_request.return_value = mock_resp

        client = OpenProjectClient('https://pms.company.com', 'test-token')
        res = client.test_connection()

        self.assertTrue(res['success'])
        self.assertEqual(res['name'], 'John Doe')

    @patch('requests.Session.request')
    def test_find_existing_work_package(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            '_embedded': {
                'elements': [
                    {
                        'id': 101,
                        'subject': 'Staff Performance Report',
                        'startDate': '2026-06-15',
                        'dueDate': '2026-06-15',
                        '_links': {'self': {'href': '/api/v3/work_packages/101'}}
                    }
                ]
            }
        }
        mock_request.return_value = mock_resp

        client = OpenProjectClient('https://pms.company.com', 'test-token')
        res = client.find_existing_work_package(1, 'Staff Performance Report', '2026-06-15')

        self.assertTrue(res['exists'])
        self.assertEqual(res['id'], 101)


class ValidatorTests(TestCase):

    def test_json_validation_valid(self):
        json_data = json.dumps([
            {
                "date": "2026-06-15",
                "title": "Staff Performance Report",
                "description": "Implemented staff performance report API",
                "hours": 8
            },
            {
                "date": "2026-06-20",
                "title": "Weekend Task",
                "description": "Working on weekend",
                "hours": 4
            }
        ])

        res = validate_and_parse_file(json_data, "tasks.json")
        self.assertTrue(res['success'])
        self.assertEqual(res['total_tasks'], 2)
        self.assertEqual(res['total_hours'], 12.0)

    def test_csv_validation_valid(self):
        csv_data = (
            "date,title,description,hours\n"
            "2026-06-15,Staff Performance Report,Implemented API,8\n"
            "2026-06-16,Holiday Report,Implemented report,7\n"
        )
        res = validate_and_parse_file(csv_data, "tasks.csv")
        self.assertTrue(res['success'])
        self.assertEqual(res['total_tasks'], 2)
        self.assertEqual(res['total_hours'], 15.0)

    def test_missing_fields_validation(self):
        json_data = json.dumps([
            {"description": "No title or date"},
            {"date": "2026-06-15"}  # missing title
        ])
        res = validate_and_parse_file(json_data, "tasks.json")
        self.assertFalse(res['success'])
        self.assertGreater(len(res['errors']), 0)

    def test_sample_generators(self):
        json_bytes = get_sample_json_bytes()
        self.assertIn(b"Staff Performance Report", json_bytes)

        csv_bytes = get_sample_csv_bytes()
        self.assertIn(b"2026-06-15", csv_bytes)


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OpenProject Bypass Uploader")


    def test_download_sample(self):
        res_json = self.client.get('/download-sample/json/')
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json['Content-Type'], 'application/json')

        res_csv = self.client.get('/download-sample/csv/')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv['Content-Type'], 'text/csv')

    def test_upload_preview_view_post(self):
        sample_file = SimpleUploadedFile(
            "tasks.json",
            get_sample_json_bytes(),
            content_type="application/json"
        )
        response = self.client.post('/api/upload-preview/', {
            'file': sample_file
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_tasks'], 3)

    def test_upload_preview_pasted_json(self):
        json_data = json.dumps([
            {
                "date": "2026-06-15",
                "title": "Pasted JSON Task",
                "description": "Testing pasted raw json",
                "hours": 5
            }
        ])
        response = self.client.post('/api/upload-preview/', {
            'json_text': json_data
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_tasks'], 1)
        self.assertEqual(data['records'][0]['title'], 'Pasted JSON Task')
