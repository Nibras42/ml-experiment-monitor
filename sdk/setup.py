from setuptools import find_packages, setup

setup(
    name='mlmonitor',
    version='0.1.0',
    description='Python SDK for the MLMonitor experiment tracking platform',
    long_description=open('README.md').read() if __import__('os').path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='MLMonitor',
    python_requires='>=3.9',
    packages=find_packages(),
    install_requires=[
        'requests>=2.28',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
