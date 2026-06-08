#!/usr/bin/env python3
"""
Ambient Documentation Database Setup Script
PostgreSQL version - creates schema and loads MTSamples data
For: health-ai-portfolio/project2-ambient-docs
"""

import psycopg2
import psycopg2.extras
import csv
import random
import string
from datetime import datetime
from pathlib import Path
import sys

# Configuration
DB_CONFIG = {"dbname": "health_ai_portfolio", "host": "localhost"}
MTSAMPLES_CSV = "/Users/nilesh/health-ai-portfolio/data/mtsamples/MTSamples.csv"
GENERAL_MEDICINE_FILTER = True
SAMPLE_LIMIT = None


def generate_id():
    """Generate a unique ID (random alphanumeric string)"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def get_connection():
    """Get PostgreSQL database connection (matches Project 1 style)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        print("   Make sure PostgreSQL is running and user 'nilesh' exists")
        sys.exit(1)

def table_exists(conn, table_name):
    """Check if table exists in database"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = %s
        )
    """, (table_name,))
    exists = cursor.fetchone()[0]
    cursor.close()
    return exists

def create_schema(conn):
    """Create all tables in the database (idempotent)"""
    cursor = conn.cursor()
    
    # TABLE 1: conversations
    if not table_exists(conn, 'conversations'):
        cursor.execute('''
            CREATE TABLE conversations (
                id VARCHAR(12) PRIMARY KEY,
                medical_specialty TEXT,
                sample_name TEXT,
                description TEXT,
                transcription TEXT,
                keywords TEXT,
                conversation TEXT,
                sample_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: conversations")
    else:
        print("✓ Table exists: conversations (skipped)")
    
    # TABLE 2: generated_notes
    if not table_exists(conn, 'generated_notes'):
        cursor.execute('''
            CREATE TABLE generated_notes (
                id VARCHAR(12) PRIMARY KEY,
                conversation_id VARCHAR(12) NOT NULL,
                format VARCHAR(50) DEFAULT 'SOAP',
                date_generated TIMESTAMP,
                generated_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        print("✓ Created table: generated_notes")
    else:
        print("✓ Table exists: generated_notes (skipped)")
    
    # TABLE 3: source_attributes
    if not table_exists(conn, 'source_attributes'):
        cursor.execute('''
            CREATE TABLE source_attributes (
                id VARCHAR(12) PRIMARY KEY,
                generated_note_id VARCHAR(12) NOT NULL,
                soap_section VARCHAR(50),
                generated_text TEXT,
                entity_type VARCHAR(50),
                entity_value TEXT,
                source_conversation_id VARCHAR(12) NOT NULL,
                source_line_number INTEGER,
                source_text_span TEXT,
                confidence FLOAT,
                is_hallucination BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (generated_note_id) REFERENCES generated_notes(id),
                FOREIGN KEY (source_conversation_id) REFERENCES conversations(id)
            )
        ''')
        print("✓ Created table: source_attributes")
    else:
        print("✓ Table exists: source_attributes (skipped)")
    
    # TABLE 4: evaluation_targets
    if not table_exists(conn, 'evaluation_targets'):
        cursor.execute('''
            CREATE TABLE evaluation_targets (
                metric_name VARCHAR(100) PRIMARY KEY,
                target_value FLOAT NOT NULL,
                metric_type VARCHAR(100),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Created table: evaluation_targets")
    else:
        print("✓ Table exists: evaluation_targets (skipped)")
    
    # TABLE 5: evaluation_metrics
    if not table_exists(conn, 'evaluation_metrics'):
        cursor.execute('''
            CREATE TABLE evaluation_metrics (
                id VARCHAR(12) PRIMARY KEY,
                generated_note_id VARCHAR(12) NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                actual_value FLOAT,
                evaluation_notes TEXT,
                last_evaluated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (generated_note_id) REFERENCES generated_notes(id),
                FOREIGN KEY (metric_name) REFERENCES evaluation_targets(metric_name)
            )
        ''')
        print("✓ Created table: evaluation_metrics")
    else:
        print("✓ Table exists: evaluation_metrics (skipped)")
    
    conn.commit()
    cursor.close()
    print("✓ Database schema ready")

def load_evaluation_targets(conn):
    """Load default evaluation targets (one-time setup, idempotent)"""
    cursor = conn.cursor()
    
    targets = [
        ("diagnosis_precision", 0.80, "entity_extraction", "Precision of diagnosis extraction using scispaCy"),
        ("medication_recall", 0.80, "entity_extraction", "Recall of medication extraction"),
        ("hallucination_rate", 0.05, "data_quality", "Max acceptable hallucination rate"),
        ("completeness", 0.90, "data_quality", "All SOAP sections present and populated"),
        ("source_attribution", 1.00, "source_attribution", "100% of claims should be linked to source"),
    ]
    
    # Check how many targets already exist
    cursor.execute('SELECT COUNT(*) FROM evaluation_targets')
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"✓ Evaluation targets already loaded ({existing_count} rows, skipped)")
        cursor.close()
        return
    
    # Insert targets using ON CONFLICT to skip if they exist
    for metric_name, target_value, metric_type, description in targets:
        cursor.execute('''
            INSERT INTO evaluation_targets 
            (metric_name, target_value, metric_type, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (metric_name) DO NOTHING
        ''', (metric_name, target_value, metric_type, description))
    
    conn.commit()
    print(f"✓ Loaded {len(targets)} evaluation targets")
    cursor.close()

def load_mtsamples(conn):
    """Load MTSamples data into conversations table (idempotent)"""
    cursor = conn.cursor()
    
    if not Path(MTSAMPLES_CSV).exists():
        print(f"✗ MTSamples CSV not found at {MTSAMPLES_CSV}")
        return 0
    
    # Check how many conversations already exist
    cursor.execute('SELECT COUNT(*) FROM conversations')
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"✓ Conversations already loaded ({existing_count} rows, skipped)")
        cursor.close()
        return existing_count
    
    loaded_count = 0
    skipped_count = 0
    
    with open(MTSAMPLES_CSV, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # Filter by medical specialty if enabled
                if GENERAL_MEDICINE_FILTER:
                    if row.get('medical_specialty', '').strip() != 'General Medicine':
                        skipped_count += 1
                        continue
                
                # Limit samples if specified
                if SAMPLE_LIMIT and loaded_count >= SAMPLE_LIMIT:
                    break
                
                # Extract and clean data
                reference = row.get('reference', '').strip()
                sample_number = int(reference) if reference.isdigit() else None
                medical_specialty = row.get('medical_specialty', '').strip()
                sample_name = row.get('sample_name', '').strip()
                description = row.get('description', '').strip()
                transcription = row.get('transcription', '').strip()
                keywords = row.get('keywords', '').strip()
                
                # Generate unique ID
                conv_id = generate_id()
                
                # Insert into conversations table
                cursor.execute('''
                    INSERT INTO conversations 
                    (id, medical_specialty, sample_name, description, transcription, keywords, sample_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (conv_id, medical_specialty, sample_name, description, transcription, keywords, sample_number))
                
                loaded_count += 1
                
                if loaded_count % 50 == 0:
                    print(f"  ... loaded {loaded_count} samples")
            
            except Exception as e:
                print(f"✗ Error loading row {row_num}: {e}")
                skipped_count += 1
                continue
    
    conn.commit()
    print(f"✓ Loaded {loaded_count} conversations from MTSamples")
    print(f"  (Skipped {skipped_count} non-General Medicine samples)")
    
    cursor.close()
    return loaded_count

def get_sample_ids(conn, limit=20):
    """Retrieve sample conversation IDs for evaluation set"""
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(f'''
        SELECT id, sample_name, description 
        FROM conversations 
        ORDER BY RANDOM() 
        LIMIT {limit}
    ''')
    results = cursor.fetchall()
    cursor.close()
    return results

def print_summary(conn):
    """Print database summary statistics"""
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM conversations')
    conv_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM evaluation_targets')
    targets_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM generated_notes')
    notes_count = cursor.fetchone()[0]
    
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)
    print(f"Conversations:       {conv_count}")
    print(f"Generated Notes:     {notes_count}")
    print(f"Evaluation Targets:  {targets_count}")
    print("="*60)
    
    cursor.close()

def main():
    """Main execution"""
    print("Ambient Documentation Database Setup (PostgreSQL)")
    print("="*60)
    print(f"Database: health_ai_portfolio")
    print(f"User: nilesh")
    print(f"Host: localhost")
    print("="*60)
    
    # Create connection
    conn = get_connection()
    
    try:
        # Create schema
        print("\n[1] Checking/creating database schema...")
        create_schema(conn)
        
        # Load evaluation targets
        print("\n[2] Loading evaluation targets...")
        load_evaluation_targets(conn)
        
        # Load MTSamples data
        print("\n[3] Loading MTSamples data...")
        print(f"    Filter: General Medicine only")
        print(f"    Limit: {SAMPLE_LIMIT if SAMPLE_LIMIT else 'All samples'}")
        loaded = load_mtsamples(conn)
        
        # Print summary
        print_summary(conn)
        
        # Show sample evaluation set
        if loaded > 0:
            print("\n[4] Sample evaluation set (random 5 of 20):")
            samples = get_sample_ids(conn, limit=5)
            for idx, row in enumerate(samples, 1):
                print(f"  {idx}. {row['sample_name']}")
                print(f"     ID: {row['id']}")
                print(f"     Desc: {row['description'][:60]}...")
        
        print(f"\n✓ PostgreSQL database ready at {DB_CONFIG['dbname']}")
        print("Ready for API development (Day 2-3)")
        
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()

