"""
Redactor
========

A Python library for text redaction and anonymization that protects sensitive information
while maintaining text readability and structure.

Basic usage:
-----------
    >>> from redactor import Redactor
    >>> redactor = Redactor()
    >>> text = "Hello, my name is John Doe"
    >>> redacted, mappings = redactor.redact(text)
    >>> print(redacted)
    Hello, my name is [PERSON_1]
    >>> original = redactor.restore(redacted, mappings)
    >>> print(original)
    Hello, my name is John Doe

Features:
--------
- Entity detection and redaction (names, emails, credit cards, etc.)
- Customizable replacement patterns
- Custom entity recognition
- Fuzzy matching support
- Reversible redaction with mapping preservation
"""

from .core import Redactor
from .patterns import RecognizerBuilder, EntityType, PatternDefinition

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

# Public API
__all__ = [
    "Redactor",
    "RecognizerBuilder",
    "EntityType",
    "PatternDefinition",
]