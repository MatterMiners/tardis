from ..configuration.configuration import Configuration
from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisError
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ..interfaces.siteadapter import ResourceStatus
from ..interfaces.siteadapter import SiteAdapter
from ..utilities.staticmapping import StaticMapping
from asyncssh import Error
from asyncssh

from asyncio import TimeoutError
from contextlib import contextmanager
from datetime import datetime
from functools import partial

import logging


class MoabAdapter(SiteAdapter):
    def __init__(self, machine_type, site_name):
        self.configuration = getattr(Configuration(), site_name)
        self._machine_type = machine_type
        self._site_name = site_name

        # get authentification
        self._remote_host = self.configuration.remote_host
        self._login = self.configuration.login
        self._key = self.configuration.key

    async def deploy_resource(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, user=self._login, client_keys=[self._key] ) as conn:
            request_command = 'msub -j oe -m p -l walltime=02:00:00:00,mem=120gb,nodes=1:ppn=20 startVM.py'
            result = await conn.run(request_command, check=True)
            logging.debug(f"{self.site_name} servers create returned {result}")
            try:
                resource_id = int(result.stdout)

            except:
                raise TardisError



    async def resource_status(self, resource_attributes):
        raise NotImplementedError

    async def terminate_resource(self, resource_attributes):
        async with asyncssh.connect(self._remote_host, user=self._login, client_keys=[self._key] ) as conn:
            request_command = f"canceljob {resource_attributes.resource_id}"
            response = await conn.run(request_command, check=True)
        logging.debug(f"{self.site_name} servers terminate returned {response}")
        return response

    @contextmanager
    def handle_exceptions(self):
        try:
            yield
        except TimeoutError as te:
            raise TardisTimeout from te
        except asyncssh.Error as exc:
            logging.info('SSH connection failed: ' + str(exc))
            raise TardisResourceStatusUpdateFailed
        except:
            raise TardisError
