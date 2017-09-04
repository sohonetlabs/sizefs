import setuptools

__author__ = 'sohonet'

setuptools.setup(
    name='SizeFS',
    version='0.4.0',
    author='Sohonet',
    author_email='dev@sohonet.com',
    packages=['sizefs', 'tests'],
    scripts=[],
    url='http://pypi.python.org/pypi/SizeFS/',
    download_url='https://github.com/sohonetlabs/sizefs',
    license='LICENSE.txt',
    description='SizeFS is a mock filesystem for creating files of particular '
                'sizes with specified contents.',
    long_description=open('README.md').read(),
    keywords=['testing', 'files', 'size'],
    install_requires=[
        "fusepy==2.0.4",
        "docopt==0.6.2",
        "fs==0.5.4"
    ],
)
