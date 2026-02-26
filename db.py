import os
import psycopg
from psycopg import sql

# Get the connection string from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_ENABLED = bool(DATABASE_URL)

# Fallback in-memory store when DATABASE_URL is not set (local/electron)
_MEM_JOBS: dict[str, dict] = {}

def _now_iso():
    try:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return None

def get_db_connection():
    """Get a connection to the database."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable not set")
    return psycopg.connect(DATABASE_URL)

def init_db():
    """Initialize the database schema."""
    if not DB_ENABLED:
        return
    conn = get_db_connection()
    cur = conn.cursor()

    # Example: Create a jobs table to track analysis jobs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            filename TEXT,
            target_grade FLOAT,
            status TEXT,
            result JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized.")

def save_job(job_id, filename, target_grade, result=None):
    """Save a job result to the database."""
    if not DB_ENABLED:
        _MEM_JOBS[job_id] = {
            "id": job_id,
            "filename": filename,
            "target_grade": target_grade,
            "status": "completed",
            "result": result,
            "created_at": _MEM_JOBS.get(job_id, {}).get("created_at") or _now_iso(),
            "updated_at": _now_iso(),
        }
        return
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO jobs (id, filename, target_grade, status, result)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            result = EXCLUDED.result,
            updated_at = NOW()
    """, (job_id, filename, target_grade, "completed", result))

    conn.commit()
    cur.close()
    conn.close()

def get_job(job_id):
    """Retrieve a job from the database."""
    if not DB_ENABLED:
        return _MEM_JOBS.get(job_id)
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        return {
            "id": row[0],
            "filename": row[1],
            "target_grade": row[2],
            "status": row[3],
            "result": row[4],
            "created_at": row[5],
            "updated_at": row[6],
        }
    return None

def list_jobs(limit=10):
    """List recent jobs."""
    if not DB_ENABLED:
        jobs = list(_MEM_JOBS.values())
        jobs.sort(key=lambda j: j.get("created_at") or "", reverse=True)
        return [
            {
                "id": j.get("id"),
                "filename": j.get("filename"),
                "target_grade": j.get("target_grade"),
                "status": j.get("status"),
                "created_at": j.get("created_at"),
            }
            for j in jobs[:limit]
        ]
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, target_grade, status, created_at
        FROM jobs
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "target_grade": row[2],
            "status": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]
