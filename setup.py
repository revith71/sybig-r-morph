from setuptools import setup, find_packages

setup(
    name="sybigr-morph",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.3.0",
        "pandas>=2.0.0",
        "numpy>=1.20.0",
        "jellyfish>=0.8.0",  
        "greek-accentuation>=1.2.0",  
        "openpyxl>=3.1.2",
        "xlrd>=2.0.1",  
        "gunicorn>=21.2.0"
    ],
    author="XXX",
    author_email="XXX",
    description="Greek Pseudoword Generator",
    keywords="linguistics, greek, pseudowords",
    url="https://github.com/revith/sybig_r",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.7",
)
