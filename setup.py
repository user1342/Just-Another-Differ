from setuptools import setup, find_packages

setup(
    name='Just Another Differ',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'fuzzywuzzy',
        'tqdm',
        'jinja2'
    ],
    entry_points={
        'console_scripts': [
            'tweezer=JustAnotherDiffer.JAD:entry',
        ],
    },
)