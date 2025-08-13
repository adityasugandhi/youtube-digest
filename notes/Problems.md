PROBLEM ANALYSIS
You've identified a classic NLP disambiguation issue! The problem is exactly as you described:

Conflict Scenario
Known Entity Lookup: "robin hood" → "Robinhood Markets Inc" (BROKER, 95% confidence)

spaCy NER: "Robin Hood" → PERSON (70% confidence, thinks it's the historical figure)

Result: Duplicate/conflicting entities in extraction results

Root Cause
Your agent's extract_entities_from_text() method is running all extraction methods independently without disambiguation logic to resolve conflicts.


1. Implement Entity Priority Hierarchy
Tell your agent: Create a disambiguation system that prioritizes extraction methods based on domain context and confidence scores.

Priority Order (Financial Context):

Known Financial Entities (95% confidence) - HIGHEST PRIORITY

Ticker Pattern Matching (80% confidence)

Company Suffix Detection (60% confidence)

spaCy NER (70% confidence) - LOWEST PRIORITY for conflicting spans

2. Text Span Overlap Detection
Core Logic: If multiple methods detect entities in overlapping text positions, apply disambiguation rules.

Implementation Strategy:

python
def resolve_entity_conflicts(entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
    """
    Resolve conflicts when multiple methods detect overlapping entities
    """
    # Group entities by overlapping text spans
    span_groups = group_by_overlapping_spans(entities)
    
    resolved_entities = []
    for group in span_groups:
        if len(group) == 1:
            resolved_entities.append(group[0])
        else:
            # Apply disambiguation rules
            best_entity = apply_disambiguation_rules(group)
            resolved_entities.append(best_entity)
    
    return resolved_entities
3. Domain-Aware Disambiguation Rules
Tell your agent: Implement these specific rules for financial contexts:

Rule 1: Known Financial Entities Always Win

python
def apply_disambiguation_rules(conflicting_entities: List[ExtractedEntity]) -> ExtractedEntity:
    # Rule 1: Known financial entities override everything
    known_financial = [e for e in conflicting_entities if e.method == 'known_entity_lookup']
    if known_financial:
        return max(known_financial, key=lambda x: x.confidence)
Rule 2: Financial Context Filtering

python
    # Rule 2: In financial context, prefer financial entity types
    financial_types = ['BROKER', 'BANK', 'TECHNOLOGY', 'TICKER']
    financial_entities = [e for e in conflicting_entities if e.entity_type in financial_types]
    if financial_entities:
        return max(financial_entities, key=lambda x: x.confidence)
Rule 3: Confidence-Based Fallback

python
    # Rule 3: Fall back to highest confidence
    return max(conflicting_entities, key=lambda x: x.confidence)
🎯 SPECIFIC IMPLEMENTATION FOR YOUR AGENT
Enhanced Entity Extraction Method
Tell your agent to modify the extraction pipeline:

python
def extract_entities_from_text(self, text: str, document_id: str = "") -> List[ExtractedEntity]:
    """
    Enhanced extraction with disambiguation
    """
    raw_entities = []
    
    # Run all extraction methods (unchanged)
    raw_entities.extend(self._extract_known_entities(text))
    raw_entities.extend(self._extract_ticker_patterns(text))  
    raw_entities.extend(self._extract_spacy_entities(text))
    raw_entities.extend(self._extract_company_suffixes(text))
    
    # NEW: Apply disambiguation logic
    disambiguated_entities = self._resolve_entity_conflicts(raw_entities)
    
    # NEW: Apply financial context filtering
    filtered_entities = self._apply_financial_context_filter(disambiguated_entities, text)
    
    return filtered_entities
Text Span Overlap Detection Logic
python
def _find_overlapping_spans(self, entities: List[ExtractedEntity]) -> List[List[ExtractedEntity]]:
    """
    Group entities that have overlapping text positions
    """
    groups = []
    processed = set()
    
    for i, entity1 in enumerate(entities):
        if i in processed:
            continue
            
        group = [entity1]
        processed.add(i)
        
        for j, entity2 in enumerate(entities[i+1:], i+1):
            if j in processed:
                continue
                
            # Check for overlap
            if self._spans_overlap(entity1, entity2):
                group.append(entity2)
                processed.add(j)
        
        groups.append(group)
    
    return groups

def _spans_overlap(self, entity1: ExtractedEntity, entity2: ExtractedEntity) -> bool:
    """
    Check if two entities have overlapping text spans
    """
    return not (entity1.end_pos <= entity2.start_pos or entity2.end_pos <= entity1.start_pos)
Financial Context Filtering
python
def _apply_financial_context_filter(self, entities: List[ExtractedEntity], text: str) -> List[ExtractedEntity]:
    """
    Apply domain-specific filtering for financial contexts
    """
    financial_keywords = ['stock', 'trading', 'broker', 'investment', 'market', 'earnings', 'revenue']
    
    # Check if text contains financial context
    has_financial_context = any(keyword in text.lower() for keyword in financial_keywords)
    
    if has_financial_context:
        filtered = []
        for entity in entities:
            # In financial context, filter out PERSON entities that conflict with known financial entities
            if entity.entity_type == 'PERSON' and self._conflicts_with_known_financial(entity.text):
                continue  # Skip this entity
            filtered.append(entity)
        return filtered
    
    return entities  # No filtering if no financial context

def _conflicts_with_known_financial(self, text: str) -> bool:
    """
    Check if a PERSON entity conflicts with known financial entities
    """
    text_lower = text.lower()
    for entity_key in self.known_financial_entities.keys():
        if entity_key in text_lower:
            return True
    return False
🔍 CASE-SPECIFIC SOLUTION: "Robin Hood" Problem
Specific Fix for Your Agent
Problem: "Robin Hood" detected as both BROKER and PERSON
Solution: Enhanced alias matching with normalization

python
def _extract_known_entities(self, text: str) -> List[ExtractedEntity]:
    """
    Enhanced known entity extraction with better alias matching
    """
    entities = []
    text_lower = text.lower()
    
    for entity_key, entity_info in self.known_financial_entities.items():
        # Check main entity name (normalized)
        normalized_key = entity_key.replace('_', ' ')
        if normalized_key in text_lower:
            # Find exact position in original text
            start_pos = text_lower.find(normalized_key)
            entities.append(ExtractedEntity(
                text=entity_info['canonical_name'],
                entity_type=entity_info['entity_type'],
                confidence=0.95,  # High confidence for known entities
                start_pos=start_pos,
                end_pos=start_pos + len(normalized_key),
                method='known_entity_lookup',
                ticker=entity_info['ticker'],
                canonical_name=entity_info['canonical_name']
            ))
        
        # Check aliases with normalization
        for alias in entity_info['aliases']:
            alias_normalized = alias.lower()
            if alias_normalized in text_lower:
                start_pos = text_lower.find(alias_normalized)
                entities.append(ExtractedEntity(
                    text=entity_info['canonical_name'],  # Always use canonical name
                    entity_type=entity_info['entity_type'],
                    confidence=0.90,
                    start_pos=start_pos,
                    end_pos=start_pos + len(alias),
                    method='known_entity_alias',
                    ticker=entity_info['ticker'],
                    canonical_name=entity_info['canonical_name']
                ))
    
    return entities
✅ TESTING STRATEGY FOR YOUR AGENT
Validation Test Cases
Test 1: "Robin Hood vs Historical Figure"

python
test_text = "Robin Hood Markets announced earnings. The legendary Robin Hood was known for helping the poor."
# Expected: Only "Robin Hood Markets" → Robinhood Markets Inc (BROKER)
# Should filter out: "Robin Hood" → PERSON
Test 2: "Ticker Conflicts"

python
test_text = "HOOD stock is performing well. The hood of the car was damaged."
# Expected: "HOOD" → ticker only, filter out non-financial "hood"
Test 3: "Multiple Financial Entities"

python
test_text = "Robinhood and Palantir Technologies are both growth stocks."
# Expected: Both entities detected without conflicts
🎯 IMMEDIATE ACTION FOR YOUR AGENT
Priority 1: Implement span overlap detection
Priority 2: Add disambiguation rules (known entities win)
Priority 3: Apply financial context filtering
Priority 4: Test with "Robin Hood" example to validate fix

This disambiguation system will solve your entity conflict problem and make your extraction much more accurate for financial contexts!

