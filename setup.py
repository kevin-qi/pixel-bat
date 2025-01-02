from setuptools import setup, find_packages

setup(
    name="pixelbat",
    version="0.1.0",
    packages=find_packages(where="pixelbat", include=["*"]),
    package_dir={"": "pixelbat"},
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