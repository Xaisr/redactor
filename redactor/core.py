"""
Core implementation of the Redactor class for text anonymization and restoration.
"""

import logging
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
import re
from typing import List, Optional, Dict, Any, Union, Tuple
from difflib import SequenceMatcher
import random
from .patterns import RecognizerBuilder  # Import our RecognizerBuilder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Redactor:
    """
    A class for redacting and restoring sensitive information in text.

    Attributes:
        DEFAULT_ENTITIES (List[str]): Default entity types to detect and redact
        MAX_TEXT_LENGTH (int): Maximum text length to process
        MIN_TEXT_LENGTH (int): Minimum text length to process
        MAX_MAPPINGS (int): Maximum number of mappings to store
        MAX_CUSTOM_WORDS (int): Maximum number of custom words

    Example:
        >>> redactor = Redactor()
        >>> text = "Hello, my name is John Doe"
        >>> redacted, mappings = redactor.redact(text)
        >>> print(redacted)
        Hello, my name is [PERSON_1]
        >>> original = redactor.restore(redacted, mappings)
        >>> print(original)
        Hello, my name is John Doe
    """

    DEFAULT_ENTITIES = [
        'DATE_TIME', 'PERSON', 'ORGANIZATION', 'LOCATION', 
        'CREDIT_CARD', 'PHONE_NUMBER', 'EMAIL_ADDRESS'
    ]
    MAX_TEXT_LENGTH = 1_000_000  # 1MB text limit
    MAX_ENTITY_LENGTH = 1000     # Max length of any single entity to detect
    MAX_MAPPINGS = 100_000      # Max number of mappings to store
    MIN_TEXT_LENGTH = 1         # Minimum text length
    MAX_CUSTOM_WORDS = 1000

    def __init__(self, custom_words: Optional[List[str]] = None, 
                 enabled_entities: Optional[List[str]] = None,
                 language: str = 'en',
                 fuzzy_mapping: int = 0):
        """
        Initialize Redactor with optional configuration.

        Args:
            custom_words: Additional words to redact
            enabled_entities: List of entity types to detect
            language: Two-letter language code
            fuzzy_mapping: Enable fuzzy matching (0 or 1)

        Raises:
            ValueError: If parameters are invalid
            TypeError: If parameters are of wrong type"""
        
        """Initialize with input validation"""
        
        # Validate custom words first
        self.custom_words = self._validate_custom_words(custom_words)
        
        # Validate enabled entities
        if enabled_entities is not None:
            if not isinstance(enabled_entities, (list, tuple)):
                raise TypeError(f"Enabled entities must be a list or tuple, got {type(enabled_entities)}")
            if not all(isinstance(e, str) for e in enabled_entities):
                raise TypeError("All enabled entities must be strings")
            if len(enabled_entities) > len(self.DEFAULT_ENTITIES):
                raise ValueError(f"Too many enabled entities (max: {len(self.DEFAULT_ENTITIES)})")
        
        # Validate language
        if not isinstance(language, str) or len(language) != 2:
            raise ValueError("Language must be a 2-letter code (e.g., 'en')")
            
        # Validate fuzzy mapping
        if fuzzy_mapping not in [0, 1]:
            raise ValueError("fuzzy_mapping must be either 0 or 1")
        
        # Continue with initialization
        self._initialize_engine(language)
        self._validate_and_set_params(self.custom_words, enabled_entities, fuzzy_mapping)
        self._initialize_state()

    
    def _validate_text_for_anonymization(self, text: str) -> str:
        """Validate text before anonymization"""
        if not isinstance(text, str):
            raise TypeError(f"Input must be a string, got {type(text)}")
        
        text = text.strip()
        text_length = len(text)

        if text_length < self.MIN_TEXT_LENGTH:
            raise ValueError("Input text cannot be empty")
            
        if text_length > self.MAX_TEXT_LENGTH:
            raise ValueError(f"Input text length ({text_length}) exceeds maximum length of {self.MAX_TEXT_LENGTH} characters")
            
        return text

    def _validate_custom_words(self, words: Optional[List[str]]) -> List[str]:
        """Validate custom words during initialization"""
        if words is None:
            return []
            
        if not isinstance(words, (list, tuple)):
            raise TypeError(f"Custom words must be a list or tuple, got {type(words)}")
            
        if len(words) > self.MAX_CUSTOM_WORDS:
            raise ValueError(f"Custom words list ({len(words)}) exceeds maximum of {self.MAX_CUSTOM_WORDS}")
            
        # Validate individual words
        validated_words = []
        for word in words:
            if not isinstance(word, str):
                raise TypeError(f"Custom word must be string, got {type(word)}")
            if len(word) > self.MAX_ENTITY_LENGTH:
                raise ValueError(f"Custom word '{word[:50]}...' exceeds maximum length of {self.MAX_ENTITY_LENGTH}")
            if word.strip():  # Only add non-empty words
                validated_words.append(word.strip())
                
        return validated_words
    
    def _check_mapping_limits(self):
        """Check and handle mapping size limits"""
        if len(self.mappings) >= self.MAX_MAPPINGS:
            # Option 1: Raise error
            raise RuntimeError(f"Maximum number of mappings ({self.MAX_MAPPINGS}) exceeded")
            
            # Option 2: Remove oldest mappings (if we want this behavior instead)
            # self.mappings = dict(list(self.mappings.items())[-(self.MAX_MAPPINGS//2):])

    def _initialize_engine(self, language: str):
        """Initialize the NLP engine and analyzer"""
        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": language, "model_name": f"{language}_core_web_sm"}]
        }
        nlp_provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        self.analyzer_engine = AnalyzerEngine(nlp_engine=nlp_provider.create_engine())
        self.anonymizer_engine = AnonymizerEngine()
        self.language = language

    def _validate_and_set_params(self, custom_words: Optional[List[str]], 
                               enabled_entities: Optional[List[str]], 
                               fuzzy_mapping: int):
        """Validate and set initial parameters"""
        if fuzzy_mapping not in [0, 1]:
            raise ValueError("fuzzy_mapping must be either 0 or 1")
        
        self.custom_words = custom_words or []
        self.fuzzy_mapping = fuzzy_mapping
        self.enabled_entities = (enabled_entities if isinstance(enabled_entities, list) 
                               else self.DEFAULT_ENTITIES)

    def _initialize_state(self):
        """Initialize state variables"""
        self.entity_recognizers = {}
        self.max_priority = 0
        self.mappings = {}
        self.counter = {}

    def _setup_custom_recognizer(self):
        """Set up custom word recognizer"""
        patterns = [
            (f"custom_{i}", r'\b' + re.escape(word) + r'\b', 1.0)
            for i, word in enumerate(self.custom_words)
        ]
        custom_recognizer = (
            RecognizerBuilder("CUSTOM")
            .with_patterns(patterns)
            .with_priority(1)
            .build()
        )
        self.add_recognizer(custom_recognizer)

    def clear_mapping(self):
        """Clear all mappings and counters"""
        self.mappings = {}
        self.counter = {}

    def _text_similarity(self, text1: str, text2: str) -> bool:
        """Check text similarity for fuzzy matching"""
        if any(char.isdigit() for char in text1) or any(char.isdigit() for char in text2):
            return False
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() >= 0.7

    def _get_fuzzy_match(self, text: str) -> Optional[str]:
        """Get existing fuzzy match from mappings"""
        if not self.fuzzy_mapping:
            return None
        return next((self.mappings[existing_text] 
                    for existing_text in self.mappings
                    if self._text_similarity(text, existing_text)), None)

    def get_enabled_entities(self, all: bool = False) -> List[str]:
        """Get list of enabled or all available entities"""
        if not all:
            return self.enabled_entities
            
        available_entities = set()
        for recognizer in self.analyzer_engine.get_recognizers():
            if hasattr(recognizer, 'supported_entities'):
                entities = recognizer.supported_entities
                available_entities.update([entities] if isinstance(entities, str) else entities)
        return sorted(list(available_entities))

    def modify_entities(self, entities: List[str], add: bool = True):
        """Add or remove entities from enabled list"""
        if add:
            self.enabled_entities = list(set(self.enabled_entities + entities))
        else:
            self.enabled_entities = [e for e in self.enabled_entities if e not in entities]

    def get_entity_details(self, entities: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about specified entities"""
        entity_criteria = {}
        all_recognizers = self.analyzer_engine.get_recognizers()
        
        available_entities = set()
        for recognizer in all_recognizers:
            if hasattr(recognizer, 'supported_entities'):
                entities_list = recognizer.supported_entities
                available_entities.update(
                    [entities_list] if isinstance(entities_list, str) else entities_list
                )
        
        entities_to_process = entities or list(available_entities)
        
        for entity in entities_to_process:
            entity_details = {}
            supporting_recognizers = [
                rec for rec in all_recognizers
                if hasattr(rec, 'supported_entities') and (
                    (isinstance(rec.supported_entities, str) and rec.supported_entities == entity) or
                    (isinstance(rec.supported_entities, (list, tuple)) and entity in rec.supported_entities)
                )
            ]
            
            if not supporting_recognizers:
                print(f"No recognizers found for entity: {entity}")
                continue
            
            for recognizer in supporting_recognizers:
                self._process_recognizer_details(recognizer, entity_details)
            
            entity_criteria[entity] = self._normalize_entity_details(entity_details)
        
        return entity_criteria

    def _process_recognizer_details(self, recognizer: Any, entity_details: Dict[str, Any]):
        """Process details from a single recognizer"""
        for attr_name in dir(recognizer):
            if not attr_name.startswith('_'):
                try:
                    attr_value = getattr(recognizer, attr_name)
                    if not callable(attr_value):
                        if attr_name not in entity_details:
                            entity_details[attr_name] = []
                        if attr_value not in entity_details[attr_name]:
                            entity_details[attr_name].append(attr_value)
                except Exception:
                    continue
        
        # Add recognizer type
        recognizer_type = recognizer.__class__.__name__
        if 'recognizer_types' not in entity_details:
            entity_details['recognizer_types'] = []
        if recognizer_type not in entity_details['recognizer_types']:
            entity_details['recognizer_types'].append(recognizer_type)
        
        # Check for special properties
        if isinstance(recognizer, SpacyRecognizer):
            entity_details['uses_nlp'] = True
        if hasattr(recognizer, 'validate_result'):
            entity_details['has_validation'] = True


    def _normalize_entity_details(self, entity_details: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize entity details for consistency"""
        if 'patterns' in entity_details:
            processed_patterns = []
            for pattern in entity_details['patterns']:
                if isinstance(pattern, (list, tuple)):
                    processed_patterns.extend(pattern)
                else:
                    processed_patterns.append(pattern)
            entity_details['patterns'] = processed_patterns
        
        return {
            k: v[0] if isinstance(v, list) and len(v) == 1 else v
            for k, v in entity_details.items()
        }

    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect entities in text including custom words"""
        # Get analyzer entities
        results = self.analyzer_engine.analyze(
            text=text,
            entities=self.enabled_entities,
            language=self.language
        )
        entities = [
            {
                'text': text[result.start:result.end],
                'type': result.entity_type,
                'start': result.start,
                'end': result.end
            }
            for result in results
        ]

        # Add custom word matches
        for word in self.custom_words:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                entities.append({
                    'text': text[match.start():match.end()],
                    'type': 'CUSTOM',
                    'start': match.start(),
                    'end': match.end()
                })

        return sorted(entities, key=lambda x: x['start'])
    

    def add_recognizer(self, recognizer):
        """Add a custom recognizer to the analyzer engine"""
        # Get entity name from supported_entities
        entity = (recognizer.supported_entities[0] 
                 if isinstance(recognizer.supported_entities, list)
                 else recognizer.supported_entities)

        # Check if the entity is already in the enabled_entities list
        if entity in self.enabled_entities:
            raise ValueError(f"Entity '{entity}' is already enabled. Please use a different entity name.")

        # Add recognizer to analyzer engine
        self.analyzer_engine.registry.add_recognizer(recognizer)

        # Add to enabled entities if not present
        self.modify_entities([entity], add=True)

        # Handle priority in the entity_recognizers dictionary instead of directly on the recognizer
        if entity not in self.entity_recognizers or self.entity_recognizers[entity] is None:
            self.max_priority += 1
            self.entity_recognizers[entity] = self.max_priority
        
        return self
    


    def get_priorities(self, recognizers: Optional[list] = None) -> Union[Dict[str, int], List[Dict[str, int]]]:
        """Get priority levels for entities or specific recognizers"""
        def get_entity_priority(recognizer) -> Tuple[str, Optional[int]]:
            entity = (recognizer.supported_entities[0] 
                     if isinstance(recognizer.supported_entities, list)
                     else recognizer.supported_entities)
            
            if entity in self.enabled_entities:
                if entity not in self.entity_recognizers:
                    self.entity_recognizers[entity] = None
                    recognizer.priority = None
                return entity, self.entity_recognizers[entity]
            return entity, None

        if recognizers is None:
            return {
                entity: priority
                for recognizer in self.analyzer_engine.get_recognizers()
                for entity, priority in [get_entity_priority(recognizer)]
                if priority is not None
            }
        
        return [
            {entity: priority}
            for recognizer in recognizers
            for entity, priority in [get_entity_priority(recognizer)]
            if priority is not None
        ]

    def assign_priority_key(self) -> Dict[str, int]:
        """Assign priorities to entities with None priority"""
        current_priorities = self.get_priorities()
        valid_priorities = [p for p in current_priorities.values() if p is not None]
        highest_priority = max(valid_priorities) if valid_priorities else 0
        
        none_priority_entities = [
            entity_type for entity_type in self.enabled_entities 
            if entity_type not in current_priorities 
            or current_priorities[entity_type] is None
        ]
        
        for entity_type in none_priority_entities:
            highest_priority += 1
            self.entity_recognizers[entity_type] = highest_priority
            
        return self.entity_recognizers

    def organize_priorities(self, priority_assignments: Optional[List[Dict[str, int]]] = None) -> Dict[str, int]:
        """Reorganize entity priorities based on assignments or fix existing priorities"""
        current_priorities = self.get_priorities()
        return (self._fix_existing_priorities(current_priorities) if priority_assignments is None
                else self._apply_priority_assignments(current_priorities, priority_assignments))

    def _fix_existing_priorities(self, current_priorities: Dict[str, int]) -> Dict[str, int]:
        """Fix conflicts in existing priorities"""
        none_priorities = [
            entity for entity, priority in current_priorities.items() 
            if priority is None
        ]
        valid_priorities = {
            entity: priority for entity, priority in current_priorities.items() 
            if priority is not None
        }
        
        entities_by_priority = {}
        for entity, priority in valid_priorities.items():
            if priority in entities_by_priority:
                entities_by_priority[priority].append(entity)
            else:
                entities_by_priority[priority] = [entity]
        
        new_priorities = {}
        next_priority = 1
        
        for priority in sorted(entities_by_priority.keys()):
            entities = entities_by_priority[priority]
            if len(entities) > 1:
                available_slots = list(range(next_priority, next_priority + len(entities)))
                random.shuffle(entities)
                for entity, new_priority in zip(entities, available_slots):
                    new_priorities[entity] = new_priority
                next_priority += len(entities)
            else:
                new_priorities[entities[0]] = next_priority
                next_priority += 1
        
        if none_priorities:
            available_slots = list(range(next_priority, next_priority + len(none_priorities)))
            random.shuffle(none_priorities)
            for entity, priority in zip(none_priorities, available_slots):
                new_priorities[entity] = priority
        
        return self._update_priorities(new_priorities)

    def _apply_priority_assignments(self, current_priorities: Dict[str, int], 
                                  priority_assignments: List[Dict[str, int]]) -> Dict[str, int]:
        """Apply new priority assignments while resolving conflicts"""
        self._validate_priority_assignments(priority_assignments)
        
        new_priorities = current_priorities.copy()
        for assignment in priority_assignments:
            for entity, desired_priority in assignment.items():
                conflicts = [
                    (e, p) for e, p in new_priorities.items() 
                    if p == desired_priority and e != entity
                ]
                
                while conflicts:
                    conflict_entity, _ = conflicts.pop()
                    new_priority = desired_priority + 1
                    new_conflicts = [
                        (e, p) for e, p in new_priorities.items() 
                        if p == new_priority and e != conflict_entity
                    ]
                    conflicts.extend(new_conflicts)
                    new_priorities[conflict_entity] = new_priority
                    
                new_priorities[entity] = desired_priority
        
        return self._update_priorities(new_priorities)

    def _validate_priority_assignments(self, priority_assignments: List[Dict[str, int]]):
        """Validate priority assignments"""
        for assignment in priority_assignments:
            for entity, priority in assignment.items():
                if entity not in self.get_enabled_entities(all=True):
                    raise ValueError(f"Entity '{entity}' not found in available entities")
                if not isinstance(priority, int) or priority < 1:
                    raise ValueError(f"Priority for entity '{entity}' must be a positive integer")

    
    def _update_priorities(self, new_priorities: Dict[str, int]) -> Dict[str, int]:
        """Update entity recognizers and recognizer priorities"""
        self.entity_recognizers = new_priorities
        for recognizer in self.analyzer_engine.get_recognizers():
            entity = (recognizer.supported_entities[0] 
                     if isinstance(recognizer.supported_entities, list)
                     else recognizer.supported_entities)
            if entity in new_priorities:
                recognizer.priority = new_priorities[entity]
        return self.entity_recognizers


    def redact(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Anonymize detected entities in text
        
        Args:
            text: Input text to anonymize
                
        Returns:
            Tuple containing anonymized text and mapping dictionary
            
        Raises:
            TypeError: If input is not a string
            ValueError: If text is empty or exceeds length limits
            RuntimeError: If mapping limits exceeded
        """
        # Validate input
        text = self._validate_text_for_anonymization(text)
        
        # Check mapping limits before processing
        self._check_mapping_limits()
        
        # Get entities
        entities = self.detect_entities(text)
        result = text
        
        # Process entities in reverse order to handle overlapping matches
        # Sort entities by start position in reverse order
        entities.sort(key=lambda x: x['start'], reverse=True)
        
        # Keep track of already processed spans
        processed_spans = set()
        
        for entity in entities:
            # Create a span tuple for current entity
            current_span = (entity['start'], entity['end'])
            
            # Skip if this span has already been processed
            if any(start <= current_span[0] < end or start < current_span[1] <= end 
                for start, end in processed_spans):
                continue
                
            original_text = entity['text']
            
            if original_text not in self.mappings:
                if self.fuzzy_mapping:
                    existing_replacement = self._get_fuzzy_match(original_text)
                    if existing_replacement:
                        self.mappings[original_text] = existing_replacement
                        replacement = existing_replacement
                    else:
                        replacement = self._generate_replacement(entity['type'], original_text)
                        self.mappings[original_text] = replacement
                else:
                    replacement = self._generate_replacement(entity['type'], original_text)
                    self.mappings[original_text] = replacement
            else:
                replacement = self.mappings[original_text]

            # Apply the replacement
            result = result[:entity['start']] + replacement + result[entity['end']:]
            
            # Add this span to processed spans
            processed_spans.add(current_span)

        return result, self.mappings
    

    def _generate_replacement(self, entity_type: str, original_text: str) -> str:
        """
        Generate replacement text for entity
        
        Args:
            entity_type: Type of entity to generate replacement for
            original_text: Original text being replaced
                
        Returns:
            Generated replacement text
        """
        if entity_type not in self.counter:
            self.counter[entity_type] = 0
        self.counter[entity_type] += 1
        return f"{entity_type}_{self.counter[entity_type]}"


    def restore(self, text: str, mappings: Optional[Dict[str, str]] = None) -> str:
        """
        Restore original text from anonymized version
        
        Args:
            text: Anonymized text to restore
            mappings: Optional mapping dictionary to use for restoration
            
        Returns:
            Restored original text
        """

        if not mappings:
            return text
        
        mappings = mappings or self.mappings
        result = text
        
        # Sort mappings by length of replacement text (longest first)
        # This prevents partial replacements of longer strings
        sorted_mappings = sorted(
            mappings.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )
        
        for original, replacement in sorted_mappings:
            result = result.replace(replacement, original)
            
        return result