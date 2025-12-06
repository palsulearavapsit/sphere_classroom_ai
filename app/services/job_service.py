"""
Background Job Service using Redis and RQ
Handles async processing for heavy tasks like OCR, ML operations, etc.
"""
import os
try:
    from rq import Queue, Worker
    from redis import Redis
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    Queue = None
    Worker = None
    Redis = None

from ..config import Config

# Redis connection
redis_conn = None
job_queue = None

def init_redis():
    """Initialize Redis connection and job queue"""
    global redis_conn, job_queue
    
    if not RQ_AVAILABLE:
        print("Redis/RQ not available - background jobs disabled")
        return False
    
    try:
        # Try to connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_conn = Redis.from_url(redis_url)
        
        # Test connection
        try:
            redis_conn.ping()
        except Exception as ping_error:
            print(f"Redis connection failed: {ping_error}")
            print("Background jobs will run synchronously")
            return False
        
        # Initialize job queue
        job_queue = Queue('default', connection=redis_conn)
        
        return True
    except Exception as e:
        print(f"Redis initialization failed: {e}")
        print("Background jobs will run synchronously")
        return False
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("Background jobs will run synchronously")
        return False

def queue_job(func, *args, **kwargs):
    """Queue a job for background processing"""
    if job_queue:
        try:
            job = job_queue.enqueue(func, *args, **kwargs)
            return {"job_id": job.id, "status": "queued"}
        except Exception as e:
            print(f"Failed to queue job: {e}")
            # Fallback to synchronous execution
            result = func(*args, **kwargs)
            return {"result": result, "status": "completed_sync"}
    else:
        # No Redis, run synchronously
        result = func(*args, **kwargs)
        return {"result": result, "status": "completed_sync"}

def get_job_status(job_id):
    """Get status of a background job"""
    if job_queue and job_id:
        try:
            job = job_queue.fetch_job(job_id)
            if job:
                return {
                    "id": job.id,
                    "status": job.get_status(),
                    "result": job.result,
                    "meta": job.meta
                }
        except Exception as e:
            print(f"Failed to get job status: {e}")
    
    return {"status": "not_found"}

def get_queue_info():
    """Get information about the job queue"""
    if job_queue:
        try:
            return {
                "name": job_queue.name,
                "length": len(job_queue),
                "failed_jobs": len(job_queue.failed_job_registry),
                "finished_jobs": len(job_queue.finished_job_registry),
                "started_jobs": len(job_queue.started_job_registry),
                "deferred_jobs": len(job_queue.deferred_job_registry),
                "scheduled_jobs": len(job_queue.scheduled_job_registry)
            }
        except Exception as e:
            print(f"Failed to get queue info: {e}")
    
    return {"error": "Queue not available"}

# Background task functions
def process_ocr_async(image_data, filename):
    """Process OCR in background"""
    from .ocr_service import extract_text
    
    try:
        result = extract_text(image_data, filename)
        return {"success": True, "text": result, "filename": filename}
    except Exception as e:
        return {"success": False, "error": str(e), "filename": filename}

def process_rag_reindex_async():
    """Reindex RAG documents in background"""
    from .rag_service import reindex_all
    
    try:
        result = reindex_all()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_assessment_async(topic, level="medium"):
    """Generate AI assessment in background"""
    from .assessments_service import generate_adaptive_test
    
    try:
        result = generate_adaptive_test(topic, level)
        return {"success": True, "assessment": result, "topic": topic}
    except Exception as e:
        return {"success": False, "error": str(e), "topic": topic}

# Initialize Redis connection when module is imported
try:
    init_redis()
except Exception as e:
    print(f"Failed to initialize Redis: {e}")
    print("Background jobs will run synchronously")