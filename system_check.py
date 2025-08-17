# system_check.py
import os
import psycopg2
import requests
import torch

# Ergebnisse für Ampel
results = []

def check_postgres():
    print("🔍 Checking PostgreSQL...")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "kiro_test"),
            user=os.getenv("POSTGRES_USER", "gitte"),
            password=os.getenv("POSTGRES_PASSWORD", "sicheres_passwort"),
            host="localhost",
            port=os.getenv("POSTGRES_PORT", "5432"),
        )
        conn.close()
        print("✅ PostgreSQL reachable")
        results.append(True)
    except Exception as e:
        print(f"❌ PostgreSQL failed: {e}")
        results.append(False)

def check_ollama():
    print("🔍 Checking Ollama...")
    try:
        url = os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/api/tags"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"✅ Ollama reachable, models: {models}")
            results.append(True)
        else:
            print(f"❌ Ollama responded with status {r.status_code}")
            results.append(False)
    except Exception as e:
        print(f"❌ Ollama failed: {e}")
        results.append(False)

def check_stable_diffusion():
    print("🔍 Checking Stable Diffusion...")
    try:
        if not torch.cuda.is_available():
            print("⚠️ CUDA not available, running on CPU (very slow).")
            results.append(True)  # CPU-Betrieb möglich, aber langsam
        from diffusers import StableDiffusionPipeline
        model_name = os.getenv("SD_MODEL", "runwayml/stable-diffusion-v1-5")
        StableDiffusionPipeline.from_pretrained(model_name)
        print(f"✅ Stable Diffusion model {model_name} is available")
        results.append(True)
    except Exception as e:
        print(f"❌ Stable Diffusion failed: {e}")
        results.append(False)

def check_minio():
    print("🔍 Checking MinIO (optional)...")
    try:
        endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        r = requests.get(endpoint, timeout=5)
        if r.status_code in (200, 403):
            print("✅ MinIO reachable")
            results.append(True)
        else:
            print(f"⚠️ MinIO responded with status {r.status_code}")
            results.append(True)  # optional, kein Blocker
    except Exception as e:
        print(f"ℹ️ MinIO check skipped/not reachable: {e}")
        results.append(True)  # optional, kein Blocker

def print_summary():
    print("\n=== Gesamtbewertung ===")
    if all(results):
        print("🟢 Alles OK – Du kannst loslegen!")
    elif any(results):
        print("🟡 Teilweise OK – einige Komponenten fehlen/fehlerhaft.")
    else:
        print("🔴 Nichts läuft – bitte Logs prüfen.")

if __name__ == "__main__":
    print("=== GITTE System Check ===")
    check_postgres()
    check_ollama()
    check_stable_diffusion()
    check_minio()
    print_summary()
    print("=== Done ===")
