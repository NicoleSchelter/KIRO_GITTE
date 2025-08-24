#!/usr/bin/env python3
"""
Performance optimization script for GITTE UX enhancements.
Runs performance analysis, optimization, and monitoring setup.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.performance_monitoring_service import (
    performance_monitor,
    start_performance_monitoring,
    get_performance_summary,
)
from services.lazy_loading_service import (
    lazy_loader,
    register_default_resources,
    preload_critical_resources,
    cleanup_unused_resources,
    get_resource_stats,
)
from services.caching_service import (
    cache_service,
    get_cache_stats,
    clear_cache,
    warm_cache,
)
from services.database_optimization_service import (
    DatabaseOptimizationService,
    initialize_db_optimizer,
)
from services.error_monitoring_service import (
    error_monitoring_service,
    get_system_health,
    get_monitoring_summary,
)

logger = logging.getLogger(__name__)


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def analyze_performance(hours: int = 1) -> dict:
    """
    Analyze system performance over the specified time period.
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        Dict with performance analysis results
    """
    print(f"🔍 Analyzing performance over the last {hours} hour(s)...")
    
    # Get performance summary
    perf_summary = get_performance_summary(hours)
    
    # Get cache statistics
    cache_stats = get_cache_stats()
    
    # Get resource statistics
    resource_stats = get_resource_stats()
    
    # Get system health
    system_health = get_system_health()
    
    # Get monitoring summary
    monitoring_summary = get_monitoring_summary()
    
    analysis = {
        "performance_summary": perf_summary,
        "cache_stats": cache_stats,
        "resource_stats": resource_stats,
        "system_health": {
            "overall_health": system_health.overall_health,
            "error_rate": system_health.error_rate,
            "resource_health": system_health.resource_health,
            "processing_health": system_health.processing_health,
        },
        "monitoring_summary": monitoring_summary,
        "timestamp": time.time()
    }
    
    return analysis


def optimize_system():
    """Run system optimization procedures."""
    print("⚡ Running system optimization...")
    
    optimization_results = {
        "lazy_loading": {},
        "caching": {},
        "database": {},
        "monitoring": {}
    }
    
    # 1. Optimize lazy loading
    print("  📦 Optimizing lazy loading...")
    try:
        # Register default resources
        register_default_resources()
        
        # Preload critical resources
        preload_critical_resources()
        
        # Clean up unused resources
        cleanup_unused_resources()
        
        resource_stats = get_resource_stats()
        optimization_results["lazy_loading"] = {
            "status": "success",
            "loaded_resources": resource_stats["loaded_resources"],
            "total_resources": resource_stats["total_resources"]
        }
        
        print(f"    ✓ Loaded {resource_stats['loaded_resources']}/{resource_stats['total_resources']} resources")
        
    except Exception as e:
        logger.error(f"Lazy loading optimization failed: {e}")
        optimization_results["lazy_loading"] = {"status": "failed", "error": str(e)}
    
    # 2. Optimize caching
    print("  💾 Optimizing caching...")
    try:
        # Clear expired entries
        cache_service.cleanup_expired()
        
        # Get cache statistics
        cache_stats = get_cache_stats()
        
        optimization_results["caching"] = {
            "status": "success",
            "memory_cache": {
                "hit_rate": cache_stats["memory"].hit_rate,
                "entry_count": cache_stats["memory"].entry_count,
                "size_mb": cache_stats["memory"].size_bytes / (1024 * 1024)
            },
            "disk_cache": {
                "hit_rate": cache_stats["disk"].hit_rate,
                "entry_count": cache_stats["disk"].entry_count,
                "size_mb": cache_stats["disk"].size_bytes / (1024 * 1024)
            }
        }
        
        print(f"    ✓ Memory cache: {cache_stats['memory'].hit_rate:.1%} hit rate, {cache_stats['memory'].entry_count} entries")
        print(f"    ✓ Disk cache: {cache_stats['disk'].hit_rate:.1%} hit rate, {cache_stats['disk'].entry_count} entries")
        
    except Exception as e:
        logger.error(f"Caching optimization failed: {e}")
        optimization_results["caching"] = {"status": "failed", "error": str(e)}
    
    # 3. Database optimization (if available)
    print("  🗄️  Optimizing database...")
    try:
        # Always reuse the central database engine from the data layer
        try:
            from data.database_factory import setup_database, _db_factory  # 'src' is already added to sys.path above
        except Exception:
            from src.data.database_factory import setup_database, _db_factory  # fallback if path differs

        setup_database()  # ensures env loading, engine with pool_pre_ping, session factory, etc.
        engine = _db_factory.engine

        initialize_db_optimizer(engine)
        db_optimizer = DatabaseOptimizationService(engine)

        
        # Get table statistics
        table_stats = db_optimizer.get_table_statistics()
        
        # Get index recommendations
        index_recommendations = db_optimizer.get_index_recommendations()
        
        optimization_results["database"] = {
            "status": "success",
            "table_count": len(table_stats),
            "index_recommendations": len(index_recommendations),
            "tables": [
                {
                    "name": stats.table_name,
                    "rows": stats.row_count,
                    "size_mb": stats.size_mb,
                    "indexes": stats.index_count
                }
                for stats in table_stats[:5]  # Show first 5 tables
            ]
        }
        
        print(f"    ✓ Analyzed {len(table_stats)} tables")
        print(f"    ✓ Generated {len(index_recommendations)} index recommendations")
        
        if index_recommendations:
            print("    📋 Index recommendations:")
            for rec in index_recommendations[:3]:  # Show first 3
                print(f"      - {rec.table_name}.{','.join(rec.columns)}: {rec.reason}")
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        optimization_results["database"] = {"status": "failed", "error": str(e)}
    
    # 4. Start monitoring
    print("  📊 Setting up monitoring...")
    try:
        # Start performance monitoring
        start_performance_monitoring(interval_seconds=60)
        
        optimization_results["monitoring"] = {
            "status": "success",
            "monitoring_active": True,
            "interval_seconds": 60
        }
        
        print("    ✓ Performance monitoring started")
        
    except Exception as e:
        logger.error(f"Monitoring setup failed: {e}")
        optimization_results["monitoring"] = {"status": "failed", "error": str(e)}
    
    return optimization_results


def benchmark_operations():
    """Run performance benchmarks for critical operations."""
    print("🏃 Running performance benchmarks...")
    
    benchmarks = {}
    
    # Benchmark cache operations
    print("  💾 Benchmarking cache operations...")
    cache_iterations = 1000
    
    start_time = time.time()
    for i in range(cache_iterations):
        cache_service.set(f"bench_key_{i}", f"bench_value_{i}")
    cache_set_time = time.time() - start_time
    
    start_time = time.time()
    for i in range(cache_iterations):
        cache_service.get(f"bench_key_{i}")
    cache_get_time = time.time() - start_time
    
    benchmarks["cache"] = {
        "set_ops_per_second": cache_iterations / cache_set_time,
        "get_ops_per_second": cache_iterations / cache_get_time,
        "set_avg_ms": (cache_set_time / cache_iterations) * 1000,
        "get_avg_ms": (cache_get_time / cache_iterations) * 1000
    }
    
    print(f"    ✓ Cache SET: {benchmarks['cache']['set_ops_per_second']:.0f} ops/sec")
    print(f"    ✓ Cache GET: {benchmarks['cache']['get_ops_per_second']:.0f} ops/sec")
    
    # Benchmark lazy loading
    print("  📦 Benchmarking lazy loading...")
    try:
        from services.lazy_loading_service import PersonDetectionModel
        
        lazy_loader.register_resource(PersonDetectionModel())
        
        # First access (should load)
        start_time = time.time()
        resource1 = lazy_loader.get_resource("person_detection_model")
        first_access_time = time.time() - start_time
        
        # Second access (should be cached)
        start_time = time.time()
        resource2 = lazy_loader.get_resource("person_detection_model")
        second_access_time = time.time() - start_time
        
        benchmarks["lazy_loading"] = {
            "first_access_ms": first_access_time * 1000,
            "cached_access_ms": second_access_time * 1000,
            "speedup_ratio": first_access_time / max(second_access_time, 0.001)
        }
        
        print(f"    ✓ First access: {benchmarks['lazy_loading']['first_access_ms']:.2f}ms")
        print(f"    ✓ Cached access: {benchmarks['lazy_loading']['cached_access_ms']:.2f}ms")
        print(f"    ✓ Speedup: {benchmarks['lazy_loading']['speedup_ratio']:.1f}x")
        
    except Exception as e:
        logger.error(f"Lazy loading benchmark failed: {e}")
        benchmarks["lazy_loading"] = {"error": str(e)}
    
    return benchmarks


def generate_performance_report():
    """Generate comprehensive performance report."""
    print("📊 Generating performance report...")
    
    report = {
        "timestamp": time.time(),
        "analysis": analyze_performance(hours=1),
        "benchmarks": benchmark_operations(),
        "recommendations": []
    }
    
    # Generate recommendations based on analysis
    analysis = report["analysis"]
    
    # Cache recommendations
    cache_stats = analysis["cache_stats"]
    if cache_stats["memory"].hit_rate < 0.8:
        report["recommendations"].append({
            "category": "caching",
            "priority": "medium",
            "recommendation": "Consider increasing memory cache size or TTL",
            "current_hit_rate": cache_stats["memory"].hit_rate
        })
    
    # Resource recommendations
    resource_stats = analysis["resource_stats"]
    if resource_stats["loaded_resources"] < resource_stats["total_resources"]:
        report["recommendations"].append({
            "category": "lazy_loading",
            "priority": "low",
            "recommendation": "Consider preloading more critical resources",
            "loaded_ratio": resource_stats["loaded_resources"] / resource_stats["total_resources"]
        })
    
    # System health recommendations
    system_health = analysis["system_health"]
    if system_health["overall_health"] < 0.8:
        report["recommendations"].append({
            "category": "system_health",
            "priority": "high",
            "recommendation": "System health is degraded, investigate error rates and resource usage",
            "current_health": system_health["overall_health"]
        })
    
    return report


def main():
    """Main function for performance optimization script."""
    parser = argparse.ArgumentParser(description="GITTE Performance Optimization Tool")
    parser.add_argument("--analyze", action="store_true", help="Analyze current performance")
    parser.add_argument("--optimize", action="store_true", help="Run optimization procedures")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--report", action="store_true", help="Generate performance report")
    parser.add_argument("--hours", type=int, default=1, help="Hours of data to analyze")
    
    args = parser.parse_args()
    
    setup_logging()
    
    if not any([args.analyze, args.optimize, args.benchmark, args.report]):
        # Default: run all operations
        args.analyze = args.optimize = args.benchmark = args.report = True
    
    results = {}
    
    try:
        if args.analyze:
            results["analysis"] = analyze_performance(args.hours)
            print("✅ Performance analysis completed")
        
        if args.optimize:
            results["optimization"] = optimize_system()
            print("✅ System optimization completed")
        
        if args.benchmark:
            results["benchmarks"] = benchmark_operations()
            print("✅ Performance benchmarks completed")
        
        if args.report:
            results["report"] = generate_performance_report()
            print("✅ Performance report generated")
            
            # Print summary
            print("\n📋 Performance Summary:")
            report = results["report"]
            
            if "analysis" in report:
                health = report["analysis"]["system_health"]
                print(f"  Overall Health: {health['overall_health']:.1%}")
                print(f"  Error Rate: {health['error_rate']:.1%}")
                print(f"  Resource Health: {health['resource_health']:.1%}")
            
            if report["recommendations"]:
                print(f"\n💡 Recommendations ({len(report['recommendations'])}):")
                for i, rec in enumerate(report["recommendations"][:5], 1):
                    print(f"  {i}. [{rec['priority'].upper()}] {rec['recommendation']}")
        
        print(f"\n🎉 Performance optimization completed successfully!")
        
    except Exception as e:
        logger.error(f"Performance optimization failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()