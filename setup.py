from setuptools import setup, find_packages

setup(
    name="pixelbat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "matplotlib",
        "spikeinterface",
        "probeinterface",
        "kilosort",
        "tqdm",
    ],
    python_requires=">=3.9",
)