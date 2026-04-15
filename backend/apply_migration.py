import psycopg2
import sys
import os

def apply_migration():
    conn_string = "postgresql://postgres.cmclozvfauiyliqvgcbz:BkJFItbqhhDOGJQg@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
    
    try:
        print("Connecting to Supabase (Direct PostgreSQL)...")
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cur = conn.cursor()
        
        # SQL migration file path
        # From backend/ folder, migrations are at ../supabase/migrations/0001_initial_schema.sql
        migration_path = os.path.join("..", "supabase", "migrations", "0001_initial_schema.sql")
        
        if not os.path.exists(migration_path):
             print(f"Error: Migration file not found at {migration_path}")
             return

        with open(migration_path, "r", encoding="utf-8") as f:
            full_sql = f.read()
        
        print("Executing migration...")
        # We execute the whole block. 
        # Note: psycopg2 can execute multiple statements if they are in one string.
        cur.execute(full_sql)
        
        print("✅ Migration applied successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migration()
