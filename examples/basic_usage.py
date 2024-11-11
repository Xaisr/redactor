"""
Comprehensive examples for the Redactor library.
From basic usage to advanced customization.
"""

from redactor import Redactor, RecognizerBuilder
from typing import Dict

###################
# Basic Examples #
###################

def basic_redaction_example():
    """
    Basic usage showing default entity redaction.
    Demonstrates core redaction and restoration functionality.
    """
    # Initialize redactor with default settings
    redactor = Redactor()
    
    # Example text with common PII
    text = """
    Contact Information:
    Name: John Smith
    Email: john.smith@example.com
    Phone: +1-555-123-4567
    Credit Card: 4532-5678-1234-5678
    Address: 123 Main St, New York, NY 10001
    Company: Microsoft Corporation
    """
    
    # Perform redaction
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Basic Redaction ===")
    print("Original:", text)
    print("Redacted:", redacted_text)
    
    # Restore original text
    restored_text = redactor.restore(redacted_text, mappings)
    print("Restored:", restored_text)

def entity_selection_example():
    """
    Example showing how to select specific entities to redact.
    """
    # Initialize redactor with specific entities
    selected_entities = ['PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER']
    redactor = Redactor(enabled_entities=selected_entities)
    
    text = """
    Employee Record:
    Name: Jane Doe
    Email: jane.doe@company.com
    Phone: +1-555-987-6543
    Address: 456 Oak Road, Chicago, IL 60601  # Won't be redacted
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Selective Entity Redaction ===")
    print("Original:", text)
    print("Redacted:", redacted_text)
    print("Enabled Entities:", redactor.get_enabled_entities())

########################
# Intermediate Examples #
########################

def custom_words_example():
    """
    Example showing custom word redaction.
    """
    # Initialize redactor with custom words
    custom_words = [
        "PROJECT-X",
        "Operation Phoenix",
        "CLASSIFIED-A123",
        "Secret Initiative"
    ]
    
    redactor = Redactor(custom_words=custom_words)
    
    text = """
    CONFIDENTIAL MEMO
    Re: PROJECT-X Development
    
    Operation Phoenix is proceeding as planned.
    Document ID: CLASSIFIED-A123
    
    The Secret Initiative will commence next week.
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Custom Words Redaction ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def fuzzy_matching_example():
    """
    Example demonstrating fuzzy matching capabilities.
    """
    # Initialize redactor with fuzzy matching enabled
    redactor = Redactor(fuzzy_mapping=1)
    
    text = """
    Meeting Participants:
    1. John Smith (Project Lead)
    2. Jon Smyth (Developer)
    3. Johnny Smith (Designer)
    4. Jonathan Smithe (Manager)
    
    Microsoft Corporation's Seattle Office
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Fuzzy Matching ===")
    print("Original:", text)
    print("Redacted:", redacted_text)
    print("Mappings:", mappings)

####################
# Advanced Examples #
####################

def custom_recognizer_example():
    """
    Example showing how to create and use custom recognizers.
    """
    # Create custom recognizer for project codes
    project_recognizer = (RecognizerBuilder("PROJECT")
                         .with_pattern(r"PRJ-\d{4}", score=0.8)
                         .with_context(["project", "code"])
                         .with_priority(1)
                         .build())
    
    # Create custom recognizer for product IDs
    product_recognizer = (RecognizerBuilder("PRODUCT")
                         .with_pattern(r"PROD-[A-Z]{2}\d{3}", score=0.9)
                         .with_pattern(r"SKU#\d{6}", score=0.85)
                         .with_context(["product", "item", "sku"])
                         .with_priority(2)
                         .build())
    
    # Initialize redactor with custom recognizers
    redactor = Redactor()
    redactor.add_recognizer(project_recognizer)
    redactor.add_recognizer(product_recognizer)
    
    text = """
    Project Summary:
    Code: PRJ-2024
    Product IDs: PROD-AB123, SKU#123456
    Status: Active
    Owner: Sarah Johnson
    Location: Seattle Office
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Custom Recognizer ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def custom_template_example():
    """
    Example showing how to customize replacement templates.
    """
    def custom_template(entity_type: str, count: int) -> str:
        """Custom template function for replacements."""
        templates = {
            'PERSON': f'👤 [REDACTED_NAME_{count}]',
            'EMAIL_ADDRESS': f'📧 [MASKED_EMAIL_{count}]',
            'PHONE_NUMBER': f'📞 [HIDDEN_PHONE_{count}]',
            'CREDIT_CARD': f'💳 [SECURED_CARD_{count}]',
            'LOCATION': f'📍 [HIDDEN_LOCATION_{count}]'
        }
        return templates.get(entity_type, f'🔒 [REDACTED_{entity_type}_{count}]')
    
    class CustomTemplateRedactor(Redactor):
        def _generate_replacement(self, entity_type: str, original_text: str) -> str:
            if entity_type not in self.counter:
                self.counter[entity_type] = 0
            self.counter[entity_type] += 1
            return custom_template(entity_type, self.counter[entity_type])
    
    redactor = CustomTemplateRedactor()
    
    text = """
    Customer Details:
    Name: Alice Brown
    Email: alice.brown@email.com
    Phone: +1-555-123-4567
    Address: 789 Pine St, Boston, MA
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Custom Templates ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

#######################
# Complex Examples #
#######################

def advanced_recognizer_example():
    """
    Example showing advanced recognizer configuration with
    multiple patterns, context words, and validation.
    """
    # Create an advanced recognizer for medical data
    def validate_medical_id(text: str) -> bool:
        """Validate medical ID format."""
        import re
        return bool(re.match(r'^MED-[A-Z]{2}\d{6}$', text))
    
    medical_recognizer = (RecognizerBuilder("MEDICAL_RECORD")
        .with_patterns([
            ("med_id", r"MED-[A-Z]{2}\d{6}", 0.9),
            ("patient_id", r"PAT#\d{8}", 0.85),
            ("room_id", r"RM-[A-Z]\d{3}", 0.7)
        ])
        .with_context([
            "patient", "medical", "record",
            "hospital", "clinic", "doctor"
        ])
        .with_validation(validate_medical_id)
        .with_priority(1)
        .build())
    
    # Create an advanced recognizer for internal codes
    internal_recognizer = (RecognizerBuilder("INTERNAL_CODE")
        .with_patterns([
            ("project", r"PRJ-\d{4}-[A-Z]{2}", 0.9),
            ("document", r"DOC-\d{6}", 0.8),
            ("asset", r"AST-[A-Z]{3}\d{4}", 0.85)
        ])
        .with_context(["internal", "classified", "confidential"])
        .with_priority(2)
        .build())
    
    # Initialize redactor with custom recognizers
    redactor = Redactor()
    redactor.add_recognizer(medical_recognizer)
    redactor.add_recognizer(internal_recognizer)
    
    text = """
    CONFIDENTIAL MEDICAL RECORD
    
    Patient ID: PAT#12345678
    Medical Record: MED-AB123456
    Room: RM-A123
    
    Internal References:
    Project: PRJ-2024-XY
    Document: DOC-123456
    Asset Tag: AST-XYZ7890
    
    Treating Physician: Dr. James Wilson
    Hospital: City General Hospital
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Advanced Recognizers ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def context_aware_template_example():
    """
    Example showing context-aware replacement templates
    that adapt based on surrounding text.
    """
    class ContextAwareRedactor(Redactor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context_cache: Dict[str, str] = {}
        
        def _generate_replacement(self, entity_type: str, original_text: str) -> str:
            if entity_type not in self.counter:
                self.counter[entity_type] = 0
            self.counter[entity_type] += 1
            
            # Get context (20 chars before and after)
            start = max(0, original_text.find(original_text) - 20)
            end = min(len(original_text), original_text.find(original_text) + len(original_text) + 20)
            context = original_text[start:end].lower()
            
            # Define context-specific replacements
            if entity_type == 'PERSON':
                if any(title in context for title in ['dr', 'doctor', 'physician']):
                    return f'[PHYSICIAN_{self.counter[entity_type]}]'
                elif any(title in context for title in ['prof', 'professor']):
                    return f'[PROFESSOR_{self.counter[entity_type]}]'
                elif any(title in context for title in ['ceo', 'chief']):
                    return f'[EXECUTIVE_{self.counter[entity_type]}]'
            
            # Default replacement
            return f'[{entity_type}_{self.counter[entity_type]}]'
    
    redactor = ContextAwareRedactor()
    
    text = """
    Hospital Staff Directory:
    
    Chief of Surgery: Dr. Michael Roberts
    Professor of Medicine: Prof. Sarah Chen
    CEO: James Thompson
    
    General Practitioner: Dr. Lisa Brown
    Nurse: Mary Johnson
    """
    
    redacted_text, mappings = redactor.redact(text)
    print("\n=== Context-Aware Templates ===")
    print("Original:", text)
    print("Redacted:", redacted_text)

def run_all_examples():
    """Run all example functions."""
    print("Running Redactor Library Examples\n")
    
    # Basic Examples
    basic_redaction_example()
    entity_selection_example()
    
    # Intermediate Examples
    custom_words_example()
    fuzzy_matching_example()
    
    # Advanced Examples
    custom_recognizer_example()
    custom_template_example()
    
    # Complex Examples
    advanced_recognizer_example()
    context_aware_template_example()

if __name__ == "__main__":
    run_all_examples()
