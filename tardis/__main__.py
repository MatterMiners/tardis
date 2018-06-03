#!/usr/bin/env python3.6
from .configuration.configuration import Configuration
from .resources.drone import Drone

import asyncio
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
    print(configuration.CloudStackAIO)

    loop = asyncio.get_event_loop()
    drones = [Drone(agents=[]).mount(event_loop=loop) for _ in range(10)]
    loop.run_forever()

if __name__ == '__main__':
    main()
