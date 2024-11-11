"""
Builder pattern implementation for creating custom recognizers.
"""

from typing import List, Callable, Tuple, Union, Optional, Dict, Any, Set
from dataclasses import dataclass
import logging
from presidio_analyzer import Pattern, PatternRecognizer, EntityRecognizer
from presidio_analyzer import RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts
import re

from enum import Enum
from typing import List, Callable, Tuple, Union, Optional, Dict, Any, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Redactor

class EntityType(Enum):
    """Standard entity types supported by Redactor."""
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    CREDIT_CARD = "CREDIT_CARD"
    DATE_TIME = "DATE_TIME"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    CUSTOM = "CUSTOM"

class RecognizerLevel(Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"
    COMPLEX = "complex"

@dataclass
class PatternDefinition:
    name: str
    regex: str
    score: float = 0.6
    flags: Optional[int] = None
    case_sensitive: bool = False
    exact_match: bool = False
  
@dataclass
class NlpConfig:
    use_nlp: bool = False
    label_groups: List[Tuple[Set[str], Set[str]]] = None
    artifacts_required: bool = False
    ner_strength: float = 0.85

class RecognizerBuilder:
    _priority_registry: Dict[int, 'RecognizerBuilder'] = {}  # Class variable to track entity priorities

    def __init__(self, entity_name: str, level: RecognizerLevel = RecognizerLevel.SIMPLE, redactor_instance: Optional['Redactor'] = None):
        # Core Identity
        self.entity_name = entity_name
        self.level = level
        self.supported_language = "en"
        self.priority: Optional[int] = None  # None means use Presidio's default confidence-based resolution

        # Pattern Related
        self.patterns: List[PatternDefinition] = []
        self.context_words: List[str] = []
        self.context_window: Optional[int] = None
        self.context_similarity_factor: float = 0.65
        self.deny_list: List[str] = []
        self.allow_list: List[str] = []
        self.replacement_pairs: List[Tuple[str, str]] = []

        # Custom Functions
        self.detection_func: Optional[Callable] = None
        self.validation_func: Optional[Callable] = None
        self.confidence_func: Optional[Callable] = None

        # Scoring & Thresholds
        self.min_score: float = 0.0
        self.max_score: float = 1.0
        self.base_confidence: float = 0.6

        # NLP Configuration
        self.nlp_config = NlpConfig()

        # Reference to the redactor instance
        self.redactor_instance = redactor_instance

        # Internal State
        self._is_pattern_based = True
        self._is_complex = False

    
    def with_pattern(
        self, 
        pattern: str, 
        score: float = 0.6,
        case_sensitive: bool = False,
        exact_match: bool = False
    ) -> 'RecognizerBuilder':
        """
        Add single pattern with enhanced configuration.
        
        Args:
            pattern: Regex pattern string
            score: Confidence score for matches (0.0-1.0)
            case_sensitive: Whether pattern matching should be case-sensitive
            exact_match: Whether pattern should match exactly or allow partial matches
        """
        if exact_match:
            pattern = f"^{pattern}$"
            
        # Instead of using flags, modify the pattern directly
        if not case_sensitive:
            pattern = f"(?i){pattern}"
            
        self.patterns.append(PatternDefinition(
            name=f"pattern_{len(self.patterns)}",
            regex=pattern,
            score=score,
            case_sensitive=case_sensitive,
            exact_match=exact_match
        ))
        return self

    def with_patterns(
        self, 
        patterns: List[Tuple[str, str, float]], 
        case_sensitive: bool = False,
        exact_match: bool = False
    ) -> 'RecognizerBuilder':
        """
        Add multiple patterns with enhanced configuration.
        
        Args:
            patterns: List of (name, regex, score) tuples
            case_sensitive: Whether pattern matching should be case-sensitive
            exact_match: Whether patterns should match exactly
        """
        for name, regex, score in patterns:
            if exact_match:
                regex = f"^{regex}$"
                
            # Instead of using flags, modify the pattern directly    
            if not case_sensitive:
                regex = f"(?i){regex}"
                
            self.patterns.append(PatternDefinition(
                name=name,
                regex=regex,
                score=score,
                case_sensitive=case_sensitive,
                exact_match=exact_match
            ))
        return self
    

    def with_context(
        self, 
        words: List[str], 
        context_window: Optional[int] = None,
        context_similarity_factor: Optional[float] = None
    ) -> 'RecognizerBuilder':
        """
        Add context words with configurable settings.
        
        Args:
            words: List of context words to look for
            context_window: Optional number of words before/after to look for context
            context_similarity_factor: Optional similarity threshold for fuzzy matching (0.0-1.0)
        """
        self.context_words.extend(words)
        
        if context_window is not None:
            if context_window < 1:
                raise ValueError("context_window must be positive")
            self.context_window = context_window
            
        if context_similarity_factor is not None:
            if not 0 <= context_similarity_factor <= 1:
                raise ValueError("context_similarity_factor must be between 0 and 1")
            self.context_similarity_factor = context_similarity_factor
        return self

    def with_deny_list(self, items: List[str]) -> 'RecognizerBuilder':
        """Add deny list items"""
        self.deny_list.extend(items)
        return self

    def with_allow_list(self, items: List[str]) -> 'RecognizerBuilder':
        """Add allow list items"""
        self.allow_list.extend(items)
        return self

    def with_validation(self, func: Callable[[str], bool]) -> 'RecognizerBuilder':
        """Add validation function"""
        self.validation_func = func
        return self

    """
    def with_priority(self, priority: int) -> 'RecognizerBuilder':

        if priority < 1:
            raise ValueError("Priority must be a positive integer")

        if priority in self._priority_registry:
            existing_entity = self._priority_registry[priority]
            logging.info(f"Priority {priority} already assigned to {existing_entity.entity_name}. Swapping priorities.")

            old_priority = existing_entity.priority
            existing_entity.priority = None  
            self.priority = priority
            existing_entity.priority = old_priority

            self._priority_registry[priority] = self
            if old_priority is not None:
                self._priority_registry[old_priority] = existing_entity
        else:
            self.priority = priority
            self._priority_registry[priority] = self

        return self"""

    def with_priority(self, priority: int) -> 'RecognizerBuilder':
        """
        Set priority for entity resolution.
        Priority 1 is the highest, and higher numbers indicate lower priority.
        When a conflict occurs, the new recognizer gets the next available priority.
        
        Args:
            priority: Desired priority level (positive integer)
            
        Returns:
            self for method chaining
            
        Raises:
            ValueError: If priority is not a positive integer
        """
        if priority < 1:
            raise ValueError("Priority must be a positive integer")

        # If priority is already taken
        if priority in self._priority_registry:
            # Find the next available priority
            existing_priorities = sorted(self._priority_registry.keys())
            next_priority = max(existing_priorities) + 1
            
            # Log the priority reassignment
            logging.info(
                f"Priority {priority} already assigned to {self._priority_registry[priority].entity_name}. "
                f"Assigning priority {next_priority} to {self.entity_name}"
            )
            
            # Assign the next available priority
            self.priority = next_priority
            self._priority_registry[next_priority] = self
        else:
            # If priority is available, use it
            self.priority = priority
            self._priority_registry[priority] = self

        return self

    def with_score_threshold(
        self,
        min_score: float = 0.0,
        max_score: float = 1.0
    ) -> 'RecognizerBuilder':
        """
        Set score thresholds for recognition.
        
        Args:
            min_score: Minimum confidence score to include matches (0.0-1.0)
            max_score: Maximum confidence score for matches (0.0-1.0)
        """
        if not 0 <= min_score <= max_score <= 1:
            raise ValueError("Scores must be between 0 and 1, and min_score must be <= max_score")
            
        self.min_score = min_score
        self.max_score = max_score
        return self

    def with_nlp(self, enable: bool = True) -> 'RecognizerBuilder':
        """Enable/disable NLP support"""
        self.nlp_config.use_nlp = enable
        self._is_pattern_based = not enable
        return self

    def with_custom_logic(
        self,
        detection_func: Callable,
        validation_func: Optional[Callable] = None,
        confidence_func: Optional[Callable] = None
    ) -> 'RecognizerBuilder':
        """Add custom detection logic"""
        self.detection_func = detection_func
        self.validation_func = validation_func
        self.confidence_func = confidence_func
        self._is_pattern_based = False
        self._is_complex = True
        return self

    def _validate_configuration(self):
        """Validate the configuration"""
        if not self.entity_name:
            raise ValueError("Entity name is required")

        if self._is_pattern_based and not self.patterns:
            raise ValueError("Pattern-based recognizer requires at least one pattern")

        if self._is_complex and not self.detection_func:
            raise ValueError("Complex recognizer requires detection function")

        if self.min_score < 0 or self.max_score > 1:
            raise ValueError("Score must be between 0 and 1")
    

    def _build_pattern_recognizer(self) -> PatternRecognizer:
        """Build pattern-based recognizer with enhanced configuration"""
        patterns = []
        for p in self.patterns:
            # Create pattern without flags parameter
            pattern = Pattern(
                name=p.name,
                regex=p.regex,
                score=p.score
            )
            patterns.append(pattern)

        recognizer = PatternRecognizer(
            supported_entity=self.entity_name,
            patterns=patterns,
            context=self.context_words,
            supported_language=self.supported_language,
            deny_list=self.deny_list if self.deny_list else None
        )

        # Set additional configuration if specified
        if self.context_window is not None:
            recognizer.context_window = self.context_window
            
        if hasattr(recognizer, "context_similarity_factor") and self.context_similarity_factor is not None:
            recognizer.context_similarity_factor = self.context_similarity_factor

        return recognizer
    

    def _build_custom_recognizer(self) -> EntityRecognizer:
        """Build custom recognizer with enhanced validation and error handling"""
        
        class CustomRecognizer(EntityRecognizer):
            def __init__(self, builder):
                if not isinstance(builder.entity_name, str) or not builder.entity_name:
                    raise ValueError("Entity name must be a non-empty string")
                    
                super().__init__(
                    supported_entities=[builder.entity_name],
                    supported_language=builder.supported_language
                )
                
                if not callable(builder.detection_func):
                    raise TypeError("Detection function must be callable")
                    
                self.detection_func = builder.detection_func
                self.validation_func = builder.validation_func
                self.confidence_func = builder.confidence_func
                self.context = builder.context_words
                self.context_window = builder.context_window
                self.context_similarity_factor = builder.context_similarity_factor
                self.priority = builder.priority
                
                self.min_score = builder.min_score
                self.max_score = builder.max_score

            def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
                if not isinstance(text, str):
                    raise ValueError("Input text must be a string")
                    
                if not text.strip():
                    return []
                    
                try:
                    results = self.detection_func(text)
                except Exception as e:
                    logging.error(f"Detection function failed: {str(e)}")
                    raise RuntimeError(f"Detection function error: {str(e)}")
                    
                if not isinstance(results, list):
                    raise TypeError("Detection function must return a list of RecognizerResult objects")
                    
                validated_results = []
                for idx, result in enumerate(results):
                    try:
                        if not isinstance(result, RecognizerResult):
                            raise TypeError(
                                f"Result at index {idx} must be a RecognizerResult object, "
                                f"got {type(result)}"
                            )
                        
                        if result.entity_type not in self.supported_entities:
                            raise ValueError(
                                f"Entity type '{result.entity_type}' at index {idx} "
                                f"not in supported entities: {self.supported_entities}"
                            )
                        
                        if not (isinstance(result.start, int) and isinstance(result.end, int)):
                            raise TypeError("Start and end positions must be integers")
                            
                        if result.start < 0 or result.end > len(text) or result.start >= result.end:
                            raise ValueError(
                                f"Invalid position indices at index {idx}: "
                                f"start={result.start}, end={result.end}, text_length={len(text)}"
                            )
                        
                        if not isinstance(result.score, (int, float)):
                            raise TypeError(f"Score at index {idx} must be a number")
                            
                        if not (self.min_score <= result.score <= self.max_score):
                            raise ValueError(
                                f"Score {result.score} at index {idx} must be between "
                                f"{self.min_score} and {self.max_score}"
                            )
                        
                        if self.validation_func:
                            match_text = text[result.start:result.end]
                            if not self.validation_func(match_text):
                                continue
                        
                        if self.confidence_func:
                            match_text = text[result.start:result.end]
                            result.score = self.confidence_func(match_text, result.score)
                            
                        validated_results.append(result)
                        
                    except (TypeError, ValueError) as e:
                        logging.warning(f"Skipping invalid result at index {idx}: {str(e)}")
                        continue
                        
                return validated_results

            def validate_result(self, text: str) -> bool:
                if not isinstance(text, str):
                    raise ValueError("Validation text must be a string")
                    
                if self.validation_func:
                    try:
                        return self.validation_func(text)
                    except Exception as e:
                        logging.error(f"Validation function error: {str(e)}")
                        return False
                return True

            def load(self) -> None:
                """Load any required resources."""
                pass

        return CustomRecognizer(self)

    def build(self):
        """Build the final recognizer"""
        self._validate_configuration()

        if self.redactor_instance and self.entity_name in self.redactor_instance.enabled_entities:
            raise ValueError(f"Entity '{self.entity_name}' is already enabled. Please use a different entity name.")

        recognizer = self._build_pattern_recognizer() if self._is_pattern_based else self._build_custom_recognizer()

        if self.priority is not None:
            recognizer.priority = self.priority

        return recognizer