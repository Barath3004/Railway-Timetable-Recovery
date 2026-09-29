from __future__ import annotations

import unittest

from src.api.app import app


class TestOperatorApi(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_read_only_operational_endpoints(self) -> None:
        self.assertEqual(self.client.get('/api/health').status_code, 200)
        dashboard = self.client.get('/api/dashboard')
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.get_json()['counts']['trains'], 552)

    def test_station_resource_lookup(self) -> None:
        response = self.client.get('/api/stations/MS/resources')
        self.assertEqual(response.status_code, 200)
        resources = response.get_json()['resources']
        self.assertTrue(resources)
        self.assertTrue(all(item['resource_id'].startswith('MS-P') for item in resources))

    def test_invalid_disruption_is_rejected(self) -> None:
        response = self.client.post(
            '/api/disruptions/detect',
            json={
                'disruption_type': 'PLATFORM_CLOSURE',
                'station_code': 'MS',
                'resource_id': 'MAS-P4',
                'day': 1,
                'start_time': '05:00:00',
                'end_time': '05:20:00',
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_controlled_disruption_detection(self) -> None:
        response = self.client.post(
            '/api/disruptions/detect',
            json={
                'disruption_type': 'PLATFORM_CLOSURE',
                'station_code': 'MS',
                'resource_id': 'MS-P9',
                'day': 1,
                'start_time': '05:00:00',
                'end_time': '05:20:00',
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['affected_train_count'], 2)
        self.assertEqual(len(payload['affected_records']), 2)


if __name__ == '__main__':
    unittest.main()
