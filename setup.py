from setuptools import setup

setup(
    name='iridium-cli',
    version='0.1',
    py_modules=['main'],
    install_requires=[
        'click',
    ],
    entry_points='''
        [console_scripts]
        iridium-cli=main:main
    ''',
)
