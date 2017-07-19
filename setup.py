"""package setup file for clupy"""
from setuptools import setup

setup(
    name='clupy',
    version='1.0.0',
    description='A simple framework and library for cluster computation in Python',
    url='https://github.com/xiaohai2016/CluPy',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Framework',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
    ],
    keywords='simple cluster',
    packages=['clupy'],
    install_requires=['tornado', 'pyyaml'],
)
