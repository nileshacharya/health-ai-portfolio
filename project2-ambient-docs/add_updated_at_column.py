#!/usr/bin/env python3
"""
Add updated_at column to conversations table
Fixes: "column 'updated_at' does not exist" error
"""

import psycopg2
import sys

# Configuration 
DB_CONFIG = {"dbname": "health_ai_portfolio", "host": "localhost"}


def get_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)


def column_exists(conn, table_name, column_name):
    """Check if column exists in table"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        )
    """, (table_name, column_name))
    exists = cursor.fetchone()[0]
    cursor.close()
    return exists


def alter_table(conn):
    """Add updated_at column to conversations table (idempotent)"""
    cursor = conn.cursor()
    
    # Check if column already exists
    if column_exists(conn, 'conversations', 'updated_at'):
        print("✓ Column 'updated_at' already exists in conversations table")
        cursor.close()
        return True
    
    try:
        cursor.execute('''
            ALTER TABLE conversations
            ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ''')
        conn.commit()
        print("✓ Added column 'updated_at' to conversations table")
        cursor.close()
        return True
    
    except psycopg2.Error as e:
        conn.rollback()
        print(f"✗ Error altering table: {e}")
        cursor.close()
        return False


def verify_column(conn):
    """Verify the column was added successfully"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'updated_at'
    """)
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        col_name, col_type, col_default = result
        print(f"✓ Verified: {col_name} ({col_type})")
        print(f"  Default: {col_default}")
        return True
    else:
        print("✗ Column verification failed")
        return False


def main():
    """Main execution"""
    print("Adding updated_at column to conversations table")
    print("="*60)
    
    # Create connection
    conn = get_connection()
    
    try:
        # Alter table
        if alter_table(conn):
            # Verify
            verify_column(conn)
            print("="*60)
            print("✓ Success! updated_at column is ready")
            print("\nYou can now run:")
            print("  python3 convert_transcription_to_conversation.py --limit 5")
            return 0
        else:
            print("="*60)
            print("✗ Failed to add column")
            return 1
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1
    
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
