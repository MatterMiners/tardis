from tardis.rest.app.security import check_scope_permissions

from fastapi import HTTPException, status


from unittest import TestCase


class TestSecurity(TestCase):
    def test_check_scope_permissions(self):
        with self.assertRaises(HTTPException) as cm:
            check_scope_permissions(
                ["user:get", "resources:get"], ["user:get", "user:put"]
            )
        self.assertEqual(cm.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            cm.exception.detail,
            "Scope 'resources:get' not assigned to user",
        )
        check_scope_permissions(["resources:get"], ["resources:get"])
