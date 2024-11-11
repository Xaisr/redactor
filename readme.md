# Redactor

[![PyPI version](https://badge.fury.io/py/redactor.svg)](https://badge.fury.io/py/redactor)
[![Python versions](https://img.shields.io/pypi/pyversions/redactor.svg)](https://pypi.org/project/redactor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library for text redaction and anonymization, a wrapper built on top of Microsoft Presidio. Super-useful for both individuals and enterprises building custom prompt anonymization layer for their LLM Inference pipelines.  

## Features

- 🔒 Automatic detection and redaction of sensitive information
- 🔄 Reversible redaction with mapping preservation
- 🎯 Custom entity recognition
- 🛠 Configurable fuzzy matching
- 📝 Support for custom word lists
- 🔧 Extensible recognizer framework

## Installation

```bash
pip install redactor
```

After installation, you'll need to download the required spaCy model:

```bash
python -m spacy download en_core_web_sm
```

## Quick Start

```python
from redactor import Redactor

# Initialize redactor
redactor = Redactor()

# Redact text
text = "My name is John Doe and my email is john.doe@example.com"
redacted_text, mappings = redactor.redact(text)
print(redacted_text)
# Output: "My name is PERSON_1 and my email is EMAIL_ADDRESS_1"

# Restore original text
original_text = redactor.restore(redacted_text, mappings)
print(original_text)
# Output: "My name is John Doe and my email is john.doe@example.com"
```

## Advanced Usage

### Custom Word Lists

```python
# Initialize with custom words to redact
redactor = Redactor(custom_words=["PROJECT-X", "OPERATION-Y"])

text = "Discussing PROJECT-X details"
redacted_text, mappings = redactor.redact(text)
print(redacted_text)
# Output: "Discussing CUSTOM_1 details"
```

### Custom Entity Recognition

```python
from redactor import RecognizerBuilder

# Create custom recognizer for product codes
product_recognizer = (RecognizerBuilder("PRODUCT")
                     .with_pattern(r"Product-[A-Z]+")
                     .with_context(["released", "shipment"])
                     .build())

redactor = Redactor()
redactor.add_recognizer(product_recognizer)

text = "The new Product-ALPHA will be released next month"
redacted_text, mappings = redactor.redact(text)
print(redacted_text)
# Output: "The new PRODUCT_1 will be released next month"
```

### Fuzzy Matching

```python
# Enable fuzzy matching
redactor = Redactor(fuzzy_mapping=1)

text = """
John Smith is the CEO.
Jon Smith signed the document.
"""
redacted_text, mappings = redactor.redact(text)
# Similar names will use the same replacement
```

## Supported Entity Types

Default entities include:
- PERSON
- EMAIL_ADDRESS
- PHONE_NUMBER
- CREDIT_CARD
- DATE_TIME
- LOCATION
- ORGANIZATION

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/xaisr/redactor.git
cd redactor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

### Run Tests

```bash
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on top of [Microsoft Presidio](https://github.com/microsoft/presidio)
- Uses [spaCy](https://spacy.io/) for NLP tasks
