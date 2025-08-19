from tardis.adapters.sites.satellite import SatelliteAdapter
from tardis.configuration.configuration import Configuration
from tardis.utilities.attributedict import AttributeDict

import asyncio
import time

configuration = Configuration("/home/jr4238/tardis/debugging/config.yml")

adapter = SatelliteAdapter(
    host_fqdn="cloud-monit.gridka.de", site_name="satellite.scc.kit.edu"
)


### get
resource_attributes = AttributeDict(drone_uuid="12345abc")
loop = asyncio.get_event_loop()
resource_attributes.update(
    loop.run_until_complete(adapter.resource_status(resource_attributes))
)

### Put

resource_attributes = AttributeDict(drone_uuid="12345abc")
loop = asyncio.get_event_loop()
resource_attributes.update(
    loop.run_until_complete(adapter.stop_resource(resource_attributes))
)

time.sleep(10)  # Wait for the resource to be deployed

### get
resource_attributes = AttributeDict(drone_uuid="12345abc")
loop = asyncio.get_event_loop()
resource_attributes.update(
    loop.run_until_complete(adapter.resource_status(resource_attributes))
)
