from setuptools import setup, find_packages
import os

repo_base_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(repo_base_dir, 'README.md'), 'r') as read_me:
    long_description = read_me.read()

setup(
    name='tardis',
    version='0.0.1',
    description='StateMachine using asyncio',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/giffels/AsyncStateMachine',
    author='Manuel Giffels',
    author_email='giffels@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Topic :: System :: Distributed Computing',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Utilities',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='asyncio tardis cloud scheduler',
    packages=find_packages(exclude=['tests']),
    install_requires=['aiohttp', 'CloudStackAIO', 'PyYAML', 'AsyncOpenStackClient', 'cobald', 'asyncssh'],
    tests_require=['aiotools'],
    zip_safe=False,
    test_suite='tests',
    project_urls={
        'Bug Reports': 'https://github.com/giffels/AsyncStateMachine/issues',
        'Source': 'https://github.com/giffels/AsyncStateMachine',
    },
)
