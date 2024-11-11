from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="redactor",
    version="0.1.0",
    author="xaisr",
    author_email="xaisr73@gmail.com",
    description="A Python library for text redaction and anonymization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xaisr/redactor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Security",  # Changed this line
        "Topic :: Text Processing :: General",
    ],
    python_requires=">=3.8",
    install_requires=[
        "presidio-analyzer>=2.2.0",
        "presidio-anonymizer>=2.2.0",
        "spacy>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black",
            "isort",
            "flake8",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov",
        ],
    }
)