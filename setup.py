from setuptools import setup, find_packages


setup(
    name="OptRideHailing",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "matplotlib",
        "gurobipy",
        "jupyter",
        "h3"
    ],
    author="Danial Moafi",
    description="Ride-Hailing Revenue Optimization via Integer Linear Programming",
    python_requires=">=3.8",
)