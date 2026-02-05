#!/usr/bin/env python3
"""
Script to apply SQL migrations to Supabase.

Usage:
    python apply_migration.py [migration_number]

Examples:
    python apply_migration.py          # Apply latest migration (010)
    python apply_migration.py 010      # Apply specific migration
    python apply_migration.py 009      # Apply migration 009

Requires:
    - SUPABASE_URL and SUPABASE_SERVICE_KEY in environment or .env file
    - supabase-py package installed
"""

import os
import sys
import argparse
from pathlib import Path

# Try to load from .env file
def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key, value)

load_env()

# Check for required environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    print("Either in environment variables or in .env file")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("Error: supabase-py package not installed")
    print("Install with: pip install supabase")
    sys.exit(1)


def find_migration_file(migration_number: str = None) -> Path:
    """Find migration file by number or return latest."""
    migrations_dir = Path(__file__).parent / 'migrations'
    
    if migration_number:
        # Look for specific migration
        pattern = f"{migration_number}_*.sql"
        matches = list(migrations_dir.glob(pattern))
        if matches:
            return matches[0]
        else:
            print(f"Error: Migration {migration_number} not found in {migrations_dir}")
            sys.exit(1)
    else:
        # Find latest migration (highest number)
        sql_files = [f for f in migrations_dir.glob("*.sql") if f.name[0:3].isdigit()]
        if not sql_files:
            print(f"Error: No migration files found in {migrations_dir}")
            sys.exit(1)
        
        # Sort by migration number
        latest = max(sql_files, key=lambda f: int(f.name[0:3]))
        return latest


def apply_migration(migration_path: Path):
    """Apply the migration SQL file."""
    if not migration_path.exists():
        print(f"Error: Migration file not found: {migration_path}")
        sys.exit(1)
    
    print(f"Reading migration file: {migration_path}")
    with open(migration_path) as f:
        sql = f.read()
    
    print(f"Connecting to Supabase: {SUPABASE_URL}")
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Split SQL into individual statements
    # This is a simple split - for complex migrations consider using a proper SQL parser
    statements = []
    current_statement = []
    in_do_block = False
    
    for line in sql.split('\n'):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('--'):
            continue
        
        # Track DO blocks
        if stripped.upper().startswith('DO'):
            in_do_block = True
        
        current_statement.append(line)
        
        # Check if statement ends
        if in_do_block:
            # End of DO block (END; or END$$;)
            if stripped.upper() in ['END;', 'END$$;', 'END $$;'] or stripped == '$$;':
                statements.append('\n'.join(current_statement))
                current_statement = []
                in_do_block = False
        else:
            # Regular statement ending with semicolon
            if stripped.endswith(';') and not stripped.upper().startswith('DO'):
                statements.append('\n'.join(current_statement))
                current_statement = []
    
    # Add any remaining statement
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    print(f"Found {len(statements)} SQL statements to execute")
    
    # Execute each statement
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for i, statement in enumerate(statements, 1):
        # Skip empty statements
        if not statement.strip():
            continue
        
        # Show first 50 chars of statement for context
        preview = statement.strip()[:50].replace('\n', ' ')
        if len(statement.strip()) > 50:
            preview += "..."
        
        try:
            # Use RPC to execute SQL
            result = supabase.rpc('exec_sql', {'sql': statement}).execute()
            print(f"  [{i}/{len(statements)}] ✓ Success: {preview}")
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            # Check if it's a "relation already exists" or similar non-critical error
            if any(x in error_msg.lower() for x in ['already exists', 'duplicate', 'exists']):
                print(f"  [{i}/{len(statements)}] ℹ Already exists (skipped): {preview}")
                skipped_count += 1
            else:
                print(f"  [{i}/{len(statements)}] ✗ Error: {error_msg[:100]}")
                print(f"      Statement: {preview}")
                error_count += 1
    
    print(f"\n{'='*50}")
    print(f"Migration complete!")
    print(f"  Successful: {success_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")
    
    if error_count > 0:
        print("\nSome statements failed. Check the errors above.")
        print("You may need to apply the migration manually via Supabase SQL Editor.")
        sys.exit(1)
    else:
        print("\nAll statements executed successfully!")


def list_migrations():
    """List all available migrations."""
    migrations_dir = Path(__file__).parent / 'migrations'
    sql_files = sorted([f for f in migrations_dir.glob("*.sql") if f.name[0:3].isdigit()])
    
    print("Available migrations:")
    for f in sql_files:
        print(f"  {f.name}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Apply SQL migrations to Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python apply_migration.py              # Apply latest migration
  python apply_migration.py 010          # Apply migration 010
  python apply_migration.py --list       # List all migrations
        """
    )
    parser.add_argument(
        'migration_number',
        nargs='?',
        help='Migration number to apply (e.g., 010). If not specified, applies latest.'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available migrations'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_migrations()
        sys.exit(0)
    
    # Find and apply migration
    migration_file = find_migration_file(args.migration_number)
    print(f"Applying migration: {migration_file.name}\n")
    apply_migration(migration_file)
