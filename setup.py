import setuptools


def readme():
    with open('README.md') as f:
        return f.read()


setuptools.setup(
    name='gameanalysis',
    version='0.0',
    description='A python module for analyzing sparse and empirical games',
    long_description=readme(),
    url='https://github.com/egtaonline/GameAnalysis.git',
    author='Strategic Reasoning Group',
    license='Apache 2.0',
    entry_points = {
        'console_scripts': ['ga=gameanalysis.scripts.__main__:main'],
    },
    install_requires=[
        'numpy~=1.11',
        'scipy~=0.18',
        'scikit-learn~=0.18',
    ],
    setup_requires=['pytest-runner'],
    tests_require=[
        'pytest-cov~=2.3',
        'pytest-xdist~=1.15',
        'pytest~=3.0',
    ],
    packages=['gameanalysis', 'gameanalysis.scripts'])
