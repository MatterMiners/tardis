from setuptools import setup, find_packages
import os
import sys

repo_base_dir = os.path.abspath(os.path.dirname(__file__))

# import __about__ file from repository to avoid reading from installed package
sys.path.insert(0, repo_base_dir)
from tardis import __about__
sys.path.pop(0)

with open(os.path.join(repo_base_dir, 'README.md'), 'r') as read_me:
    long_description = read_me.read()

TESTS_REQUIRE = ['aiotools', 'flake8']

setup(
    name=__about__.__package__,
    version=__about__.__version__,
    description=__about__.__summary__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=__about__.__url__,
    author=__about__.__author__,
    author_email=__about__.__email__,
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
    keywords=__about__.__keywords__,
    packages=find_packages(exclude=['tests']),
    install_requires=['aiohttp', 'CloudStackAIO', 'PyYAML', 'AsyncOpenStackClient',
                      'cobald', 'asyncssh', 'aiotelegraf'],
    extras_require={
        'docs': ["sphinx", "sphinx_rtd_theme", "sphinxcontrib-contentui"],
        'test': TESTS_REQUIRE,
    },
    tests_require=TESTS_REQUIRE,
    zip_safe=False,
    test_suite='tests',
    project_urls={
        'Bug Reports': 'https://github.com/matterminers/tardis/issues',
        'Source': 'https://github.com/materminers/tardis',
    },
)
