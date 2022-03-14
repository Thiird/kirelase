from setuptools import setup

setup(
    name="kirealease",
    version="1",
    description="Automate the release of Kicad projects",
    author="Stefano Nicolis",
    author_email="stenicolis@gmail.com",
    url='https://github.com/Thiird/kirelase.git',
    keywords=['kicad', 'export', 'schematic', 'bom', 'step', 'gerbers'],
    platform='linux',
    scripts=['kirelease'],
    entry_points={
        'console_scripts': [
            'kirelease = kirelease:main'
        ]
    },
    install_requires=[
        'setuptools' == '59.1.1',
        'xvfbwrapper' == '0.2.9'
    ],
)
