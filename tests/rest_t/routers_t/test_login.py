from tests.rest_t.routers_t.base_test_case_routers import TestCaseRouters
from tests.utilities.utilities import run_async

from datetime import datetime
from unittest.mock import patch


class TestLogin(TestCaseRouters):
    # Reminder: When defining `setUp`, `setUpClass`, `tearDown` and `tearDownClass`
    # in router tests the corresponding super().function() needs to be called as well.
    @patch("tardis.rest.app.security.datetime")
    def test_get_access_token(self, mocked_datetime):
        header = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "",
            "username": "test1",
            "password": "test",
            "scope": "",
            "client_id": "",
            "client_secret": "",
        }

        self.clear_lru_cache()
        response = run_async(self.client.post, "/login/access-token")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": [
                    {
                        "loc": ["body", "username"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    },
                    {
                        "loc": ["body", "password"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    },
                ]
            },
        )

        self.clear_lru_cache()
        mocked_datetime.utcnow.return_value = datetime.utcfromtimestamp(0)
        response = run_async(
            self.client.post, "/login/access-token", data=data, headers=header
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0Iiwic2NvcGVzIjpbInJlc291cmNlczpnZXQiXSwiZXhwIjo4NjQwMH0.FBozcHL4n21BMprTP8snzniaNClpPat3hlJ1b-glgJg",  # noqa B509
                "token_type": "bearer",
            },
        )

        self.clear_lru_cache()
        self.config.Services.restapi.get_user.side_effect = lambda user_name: None
        response = run_async(
            self.client.post, "/login/access-token", data=data, headers=header
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Incorrect username or password"})
        self.config.Services.restapi.get_user.side_effect = None

        self.clear_lru_cache()
        data["password"] = "wrong"
        response = run_async(
            self.client.post, "/login/access-token", data=data, headers=header
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Incorrect username or password"})
