#!/usr/bin/env python3
"""
Evaluation Batch Creator - Categorize & Select 20 Conversations
For: health-ai-portfolio/project2-ambient-docs

Categorizes conversations by complexity:
- SIMPLE (5): Straightforward patient cases, clear presentations
- MODERATE (5): Multiple symptoms/conditions, more clinical reasoning needed
- COMPLEX (5): Multiple comorbidities, complicated presentations
- RARE/EDGE (5): Unusual cases, edge cases, rare presentations

Algorithm:
1. Extract clinical features from transcription/conversation
2. Score complexity based on:
   - Number of unique medical entities (diagnoses, medications, symptoms)
   - Number of comorbidities/chronic conditions
   - Presence of rare/unusual terminology
   - Clinical reasoning complexity
   - Multi-system involvement
3. Categorize into buckets
4. Select diverse examples from each bucket
5. Export as JSON for evaluation
"""

import psycopg2
import psycopg2.extras
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict, Tuple

# Configuration
DB_CONFIG = {"dbname": "health_ai_portfolio", "host": "localhost"}
OUTPUT_DIR = Path("/Users/nilesh/health-ai-portfolio/project2-ambient-docs/eval")
OUTPUT_DIR.mkdir(exist_ok=True)


class ComplexityAnalyzer:
    """Analyze conversation complexity for categorization"""
    
    # Medical terminology patterns
    SYMPTOM_KEYWORDS = {
        'pain', 'ache', 'fever', 'cough', 'shortness of breath', 'dyspnea', 
        'nausea', 'vomiting', 'diarrhea', 'fatigue', 'weakness', 'dizziness',
        'headache', 'chest pain', 'abdominal pain', 'rash', 'itching', 'swelling',
        'bleeding', 'bruising', 'difficulty swallowing', 'hoarseness', 'wheezing',
        'congestion', 'discharge', 'tremor', 'numbness', 'tingling', 'memory loss',
        'confusion', 'anxiety', 'depression', 'sleep disturbance', 'weight loss'
    }
    
    DIAGNOSIS_KEYWORDS = {
        'diabetes', 'hypertension', 'asthma', 'pneumonia', 'bronchitis', 'copd',
        'heart disease', 'coronary', 'myocardial infarction', 'arrhythmia', 'heart failure',
        'stroke', 'cancer', 'leukemia', 'lymphoma', 'arthritis', 'osteoporosis',
        'kidney disease', 'renal', 'liver disease', 'cirrhosis', 'hepatitis',
        'thyroid', 'hyperthyroid', 'hypothyroid', 'anemia', 'infection', 'sepsis',
        'pneumonia', 'bronchitis', 'flu', 'covid', 'tuberculosis', 'hiv', 'aids',
        'depression', 'anxiety', 'schizophrenia', 'bipolar', 'autism', 'adhd',
        'gastroenteritis', 'ulcer', 'ibs', 'crohn\'s', 'colitis', 'migraine'
    }
    
    MEDICATION_KEYWORDS = {
        'aspirin', 'ibuprofen', 'acetaminophen', 'metformin', 'insulin', 'lisinopril',
        'atorvastatin', 'amoxicillin', 'penicillin', 'warfarin', 'heparin', 'morphine',
        'oxycodone', 'hydrocodone', 'lorazepam', 'alprazolam', 'sertraline', 'fluoxetine',
        'omeprazole', 'metoprolol', 'calcium', 'vitamin', 'antibiotic', 'steroid',
        'hormone', 'chemotherapy', 'radiation', 'anticoagulant', 'antihypertensive'
    }
    
    PROCEDURE_KEYWORDS = {
        'x-ray', 'mri', 'ct scan', 'ultrasound', 'endoscopy', 'colonoscopy',
        'surgery', 'operation', 'biopsy', 'aspiration', 'injection', 'catheter',
        'intubation', 'ventilation', 'dialysis', 'transfusion', 'transplant',
        'bypass', 'angioplasty', 'stent', 'ablation', 'radiation', 'chemotherapy'
    }
    
    COMORBIDITY_KEYWORDS = {
        'also', 'additionally', 'history of', 'previous', 'chronic', 'ongoing',
        'has been', 'had', 'multiple', 'several', 'various', 'associated with',
        'comorbid', 'comorbidities', 'and', 'plus', 'as well as'
    }
    
    # Rare/unusual terminology
    RARE_KEYWORDS = {
        'rare', 'unusual', 'atypical', 'paradoxical', 'unexpected', 'peculiar',
        'syndrome', 'disease', 'condition', 'manifestation', 'presentation',
        'zebra', 'edge case', 'complicated', 'challenging', 'difficult'
    }
    
    def __init__(self):
        self.text_cache = {}
    
    def count_entities(self, text: str, keywords: set) -> int:
        """Count occurrences of keyword set in text"""
        if not text:
            return 0
        text_lower = text.lower()
        count = 0
        for keyword in keywords:
            # Simple word boundary matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = len(re.findall(pattern, text_lower))
            count += matches
        return count
    
    def extract_features(self, transcription: str, conversation: str) -> Dict:
        """Extract complexity features from conversation"""
        text = f"{transcription} {conversation}".lower() if transcription and conversation else ""
        
        # Count medical entities
        symptom_count = self.count_entities(text, self.SYMPTOM_KEYWORDS)
        diagnosis_count = self.count_entities(text, self.DIAGNOSIS_KEYWORDS)
        medication_count = self.count_entities(text, self.MEDICATION_KEYWORDS)
        procedure_count = self.count_entities(text, self.PROCEDURE_KEYWORDS)
        rare_count = self.count_entities(text, self.RARE_KEYWORDS)
        
        # Detect comorbidities (presence of multiple conditions)
        comorbidity_indicators = self.count_entities(text, self.COMORBIDITY_KEYWORDS)
        estimated_conditions = (diagnosis_count // 2) + 1  # Rough estimate
        
        # Detect multi-system involvement
        systems = set()
        if any(kw in text for kw in ['respiratory', 'lung', 'breath', 'asthma', 'pneumonia', 'bronch']):
            systems.add('respiratory')
        if any(kw in text for kw in ['cardiac', 'heart', 'chest', 'arrhythmia', 'mi', 'cad']):
            systems.add('cardiac')
        if any(kw in text for kw in ['neuro', 'brain', 'seizure', 'stroke', 'head', 'nerve']):
            systems.add('neurological')
        if any(kw in text for kw in ['gastro', 'abdominal', 'gi', 'digestive', 'stomach']):
            systems.add('gastrointestinal')
        if any(kw in text for kw in ['kidney', 'renal', 'urinary', 'bladder']):
            systems.add('renal')
        if any(kw in text for kw in ['mental', 'psychiatric', 'psychological', 'mood', 'depression', 'anxiety']):
            systems.add('psychiatric')
        if any(kw in text for kw in ['endocrine', 'diabetes', 'thyroid', 'hormone']):
            systems.add('endocrine')
        if any(kw in text for kw in ['hematology', 'blood', 'anemia', 'clot']):
            systems.add('hematologic')
        
        # Text complexity metrics
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        return {
            'symptom_count': symptom_count,
            'diagnosis_count': diagnosis_count,
            'medication_count': medication_count,
            'procedure_count': procedure_count,
            'rare_count': rare_count,
            'comorbidity_indicators': comorbidity_indicators,
            'estimated_conditions': estimated_conditions,
            'system_count': len(systems),
            'systems': list(systems),
            'word_count': word_count,
            'avg_sentence_length': avg_sentence_length,
            'total_entities': symptom_count + diagnosis_count + medication_count + procedure_count
        }
    
    def calculate_complexity_score(self, features: Dict) -> float:
        """Calculate overall complexity score (0-100)
        
        ADJUSTED SCORING for better distribution:
        - Lower weights for medication & symptoms
        - Higher emphasis on diagnosis count
        - Multi-system heavily weighted
        """
        score = 0
        
        # Primary factor: Number of diagnoses (main driver of complexity)
        # Each diagnosis adds significant complexity
        score += features['diagnosis_count'] * 8  # No cap - this is the main driver
        
        # Secondary: Medications (treatment burden)
        score += features['medication_count'] * 4  # Reduced weight
        
        # Tertiary: Symptoms (severity indicator)
        score += features['symptom_count'] * 2  # Reduced weight
        
        # Multi-system involvement (strong indicator of true complexity)
        score += features['system_count'] * 12  # High weight
        
        # Comorbidities (presence of multiple ongoing conditions)
        score += features['estimated_conditions'] * 6
        
        # Procedures (diagnostic/therapeutic intensity)
        score += features['procedure_count'] * 3
        
        # Rare/unusual cases (special bonus for edge cases)
        if features['rare_count'] > 0:
            score += min(features['rare_count'] * 15, 20)  # Bonus for rarity
        
        # Normalize to 0-100 with new scaling
        # Max theoretical: 10*8 + 10*4 + 10*2 + 8*12 + 3*6 + 3*3 + 20 = 229
        # Scale down so we get better distribution
        return min(score / 2.5, 100)  # Scale to 0-100 with new weights
    
    def categorize_conversation(self, conv_id: str, sample_name: str, 
                               transcription: str, conversation: str) -> Dict:
        """Categorize a conversation by complexity"""
        features = self.extract_features(transcription, conversation)
        complexity_score = self.calculate_complexity_score(features)
        
        # Categorize based on score and features
        # DRASTICALLY ADJUSTED THRESHOLDS for 57-conversation dataset
        # Goal: Distribute evenly across all 4 categories
        
        # First: Check for RARE/EDGE (overrides everything)
        if features['rare_count'] > 2:
            category = 'RARE/EDGE'
        # For others: Use much tighter thresholds with new scoring
        # New scoring: 0-100 range with better distribution
        elif complexity_score >= 60:
            # COMPLEX: High complexity cases (60+)
            category = 'COMPLEX'
        elif complexity_score >= 40:
            # MODERATE: Medium complexity (40-59)
            category = 'MODERATE'
        else:
            # SIMPLE: Low complexity (0-39)
            category = 'SIMPLE'
        
        return {
            'id': conv_id,
            'sample_name': sample_name,
            'category': category,
            'complexity_score': round(complexity_score, 2),
            'features': features,
            'has_conversation': bool(conversation)
        }


class EvaluationBatchCreator:
    """Create balanced evaluation batch of 20 conversations"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.analyzer = ComplexityAnalyzer()
        self.categorized = {
            'SIMPLE': [],
            'MODERATE': [],
            'COMPLEX': [],
            'RARE/EDGE': []
        }
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            return True
        except psycopg2.Error as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
    
    def get_conversations_with_data(self) -> List[Tuple]:
        """Get all conversations that have been populated"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, sample_name, transcription, conversation
                FROM conversations
                WHERE conversation IS NOT NULL AND conversation != ''
                ORDER BY sample_number ASC
            """)
            results = cursor.fetchall()
            cursor.close()
            return results
        except psycopg2.Error as e:
            print(f"✗ Error querying conversations: {e}")
            return []
    
    def analyze_and_categorize(self, conversations: List[Tuple]) -> Dict:
        """Analyze all conversations and categorize them"""
        print(f"\nAnalyzing {len(conversations)} conversations...")
        
        for conv_id, sample_name, transcription, conversation in conversations:
            categorization = self.analyzer.categorize_conversation(
                conv_id, sample_name, transcription, conversation
            )
            category = categorization['category']
            self.categorized[category].append(categorization)
            
            if len(conversations) > 0 and (len(self.categorized['SIMPLE']) + 
                                           len(self.categorized['MODERATE']) + 
                                           len(self.categorized['COMPLEX']) + 
                                           len(self.categorized['RARE/EDGE'])) % 50 == 0:
                total = (len(self.categorized['SIMPLE']) + 
                        len(self.categorized['MODERATE']) + 
                        len(self.categorized['COMPLEX']) + 
                        len(self.categorized['RARE/EDGE']))
                print(f"  ... analyzed {total} conversations")
        
        return self.categorized
    
    def select_balanced_batch(self) -> List[Dict]:
        """Select exactly 5 from each category using percentile-based approach
        
        This ensures we get exactly 20 samples (5 from each category) regardless
        of the actual distribution of the 57 conversations.
        """
        batch = []
        all_samples = []
        
        print("\nSelecting balanced batch (percentile-based approach):")
        
        # Get all conversations sorted by complexity score
        for category in ['SIMPLE', 'MODERATE', 'COMPLEX', 'RARE/EDGE']:
            all_samples.extend(self.categorized[category])
        
        # Sort all by complexity score
        all_samples_sorted = sorted(all_samples, key=lambda x: x['complexity_score'])
        
        # Strategy: Select samples to represent the full spectrum
        # Divide into 4 quartiles and select 5 from each
        quartiles = {
            'SIMPLE': [],      # Lowest 25% (simplest cases)
            'MODERATE': [],    # 25-50%
            'COMPLEX': [],     # 50-75%
            'RARE/EDGE': []    # Highest 25% (most complex/rare)
        }
        
        total_samples = len(all_samples_sorted)
        q1 = total_samples // 4
        q2 = total_samples // 2
        q3 = (3 * total_samples) // 4
        
        # Assign samples to quartiles
        for idx, sample in enumerate(all_samples_sorted):
            if idx < q1:
                quartiles['SIMPLE'].append(sample)
            elif idx < q2:
                quartiles['MODERATE'].append(sample)
            elif idx < q3:
                quartiles['COMPLEX'].append(sample)
            else:
                quartiles['RARE/EDGE'].append(sample)
        
        # Select 5 from each quartile
        for category in ['SIMPLE', 'MODERATE', 'COMPLEX', 'RARE/EDGE']:
            samples = quartiles[category]
            
            # If we have 5 or more, select 5 evenly spaced
            if len(samples) >= 5:
                step = len(samples) // 5
                selected = [samples[i * step] for i in range(5) if i * step < len(samples)]
            else:
                # If less than 5, take all and note the shortage
                selected = samples
            
            batch.extend(selected)
            print(f"  {category:15} {len(selected):2} samples selected (quartile had {len(samples):2})")
        
        print(f"\nTotal samples selected: {len(batch)}")
        return batch
    
    def create_evaluation_json(self, batch: List[Dict]) -> Dict:
        """Create evaluation JSON structure"""
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_samples": len(batch),
                "categories": {
                    "SIMPLE": 5,
                    "MODERATE": 5,
                    "COMPLEX": 5,
                    "RARE/EDGE": 5
                },
                "description": "Balanced evaluation batch for ambient documentation",
                "evaluation_approach": "5 simple, 5 moderate, 5 complex, 5 rare/edge cases"
            },
            "batch": [
                {
                    "index": idx + 1,
                    "conversation_id": sample['id'],
                    "sample_name": sample['sample_name'],
                    "category": sample['category'],
                    "complexity_score": sample['complexity_score'],
                    "features": {
                        "diagnoses": sample['features']['diagnosis_count'],
                        "symptoms": sample['features']['symptom_count'],
                        "medications": sample['features']['medication_count'],
                        "procedures": sample['features']['procedure_count'],
                        "system_count": sample['features']['system_count'],
                        "systems_involved": sample['features']['systems'],
                        "estimated_conditions": sample['features']['estimated_conditions']
                    }
                }
                for idx, sample in enumerate(batch)
            ]
        }
    
    def create_summary_stats(self) -> Dict:
        """Create summary statistics"""
        return {
            "total_analyzed": sum(len(v) for v in self.categorized.values()),
            "distribution": {
                "SIMPLE": len(self.categorized['SIMPLE']),
                "MODERATE": len(self.categorized['MODERATE']),
                "COMPLEX": len(self.categorized['COMPLEX']),
                "RARE/EDGE": len(self.categorized['RARE/EDGE'])
            }
        }
    
    def save_batch(self, evaluation_json: Dict, filename: str = "evaluation_batch_20.json"):
        """Save evaluation batch to JSON file"""
        output_file = OUTPUT_DIR / filename
        
        try:
            with open(output_file, 'w') as f:
                json.dump(evaluation_json, f, indent=2)
            print(f"\n✓ Evaluation batch saved to {output_file}")
            return True
        except Exception as e:
            print(f"✗ Error saving batch: {e}")
            return False
    
    def print_summary(self):
        """Print categorization summary"""
        print("\n" + "="*70)
        print("CATEGORIZATION SUMMARY")
        print("="*70)
        for category in ['SIMPLE', 'MODERATE', 'COMPLEX', 'RARE/EDGE']:
            count = len(self.categorized[category])
            print(f"{category:15} {count:4} conversations")
            if count > 0:
                scores = [s['complexity_score'] for s in self.categorized[category]]
                print(f"{'':15} Scores: min={min(scores):.1f}, avg={sum(scores)/len(scores):.1f}, max={max(scores):.1f}")
        print("="*70)


def main():
    """Main execution"""
    print("Creating Evaluation Batch - 20 Conversations")
    print("="*70)
    
    creator = EvaluationBatchCreator(DB_CONFIG)
    
    try:
        # Connect
        if not creator.connect():
            sys.exit(1)
        
        # Get conversations
        print("Fetching conversations from database...")
        conversations = creator.get_conversations_with_data()
        
        if not conversations:
            print("✗ No conversations found in database")
            sys.exit(1)
        
        print(f"✓ Found {len(conversations)} conversations with populated data")
        
        # Analyze and categorize
        categorized = creator.analyze_and_categorize(conversations)
        creator.print_summary()
        
        # Check if we have enough for balanced batch
        for category in ['SIMPLE', 'MODERATE', 'COMPLEX', 'RARE/EDGE']:
            if len(categorized[category]) < 5:
                print(f"\n⚠ Warning: Only {len(categorized[category])} {category} samples available (need 5)")
        
        # Select balanced batch
        batch = creator.select_balanced_batch()
        
        # Create JSON
        evaluation_json = creator.create_evaluation_json(batch)
        
        # Save
        if creator.save_batch(evaluation_json):
            print(f"\n✓ Batch created with {len(batch)} samples")
            print(f"  Breakdown: {sum(1 for s in batch if s['category']=='SIMPLE')} simple, " +
                  f"{sum(1 for s in batch if s['category']=='MODERATE')} moderate, " +
                  f"{sum(1 for s in batch if s['category']=='COMPLEX')} complex, " +
                  f"{sum(1 for s in batch if s['category']=='RARE/EDGE')} rare/edge")
            print("\nReady for evaluation phase! Next:")
            print("  1. Review the sample categories in evaluation_batch_20.json")
            print("  2. Start Phase 2: SOAP note generation (Days 2-3 Guide)")
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
    
    finally:
        creator.disconnect()


if __name__ == "__main__":
    main()
