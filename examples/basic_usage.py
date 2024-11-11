"""
Basic usage examples for the Redactor library.
This file demonstrates common use cases and features.
"""

from redactor import Redactor, RecognizerBuilder

def basic_redaction_example():
    """Basic usage of redaction and restoration."""
    # Initialize redactor
    redactor = Redactor()
    
    # Example text with sensitive information
    text = """
    Hello, my name is John Doe.
    You can reach me at john.doe@example.com or call at +1-202-555-0123.
    I work at Microsoft in New York.
    My credit card number is 4532-5678-1234-5678.
    """
    
    # Perform redaction
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Basic Redaction ===")
    print("Original:", text)
    print("Redacted:", redacted_text)
    
    # Restore original text
    restored_text = redactor.restore(redacted_text, mappings)
    print("Restored:", restored_text)

def custom_words_example():
    """Example using custom word redaction."""
    # Initialize redactor with custom words
    redactor = Redactor(custom_words=["PROJECT-X", "OPERATION-Y"])
    
    text = "The secret PROJECT-X details and OPERATION-Y plans are confidential."
    redacted_text, mappings = redactor.redact(text)
    
    print("\n=== Custom Words Redaction ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def custom_recognizer_example():
    """Example demonstrating custom entity recognition."""
    # Create a custom recognizer for product codes
    product_recognizer = (RecognizerBuilder("PRODUCT")
                         .with_pattern(r"Product-[A-Z]+", score=0.8)
                         .with_context(["released", "shipment"])
                         .build())
    
    # Initialize redactor and add custom recognizer
    redactor = Redactor()
    redactor.add_recognizer(product_recognizer)
    
    text = "The new Product-ALPHA will be released next month for shipment."
    redacted_text, mappings = redactor.redact(text)
    
    print("\n=== Custom Recognizer ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def fuzzy_matching_example():
    """Example showing fuzzy matching capabilities."""
    # Initialize redactor with fuzzy matching
    redactor = Redactor(fuzzy_mapping=1)
    
    text = """
    John Smith is the CEO.
    Jon Smith signed the document.
    """
    redacted_text, mappings = redactor.redact(text)
    
    print("\n=== Fuzzy Matching ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def main():
    """Run all examples."""
    print("Redactor Library Usage Examples\n")
    
    basic_redaction_example()
    custom_words_example()
    custom_recognizer_example()
    fuzzy_matching_example()

if __name__ == "__main__":
    main()