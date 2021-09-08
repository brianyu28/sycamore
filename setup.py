from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

setup(
    author="Brian Yu",
    author_email="brian@brianyu.me",
    description="2D animation tool.",
    include_package_data=True,
    install_requires=[
        "numpy",
        "pillow==8.3.2",
    ],
    license="GPL-3.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    name="sycamore",
    packages=["sycamore"],
    url="https://github.com/brianyu28/sycamore",
    version="0.0.1"
)
