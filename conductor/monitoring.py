"""
Production monitoring and metrics collection.

Tracks performance metrics, success rates, and system health.
"""

import logging
import time
from typing import Dict, Any, Optional
from functools import wraps
from collections import defaultdict
from datetime import datetime

# Lazy load prometheus_client to avoid dependency issues
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed. Metrics will be collected in-memory only.")

logger = logging.getLogger(__name__)

# In-memory metrics (always available)
_metrics = {
    "query_count": 0,
    "query_success": 0,
    "query_failures": 0,
    "ingestion_sessions": 0,
    "ingestion_files": 0,
    "file_processing_errors": defaultdict(int),
    "query_latencies": [],
    "ingestion_latencies": [],
}

# Prometheus metrics (if available)
if PROMETHEUS_AVAILABLE:
    query_counter = Counter('conductor_queries_total', 'Total number of queries', ['status'])
    query_latency = Histogram('conductor_query_duration_seconds', 'Query latency in seconds')
    ingestion_counter = Counter('conductor_ingestion_sessions_total', 'Total sessions ingested')
    file_counter = Counter('conductor_files_processed_total', 'Total files processed', ['file_type', 'status'])
    error_counter = Counter('conductor_errors_total', 'Total errors', ['error_type'])
else:
    query_counter = None
    query_latency = None
    ingestion_counter = None
    file_counter = None
    error_counter = None


def track_query(func):
    """Decorator to track query performance and success."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}")
            _metrics["query_failures"] += 1
            if error_counter:
                error_counter.labels(error_type=type(e).__name__).inc()
            raise
        finally:
            latency = time.time() - start_time
            _metrics["query_count"] += 1
            _metrics["query_latencies"].append(latency)
            
            if success:
                _metrics["query_success"] += 1
                if query_counter:
                    query_counter.labels(status='success').inc()
            else:
                if query_counter:
                    query_counter.labels(status='failure').inc()
            
            if query_latency:
                query_latency.observe(latency)
            
            # Keep only last 1000 latencies in memory
            if len(_metrics["query_latencies"]) > 1000:
                _metrics["query_latencies"] = _metrics["query_latencies"][-1000:]
    
    return wrapper


def track_file_processing(file_type: str, success: bool, error_type: Optional[str] = None):
    """Track file processing metrics."""
    _metrics["ingestion_files"] += 1
    
    if not success:
        _metrics["file_processing_errors"][file_type] += 1
        if error_type and error_counter:
            error_counter.labels(error_type=error_type).inc()
    
    if file_counter:
        status = "success" if success else "failure"
        file_counter.labels(file_type=file_type, status=status).inc()


def track_ingestion(session_count: int, latency: float):
    """Track ingestion metrics."""
    _metrics["ingestion_sessions"] += session_count
    _metrics["ingestion_latencies"].append(latency)
    
    if ingestion_counter:
        ingestion_counter.inc(session_count)
    
    # Keep only last 100 latencies in memory
    if len(_metrics["ingestion_latencies"]) > 100:
        _metrics["ingestion_latencies"] = _metrics["ingestion_latencies"][-100:]


def get_metrics_summary() -> Dict[str, Any]:
    """Get summary of all collected metrics."""
    latencies = _metrics["query_latencies"]
    ingestion_lats = _metrics["ingestion_latencies"]
    
    summary = {
        "queries": {
            "total": _metrics["query_count"],
            "success": _metrics["query_success"],
            "failures": _metrics["query_failures"],
            "success_rate": (
                _metrics["query_success"] / _metrics["query_count"]
                if _metrics["query_count"] > 0 else 0.0
            ),
            "avg_latency_seconds": (
                sum(latencies) / len(latencies) if latencies else 0.0
            ),
            "p95_latency_seconds": (
                sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
            ),
        },
        "ingestion": {
            "total_sessions": _metrics["ingestion_sessions"],
            "total_files": _metrics["ingestion_files"],
            "avg_latency_seconds": (
                sum(ingestion_lats) / len(ingestion_lats) if ingestion_lats else 0.0
            ),
        },
        "file_errors": dict(_metrics["file_processing_errors"]),
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "timestamp": datetime.now().isoformat(),
    }
    
    return summary


def get_prometheus_metrics() -> Optional[bytes]:
    """Get Prometheus metrics in text format."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return None

