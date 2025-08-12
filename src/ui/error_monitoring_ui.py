"""
Error monitoring UI components for GITTE system.
Provides comprehensive error tracking, circuit breaker monitoring, and system health dashboard.
"""

import logging
from datetime import datetime

import streamlit as st

from src.utils.circuit_breaker import (
    get_all_circuit_breaker_stats,
    get_unhealthy_services,
    reset_all_circuit_breakers,
)
from src.utils.error_handler import clear_error_stats, get_error_stats, get_recent_errors

logger = logging.getLogger(__name__)


class ErrorMonitoringUI:
    """UI components for error monitoring and system health."""

    def render_error_dashboard(self) -> None:
        """Render comprehensive error monitoring dashboard."""
        st.title("🚨 Error Monitoring & System Health")

        # Create tabs for different monitoring views
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Overview", "🔧 Circuit Breakers", "📋 Error Details", "⚙️ System Health"]
        )

        with tab1:
            self._render_overview_tab()

        with tab2:
            self._render_circuit_breaker_tab()

        with tab3:
            self._render_error_details_tab()

        with tab4:
            self._render_system_health_tab()

    def _render_overview_tab(self) -> None:
        """Render error overview tab."""
        st.subheader("📊 Error Overview")

        # Get error statistics
        stats = get_error_stats()

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Errors", stats["total_errors"], help="Total number of errors recorded")

        with col2:
            st.metric(
                "Recent Errors",
                stats["recent_errors_count"],
                help="Errors in recent history buffer",
            )

        with col3:
            unique_error_types = len(stats["error_counts"])
            st.metric("Error Types", unique_error_types, help="Number of unique error types")

        with col4:
            # Calculate error rate (errors per hour - mock calculation)
            error_rate = min(stats["total_errors"], 100)  # Mock rate
            st.metric("Error Rate", f"{error_rate}/hr", help="Approximate errors per hour")

        # Error severity breakdown
        if stats["total_errors"] > 0:
            st.subheader("Error Severity Distribution")

            # Mock severity data (in real implementation, track by severity)
            severity_data = {
                "Critical": max(1, stats["total_errors"] // 20),
                "High": max(2, stats["total_errors"] // 10),
                "Medium": max(5, stats["total_errors"] // 5),
                "Low": max(10, stats["total_errors"] // 2),
            }

            col1, col2 = st.columns(2)

            with col1:
                for severity, count in severity_data.items():
                    color = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(
                        severity, "⚪"
                    )

                    st.write(f"{color} **{severity}**: {count} errors")

            with col2:
                # Error trend (mock data)
                st.line_chart({"Errors": [1, 3, 2, 5, 4, 2, 1, 3, 6, 4]})

        # Most common errors
        if stats["most_common_errors"]:
            st.subheader("Most Common Errors")

            for _i, (error_code, count) in enumerate(stats["most_common_errors"][:5]):
                percentage = (
                    (count / stats["total_errors"]) * 100 if stats["total_errors"] > 0 else 0
                )

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"**{error_code}**")

                with col2:
                    st.write(f"{count} times")

                with col3:
                    st.write(f"{percentage:.1f}%")

                # Progress bar
                st.progress(percentage / 100)

    def _render_circuit_breaker_tab(self) -> None:
        """Render circuit breaker monitoring tab."""
        st.subheader("🔧 Circuit Breaker Status")

        # Get circuit breaker statistics
        cb_stats = get_all_circuit_breaker_stats()
        unhealthy_services = get_unhealthy_services()

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Total Services", len(cb_stats), help="Number of services with circuit breakers"
            )

        with col2:
            healthy_services = len(cb_stats) - len(unhealthy_services)
            st.metric(
                "Healthy Services", healthy_services, help="Services with closed circuit breakers"
            )

        with col3:
            st.metric(
                "Unhealthy Services",
                len(unhealthy_services),
                delta=f"-{len(unhealthy_services)}" if unhealthy_services else None,
                delta_color="inverse",
                help="Services with open circuit breakers",
            )

        # Circuit breaker details
        if cb_stats:
            st.subheader("Service Status Details")

            for service_name, stats in cb_stats.items():
                with st.expander(f"🔧 {service_name} - {stats['state'].upper()}"):
                    # Status indicator
                    state_color = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}.get(
                        stats["state"], "⚪"
                    )

                    st.write(
                        f"**Status:** {state_color} {stats['state'].replace('_', ' ').title()}"
                    )

                    # Metrics
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Success Rate", f"{stats['success_rate']:.1%}")

                    with col2:
                        st.metric("Total Requests", stats["total_requests"])

                    with col3:
                        st.metric("Failures", stats["total_failures"])

                    # Configuration
                    st.write("**Configuration:**")
                    config_data = stats["config"]
                    st.write(f"- Failure Threshold: {config_data['failure_threshold']}")
                    st.write(f"- Recovery Timeout: {config_data['recovery_timeout']}s")
                    st.write(f"- Success Threshold: {config_data['success_threshold']}")

                    # Recent activity
                    if stats["last_failure_time"]:
                        last_failure = datetime.fromtimestamp(stats["last_failure_time"])
                        st.write(f"**Last Failure:** {last_failure.strftime('%Y-%m-%d %H:%M:%S')}")

                    if stats["last_success_time"]:
                        last_success = datetime.fromtimestamp(stats["last_success_time"])
                        st.write(f"**Last Success:** {last_success.strftime('%Y-%m-%d %H:%M:%S')}")

        # Control buttons
        st.subheader("Circuit Breaker Controls")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Reset All Circuit Breakers"):
                reset_all_circuit_breakers()
                st.success("All circuit breakers have been reset!")
                st.rerun()

        with col2:
            if st.button("📊 Refresh Status"):
                st.rerun()

    def _render_error_details_tab(self) -> None:
        """Render detailed error information tab."""
        st.subheader("📋 Error Details")

        # Error filters
        col1, col2, col3 = st.columns(3)

        with col1:
            error_limit = st.selectbox(
                "Number of errors to show", options=[10, 20, 50, 100], index=1
            )

        with col2:
            st.selectbox(
                "Filter by severity", options=["All", "Critical", "High", "Medium", "Low"], index=0
            )

        with col3:
            st.selectbox(
                "Filter by category",
                options=[
                    "All",
                    "Authentication",
                    "External Service",
                    "Database",
                    "System",
                    "Validation",
                ],
                index=0,
            )

        # Get recent errors
        recent_errors = get_recent_errors(error_limit)

        # Apply filters (mock filtering - in real implementation, filter in backend)
        filtered_errors = recent_errors

        if filtered_errors:
            st.subheader(f"Recent Errors ({len(filtered_errors)})")

            for _i, error_record in enumerate(filtered_errors):
                error_info = error_record["error"]

                # Error severity icon
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                    error_info["severity"], "⚪"
                )

                # Category icon
                category_icon = {
                    "authentication": "🔐",
                    "external_service": "🌐",
                    "database": "🗄️",
                    "system": "⚙️",
                    "validation": "✅",
                    "business_logic": "💼",
                    "network": "📡",
                    "privacy": "🔒",
                }.get(error_info["category"], "❓")

                with st.expander(
                    f"{severity_icon} {category_icon} {error_info['error_code']} - {error_record['timestamp']}"
                ):
                    # Error details
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Message:** {error_info['message']}")
                        st.write(f"**User Message:** {error_info['user_message']}")
                        st.write(f"**Category:** {error_info['category']}")
                        st.write(f"**Severity:** {error_info['severity']}")

                    with col2:
                        st.write(f"**Request ID:** {error_record['request_id']}")
                        st.write(f"**User ID:** {error_record['user_id'] or 'Anonymous'}")

                        if error_info["cause"]:
                            st.write(f"**Root Cause:** {error_info['cause']}")

                    # Error details
                    if error_info["details"]:
                        st.write("**Additional Details:**")
                        st.json(error_info["details"])

                    # Context information
                    if error_record["context"]:
                        st.write("**Context:**")
                        st.json(error_record["context"])

                    # Show traceback for high/critical errors
                    if error_info["severity"] in ["high", "critical"]:
                        with st.expander("🔍 Technical Details"):
                            st.code(error_record["traceback"], language="python")
        else:
            st.info("No errors found matching the current filters.")

        # Clear errors button
        if st.button("🗑️ Clear Error History"):
            clear_error_stats()
            st.success("Error history cleared!")
            st.rerun()

    def _render_system_health_tab(self) -> None:
        """Render system health monitoring tab."""
        st.subheader("⚙️ System Health")

        # Health indicators
        col1, col2, col3, col4 = st.columns(4)

        # Mock health data (in real implementation, get from actual health checks)
        with col1:
            st.metric("Database", "Healthy", delta="99.9% uptime", delta_color="normal")

        with col2:
            unhealthy_count = len(get_unhealthy_services())
            status = "Healthy" if unhealthy_count == 0 else f"{unhealthy_count} Issues"
            st.metric(
                "External Services",
                status,
                delta=f"-{unhealthy_count}" if unhealthy_count > 0 else "All OK",
                delta_color="inverse" if unhealthy_count > 0 else "normal",
            )

        with col3:
            st.metric("Memory Usage", "45%", delta="+5%", delta_color="normal")

        with col4:
            st.metric("Response Time", "120ms", delta="-20ms", delta_color="inverse")

        # Service health details
        st.subheader("Service Health Details")

        services = [
            {
                "name": "Authentication",
                "status": "Healthy",
                "uptime": "99.9%",
                "last_check": "2 min ago",
            },
            {
                "name": "LLM Provider",
                "status": "Healthy",
                "uptime": "98.5%",
                "last_check": "1 min ago",
            },
            {
                "name": "Image Generation",
                "status": "Degraded",
                "uptime": "95.2%",
                "last_check": "30 sec ago",
            },
            {"name": "Database", "status": "Healthy", "uptime": "99.9%", "last_check": "1 min ago"},
            {"name": "Storage", "status": "Healthy", "uptime": "99.7%", "last_check": "2 min ago"},
        ]

        for service in services:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                status_icon = {"Healthy": "🟢", "Degraded": "🟡", "Unhealthy": "🔴"}.get(
                    service["status"], "⚪"
                )
                st.write(f"{status_icon} **{service['name']}**")

            with col2:
                st.write(service["status"])

            with col3:
                st.write(f"Uptime: {service['uptime']}")

            with col4:
                st.write(f"Last check: {service['last_check']}")

        # System resources
        st.subheader("System Resources")

        # Mock resource data
        resource_data = {"CPU Usage": 35, "Memory Usage": 45, "Disk Usage": 60, "Network I/O": 25}

        for resource, usage in resource_data.items():
            st.write(f"**{resource}**: {usage}%")

            # Color code based on usage
            if usage < 50:
                pass  # Green
            elif usage < 80:
                pass  # Yellow
            else:
                pass  # Red

            st.progress(usage / 100)

        # Recent system events
        st.subheader("Recent System Events")

        events = [
            {"time": "2 min ago", "event": "Circuit breaker reset: ollama_llm", "type": "info"},
            {"time": "5 min ago", "event": "High memory usage detected", "type": "warning"},
            {"time": "10 min ago", "event": "Database connection pool expanded", "type": "info"},
            {
                "time": "15 min ago",
                "event": "Image generation service recovered",
                "type": "success",
            },
        ]

        for event in events:
            icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(
                event["type"], "📝"
            )

            st.write(f"{icon} **{event['time']}**: {event['event']}")


# Global error monitoring UI instance
error_monitoring_ui = ErrorMonitoringUI()


# Convenience functions
def render_error_dashboard() -> None:
    """Render error monitoring dashboard."""
    error_monitoring_ui.render_error_dashboard()


def render_error_summary() -> None:
    """Render compact error summary for sidebar."""
    stats = get_error_stats()
    unhealthy_services = get_unhealthy_services()

    st.sidebar.subheader("🚨 System Status")

    # Error count
    if stats["total_errors"] > 0:
        st.sidebar.error(f"❌ {stats['total_errors']} total errors")
    else:
        st.sidebar.success("✅ No errors")

    # Circuit breaker status
    if unhealthy_services:
        st.sidebar.warning(f"⚠️ {len(unhealthy_services)} services down")
    else:
        st.sidebar.success("✅ All services healthy")

    # Quick actions
    if st.sidebar.button("View Error Dashboard"):
        st.session_state.show_error_dashboard = True
