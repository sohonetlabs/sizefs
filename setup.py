__author__ = 'jjw'

from distutils.core import setup

setup(
    name='SizeFS',
    version='0.2.0',
    author='Joel Wright',
    author_email='joel.wright@sohonet.com',
    packages=['sizefs', 'sizefs.test'],
    scripts=[],
    #url='http://pypi.python.org/pypi/SizeFS/',
    license='LICENSE.txt',
    description='SizeFS is a mock filesystem for creating files of particular'
                'sizes with specified contents.',
    long_description=open('README.rst').read(),
    install_requires=[
        "fusepy>=2.0.2",
        "Cython>=0.19.1",
        ],
)
