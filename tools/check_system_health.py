#!/usr/bin/env python3
"""
System Health Check for GITTE
Quick validation of system prerequisites and configuration
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_environment():
    """Check environment configuration"""
    print("🔧 Environment Configuration")
    print("-" * 40)
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
    else:
        print("⚠️ .env file missing (using defaults)")
    
    # Check key environment variables
    key_vars = [
        "POSTGRES_DSN",
        "OLLAMA_URL", 
        "ENVIRONMENT",
        "SECRET_KEY"
    ]
    
    for var in key_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "password" in var.lower() or "key" in var.lower():
                display_value = "***" + value[-4:] if len(value) > 4 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")

def check_database():
    """Check database connectivity"""
    print("\n🗄️ Database Connectivity")
    print("-" * 40)
    
    try:
        from src.data.database_factory import _db_factory
        
        # Test connection
        if _db_factory.health_check():
            print("✅ Database connection: OK")
            
            # Check basic tables
            try:
                with _db_factory.get_session() as session:
                    result = session.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('users', 'consent_records', 'pseudonyms')
                    """)
                    tables = [row[0] for row in result.fetchall()]
                    
                    if len(tables) >= 2:
                        print(f"✅ Database schema: {len(tables)} core tables found")
                    else:
                        print(f"⚠️ Database schema: Only {len(tables)} tables found, may need migration")
                        
            except Exception as e:
                print(f"⚠️ Database schema check failed: {e}")
                
        else:
            print("❌ Database connection: Failed")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")

def check_services():
    """Check external services"""
    print("\n🌐 External Services")
    print("-" * 40)
    
    # Check Ollama
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama: Connected ({len(models)} models)")
        else:
            print(f"⚠️ Ollama: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ollama: Not accessible ({e})")
    
    # Check MinIO (if enabled)
    try:
        minio_enabled = os.getenv("FEATURE_ENABLE_MINIO_STORAGE", "false").lower() == "true"
        if minio_enabled:
            minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            response = requests.get(f"http://{minio_endpoint}/minio/health/live", timeout=5)
            if response.status_code == 200:
                print("✅ MinIO: Connected")
            else:
                print(f"⚠️ MinIO: HTTP {response.status_code}")
        else:
            print("ℹ️ MinIO: Disabled (using filesystem)")
            
    except Exception as e:
        print(f"❌ MinIO: Not accessible ({e})")

def check_python_environment():
    """Check Python environment and dependencies"""
    print("\n🐍 Python Environment")
    print("-" * 40)
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    
    # Check key dependencies
    key_deps = [
        "streamlit",
        "sqlalchemy", 
        "psycopg2",
        "pydantic",
        "requests"
    ]
    
    for dep in key_deps:
        try:
            __import__(dep)
            print(f"✅ {dep}: Available")
        except ImportError:
            print(f"❌ {dep}: Missing")

def check_file_structure():
    """Check critical file structure"""
    print("\n📁 File Structure")
    print("-" * 40)
    
    critical_paths = [
        "src/ui/main.py",
        "src/data/models.py",
        "config/config.py",
        "requirements.txt",
        "migrations/env.py"
    ]
    
    for path in critical_paths:
        if Path(path).exists():
            print(f"✅ {path}")
        else:
            print(f"❌ {path}: Missing")

def main():
    """Run complete system health check"""
    print("🏥 GITTE System Health Check")
    print("=" * 50)
    
    check_environment()
    check_python_environment()
    check_file_structure()
    check_database()
    check_services()
    
    print("\n" + "=" * 50)
    print("Health check complete!")
    print("\nTo fix issues:")
    print("  1. Run: .\\tools\\smoke_run.ps1")
    print("  2. Check .env configuration")
    print("  3. Ensure services are running")

if __name__ == "__main__":
    main()