"""Setup script for the pub-search-kit package."""

from pathlib import Path

from setuptools import find_packages, setup

BASE_DIR = Path(__file__).parent


def read_readme() -> str:
    readme_path = BASE_DIR / "README.md"
    return readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""


setup(
    name="pub-search-kit",
    version="0.1.0",
    author="Numan Burak Fidan",
    author_email="numanburakfidan@yandex.com",
    description="Unified adapters for querying biomedical publication APIs.",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/OdyOSG/pub-search-kit",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.12",
    install_requires=[
        "requests>=2.31",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
        ],
        "test": [
            "pytest>=8.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
