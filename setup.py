from setuptools import setup, find_packages


long_description = open('README.md').read()

setup(
    name='PyFoldingAtHomeControl',
    version='0.0.2',
    license='MIT',
    url='https://github.com/eifinger/PyFoldingAtHomeControl',
    author='Kevin Eifinger',
    author_email='k.eifinger@googlemail.com',
    description='Python lib to get stats from your Folding@Home clients.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=[],
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