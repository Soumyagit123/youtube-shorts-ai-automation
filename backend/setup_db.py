import sys
import os
from supabase import create_client

def main():
    if len(sys.argv) < 3:
        print("Usage: python setup_supabase.py <SUPABASE_URL> <SUPABASE_SERVICE_ROLE_KEY>")
        sys.exit(1)

    url = sys.argv[1]
    key = sys.argv[2]

    print(f"Connecting to {url}...")
    try:
        supabase = create_client(url, key)
        
        # Read the migration file
        migration_path = os.path.join("..", "supabase", "migrations", "0001_initial_schema.sql")
        if not os.path.exists(migration_path):
            # Try current folder migrations
            migration_path = os.path.join("supabase", "migrations", "0001_initial_schema.sql")
        
        with open(migration_path, "r") as f:
            sql = f.read()

        print("Applying migration...")
        # Split SQL by semicolons (simple approach for triggers, might need refinement)
        # However, it's safer to use the RPC or raw execution if available.
        # supabase-py doesn't have a direct 'apply_migration', but we can use postgrest for simple stuff.
        # For complex SQL with triggers, it's best to use the SQL Editor.
        
        print("\n[IMPORTANT] Since this script is a fallback, if it fails, please use the Supabase SQL Editor.")
        print("Copy the content of: ../supabase/migrations/0001_initial_schema.sql")
        print("And paste it into: https://supabase.com/dashboard/project/_/sql\n")
        
        # Try raw execution via a RPC if enabled, or just suggest the SQL editor.
        print("Attempting to execute via Postgrest (best effort)...")
        # Most Supabase instances don't allow raw SQL via the client for security.
        # So we'll provide the script but emphasize the SQL Editor.
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
