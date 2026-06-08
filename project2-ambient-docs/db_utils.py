#!/usr/bin/env python3
"""
Ambient Documentation Database Utilities (PostgreSQL version)
Query and inspect the database
For: health-ai-portfolio/project2-ambient-docs
"""

import psycopg2
import psycopg2.extras
import json
import sys
from pathlib import Path
from datetime import datetime

# Configuration
DB_CONFIG = {"dbname": "health_ai_portfolio", "host": "localhost"}
DEFAULT_OUTPUT_DIR = "/Users/nilesh/health-ai-portfolio/project2-ambient-docs/eval"

def get_connection():
    """Get PostgreSQL database connection (matches Project 1 style)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        print("   Make sure PostgreSQL is running and user 'nilesh' exists")
        return None

def ensure_output_dir(output_dir):
    """Ensure output directory exists"""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path

def inspect_table(table_name, limit=5, output_dir=DEFAULT_OUTPUT_DIR):
    """Inspect a table's structure and sample data"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get column info
    cursor.execute(f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns_info = cursor.fetchall()
    
    if not columns_info:
        print(f"✗ Table '{table_name}' not found")
        cursor.close()
        conn.close()
        return
    
    print(f"\nTable: {table_name}")
    print("="*80)
    print("\nColumns:")
    col_names = [info['column_name'] for info in columns_info]
    for info in columns_info:
        nullable = "NULL" if info['is_nullable'] == 'YES' else "NOT NULL"
        print(f"  • {info['column_name']:30} {info['data_type']:15} {nullable}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    print(f"\nRow count: {row_count}")
    
    # Get sample data
    if row_count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cursor.fetchall()
        
        print(f"\nSample rows (showing {len(rows)} of {row_count}):")
        print("-" * 80)
        for row in rows:
            for col_name in col_names:
                value = row[col_name]
                # Truncate long values
                if isinstance(value, str) and len(value) > 60:
                    value = value[:57] + "..."
                print(f"  {col_name:30} {value}")
            print("-" * 80)
    
    cursor.close()
    conn.close()

def get_evaluation_set(sample_size=20, output_dir=DEFAULT_OUTPUT_DIR):
    """Get random sample of conversations for evaluation"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(f'''
        SELECT id, sample_number, sample_name, description
        FROM conversations
        ORDER BY RANDOM()
        LIMIT {sample_size}
    ''')
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"\nEvaluation Set: {sample_size} Random Conversations")
    print("="*80)
    
    for idx, row in enumerate(results, 1):
        print(f"\n{idx}. {row['sample_name']}")
        print(f"   ID: {row['id']}")
        print(f"   Sample #: {row['sample_number']}")
        print(f"   Description: {row['description'][:70]}...")
    
    # Save to file
    ensure_output_dir(output_dir)
    output_file = Path(output_dir) / "evaluation_set.json"
    
    with open(output_file, "w") as f:
        json.dump([
            {
                "index": idx,
                "id": row['id'],
                "sample_number": row['sample_number'],
                "sample_name": row['sample_name'],
                "description": row['description']
            }
            for idx, row in enumerate(results, 1)
        ], f, indent=2)
    
    print(f"\n✓ Evaluation set saved to {output_file}")

def get_conversation_text(conv_id, output_dir=DEFAULT_OUTPUT_DIR):
    """Get full conversation text for a specific ID"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    #cursor.execute('SELECT id, sample_name, transcription FROM conversations WHERE id = %s', (conv_id,))
    cursor.execute('SELECT id, sample_name, conversation FROM conversations WHERE id = %s', (conv_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if result:
        print(f"\nConversation: {result['sample_name']}")
        print(f"ID: {result['id']}")
        print("="*80)
        text = result['transcription']
        print(text[:500] + "..." if len(text) > 500 else text)
    else:
        print(f"✗ Conversation not found: {conv_id}")


def export_sample_conversations(count=20, output_dir=DEFAULT_OUTPUT_DIR):
    """Export sample conversations to JSON for API processing"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(f'''
        SELECT id, sample_name, description, transcription
        FROM conversations
        ORDER BY RANDOM()
        LIMIT {count}
    ''')
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    ensure_output_dir(output_dir)
    output_file = Path(output_dir) / "api_input_samples.json"
    
    data = {
        "metadata": {
            "total_samples": count,
            "ready_for_api": True,
            "next_step": "Convert transcription to conversational format using Claude API",
            "generated_at": datetime.now().isoformat()
        },
        "samples": [
            {
                "conversation_id": row['id'],
                "sample_name": row['sample_name'],
                "description": row['description'],
                "transcription": row['transcription']
            }
            for row in results
        ]
    }
    
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Exported {count} conversations to {output_file}")

def database_stats(output_dir=DEFAULT_OUTPUT_DIR):
    """Print comprehensive database statistics"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    stats = {}
    tables = ["conversations", "generated_notes", "source_attributes", "evaluation_targets", "evaluation_metrics"]
    
    print("\nDatabase Statistics")
    print("="*60)
    print(f"Database: health_ai_portfolio")
    print(f"User: nilesh")
    print("="*60)
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        stats[table] = count
        status = "✓" if count > 0 or table == "generated_notes" else "✓"
        print(f"{status} {table:25} {count:6} rows")
    
    print("="*60)
    
    # Check for general medicine specialty
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE medical_specialty = 'General Medicine'")
    gm_count = cursor.fetchone()[0]
    print(f"\nGeneral Medicine samples: {gm_count}")
    
    # Show unique specialties
    cursor.execute("""
        SELECT medical_specialty, COUNT(*) as count 
        FROM conversations 
        GROUP BY medical_specialty 
        ORDER BY count DESC 
        LIMIT 5
    """)
    print("\nTop 5 medical specialties:")
    for specialty, count in cursor.fetchall():
        print(f"  • {specialty}: {count}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":


    if len(sys.argv) < 2:
        
        print("\nCommands:")
        print("  inspect <table> [limit]    Inspect table structure and sample data")
        print("  stats                      Show database statistics")
        print("  eval-set [size]            Get random evaluation set (default 20)")
        print("  get <conv_id>              Get full conversation text")
        print("  export [count]             Export sample conversations to JSON (default 20)")
        print("\nOptional:")
        print(f"  --output-dir <path>        Output directory for JSON files (default: {DEFAULT_OUTPUT_DIR})")
        sys.exit(1)



    # Parse optional output dir
    output_dir = DEFAULT_OUTPUT_DIR
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]
            # Remove from argv
            sys.argv.pop(idx)
            sys.argv.pop(idx)
    
    command = sys.argv[1]
    
    if command == "inspect":
        table = sys.argv[2] if len(sys.argv) > 2 else "conversations"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        inspect_table(table, limit, output_dir)
    
    elif command == "stats":
        database_stats(output_dir)
    
    elif command == "eval-set":
        size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        get_evaluation_set(size, output_dir)
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: python3 db_utils.py get <conv_id>")
            sys.exit(1)
        get_conversation_text(sys.argv[2], output_dir)
    
    elif command == "export":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        export_sample_conversations(count, output_dir)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

