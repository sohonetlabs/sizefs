__author__ = 'mm'
import setuptools

setuptools.setup(
    name='SizeFS',
    version='0.3.1',
    author='Mark McArdle',
    author_email='mark.mcardle@sohonet.com',
    packages=['sizefs', 'tests'],
    scripts=[],
    url='http://pypi.python.org/pypi/SizeFS/',
    download_url='https://github.com/sohonetlabs/sizefs',
    license='LICENSE.txt',
    description='SizeFS is a mock filesystem for creating files of particular '
                'sizes with specified contents.',
    long_description=open('README.txt').read(),
    keywords=['testing', 'files', 'size'],
    install_requires=[
        "fusepy==2.0.4",
        "docopt==0.6.2",
        "fs==0.5.4"
    ],
)
