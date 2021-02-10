import kubernetes_asyncio.client

from ...configuration.configuration import Configuration
from ...exceptions.tardisexceptions import TardisError
from ...interfaces.siteadapter import SiteAdapter
from ...interfaces.siteadapter import ResourceStatus
from ...utilities.attributedict import AttributeDict
from ...utilities.staticmapping import StaticMapping

from kubernetes_asyncio import client

from functools import partial
from datetime import datetime
from contextlib import contextmanager


class KubernetesAdapter(SiteAdapter):
    def __init__(self, machine_type: str, site_name: str):
        self._configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name

        self.aConfiguration = kubernetes_asyncio.client.Configuration(
            host=self._configuration.host,
            api_key={"authorization": self._configuration.token},
        )

        self.aConfiguration.api_key_prefix["authorization"] = "Bearer"

        self.aConfiguration.verify_ssl = False

        # configuration.verify_ssl=True
        # ssl_ca_cert is the filepath to the file that contains the certificate.
        # configuration.ssl_ca_cert="certificate"

        key_translator = StaticMapping(
            remote_resource_uuid="uid", drone_uuid="name", resource_status="type"
        )

        translator_functions = StaticMapping(
            created=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z"),
            updated=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z"),
            type=lambda x, translator=StaticMapping(
                Progressing=ResourceStatus.Running,
                Available=ResourceStatus.Running,
                Stopped=ResourceStatus.Stopped,
                Deleted=ResourceStatus.Deleted,
                ReplicaFailure=ResourceStatus.Error,
            ): translator[x],
        )

        self.handle_response = partial(
            self.handle_response,
            key_translator=key_translator,
            translator_functions=translator_functions,
        )

    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        self.client = client.AppsV1Api(client.ApiClient(self.aConfiguration))
        spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": self.machine_type_configuration.label}
            ),
            template=client.V1PodTemplateSpec(),
        )

        container = client.V1Container(
            image=self.machine_type_configuration.image,
            args=self.machine_type_configuration.args.split(","),
            name=resource_attributes.drone_uuid,
            resources=client.V1ResourceRequirements(
                limits={
                    "cpu": self.machine_meta_data.Cores,
                    "memory": self.machine_meta_data.Memory,
                }
            ),
        )

        spec.template.metadata = client.V1ObjectMeta(
            name=self.machine_type_configuration.label,
            labels={"app": self.machine_type_configuration.label},
        )

        spec.template.spec = client.V1PodSpec(containers=[container])
        body = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=resource_attributes.drone_uuid),
            spec=spec,
        )

        responseTemp = await self.client.create_namespaced_deployment(
            namespace="default", body=body
        )

        response = dict(
            {
                "uid": responseTemp.metadata.uid,
                "name": responseTemp.metadata.name,
                "type": "Progressing",
            }
        )

        return self.handle_response(response)

    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        self.client = client.AppsV1Api(client.ApiClient(self.aConfiguration))

        list = await self.client.list_namespaced_deployment(namespace="default")

        response = dict(
            {
                "uid": resource_attributes.remote_resource_uuid,
                "name": resource_attributes.drone_uuid,
                "type": "Deleted",
            }
        )

        for x in list.items:
            if x.metadata.name == resource_attributes.drone_uuid:
                responseTemp = await self.client.read_namespaced_deployment(
                    name=resource_attributes.drone_uuid, namespace="default"
                )

                if responseTemp.spec.replicas == 0:
                    response = dict(
                        {
                            "uid": responseTemp.metadata.uid,
                            "name": responseTemp.metadata.name,
                            "type": "Stopped",
                        }
                    )
                else:
                    response = dict(
                        {
                            "uid": responseTemp.metadata.uid,
                            "name": responseTemp.metadata.name,
                            "type": responseTemp.status.conditions[0].type,
                        }
                    )

        return self.handle_response(response)

    async def stop_resource(self, resource_attributes: AttributeDict):
        self.client = client.AppsV1Api(client.ApiClient(self.aConfiguration))
        body = await self.client.read_namespaced_deployment(
            name=resource_attributes.drone_uuid, namespace="default"
        )
        body.spec.replicas = 0
        response = await self.client.replace_namespaced_deployment(
            name=resource_attributes.drone_uuid, namespace="default", body=body
        )
        return response

    async def terminate_resource(self, resource_attributes: AttributeDict):
        self.client = client.AppsV1Api(client.ApiClient(self.aConfiguration))
        response = await self.client.delete_namespaced_deployment(
            name=resource_attributes.drone_uuid,
            namespace="default",
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=5
            ),
        )
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except Exception as ex:
            raise TardisError from ex
