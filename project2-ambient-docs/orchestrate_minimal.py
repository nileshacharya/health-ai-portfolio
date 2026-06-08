#!/usr/bin/env python3
"""
MINIMAL IMPLEMENTATION: Orchestrate SOAP Generation + Source Attribution

Simple wrapper that combines both APIs for POC use.
No database integration, just core functionality.

Usage:
    from orchestrate_minimal import generate_soap_with_attribution
    
    result = generate_soap_with_attribution("patient conversation text")
    print(result['data']['soap_note'])
    print(result['data']['attributions'])
"""

import logging
from datetime import datetime
from typing import Dict, Optional

# Import the two existing APIs
from generate_soap_note import get_soap_note
from attribute_sources_PRODUCTION import attribute_sources

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ORCHESTRATION API - MINIMAL
# ============================================================================

def generate_soap_with_attribution(
    conversation: str
) -> Dict:
    """
    Unified API: Generate SOAP note + attribute sources in one call.
    
    This is the minimal version - just orchestrates existing APIs with
    no database integration. Perfect for POC and testing.
    
    Args:
        conversation (str): Patient-clinician conversation text
        
    Returns:
        dict: {
            'success': bool,
            'data': {
                'soap_note': str,
                'attributions': [...],
                'statistics': {...}
            },
            'error': str or None,
            'timestamp': str
        }
        
    Example:
        >>> conversation = "PATIENT: I have fever. CLINICIAN: How long?"
        >>> result = generate_soap_with_attribution(conversation)
        >>> if result['success']:
        ...     print(result['data']['soap_note'])
        ...     for attr in result['data']['attributions']:
        ...         print(f"{attr['soap_text']} ← {attr['source_text']}")
    """
    
    # Input validation
    if not conversation or not isinstance(conversation, str):
        logger.error("Invalid conversation input")
        return {
            'success': False,
            'data': None,
            'error': 'Conversation must be non-empty string',
            'timestamp': datetime.now().isoformat()
        }
    
    try:
        logger.info(f"Starting SOAP generation + attribution (conv_length={len(conversation)})")
        
        # Step 1: Generate SOAP note
        logger.info("→ Generating SOAP note...")
        soap_result = get_soap_note(conversation)
        
        if not soap_result['success']:
            
            logger.error(f"SOAP generation failed: {soap_result['error']}")
            return {
                'success': False,
                'data': None,
                'error': f'SOAP generation failed: {soap_result["error"]}',
                'timestamp': datetime.now().isoformat()
            }
        
        soap_note = soap_result['soap_note']
        logger.info(f"✓ SOAP generated ({len(soap_note)} chars)")
        
        # Step 2: Generate attributions
        logger.info("→ Generating attributions...")
        attr_result = attribute_sources(
            soap_note=soap_note,
            conversation=conversation
        )
        
        if not attr_result['success']:
            logger.error(f"Attribution failed: {attr_result['error']}")
            return {
                'success': False,
                'data': None,
                'error': f'Attribution failed: {attr_result["error"]}',
                'timestamp': datetime.now().isoformat()
            }
        
        logger.info(f"✓ Attributions generated ({attr_result['data']['statistics']['total_entities']} entities)")
        
        # Step 3: Combine results
        result = {
            'success': True,
            'data': {
                'soap_note': soap_note,
                'attributions': attr_result['data']['attributions'],
                'statistics': attr_result['data']['statistics'],
                'quality_assessment': {
                    'soap_quality': 'good',  # Can add SOAP quality scoring later
                    'attribution_quality': attr_result['data']['statistics']['quality_score'],
                    'overall_quality': attr_result['data']['statistics']['quality_score']
                }
            },
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("✓ SOAP generation + attribution complete")
        return result
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': f'Unexpected error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# EXAMPLE USAGE & TESTING
# ============================================================================

def example_usage():
    """Example of how to use the orchestrated API"""
    
    # Example conversation
    conversation = """
    PATIENT: I've been having a cough for about a week. It's pretty bad, 
    and I'm coughing up some yellow stuff.
    
    CLINICIAN: How long have you had the fever?
    
    PATIENT: The fever started about 3 days ago. It usually goes up to 
    around 101 or 102 degrees.
    
    CLINICIAN: Any chest pain or shortness of breath?
    
    PATIENT: My chest feels a little tight when I cough hard, but nothing 
    severe. I do get a bit short of breath when I climb stairs.
    
    CLINICIAN: Let me examine you and we'll get a chest X-ray.
    [Examination and stethoscope findings]
    
    CLINICIAN: Your lungs sound a bit rough, especially on the right side. 
    The X-ray shows some infiltrates. You likely have pneumonia.
    """
    
    print("=" * 70)
    print("EXAMPLE: SOAP GENERATION + SOURCE ATTRIBUTION")
    print("=" * 70)
    print(f"\nInput Conversation ({len(conversation)} chars):")
    print("-" * 70)
    print(conversation[:200] + "...")
    print("-" * 70)
    
    # Call orchestrated API
    result = generate_soap_with_attribution(conversation)
    
    if result['success']:
        print("\n✓ SUCCESS\n")
        
        # Show SOAP note
        print("GENERATED SOAP NOTE:")
        print("-" * 70)
        print(result['data']['soap_note'])
        print("-" * 70)
        
        # Show statistics
        stats = result['data']['statistics']
        print(f"\nSTATISTICS:")
        print(f"  Total entities: {stats['total_entities']}")
        print(f"  Attributed: {stats['entities_attributed']}")
        print(f"  Hallucinations: {stats['hallucination_count']}")
        print(f"  Coverage: {stats['attribution_coverage']:.1%}")
        print(f"  Quality: {stats['quality_score'].upper()}")
        
        # Show attributions
        print(f"\nATTRIBUTIONS ({stats['total_entities']} total):")
        print("-" * 70)
        for attr in result['data']['attributions'][:5]:  # First 5
            status = "⚠" if attr['is_hallucination'] else "✓"
            if attr['source_text'] :  
                print(f"{status} {attr['soap_text']:<20} → {attr['source_text'][:40]}")
                print(f"   confidence: {attr['confidence']:.2f}, hallucination: {attr['is_hallucination']}")
            else:
                print(f"{status} {attr['soap_text']:<20} → NO Match")
                print(f"   confidence: {attr['confidence']:.2f}, hallucination: {attr['is_hallucination']}")
               
        
        if len(result['data']['attributions']) > 5:
            print(f"... and {len(result['data']['attributions']) - 5} more")
    
    else:
        print(f"\n✗ FAILED: {result['error']}")


if __name__ == "__main__":
    # Run example
    example_usage()
