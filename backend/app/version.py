'''
@create_time: 2026/4/27 下午8:13
@Author: GeChao
@File: version.py
'''

from importlib.metadata import version, PackageNotFoundError

PACKAGE_NAME = "zhi-yuan-agentic"


def get_app_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "0.1.0"
