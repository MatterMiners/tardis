from setuptools import setup, find_packages
import os
import ssl

repo_base_dir = os.path.abspath(os.path.dirname(__file__))

package_about = {}
# import __about__ file from repository to avoid reading from installed package
with open(os.path.join(repo_base_dir, "tardis", "__about__.py")) as about_file:
    exec(about_file.read(), package_about)

with open(os.path.join(repo_base_dir, "README.md"), "r") as read_me:
    long_description = read_me.read()

TESTS_REQUIRE = ["flake8"]


def get_cryptography_version():
    if ssl.OPENSSL_VERSION_INFO < (1, 1, 0):
        return "cryptography<3.2"  # to support openssl<1.1 (Centos 7)"
    else:
        return "cryptography"


setup(
    name=package_about["__package__"],
    version=package_about["__version__"],
    description=package_about["__summary__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=package_about["__url__"],
    author=package_about["__author__"],
    author_email=package_about["__email__"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Topic :: System :: Distributed Computing",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Utilities",
        "Framework :: AsyncIO",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "cobald.config.yaml_constructors": [
            "TardisPoolFactory = tardis.resources.poolfactory:create_composite_pool",
            "TardisPeriodicValue = tardis.utilities.simulators.periodicvalue:PeriodicValue",  # noqa: B950
            "TardisRandomGauss = tardis.utilities.simulators.randomgauss:RandomGauss",
            "TardisSSHExecutor = tardis.utilities.executors.sshexecutor:SSHExecutor",
            "TardisShellExecutor = tardis.utilities.executors.shellexecutor:ShellExecutor",  # noqa: B950
        ],
        "cobald.config.sections": [
            "tardis = tardis.configuration.configuration:Configuration"
        ],
    },
    keywords=package_about["__keywords__"],
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "aiohttp<4.0; python_version<'3.7'",  # to support python3.6 (Centos 7)
        "aiohttp; python_version>='3.7'",
        get_cryptography_version(),
        "CloudStackAIO",
        "PyYAML",
        "AsyncOpenStackClient",
        "cobald>=0.12.1",
        "asyncssh",
        "aiotelegraf",
        "elasticsearch",
        "aioprometheus",
        "kubernetes_asyncio",
        "pydantic",
    ],
    extras_require={
        "docs": ["sphinx", "sphinx_rtd_theme", "sphinxcontrib-contentui"],
        "test": TESTS_REQUIRE,
        "contrib": ["flake8", "flake8-bugbear", "black; implementation_name=='cpython'"]
        + TESTS_REQUIRE,
    },
    tests_require=TESTS_REQUIRE,
    zip_safe=False,
    test_suite="tests",
    project_urls={
        "Bug Reports": "https://github.com/matterminers/tardis/issues",
        "Source": "https://github.com/matterminers/tardis",
    },
)
