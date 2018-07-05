#!/usr/bin/env python3.6
from .adapter.htcondor import HTCondorAdapter
from .agents.batchsystemagent import BatchSystemAgent
from .agents.siteagent import SiteAgent
from .configuration.configuration import Configuration
from .resources.drone import Drone
from .utilities.looper import Looper

from importlib import import_module
import logging


def main():
    logging.basicConfig(filename="my_log_file.log", level=logging.DEBUG, format='%(asctime)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    configuration = Configuration('tardis.yml')

    loop = Looper().get_event_loop()

    batch_system_agent = BatchSystemAgent(batch_system_adapter=HTCondorAdapter())

    for site in configuration.Sites:
        site_adapter = getattr(import_module(name="tardis.adapter.{}".format(site.lower())), '{}Adapter'.format(site))
        for machine_type in getattr(configuration, site).MachineTypes:
            [loop.create_task(Drone(site_agent=SiteAgent(site_adapter(machine_type=machine_type,
                                                                      site_name=site.lower())),
                                    batch_system_agent=batch_system_agent).run()) for _ in range(1)]
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()


if __name__ == '__main__':
    main()
