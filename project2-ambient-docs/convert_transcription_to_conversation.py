#!/usr/bin/env python3
"""
Ambient Documentation - Transcription to Conversation Converter
Converts medical transcriptions to conversational format using Claude API
For: health-ai-portfolio/project2-ambient-docs/Day 2 - Phase 1

This script:
1. Reads transcriptions from the conversations table
2. Uses Claude API to convert to Q&A conversational format
3. Updates the conversation column in PostgreSQL
4. Tracks progress and logs results
"""

import psycopg2
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

# Configuration
DB_CONFIG = {"dbname": "health_ai_portfolio", "host": "localhost"}
LOG_DIR = Path("/Users/nilesh/health-ai-portfolio/project2-ambient-docs/logs")
LOG_DIR.mkdir(exist_ok=True)

# Claude API configuration
client = Anthropic()
MODEL = "claude-opus-4-20250514"
MAX_TOKENS = 1500

# Conversion prompt template
CONVERSION_PROMPT = """You are a medical documentation expert. Convert this clinical transcription into a natural Q&A dialogue between a clinician and patient.

IMPORTANT GUIDELINES:
1. Format as realistic conversation: CLINICIAN: [question/observation], PATIENT: [response], etc.
2. Keep under 500 words
3. Preserve all clinical information from the transcription
4. Use natural, conversational language (not formal documentation)
5. Include vital signs, symptoms, history naturally in dialogue
6. Make it flow like an actual patient encounter

TRANSCRIPTION:
{transcription}

OUTPUT:
Generate the Q&A dialogue below. Start directly with CLINICIAN: (no preamble)."""


class TranscriptionConverter:
    """Convert medical transcriptions to conversational format using Claude API"""
    
    def __init__(self, db_config, log_dir=None):
        self.db_config = db_config
        self.log_dir = log_dir or LOG_DIR
        self.conn = None
        self.log_file = self.log_dir / f"conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.stats = {
            "total_attempted": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
    def log(self, message, level="INFO"):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        with open(self.log_file, "a") as f:
            f.write(log_message + "\n")
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.log("Connected to PostgreSQL database")
            return True
        except psycopg2.Error as e:
            self.log(f"Failed to connect to database: {e}", "ERROR")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.log("Disconnected from database")
    
    def get_unconverted_transcriptions(self, limit=None):
        """Get transcriptions that haven't been converted yet"""
        try:
            cursor = self.conn.cursor()
            
            if limit:
                cursor.execute("""
                    SELECT id, sample_name, transcription
                    FROM conversations
                    WHERE conversation IS NULL OR conversation = ''
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT id, sample_name, transcription
                    FROM conversations
                    WHERE conversation IS NULL OR conversation = ''
                    ORDER BY sample_number ASC
                """)
            
            results = cursor.fetchall()
            cursor.close()
            return results
        
        except psycopg2.Error as e:
            self.log(f"Error fetching unconverted transcriptions: {e}", "ERROR")
            return []
    
    def convert_transcription(self, transcription):
        """Use Claude API to convert transcription to conversation"""
        try:
            prompt = CONVERSION_PROMPT.format(transcription=transcription)
            
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            conversation = message.content[0].text
            return conversation, None
        
        except Exception as e:
            error_msg = f"Claude API error: {str(e)}"
            return None, error_msg
    
    def update_conversation(self, conversation_id, conversation_text):
        """Update conversation column in database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE conversations
                SET conversation = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (conversation_text, conversation_id))
            
            self.conn.commit()
            cursor.close()
            return True
        
        except psycopg2.Error as e:
            self.conn.rollback()
            self.log(f"Database update error: {e}", "ERROR")
            return False
    
    def process_sample(self, conv_id, sample_name, transcription):
        """Process a single transcription"""
        self.stats["total_attempted"] += 1
        
        # Skip very short transcriptions
        if not transcription or len(transcription.strip()) < 50:
            self.log(f"SKIP [{self.stats['total_attempted']}] {sample_name}: Too short", "WARN")
            self.stats["skipped"] += 1
            return False
        
        # Convert using Claude
        self.log(f"[{self.stats['total_attempted']}] Converting: {sample_name}...")
        conversation, error = self.convert_transcription(transcription)
        
        if error:
            self.log(f"  ✗ ERROR: {error}", "ERROR")
            self.stats["failed"] += 1
            self.stats["errors"].append({
                "id": conv_id,
                "sample": sample_name,
                "error": error
            })
            return False
        
        # Validate conversion
        if not conversation or len(conversation.strip()) < 20:
            self.log(f"  ✗ INVALID: Empty or too short conversion", "ERROR")
            self.stats["failed"] += 1
            return False
        
        # Update database
        if self.update_conversation(conv_id, conversation):
            self.log(f"  ✓ SUCCESS: Conversion saved ({len(conversation)} chars)")
            self.stats["successful"] += 1
            return True
        else:
            self.log(f"  ✗ FAILED: Could not save to database", "ERROR")
            self.stats["failed"] += 1
            return False
    
    def process_batch(self, limit=None, sample_ids=None):
        """Process batch of transcriptions"""
        self.log("="*70)
        self.log("Starting Transcription to Conversation Conversion")
        self.log("="*70)
        
        # Get samples to process
        if sample_ids:
            # Process specific sample IDs
            self.log(f"Processing {len(sample_ids)} specified samples...")
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, sample_name, transcription
                FROM conversations
                WHERE id = ANY(%s)
            """, (sample_ids,))
            samples = cursor.fetchall()
            cursor.close()
        else:
            # Process unconverted samples
            samples = self.get_unconverted_transcriptions(limit)
            self.log(f"Found {len(samples)} unconverted transcriptions")
        
        if not samples:
            self.log("No samples to process", "WARN")
            return False
        
        # Process each sample
        for conv_id, sample_name, transcription in samples:
            self.process_sample(conv_id, sample_name, transcription)
        
        # Print summary
        self.print_summary()
        self.save_summary()
        
        return self.stats["successful"] > 0
    
    def print_summary(self):
        """Print processing summary"""
        self.log("="*70)
        self.log("SUMMARY")
        self.log("="*70)
        self.log(f"Total Attempted:  {self.stats['total_attempted']}")
        self.log(f"Successful:       {self.stats['successful']}")
        self.log(f"Failed:           {self.stats['failed']}")
        self.log(f"Skipped:          {self.stats['skipped']}")
        
        if self.stats["failed"] > 0:
            self.log(f"\nErrors ({self.stats['failed']}):")
            for error in self.stats["errors"][:5]:  # Show first 5 errors
                self.log(f"  - {error['sample']}: {error['error']}")
            if len(self.stats["errors"]) > 5:
                self.log(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        self.log("="*70)
    
    def save_summary(self):
        """Save summary to JSON file"""
        summary_file = self.log_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(summary_file, "w") as f:
                json.dump(self.stats, f, indent=2)
            self.log(f"Summary saved to {summary_file}")
        except Exception as e:
            self.log(f"Could not save summary: {e}", "ERROR")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert medical transcriptions to conversational format using Claude API"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of samples to process (default: all unconverted)"
    )
    parser.add_argument(
        "--sample-ids",
        nargs="+",
        help="Process specific sample IDs (space-separated)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from where it left off (default behavior)"
    )
    
    args = parser.parse_args()
    
    # Initialize converter
    converter = TranscriptionConverter(DB_CONFIG)
    
    try:
        # Connect to database
        if not converter.connect():
            sys.exit(1)
        
        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            converter.log("ANTHROPIC_API_KEY environment variable not set", "ERROR")
            converter.log("Set it with: export ANTHROPIC_API_KEY='your-key'", "ERROR")
            sys.exit(1)
        
        # Process batch
        if args.sample_ids:
            success = converter.process_batch(sample_ids=args.sample_ids)
        else:
            success = converter.process_batch(limit=args.limit)
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        converter.log("\nInterrupted by user", "WARN")
        converter.print_summary()
        sys.exit(1)
    
    except Exception as e:
        converter.log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)
    
    finally:
        converter.disconnect()


if __name__ == "__main__":
    main()
