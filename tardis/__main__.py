#!/usr/bin/env python3.6
from .agents.batchsystemagent import BatchSystemAgent
from .agents.siteagent import SiteAgent
from .adapter.exoscale import ExoscaleAdapter
from .configuration.configuration import Configuration
from .resources.drone import Drone
from .utilities.looper import Looper

import logging


def main():
    logging.basicConfig(filename="my_log_file.log", level=logging.DEBUG, format='%(asctime)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    Configuration('tardis.yml')

    loop = Looper().get_event_loop()
    site_agent = SiteAgent(ExoscaleAdapter())
    batch_system_agent = BatchSystemAgent()
    [loop.create_task(Drone(site_agent=site_agent,
                            batch_system_agent=batch_system_agent).run()) for _ in range(10)]
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()


if __name__ == '__main__':
    main()
