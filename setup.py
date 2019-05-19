"""
rio is a library for temporarily patching python objects so they are executed
by a remote server.
"""
import os
import re
from setuptools import setup, find_packages


_dirname = os.path.abspath(os.path.dirname(__file__))


def read(*paths):
    with open(os.path.join(_dirname, *paths)) as f:
        return f.read()


def version():
    """
    Sources version from the __init__.py so we don't have to maintain the
    value in two places.
    """
    regex = re.compile(r'__version__ = \'([0-9.]+)\'')
    for line in read('rio', '__init__.py').split('\n'):
        match = regex.match(line)
        if match:
            return match.groups()[0]


def requirements():
    """
    Sources install_requires from requirements.txt so we don't have to maintain
    in two places.
    """
    results = []
    for line in read('requirements.txt').split('\n'):
        line = line.strip()
        if line.startswith('#'):
            continue
        results.append(line.split(' ')[0].split('#')[0])
    return results


setup(
    name='rio',
    version=version(),
    description=__doc__,
    long_description=read('README.md'),
    author='Sam Bourne',
    packages=find_packages(),
    install_requires=requirements(),
    extras_require={
        'tests': [
            'pytest',
        ],
    }
)
