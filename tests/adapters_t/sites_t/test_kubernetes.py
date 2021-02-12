from tardis.adapters.sites.kubernetes import KubernetesAdapter
from tardis.exceptions.tardisexceptions import TardisError
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus
from tests.utilities.utilities import async_return
from tests.utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch

import logging
from kubernetes_asyncio import client


class TestKubernetesStackAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch(
            "tardis.adapters.sites.kubernetes.Configuration"
        )
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_kubernetes_api_patcher = patch(
            "tardis.adapters.sites.kubernetes.client.AppsV1Api"
        )
        cls.mock_kubernetes_api = cls.mock_kubernetes_api_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_kubernetes_api_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.host = "https://172.16.254.1:6443"
        test_site_config.token = "31ada4fd-adec-460c-809a-9e56ceb75269"
        test_site_config.MachineTypeConfiguration = AttributeDict(
            test2large=AttributeDict(
                image="busybox:1.26.1", label="busybox", args="sleep,3600"
            )
        )
        test_site_config.MachineMetaData = AttributeDict(
            test2large=AttributeDict(Cores="2", Memory="400Mi")
        )

        kubernetes_api = self.mock_kubernetes_api.return_value

        spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": "busybox"}),
            template=client.V1PodTemplateSpec(),
        )

        container = client.V1Container(
            image="busybox:1.26.1",
            args=["sleep", "3600"],
            name="testsite-089123",
            resources=client.V1ResourceRequirements(
                limits={"cpu": "2", "memory": "400Mi"}
            ),
        )

        spec.template.metadata = client.V1ObjectMeta(
            name="busybox",
            labels={"app": "busybox"},
        )

        spec.template.spec = client.V1PodSpec(containers=[container])
        self.body = client.V1Deployment(
            metadata=client.V1ObjectMeta(name="testsite-089123"),
            spec=spec,
        )

        self.create_return_value = client.V1Deployment(
            metadata=client.V1ObjectMeta(name="testsite-089123", uid="123456"),
            spec=spec,
        )

        kubernetes_api.create_namespaced_deployment.return_value = async_return(
            return_value=self.create_return_value
        )

        list2 = [
            client.V1DeploymentCondition(
                status="True",
                type="Progressing",
            )
        ]

        self.read_return_value = client.V1Deployment(
            metadata=client.V1ObjectMeta(name="testsite-089123", uid="123456"),
            spec=spec,
            status=client.V1DeploymentStatus(conditions=list2),
        )

        kubernetes_api.read_namespaced_deployment.return_value = async_return(
            return_value=self.read_return_value
        )

        list1 = [
            client.V1Deployment(
                metadata=client.V1ObjectMeta(name="testsite-089123", uid="123456"),
                spec=spec,
            )
        ]

        self.list_return_value = client.AppsV1beta1DeploymentList(items=list1)

        kubernetes_api.list_namespaced_deployment.return_value = async_return(
            return_value=self.list_return_value
        )

        kubernetes_api.replace_namespaced_deployment.return_value = async_return(
            return_value=None
        )

        kubernetes_api.delete_namespaced_deployment.return_value = async_return(
            return_value=None
        )

        self.kubernetes_adapter = KubernetesAdapter(
            machine_type="test2large", site_name="TestSite"
        )

    def tearDown(self):
        self.mock_kubernetes_api.reset_mock()

    def test_deploy_resource(self):
        self.assertEqual(
            run_async(
                self.kubernetes_adapter.deploy_resource,
                resource_attributes=AttributeDict(
                    drone_uuid="testsite-089123", remote_resource_uuid="123456"
                ),
            ),
            AttributeDict(
                remote_resource_uuid="123456",
                drone_uuid="testsite-089123",
                resource_status=ResourceStatus.Running,
            ),
        )
        self.mock_kubernetes_api.return_value.create_namespaced_deployment.assert_called_with(  # noqa: B950
            namespace="default", body=self.body
        )

    def test_machine_meta_data(self):
        self.assertEqual(
            self.kubernetes_adapter.machine_meta_data,
            AttributeDict(Cores="2", Memory="400Mi"),
        )

    def test_machine_type(self):
        self.assertEqual(self.kubernetes_adapter.machine_type, "test2large")

    def test_site_name(self):
        self.assertEqual(self.kubernetes_adapter.site_name, "TestSite")

    def test_resource_status(self):
        self.assertEqual(
            run_async(
                self.kubernetes_adapter.resource_status,
                resource_attributes=AttributeDict(
                    drone_uuid="testsite-089123", remote_resource_uuid="123456"
                ),
            ),
            AttributeDict(
                remote_resource_uuid="123456",
                drone_uuid="testsite-089123",
                resource_status=ResourceStatus.Running,
            ),
        )

        self.mock_kubernetes_api.return_value.list_namespaced_deployment.assert_called_with(  # noqa: B950
            namespace="default"
        )

        self.mock_kubernetes_api.return_value.read_namespaced_deployment.assert_called_with(  # noqa: B950
            name="testsite-089123", namespace="default"
        )

    def test_stop_resource(self):

        self.body.metadata.uid = "123456"
        self.body.status = client.V1DeploymentStatus(
            conditions=[
                client.V1DeploymentCondition(
                    status="True",
                    type="Progressing",
                )
            ]
        )

        run_async(
            self.kubernetes_adapter.stop_resource,
            resource_attributes=AttributeDict(drone_uuid="testsite-089123"),
        )

        self.mock_kubernetes_api.return_value.read_namespaced_deployment.assert_called_with(  # noqa: B950
            name="testsite-089123", namespace="default"
        )

        self.mock_kubernetes_api.return_value.replace_namespaced_deployment.assert_called_with(  # noqa: B950
            name="testsite-089123", namespace="default", body=self.body
        )

    def test_terminate_resource(self):
        run_async(
            self.kubernetes_adapter.terminate_resource,
            resource_attributes=AttributeDict(drone_uuid="testsite-089123"),
        )

        self.mock_kubernetes_api.return_value.delete_namespaced_deployment.assert_called_with(  # noqa: B950
            name="testsite-089123",
            namespace="default",
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=5
            ),
        )

    def test_exception_handling(self):
        def test_exception_handling(to_raise, to_catch):
            with self.assertRaises(to_catch):
                with self.assertLogs(level=logging.WARNING):
                    with self.kubernetes_adapter.handle_exceptions():
                        raise to_raise

        matrix = [
            (Exception, TardisError),
        ]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
