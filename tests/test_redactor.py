"""Tests for the Redactor library"""
import logging
import pytest
from redactor import Redactor, RecognizerBuilder
from redactor.patterns import RecognizerLevel

def test_basic_redaction():
    """Test basic redaction functionality."""
    redactor = Redactor()
    text = "Hello, my name is John Doe"
    redacted, mappings = redactor.redact(text)
    assert "John Doe" not in redacted
    assert "PERSON_1" in redacted  # Changed from [PERSON_1]

def test_multiple_entities():
    """Test redaction of multiple entity types."""
    redactor = Redactor()
    text = "John Doe's email is john.doe@example.com and phone is 123-456-7890"
    redacted, mappings = redactor.redact(text)
    
    # Check all sensitive info is redacted
    assert "John Doe" not in redacted
    assert "john.doe@example.com" not in redacted
    assert "123-456-7890" not in redacted
    
    # Check replacements exist
    assert "PERSON_" in redacted  # Changed from [PERSON_
    assert "EMAIL_ADDRESS_" in redacted
    assert "PHONE_NUMBER_" in redacted

def test_fuzzy_matching():
    """Test fuzzy matching functionality."""
    redactor = Redactor(fuzzy_mapping=1)
    text = """
    John Smith is the CEO.
    Jon Smith signed the document.
    """  # Changed to test similar names
    redacted, mappings = redactor.redact(text)
    
    # Both versions of the name should use same replacement
    replacements = set()
    for value in mappings.values():
        if "PERSON" in value:
            replacements.add(value)
    
    # Should have only one replacement for both similar names
    assert len(replacements) == 1

def test_custom_words():
    """Test redaction of custom words."""
    custom_words = ["PROJECT-X", "OPERATION-Y"]
    redactor = Redactor(custom_words=custom_words)
    
    text = "Discussing PROJECT-X and OPERATION-Y details"
    redacted, mappings = redactor.redact(text)
    
    for word in custom_words:
        assert word not in redacted
    assert "CUSTOM_1" in redacted  # Changed from [CUSTOM_1]
    assert "CUSTOM_2" in redacted

def test_custom_recognizer():
    """Test adding and using custom recognizer."""
    redactor = Redactor()
    
    # Create custom recognizer for project codes
    recognizer = (RecognizerBuilder("PROJECT")
        .with_pattern(r"Project-[A-Z]+")
        .with_context(["secret", "confidential"])
        .build())
    
    redactor.add_recognizer(recognizer)
    
    text = "Working on secret Project-ZEUS details"
    redacted, mappings = redactor.redact(text)
    
    assert "Project-ZEUS" not in redacted
    assert "PROJECT_1" in redacted  # Changed from [PROJECT_1]

def test_redaction_consistency():
    """Test consistent redaction within same run."""
    redactor = Redactor()
    
    # Test similar names in same text
    text = """John is here.
              Johnn is there."""
              
    redacted, _ = redactor.redact(text)
    
    # Should contain same replacement for both names
    assert "PERSON_1" in redacted
    assert "PERSON_2" not in redacted  # Should use same replacement

def test__check_mapping_limits():
    redactor = Redactor(custom_words=["SECRET1", "SECRET2", "SECRET3"])
    redactor.MAX_MAPPINGS = 2

    # Run redact() to create some mappings
    redactor.redact("SECRET1 SECRET2")
    assert len(redactor.mappings) == 2

    # Try to redact again, which should exceed the mapping limit
    try:
        redactor.redact("SECRET4")
        assert False, "RuntimeError should have been raised"
    except RuntimeError:
        pass
    else:
        assert False, "RuntimeError should have been raised"


def test_restoration_with_invalid_mapping():
    """Test restoration with invalid/incomplete mapping."""
    redactor = Redactor()
    text = "Hello, John Doe"
    redacted, mappings = redactor.redact(text)
    
    # When using empty mappings, should keep redacted form
    restored = redactor.restore(redacted, {})
    assert restored == redacted  # Should keep PERSON_1, not restore original
    
    # When using original mappings, should restore
    restored_full = redactor.restore(redacted, mappings)
    assert restored_full == text  # Should get original back

def test_custom_recognizer():
    redactor = Redactor()

    # Create a custom recognizer for product codes
    product_recognizer = (RecognizerBuilder("PRODUCT")
                          .with_pattern(r"Product-[A-Z]+", score=0.8)
                          .with_context(["released", "shipment"])
                          .build())
    redactor.add_recognizer(product_recognizer)

    text = "The new Product-ALPHA will be released next month for shipment."
    redacted, mappings = redactor.redact(text)

    assert "Product-ALPHA" not in redacted
    assert "PRODUCT_1" in redacted
    assert "PRODUCT_1" in mappings.values()

def test_text_restoration():
    redactor = Redactor()
    text = "My email is john.doe@example.com and my phone is 123-456-7890."
    redacted, mappings = redactor.redact(text)

    restored = redactor.restore(redacted, mappings)
    assert restored == text

def test_invalid_input_handling():
    redactor = Redactor()

    with pytest.raises(TypeError):
        redactor.redact(123)  # Non-string input

    with pytest.raises(ValueError):
        redactor.redact("")  # Empty input

    with pytest.raises(ValueError):
        redactor.redact("x" * 1_000_001)  # Input exceeds max length

def test_recognizer_builder():
    # Test invalid configuration
    with pytest.raises(ValueError):
        RecognizerBuilder("", level=RecognizerLevel.SIMPLE).build()

    with pytest.raises(ValueError):
        RecognizerBuilder("PERSON").with_pattern(r"John Doe").with_score_threshold(min_score=1.1, max_score=0.9).build()

    # Test priority assignment and conflict resolution
    builder1 = RecognizerBuilder("PERSON").with_pattern(r"John Doe")
    builder1.with_priority(1)
    builder2 = RecognizerBuilder("LOCATION").with_pattern(r"New York")
    builder2.with_priority(2)
    builder3 = RecognizerBuilder("ORGANIZATION").with_pattern(r"Acme Corp")
    builder3.with_priority(1)

    recognizer1 = builder1.build()
    recognizer2 = builder2.build()
    recognizer3 = builder3.build()

    assert recognizer1.priority == 1
    assert recognizer2.priority == 2
    assert recognizer3.priority == 3
