from setuptools import setup, find_packages
from FoldingAtHomeControl import __version__


long_description = open('README.md').read()

setup(
    name='PyFoldingAtHomeControl',
    version=__version__,
    license='MIT',
    url='https://github.com/eifinger/PyFoldingAtHomeControl',
    author='Kevin Eifinger',
    author_email='k.eifinger@googlemail.com',
    description='Python lib to get stats from your Folding@Home clients.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=["tests", "tests.*"]),
    zip_safe=True,
    platforms='any',
    install_requires=list(val.strip() for val in open('requirements.txt')),
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "License :: OSI Approved :: MIT License"
    ]
)
