from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters
from tests.utilities.utilities import async_return, run_async


class TestResources(TestCaseRouters):
    # Reminder: When defining `setUp`, `setUpClass`, `tearDown` and `tearDownClass`
    # in router tests the corresponding super().function() needs to be called as well.
    def setUp(self):
        super().setUp()
        login = {"user_name": "test", "password": "test"}
        # TODO: Create a static login token to make this test
        # independent from /user/login
        response = run_async(self.client.post, "/user/login", json=login)
        self.assertEqual(response.status_code, 200)

    def test_get_resource_state(self):
        self.clear_lru_cache()
        self.mock_crud.get_resource_state.return_value = async_return(
            return_value=[{"drone_uuid": "test-0123456789", "state": "AvailableState"}]
        )

        response = run_async(
            self.client.get,
            "/resources/test-0123456789/state",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"drone_uuid": "test-0123456789", "state": "AvailableState"},
        )

        self.mock_crud.get_resource_state.return_value = async_return(return_value=[])
        response = run_async(self.client.get, "/resources/test-1234567890/state")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Drone not found"})

        response = run_async(self.client.get, "/resources/test-invalid/state")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "ctx": {"pattern": "^\\S+-[A-Fa-f0-9]{10}$"},
                        "loc": ["path", "drone_uuid"],
                        "msg": 'string does not match regex "^\\S+-[A-Fa-f0-9]{10}$"',
                        "type": "value_error.str.regex",
                    }
                ]
            },
        )

        response = run_async(
            self.client.get,
            "/resources/state",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not Found"})

    def test_get_resources(self):
        self.clear_lru_cache()
        full_expected_resources = [
            {
                "remote_resource_uuid": "14fa5640a7c146e482e8be41ec5dffea",
                "state": "AvailableState",
                "drone_uuid": "test-0125bc9fd8",
                "site_name": "Test",
                "machine_type": "m1.test",
                "created": "2021-10-08T12:42:16.354400",
                "updated": "2021-10-08T12:42:28.382025",
            },
            {
                "remote_resource_uuid": "b3efcc5bc8b741af9222987e0434ca61",
                "state": "AvailableState",
                "drone_uuid": "test-6af3cfef14",
                "site_name": "Test",
                "machine_type": "m1.test",
                "created": "2021-10-08T12:42:16.373454",
                "updated": "2021-10-08T12:42:30.648325",
            },
        ]
        self.mock_crud.get_resources.return_value = async_return(
            return_value=full_expected_resources
        )

        response = run_async(self.client.get, "/resources/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            full_expected_resources,
        )

    def test_shutdown_drone(self):
        self.clear_lru_cache()
        self.mock_crud.set_state_to_draining.return_value = async_return()

        response = run_async(self.client.patch, "/resources/test-0125bc9fd8/drain")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"msg": "Drone set to DrainState"})

        # missing scope
        self.set_scopes(["resources:get"])
        self.login()
        response = run_async(self.client.patch, "/resources/test-0125bc9fd8/drain")
        self.assertEqual(response.status_code, 403)
