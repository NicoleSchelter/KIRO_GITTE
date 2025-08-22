"""
Database Optimization Service for GITTE UX enhancements.
Provides query optimization, indexing, and database performance monitoring.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text, inspect, Index
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.services.performance_monitoring_service import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformance:
    """Query performance metrics."""
    query_hash: str
    query_text: str
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime
    table_name: Optional[str] = None
    operation_type: Optional[str] = None  # SELECT, INSERT, UPDATE, DELETE


@dataclass
class IndexRecommendation:
    """Database index recommendation."""
    table_name: str
    columns: List[str]
    index_type: str  # btree, hash, gin, etc.
    estimated_benefit: float  # 0.0 to 1.0
    reason: str
    query_patterns: List[str]


@dataclass
class TableStats:
    """Database table statistics."""
    table_name: str
    row_count: int
    size_mb: float
    index_count: int
    last_analyzed: Optional[datetime]
    most_frequent_queries: List[str]


class DatabaseOptimizationService:
    """Service for optimizing database performance."""
    
    def __init__(self, engine: Engine):
        """
        Initialize database optimization service.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.query_history: List[QueryPerformance] = []
        self.max_query_history = 10000
        
        # Query pattern tracking
        self.query_patterns: Dict[str, int] = {}
        self.slow_query_threshold_ms = 1000.0
        
        logger.info("Database optimization service initialized")
    
    def track_query(
        self,
        query_text: str,
        execution_time_ms: float,
        rows_affected: int = 0,
        table_name: str = None,
        operation_type: str = None
    ):
        """
        Track query performance for analysis.
        
        Args:
            query_text: SQL query text
            execution_time_ms: Query execution time in milliseconds
            rows_affected: Number of rows affected by the query
            table_name: Primary table involved in the query
            operation_type: Type of operation (SELECT, INSERT, etc.)
        """
        # Generate query hash for pattern matching
        query_hash = str(hash(self._normalize_query(query_text)))
        
        query_perf = QueryPerformance(
            query_hash=query_hash,
            query_text=query_text,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            timestamp=datetime.now(),
            table_name=table_name,
            operation_type=operation_type
        )
        
        # Add to history
        self.query_history.append(query_perf)
        
        # Maintain history size
        if len(self.query_history) > self.max_query_history:
            self.query_history = self.query_history[-self.max_query_history:]
        
        # Track query patterns
        normalized_query = self._normalize_query(query_text)
        self.query_patterns[normalized_query] = self.query_patterns.get(normalized_query, 0) + 1
        
        # Log slow queries
        if execution_time_ms > self.slow_query_threshold_ms:
            logger.warning(
                f"Slow query detected ({execution_time_ms:.2f}ms): {query_text[:100]}..."
            )
        
        # Record performance metrics
        performance_monitor.record_histogram(
            "database_query_duration_ms",
            execution_time_ms,
            {"table": table_name or "unknown", "operation": operation_type or "unknown"},
            "milliseconds"
        )
    
    def analyze_query_performance(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze query performance over the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dict with query performance analysis
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_queries = [q for q in self.query_history if q.timestamp > cutoff_time]
        
        if not recent_queries:
            return {"message": "No queries in the specified time period"}
        
        # Calculate statistics
        total_queries = len(recent_queries)
        total_time_ms = sum(q.execution_time_ms for q in recent_queries)
        avg_time_ms = total_time_ms / total_queries
        
        # Find slow queries
        slow_queries = [q for q in recent_queries if q.execution_time_ms > self.slow_query_threshold_ms]
        slow_query_percentage = (len(slow_queries) / total_queries) * 100
        
        # Group by operation type
        operation_stats = {}
        for query in recent_queries:
            op_type = query.operation_type or "unknown"
            if op_type not in operation_stats:
                operation_stats[op_type] = {
                    "count": 0,
                    "total_time_ms": 0,
                    "avg_time_ms": 0,
                    "max_time_ms": 0
                }
            
            stats = operation_stats[op_type]
            stats["count"] += 1
            stats["total_time_ms"] += query.execution_time_ms
            stats["max_time_ms"] = max(stats["max_time_ms"], query.execution_time_ms)
        
        # Calculate averages
        for stats in operation_stats.values():
            stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
        
        # Find most frequent query patterns
        pattern_frequency = {}
        for query in recent_queries:
            normalized = self._normalize_query(query.query_text)
            pattern_frequency[normalized] = pattern_frequency.get(normalized, 0) + 1
        
        most_frequent_patterns = sorted(
            pattern_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "time_period_hours": hours,
            "total_queries": total_queries,
            "avg_execution_time_ms": avg_time_ms,
            "total_execution_time_ms": total_time_ms,
            "slow_queries": {
                "count": len(slow_queries),
                "percentage": slow_query_percentage,
                "threshold_ms": self.slow_query_threshold_ms
            },
            "operation_stats": operation_stats,
            "most_frequent_patterns": [
                {"pattern": pattern, "count": count}
                for pattern, count in most_frequent_patterns
            ]
        }
    
    def get_index_recommendations(self) -> List[IndexRecommendation]:
        """
        Generate index recommendations based on query patterns.
        
        Returns:
            List of index recommendations
        """
        recommendations = []
        
        try:
            with self.engine.connect() as conn:
                # Get table information
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                
                for table_name in tables:
                    table_recommendations = self._analyze_table_for_indexes(table_name, conn)
                    recommendations.extend(table_recommendations)
        
        except Exception as e:
            logger.error(f"Failed to generate index recommendations: {e}")
        
        return recommendations
    
    def get_table_statistics(self) -> List[TableStats]:
        """
        Get statistics for all tables in the database.
        
        Returns:
            List of table statistics
        """
        table_stats = []
        
        try:
            with self.engine.connect() as conn:
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                
                for table_name in tables:
                    stats = self._get_table_stats(table_name, conn)
                    if stats:
                        table_stats.append(stats)
        
        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
        
        return table_stats
    
    def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """
        Optimize a specific table (analyze, vacuum, etc.).
        
        Args:
            table_name: Name of the table to optimize
            
        Returns:
            Dict with optimization results
        """
        results = {
            "table_name": table_name,
            "operations_performed": [],
            "errors": []
        }
        
        try:
            with self.engine.connect() as conn:
                # For PostgreSQL, run ANALYZE to update statistics
                if self.engine.dialect.name == 'postgresql':
                    conn.execute(text(f"ANALYZE {table_name}"))
                    results["operations_performed"].append("ANALYZE")
                    logger.info(f"Analyzed table: {table_name}")
                
                # For PostgreSQL, run VACUUM if needed
                if self.engine.dialect.name == 'postgresql':
                    # Note: VACUUM cannot be run inside a transaction
                    conn.execute(text("COMMIT"))
                    conn.execute(text(f"VACUUM {table_name}"))
                    results["operations_performed"].append("VACUUM")
                    logger.info(f"Vacuumed table: {table_name}")
        
        except Exception as e:
            error_msg = f"Failed to optimize table {table_name}: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def create_recommended_indexes(self, recommendations: List[IndexRecommendation] = None) -> Dict[str, Any]:
        """
        Create recommended indexes.
        
        Args:
            recommendations: List of index recommendations (generates if None)
            
        Returns:
            Dict with creation results
        """
        if recommendations is None:
            recommendations = self.get_index_recommendations()
        
        results = {
            "indexes_created": 0,
            "indexes_failed": 0,
            "created_indexes": [],
            "errors": []
        }
        
        for recommendation in recommendations:
            try:
                index_name = f"idx_{recommendation.table_name}_{'_'.join(recommendation.columns)}"
                columns_str = ', '.join(recommendation.columns)
                
                create_sql = f"CREATE INDEX {index_name} ON {recommendation.table_name} ({columns_str})"
                
                with self.engine.connect() as conn:
                    conn.execute(text(create_sql))
                    conn.commit()
                
                results["indexes_created"] += 1
                results["created_indexes"].append({
                    "index_name": index_name,
                    "table_name": recommendation.table_name,
                    "columns": recommendation.columns
                })
                
                logger.info(f"Created index: {index_name}")
                
            except Exception as e:
                error_msg = f"Failed to create index on {recommendation.table_name}: {e}"
                logger.error(error_msg)
                results["indexes_failed"] += 1
                results["errors"].append(error_msg)
        
        return results
    
    def _normalize_query(self, query_text: str) -> str:
        """
        Normalize query text for pattern matching.
        
        Args:
            query_text: Raw SQL query text
            
        Returns:
            Normalized query text
        """
        # Remove extra whitespace and convert to lowercase
        normalized = ' '.join(query_text.lower().split())
        
        # Replace parameter placeholders with generic markers
        import re
        normalized = re.sub(r'\$\d+', '?', normalized)  # PostgreSQL parameters
        normalized = re.sub(r':\w+', '?', normalized)   # Named parameters
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # String literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)    # Numeric literals
        
        return normalized
    
    def _analyze_table_for_indexes(self, table_name: str, conn) -> List[IndexRecommendation]:
        """
        Analyze a table for potential index recommendations.
        
        Args:
            table_name: Name of the table to analyze
            conn: Database connection
            
        Returns:
            List of index recommendations for the table
        """
        recommendations = []
        
        try:
            # Get existing indexes
            inspector = inspect(self.engine)
            existing_indexes = inspector.get_indexes(table_name)
            existing_columns = set()
            for index in existing_indexes:
                existing_columns.update(index['column_names'])
            
            # Analyze query patterns for this table
            table_queries = [
                q for q in self.query_history
                if q.table_name == table_name or table_name in q.query_text.lower()
            ]
            
            if not table_queries:
                return recommendations
            
            # Look for WHERE clause patterns
            where_columns = self._extract_where_columns(table_queries)
            
            for column, frequency in where_columns.items():
                if column not in existing_columns and frequency > 5:  # Threshold for recommendation
                    recommendations.append(IndexRecommendation(
                        table_name=table_name,
                        columns=[column],
                        index_type="btree",
                        estimated_benefit=min(frequency / 100.0, 1.0),
                        reason=f"Frequently used in WHERE clauses ({frequency} times)",
                        query_patterns=[q.query_text[:100] for q in table_queries[:3]]
                    ))
            
            # Look for ORDER BY patterns
            order_columns = self._extract_order_columns(table_queries)
            
            for column, frequency in order_columns.items():
                if column not in existing_columns and frequency > 3:
                    recommendations.append(IndexRecommendation(
                        table_name=table_name,
                        columns=[column],
                        index_type="btree",
                        estimated_benefit=min(frequency / 50.0, 1.0),
                        reason=f"Frequently used in ORDER BY clauses ({frequency} times)",
                        query_patterns=[q.query_text[:100] for q in table_queries[:3]]
                    ))
        
        except Exception as e:
            logger.error(f"Failed to analyze table {table_name} for indexes: {e}")
        
        return recommendations
    
    def _get_table_stats(self, table_name: str, conn) -> Optional[TableStats]:
        """
        Get statistics for a specific table.
        
        Args:
            table_name: Name of the table
            conn: Database connection
            
        Returns:
            TableStats object or None if failed
        """
        try:
            # Get row count
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = result.scalar()
            
            # Get table size (PostgreSQL specific)
            size_mb = 0.0
            if self.engine.dialect.name == 'postgresql':
                result = conn.execute(text(f"SELECT pg_total_relation_size('{table_name}') / 1024.0 / 1024.0"))
                size_mb = result.scalar() or 0.0
            
            # Get index count
            inspector = inspect(self.engine)
            indexes = inspector.get_indexes(table_name)
            index_count = len(indexes)
            
            # Get most frequent queries for this table
            table_queries = [
                q.query_text for q in self.query_history
                if q.table_name == table_name or table_name in q.query_text.lower()
            ]
            
            # Count query patterns
            query_patterns = {}
            for query in table_queries:
                normalized = self._normalize_query(query)
                query_patterns[normalized] = query_patterns.get(normalized, 0) + 1
            
            most_frequent = sorted(query_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
            most_frequent_queries = [pattern for pattern, _ in most_frequent]
            
            return TableStats(
                table_name=table_name,
                row_count=row_count,
                size_mb=size_mb,
                index_count=index_count,
                last_analyzed=datetime.now(),  # Approximate
                most_frequent_queries=most_frequent_queries
            )
        
        except Exception as e:
            logger.error(f"Failed to get stats for table {table_name}: {e}")
            return None
    
    def _extract_where_columns(self, queries: List[QueryPerformance]) -> Dict[str, int]:
        """
        Extract columns used in WHERE clauses from queries.
        
        Args:
            queries: List of query performance records
            
        Returns:
            Dict mapping column names to usage frequency
        """
        where_columns = {}
        
        for query in queries:
            query_text = query.query_text.lower()
            
            # Simple regex to find WHERE clause columns
            import re
            where_matches = re.findall(r'where\s+.*?(\w+)\s*[=<>!]', query_text)
            
            for column in where_matches:
                if len(column) > 2:  # Filter out very short matches
                    where_columns[column] = where_columns.get(column, 0) + 1
        
        return where_columns
    
    def _extract_order_columns(self, queries: List[QueryPerformance]) -> Dict[str, int]:
        """
        Extract columns used in ORDER BY clauses from queries.
        
        Args:
            queries: List of query performance records
            
        Returns:
            Dict mapping column names to usage frequency
        """
        order_columns = {}
        
        for query in queries:
            query_text = query.query_text.lower()
            
            # Simple regex to find ORDER BY clause columns
            import re
            order_matches = re.findall(r'order\s+by\s+(\w+)', query_text)
            
            for column in order_matches:
                if len(column) > 2:  # Filter out very short matches
                    order_columns[column] = order_columns.get(column, 0) + 1
        
        return order_columns


def query_performance_tracker(engine: Engine):
    """
    Decorator to track query performance.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Try to extract query information
                query_text = "unknown"
                if hasattr(result, 'statement'):
                    query_text = str(result.statement)
                elif len(args) > 0 and hasattr(args[0], 'text'):
                    query_text = str(args[0].text)
                
                # Track the query performance
                db_optimizer = DatabaseOptimizationService(engine)
                db_optimizer.track_query(
                    query_text=query_text,
                    execution_time_ms=execution_time_ms,
                    rows_affected=getattr(result, 'rowcount', 0)
                )
                
                return result
                
            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                logger.error(f"Query failed after {execution_time_ms:.2f}ms: {e}")
                raise
        
        return wrapper
    return decorator


# Global database optimization service instance (initialized when engine is available)
_db_optimizer: Optional[DatabaseOptimizationService] = None


def initialize_db_optimizer(engine: Engine):
    """Initialize the global database optimizer."""
    global _db_optimizer
    _db_optimizer = DatabaseOptimizationService(engine)


def get_db_optimizer() -> Optional[DatabaseOptimizationService]:
    """Get the global database optimizer instance."""
    return _db_optimizer


def track_query_performance(
    query_text: str,
    execution_time_ms: float,
    rows_affected: int = 0,
    table_name: str = None,
    operation_type: str = None
):
    """Track query performance using the global optimizer."""
    if _db_optimizer:
        _db_optimizer.track_query(
            query_text, execution_time_ms, rows_affected, table_name, operation_type
        )