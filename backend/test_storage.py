import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing SUPABASE credentials in .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

bucket_name = "youtube-automation"

try:
    print(f"Checking buckets...")
    buckets = supabase.storage.list_buckets()
    print("Buckets in Supabase:")
    for b in buckets:
        print(f" - {b.name}")
    
    if any(b.name == bucket_name for b in buckets):
        print(f"\nSUCCESS: Bucket '{bucket_name}' exists and is accessible!")
    else:
        print(f"\nWARNING: Bucket '{bucket_name}' not found!")
    
    # Try an upload test
    test_file = "test_upload.txt"
    with open(test_file, "w") as f:
        f.write("Hello Supabase Storage!")
        
    print(f"\nTesting upload to {bucket_name}/test/test_upload.txt ...")
    with open(test_file, "rb") as f:
        supabase.storage.from_(bucket_name).upload("test/test_upload.txt", f)
        
    url = supabase.storage.from_(bucket_name).get_public_url("test/test_upload.txt")
    print(f"Upload successful! Public URL generated: {url}")
    
    # Cleanup
    print("\nCleaning up test files...")
    supabase.storage.from_(bucket_name).remove(["test/test_upload.txt"])
    os.remove(test_file)
    print("Test finished successfully!")
    
except Exception as e:
    print(f"\n[ERROR] Storage test failed: {e}")
