"""
Admin UI components for GITTE system.
Provides Streamlit components for administrative functions, data export, and monitoring.
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config.config import get_text
from src.data.database import get_session
from src.data.repositories import get_user_repository
from src.logic.authentication import AuthenticationLogic
from src.logic.pald import PALDManager
from src.services.admin_statistics_service import get_admin_statistics_service
from src.services.audit_service import get_audit_service
from src.services.monitoring_service import get_monitoring_service
from src.services.session_manager import get_session_manager
from src.ui.error_monitoring_ui import render_error_dashboard

logger = logging.getLogger(__name__)


class AdminUI:
    """UI components for administrative functions."""

    def __init__(self):
        self.auth_logic = AuthenticationLogic(
            user_repository=get_user_repository(), session_manager=get_session_manager()
        )
        self.audit_service = get_audit_service()
        self.monitoring_service = get_monitoring_service()
        self.statistics_service = get_admin_statistics_service()

    def render_admin_dashboard(self, admin_user_id: UUID) -> None:
        """
        Render the main admin dashboard.

        Args:
            admin_user_id: Admin user identifier
        """
        st.title(get_text("admin_title"))

        # Admin navigation
        admin_tab = st.selectbox(
            "Admin Section",
            options=[
                "Dashboard Overview",
                "User Management",
                "Data Export",
                "System Monitoring",
                "Performance Analytics",
                "Error Monitoring",
                "PALD Management",
                "Audit Logs",
                "System Health",
                "Reports",
            ],
        )

        # Render selected admin section
        if admin_tab == "Dashboard Overview":
            self._render_dashboard_overview(admin_user_id)
        elif admin_tab == "User Management":
            self._render_user_management(admin_user_id)
        elif admin_tab == "Data Export":
            self._render_data_export(admin_user_id)
        elif admin_tab == "System Monitoring":
            self._render_system_monitoring(admin_user_id)
        elif admin_tab == "Performance Analytics":
            self._render_performance_analytics(admin_user_id)
        elif admin_tab == "Error Monitoring":
            render_error_dashboard()
        elif admin_tab == "PALD Management":
            self._render_pald_management(admin_user_id)
        elif admin_tab == "Audit Logs":
            self._render_audit_logs(admin_user_id)
        elif admin_tab == "System Health":
            self._render_system_health(admin_user_id)
        elif admin_tab == "Reports":
            self._render_reports(admin_user_id)

    def _render_dashboard_overview(self, admin_user_id: UUID) -> None:
        """Render enhanced dashboard overview with comprehensive statistics."""
        st.header("System Overview")

        # Get comprehensive statistics
        dashboard_stats = self.statistics_service.get_dashboard_statistics()

        if "error" in dashboard_stats:
            st.error(f"Error loading dashboard statistics: {dashboard_stats['error']}")
            return

        # Key metrics row 1
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Users",
                dashboard_stats["users"]["total"],
                delta=f"+{dashboard_stats['users']['new_today']} today",
            )

        with col2:
            st.metric(
                "Active Users (24h)",
                dashboard_stats["users"]["active_today"],
                delta=f"{dashboard_stats['users']['active_this_week']} this week",
            )

        with col3:
            st.metric("Chat Sessions", dashboard_stats["system"]["chat_sessions"], delta=None)

        with col4:
            st.metric("Images Generated", dashboard_stats["system"]["images_generated"], delta=None)

        # Key metrics row 2
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "PALD Records",
                dashboard_stats["pald"]["total_records"],
                delta=f"{dashboard_stats['pald']['schema_versions']} schema versions",
            )

        with col2:
            avg_response = dashboard_stats["performance"]["avg_llm_response_time_ms"]
            st.metric(
                "Avg Response Time", f"{avg_response:.0f}ms" if avg_response else "N/A", delta=None
            )

        with col3:
            error_rate = dashboard_stats["system"]["error_rate_percent"]
            st.metric("Error Rate", f"{error_rate:.1f}%" if error_rate else "0%", delta=None)

        with col4:
            uptime = dashboard_stats["system"]["uptime_hours"]
            st.metric("System Uptime", f"{uptime:.1f}h" if uptime else "N/A", delta=None)

        # Activity trends chart
        st.subheader("Activity Trends (Last 7 Days)")

        activity_trends = self.statistics_service.get_activity_trends(7)
        if activity_trends:
            # Convert to DataFrame for plotting
            df = pd.DataFrame(activity_trends)
            df["date"] = pd.to_datetime(df["date"])

            fig = px.line(
                df,
                x="date",
                y=["chat_sessions", "images_generated", "active_users"],
                title="Daily Activity Trends",
                labels={"date": "Date", "value": "Count", "variable": "Metric"},
            )
            fig.update_layout(xaxis_title="Date", yaxis_title="Count", legend_title="Metrics")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No activity trend data available")

        # System health and alerts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("System Health")
            system_status = self.monitoring_service.get_system_status()

            overall_status = system_status.get("overall_status", "unknown")
            if overall_status == "healthy":
                st.success("🟢 System Healthy")
            elif overall_status == "warning":
                st.warning("🟡 System Warning")
            elif overall_status == "critical":
                st.error("🔴 System Critical")
            else:
                st.info("⚪ Status Unknown")

            # Service status
            health_checks = system_status.get("health_checks", {})
            for service, check in health_checks.items():
                status_icon = {
                    "healthy": "🟢",
                    "warning": "🟡",
                    "critical": "🔴",
                    "unknown": "⚪",
                }.get(check["status"], "⚪")

                response_time = check.get("response_time_ms")
                response_str = f" ({response_time:.0f}ms)" if response_time else ""

                st.write(f"{status_icon} **{service.title()}**{response_str}")

        with col2:
            st.subheader("Active Alerts")
            active_alerts = self.monitoring_service.get_active_alerts()

            if active_alerts:
                for alert in active_alerts[:5]:  # Show top 5 alerts
                    level_icon = {"info": "ℹ️", "warning": "⚠️", "error": "🚨", "critical": "🔥"}.get(
                        alert["level"], "ℹ️"
                    )

                    st.write(f"{level_icon} **{alert['service']}**: {alert['message']}")
            else:
                st.success("✅ No active alerts")

        # Quick stats summary
        st.subheader("Quick Statistics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**User Engagement**")
            engagement = self.statistics_service.get_user_engagement_metrics()
            st.write(f"• Avg sessions/user: {engagement.get('avg_sessions_per_user', 0):.1f}")
            st.write(f"• 7-day retention: {engagement.get('retention_7_day_percent', 0):.1f}%")
            st.write(f"• 30-day retention: {engagement.get('retention_30_day_percent', 0):.1f}%")

        with col2:
            st.write("**PALD Analytics**")
            st.write(f"• Schema versions: {dashboard_stats['pald']['schema_versions']}")
            st.write(f"• Avg coverage: {dashboard_stats['pald']['avg_coverage_percent']:.1f}%")
            st.write(f"• Attribute candidates: {dashboard_stats['pald']['attribute_candidates']}")

        with col3:
            st.write("**Performance**")
            st.write(
                f"• Peak concurrent users: {dashboard_stats['performance']['peak_concurrent_users']}"
            )
            st.write(f"• Requests/hour: {dashboard_stats['performance']['requests_per_hour']:.1f}")
            st.write(
                f"• Cache hit rate: {dashboard_stats['performance']['cache_hit_rate_percent']:.1f}%"
            )

    def _render_user_management(self, admin_user_id: UUID) -> None:
        """Render user management interface."""
        st.header("User Management")

        # User statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            try:
                with get_session() as db_session:
                    total_users = db_session.execute("SELECT COUNT(*) FROM users").scalar()
                st.metric("Total Users", total_users or 0)
            except:
                st.metric("Total Users", "N/A")

        with col2:
            try:
                with get_session() as db_session:
                    admin_count = db_session.execute(
                        "SELECT COUNT(*) FROM users WHERE role = 'ADMIN'"
                    ).scalar()
                st.metric("Admin Users", admin_count or 0)
            except:
                st.metric("Admin Users", "N/A")

        with col3:
            try:
                with get_session() as db_session:
                    participant_count = db_session.execute(
                        "SELECT COUNT(*) FROM users WHERE role = 'PARTICIPANT'"
                    ).scalar()
                st.metric("Participants", participant_count or 0)
            except:
                st.metric("Participants", "N/A")

        # User list
        st.subheader("User List")

        try:
            with get_session() as db_session:
                users_query = """
                SELECT id, username, role, created_at, pseudonym 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 50
                """
                result = db_session.execute(users_query)
                users = result.fetchall()

                if users:
                    user_data = []
                    for user in users:
                        user_data.append(
                            {
                                "ID": str(user.id)[:8] + "...",
                                "Username": user.username,
                                "Role": user.role,
                                "Created": (
                                    user.created_at.strftime("%Y-%m-%d %H:%M")
                                    if user.created_at
                                    else "N/A"
                                ),
                                "Pseudonym": user.pseudonym,
                            }
                        )

                    df = pd.DataFrame(user_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No users found.")

        except Exception as e:
            st.error(f"Error loading users: {e}")

    def _render_data_export(self, admin_user_id: UUID) -> None:
        """Render data export interface."""
        st.header("Data Export")

        # Export options
        export_type = st.selectbox(
            "Select data to export",
            options=["User Data", "PALD Data", "Audit Logs", "Chat History", "Generated Images"],
        )

        # Date range filter
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))

        with col2:
            end_date = st.date_input("End Date", value=datetime.now())

        # Export format
        export_format = st.radio("Export Format", options=["CSV", "JSON"], horizontal=True)

        # Additional filters
        with st.expander("Additional Filters"):
            if export_type == "User Data":
                st.multiselect("User Roles", options=["ADMIN", "PARTICIPANT"])
            elif export_type == "Audit Logs":
                st.text_input("Operation Filter (optional)")
            elif export_type == "PALD Data":
                st.text_input("Schema Version (optional)")

        # Export button
        if st.button("Generate Export", type="primary"):
            with st.spinner("Generating export..."):
                try:
                    export_data = self._generate_export_data(
                        export_type, start_date, end_date, export_format
                    )

                    if export_data:
                        filename = f"gitte_{export_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format.lower()}"

                        st.download_button(
                            label=f"Download {export_type} Export",
                            data=export_data,
                            file_name=filename,
                            mime="text/csv" if export_format == "CSV" else "application/json",
                        )

                        st.success("Export generated successfully!")
                    else:
                        st.warning("No data found for the specified criteria.")

                except Exception as e:
                    st.error(f"Export failed: {e}")

    def _render_system_monitoring(self, admin_user_id: UUID) -> None:
        """Render system monitoring interface."""
        st.header("System Monitoring")

        # Performance metrics
        st.subheader("Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Avg Response Time", "1.2s", "-0.3s")

        with col2:
            st.metric("Error Rate", "0.5%", "-0.2%")

        with col3:
            st.metric("Uptime", "99.8%", "+0.1%")

        with col4:
            st.metric("Active Connections", "15", "+3")

        # Service status
        st.subheader("Service Status")

        services = [
            {"name": "Database", "status": "healthy", "response_time": "5ms"},
            {"name": "LLM Service", "status": "healthy", "response_time": "1.2s"},
            {"name": "Image Generation", "status": "healthy", "response_time": "15s"},
            {"name": "Storage", "status": "healthy", "response_time": "10ms"},
        ]

        for service in services:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                status_icon = "🟢" if service["status"] == "healthy" else "🔴"
                st.write(f"{status_icon} **{service['name']}**")

            with col2:
                st.write(service["status"].title())

            with col3:
                st.write(service["response_time"])

        # Resource usage
        st.subheader("Resource Usage")

        # Mock resource data
        resource_data = pd.DataFrame(
            {
                "Time": pd.date_range(start="2024-01-01", periods=24, freq="H"),
                "CPU %": [20 + 10 * np.sin(i / 4) + np.random.normal(0, 2) for i in range(24)],
                "Memory %": [60 + 15 * np.sin(i / 6) + np.random.normal(0, 3) for i in range(24)],
                "Disk %": [30 + 5 * np.sin(i / 8) + np.random.normal(0, 1) for i in range(24)],
            }
        )

        fig = px.line(
            resource_data,
            x="Time",
            y=["CPU %", "Memory %", "Disk %"],
            title="Resource Usage (Last 24 Hours)",
        )
        st.plotly_chart(fig, use_container_width=True)

    def _render_performance_analytics(self, admin_user_id: UUID) -> None:
        """Render performance analytics interface."""
        st.header("Performance Analytics")

        # Performance overview
        performance_stats = self.statistics_service.get_performance_statistics()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Avg LLM Response", f"{performance_stats.avg_llm_response_time_ms:.0f}ms")

        with col2:
            st.metric(
                "Avg Image Generation", f"{performance_stats.avg_image_generation_time_ms:.0f}ms"
            )

        with col3:
            st.metric("Peak Concurrent Users", performance_stats.peak_concurrent_users)

        with col4:
            st.metric("Requests/Hour", f"{performance_stats.requests_per_hour:.1f}")

        # Error rates by operation
        st.subheader("Error Rates by Operation")

        if performance_stats.error_rate_by_operation:
            error_df = pd.DataFrame(
                [
                    {"Operation": op, "Error Rate %": rate}
                    for op, rate in performance_stats.error_rate_by_operation.items()
                ]
            )

            fig = px.bar(
                error_df,
                x="Operation",
                y="Error Rate %",
                title="Error Rates by Operation (Last 24 Hours)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No error rate data available")

        # Response time trends
        st.subheader("Response Time Trends")

        metrics_history = self.monitoring_service.get_metrics_history(24)
        if metrics_history:
            # Convert to DataFrame
            df = pd.DataFrame(metrics_history)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Extract response times for different operations
            response_times_data = []
            for _, row in df.iterrows():
                for operation, time_ms in row["response_times"].items():
                    response_times_data.append(
                        {
                            "timestamp": row["timestamp"],
                            "operation": operation,
                            "response_time_ms": time_ms,
                        }
                    )

            if response_times_data:
                rt_df = pd.DataFrame(response_times_data)
                fig = px.line(
                    rt_df,
                    x="timestamp",
                    y="response_time_ms",
                    color="operation",
                    title="Response Time Trends (Last 24 Hours)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No response time trend data available")
        else:
            st.info("No metrics history available")

    def _render_system_health(self, admin_user_id: UUID) -> None:
        """Render system health monitoring interface."""
        st.header("System Health Monitoring")

        # Overall system status
        system_status = self.monitoring_service.get_system_status()

        col1, col2, col3 = st.columns(3)

        with col1:
            overall_status = system_status.get("overall_status", "unknown")
            status_color = {
                "healthy": "🟢",
                "warning": "🟡",
                "critical": "🔴",
                "unknown": "⚪",
            }.get(overall_status, "⚪")

            st.metric("Overall Status", f"{status_color} {overall_status.title()}")

        with col2:
            active_alerts_count = system_status.get("active_alerts", 0)
            st.metric("Active Alerts", active_alerts_count)

        with col3:
            uptime = system_status.get("uptime_hours", 0)
            st.metric("Uptime", f"{uptime:.1f} hours")

        # Service health checks
        st.subheader("Service Health Checks")

        health_checks = system_status.get("health_checks", {})

        for service_name, check in health_checks.items():
            with st.expander(f"{service_name.title()} - {check['status'].title()}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Status:** {check['status']}")
                    st.write(f"**Message:** {check['message']}")
                    if check.get("response_time_ms"):
                        st.write(f"**Response Time:** {check['response_time_ms']:.0f}ms")

                with col2:
                    st.write(f"**Last Check:** {check['timestamp']}")
                    if check.get("details"):
                        st.write("**Details:**")
                        st.json(check["details"])

        # Active alerts
        st.subheader("Active Alerts")

        active_alerts = self.monitoring_service.get_active_alerts()

        if active_alerts:
            for alert in active_alerts:
                level_color = {
                    "info": "blue",
                    "warning": "orange",
                    "error": "red",
                    "critical": "red",
                }.get(alert["level"], "gray")

                with st.container():
                    st.markdown(
                        f"**:{level_color}[{alert['level'].upper()}]** - {alert['service']}"
                    )
                    st.write(alert["message"])
                    st.caption(f"Triggered: {alert['timestamp']}")

                    if st.button("Resolve Alert", key=f"resolve_{alert['id']}"):
                        if self.monitoring_service.resolve_alert(alert["id"]):
                            st.success("Alert resolved!")
                            st.experimental_rerun()
                        else:
                            st.error("Failed to resolve alert")

                    st.divider()
        else:
            st.success("✅ No active alerts")

        # Resource usage
        st.subheader("Current Resource Usage")

        metrics = system_status.get("metrics", {})

        col1, col2, col3 = st.columns(3)

        with col1:
            cpu_percent = metrics.get("cpu_percent", 0)
            st.metric("CPU Usage", f"{cpu_percent:.1f}%")
            st.progress(cpu_percent / 100)

        with col2:
            memory_percent = metrics.get("memory_percent", 0)
            st.metric("Memory Usage", f"{memory_percent:.1f}%")
            st.progress(memory_percent / 100)

        with col3:
            disk_percent = metrics.get("disk_percent", 0)
            st.metric("Disk Usage", f"{disk_percent:.1f}%")
            st.progress(disk_percent / 100)

    def _render_reports(self, admin_user_id: UUID) -> None:
        """Render reports generation interface."""
        st.header("Administrative Reports")

        # Report type selection
        report_type = st.selectbox(
            "Select Report Type",
            options=["user_activity", "system_performance", "pald_analysis", "audit_summary"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

        # Date range selection
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))

        with col2:
            end_date = st.date_input("End Date", value=datetime.now())

        # Additional filters
        with st.expander("Additional Filters"):
            if report_type == "user_activity":
                user_role_filter = st.multiselect("User Roles", options=["ADMIN", "PARTICIPANT"])
                include_inactive = st.checkbox("Include Inactive Users")

                filters = {"user_roles": user_role_filter, "include_inactive": include_inactive}

            elif report_type == "system_performance":
                operation_filter = st.multiselect(
                    "Operations", options=["chat", "image_generation", "pald_update", "login"]
                )
                min_response_time = st.number_input("Min Response Time (ms)", value=0)

                filters = {"operations": operation_filter, "min_response_time": min_response_time}

            elif report_type == "pald_analysis":
                schema_version_filter = st.text_input("Schema Version Filter")
                min_coverage = st.slider("Minimum Coverage %", 0, 100, 0)

                filters = {"schema_version": schema_version_filter, "min_coverage": min_coverage}

            else:  # audit_summary
                status_filter = st.multiselect("Status", options=["success", "error", "pending"])
                operation_filter = st.text_input("Operation Filter")

                filters = {"status": status_filter, "operation": operation_filter}

        # Generate report
        if st.button("Generate Report", type="primary"):
            with st.spinner("Generating report..."):
                try:
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    end_datetime = datetime.combine(end_date, datetime.max.time())

                    report = self.statistics_service.generate_export_report(
                        report_type, start_datetime, end_datetime, filters
                    )

                    if "error" in report:
                        st.error(f"Report generation failed: {report['error']}")
                    else:
                        st.success("Report generated successfully!")

                        # Display report summary
                        st.subheader("Report Summary")
                        st.write(
                            f"**Report Type:** {report['report_type'].replace('_', ' ').title()}"
                        )
                        st.write(f"**Date Range:** {report['start_date']} to {report['end_date']}")
                        st.write(f"**Generated:** {report['generated_at']}")

                        if report.get("filters"):
                            st.write("**Filters Applied:**")
                            st.json(report["filters"])

                        # Download report
                        report_json = json.dumps(report, indent=2)
                        filename = f"gitte_{report_type}_{start_date}_{end_date}.json"

                        st.download_button(
                            label="Download Report (JSON)",
                            data=report_json,
                            file_name=filename,
                            mime="application/json",
                        )

                        # Display report data preview
                        if report.get("data"):
                            st.subheader("Report Data Preview")
                            st.json(report["data"])

                except Exception as e:
                    st.error(f"Error generating report: {e}")

        # Recent reports
        st.subheader("Quick Reports")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("User Activity (Last 7 Days)"):
                activity_trends = self.statistics_service.get_activity_trends(7)
                if activity_trends:
                    st.json(activity_trends)
                else:
                    st.info("No activity data available")

        with col2:
            if st.button("System Health Summary"):
                health_summary = self.statistics_service.get_system_health_summary()
                if health_summary:
                    st.json(health_summary)
                else:
                    st.info("No health data available")

    def _render_pald_management(self, admin_user_id: UUID) -> None:
        """Render PALD management interface."""
        st.header("PALD Management")

        # PALD statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            try:
                with get_session() as db_session:
                    pald_count = db_session.execute("SELECT COUNT(*) FROM pald_data").scalar()
                st.metric("Total PALD Records", pald_count or 0)
            except:
                st.metric("Total PALD Records", "N/A")

        with col2:
            try:
                with get_session() as db_session:
                    schema_versions = db_session.execute(
                        "SELECT COUNT(DISTINCT schema_version) FROM pald_data"
                    ).scalar()
                st.metric("Schema Versions", schema_versions or 0)
            except:
                st.metric("Schema Versions", "N/A")

        with col3:
            try:
                with get_session() as db_session:
                    avg_coverage = db_session.execute(
                        "SELECT AVG(jsonb_array_length(pald_content::jsonb)) FROM pald_data"
                    ).scalar()
                st.metric("Avg Coverage", f"{avg_coverage:.1f}" if avg_coverage else "N/A")
            except:
                st.metric("Avg Coverage", "N/A")

        # Schema evolution tracking
        st.subheader("Schema Evolution")

        try:
            with get_session() as db_session:
                candidates_query = """
                SELECT attribute_name, mention_count, threshold_reached, added_to_schema
                FROM pald_attribute_candidates 
                ORDER BY mention_count DESC 
                LIMIT 10
                """
                result = db_session.execute(candidates_query)
                candidates = result.fetchall()

                if candidates:
                    candidate_data = []
                    for candidate in candidates:
                        candidate_data.append(
                            {
                                "Attribute": candidate.attribute_name,
                                "Mentions": candidate.mention_count,
                                "Threshold Reached": "✅" if candidate.threshold_reached else "❌",
                                "Added to Schema": "✅" if candidate.added_to_schema else "❌",
                            }
                        )

                    df = pd.DataFrame(candidate_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No attribute candidates found.")

        except Exception as e:
            st.error(f"Error loading PALD data: {e}")

        # PALD comparison tool
        st.subheader("PALD Comparison Tool")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Select First PALD Record**")
            try:
                with get_session() as db_session:
                    pald_query = """
                    SELECT p.id, u.pseudonym, p.schema_version, p.created_at
                    FROM pald_data p
                    JOIN users u ON p.user_id = u.id
                    ORDER BY p.created_at DESC
                    LIMIT 20
                    """
                    result = db_session.execute(pald_query)
                    pald_records = result.fetchall()

                    if pald_records:
                        pald_options_1 = {
                            f"{record.pseudonym} - v{record.schema_version} ({record.created_at.strftime('%Y-%m-%d')})": record.id
                            for record in pald_records
                        }
                        selected_pald_1 = st.selectbox(
                            "First PALD", options=list(pald_options_1.keys()), key="pald_1"
                        )
                        pald_id_1 = pald_options_1.get(selected_pald_1)
                    else:
                        st.info("No PALD records available")
                        pald_id_1 = None
            except Exception as e:
                st.error(f"Error loading PALD records: {e}")
                pald_id_1 = None

        with col2:
            st.write("**Select Second PALD Record**")
            if pald_records:
                pald_options_2 = {
                    f"{record.pseudonym} - v{record.schema_version} ({record.created_at.strftime('%Y-%m-%d')})": record.id
                    for record in pald_records
                }
                selected_pald_2 = st.selectbox(
                    "Second PALD", options=list(pald_options_2.keys()), key="pald_2"
                )
                pald_id_2 = pald_options_2.get(selected_pald_2)
            else:
                pald_id_2 = None

        if pald_id_1 and pald_id_2 and st.button("Compare PALDs"):
            try:
                pald_manager = PALDManager()

                # Get PALD data
                with get_session() as db_session:
                    pald_1_result = db_session.execute(
                        "SELECT pald_content FROM pald_data WHERE id = %s", (pald_id_1,)
                    ).fetchone()
                    pald_2_result = db_session.execute(
                        "SELECT pald_content FROM pald_data WHERE id = %s", (pald_id_2,)
                    ).fetchone()

                    if pald_1_result and pald_2_result:
                        pald_1_data = pald_1_result.pald_content
                        pald_2_data = pald_2_result.pald_content

                        # Calculate diff
                        diff_result = pald_manager.calculate_pald_diff(pald_1_data, pald_2_data)

                        st.subheader("PALD Comparison Results")

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Added Fields", len(diff_result.get("added", [])))

                        with col2:
                            st.metric("Removed Fields", len(diff_result.get("removed", [])))

                        with col3:
                            st.metric("Modified Fields", len(diff_result.get("modified", [])))

                        # Show detailed differences
                        if diff_result.get("added"):
                            st.write("**Added Fields:**")
                            for field in diff_result["added"]:
                                st.write(f"• {field}")

                        if diff_result.get("removed"):
                            st.write("**Removed Fields:**")
                            for field in diff_result["removed"]:
                                st.write(f"• {field}")

                        if diff_result.get("modified"):
                            st.write("**Modified Fields:**")
                            for field, changes in diff_result["modified"].items():
                                st.write(f"• **{field}**: {changes['old']} → {changes['new']}")

                        if not any(
                            [
                                diff_result.get("added"),
                                diff_result.get("removed"),
                                diff_result.get("modified"),
                            ]
                        ):
                            st.success("✅ PALDs are identical")

                    else:
                        st.error("Could not load PALD data for comparison")

            except Exception as e:
                st.error(f"Error comparing PALDs: {e}")

        # PALD coverage analysis
        st.subheader("PALD Coverage Analysis")

        try:
            with get_session() as db_session:
                coverage_query = """
                SELECT 
                    u.pseudonym,
                    p.schema_version,
                    p.pald_content,
                    p.created_at
                FROM pald_data p
                JOIN users u ON p.user_id = u.id
                ORDER BY p.created_at DESC
                LIMIT 10
                """
                result = db_session.execute(coverage_query)
                coverage_records = result.fetchall()

                if coverage_records:
                    coverage_data = []
                    pald_manager = PALDManager()

                    for record in coverage_records:
                        coverage = pald_manager.calculate_pald_coverage(record.pald_content)
                        coverage_data.append(
                            {
                                "User": record.pseudonym,
                                "Schema Version": record.schema_version,
                                "Coverage %": f"{coverage:.1f}%",
                                "Created": (
                                    record.created_at.strftime("%Y-%m-%d %H:%M")
                                    if record.created_at
                                    else "N/A"
                                ),
                            }
                        )

                    st.write("**Recent PALD Coverage Analysis:**")
                    df = pd.DataFrame(coverage_data)
                    st.dataframe(df, use_container_width=True)

                    # Coverage statistics
                    coverages = [float(row["Coverage %"].replace("%", "")) for row in coverage_data]

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Average Coverage", f"{np.mean(coverages):.1f}%")

                    with col2:
                        st.metric("Min Coverage", f"{np.min(coverages):.1f}%")

                    with col3:
                        st.metric("Max Coverage", f"{np.max(coverages):.1f}%")

                else:
                    st.info("No PALD records available for coverage analysis")

        except Exception as e:
            st.error(f"Error performing coverage analysis: {e}")

    def _render_audit_logs(self, admin_user_id: UUID) -> None:
        """Render audit logs interface."""
        st.header("Audit Logs")

        # Audit statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            try:
                with get_session() as db_session:
                    total_logs = db_session.execute("SELECT COUNT(*) FROM audit_logs").scalar()
                st.metric("Total Log Entries", total_logs or 0)
            except:
                st.metric("Total Log Entries", "N/A")

        with col2:
            try:
                with get_session() as db_session:
                    today_logs = db_session.execute(
                        "SELECT COUNT(*) FROM audit_logs WHERE DATE(created_at) = CURRENT_DATE"
                    ).scalar()
                st.metric("Today's Entries", today_logs or 0)
            except:
                st.metric("Today's Entries", "N/A")

        with col3:
            try:
                with get_session() as db_session:
                    error_logs = db_session.execute(
                        "SELECT COUNT(*) FROM audit_logs WHERE status = 'error'"
                    ).scalar()
                st.metric("Error Entries", error_logs or 0)
            except:
                st.metric("Error Entries", "N/A")

        # Log filters
        st.subheader("Filter Logs")

        col1, col2, col3 = st.columns(3)

        with col1:
            operation_filter = st.selectbox(
                "Operation",
                options=["All", "chat", "image_generation", "pald_update", "login", "consent"],
            )

        with col2:
            status_filter = st.selectbox("Status", options=["All", "success", "error", "pending"])

        with col3:
            limit = st.selectbox("Show", options=[10, 25, 50, 100], index=1)

        # Display logs
        try:
            with get_session() as db_session:
                query = "SELECT * FROM audit_logs"
                conditions = []

                if operation_filter != "All":
                    conditions.append(f"operation = '{operation_filter}'")

                if status_filter != "All":
                    conditions.append(f"status = '{status_filter}'")

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += f" ORDER BY created_at DESC LIMIT {limit}"

                result = db_session.execute(query)
                logs = result.fetchall()

                if logs:
                    log_data = []
                    for log in logs:
                        log_data.append(
                            {
                                "Time": (
                                    log.created_at.strftime("%Y-%m-%d %H:%M:%S")
                                    if log.created_at
                                    else "N/A"
                                ),
                                "Operation": log.operation,
                                "Status": log.status,
                                "User ID": str(log.user_id)[:8] + "..." if log.user_id else "N/A",
                                "Model": log.model_used or "N/A",
                                "Latency (ms)": log.latency_ms or "N/A",
                            }
                        )

                    df = pd.DataFrame(log_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No audit logs found matching the criteria.")

        except Exception as e:
            st.error(f"Error loading audit logs: {e}")

    def _check_system_health(self) -> dict[str, Any]:
        """Check overall system health."""
        try:
            # Check database connection
            with get_session() as db_session:
                db_session.execute("SELECT 1")

            # Check other services (mock for now)
            return {"status": "Healthy", "delta": None}

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {"status": "Degraded", "delta": "⚠️"}

    def _get_system_alerts(self) -> list[dict[str, str]]:
        """Get current system alerts."""
        alerts = []

        try:
            # Check for high error rates (mock logic)
            # In production, this would check real metrics

            # Example alerts
            alerts.append({"level": "info", "message": "System running normally"})

            return alerts

        except Exception as e:
            logger.error(f"Error getting system alerts: {e}")
            return [{"level": "error", "message": "Error checking system alerts"}]

    def _generate_export_data(
        self, export_type: str, start_date, end_date, export_format: str
    ) -> str | None:
        """Generate export data based on type and format."""
        try:
            if export_type == "User Data":
                return self._export_user_data(start_date, end_date, export_format)
            elif export_type == "PALD Data":
                return self._export_pald_data(start_date, end_date, export_format)
            elif export_type == "Audit Logs":
                return self._export_audit_logs(start_date, end_date, export_format)
            else:
                return None

        except Exception as e:
            logger.error(f"Error generating export data: {e}")
            return None

    def _export_user_data(self, start_date, end_date, export_format: str) -> str:
        """Export user data."""
        with get_session() as db_session:
            query = """
            SELECT username, role, created_at, pseudonym
            FROM users 
            WHERE created_at BETWEEN %s AND %s
            ORDER BY created_at DESC
            """

            result = db_session.execute(query, (start_date, end_date))
            users = result.fetchall()

            if export_format == "CSV":
                import io

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Username", "Role", "Created At", "Pseudonym"])

                for user in users:
                    writer.writerow(
                        [
                            user.username,
                            user.role,
                            user.created_at.isoformat() if user.created_at else "",
                            user.pseudonym,
                        ]
                    )

                return output.getvalue()

            else:  # JSON
                user_data = []
                for user in users:
                    user_data.append(
                        {
                            "username": user.username,
                            "role": user.role,
                            "created_at": user.created_at.isoformat() if user.created_at else None,
                            "pseudonym": user.pseudonym,
                        }
                    )

                return json.dumps(user_data, indent=2)

    def _export_pald_data(self, start_date, end_date, export_format: str) -> str:
        """Export PALD data."""
        with get_session() as db_session:
            query = """
            SELECT p.pald_content, p.schema_version, p.created_at, u.pseudonym
            FROM pald_data p
            JOIN users u ON p.user_id = u.id
            WHERE p.created_at BETWEEN %s AND %s
            ORDER BY p.created_at DESC
            """

            result = db_session.execute(query, (start_date, end_date))
            pald_records = result.fetchall()

            if export_format == "JSON":
                pald_data = []
                for record in pald_records:
                    pald_data.append(
                        {
                            "pald_content": record.pald_content,
                            "schema_version": record.schema_version,
                            "created_at": (
                                record.created_at.isoformat() if record.created_at else None
                            ),
                            "user_pseudonym": record.pseudonym,
                        }
                    )

                return json.dumps(pald_data, indent=2)

            else:  # CSV
                # For CSV, we'll flatten the PALD content
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["User Pseudonym", "Schema Version", "Created At", "PALD Content"])

                for record in pald_records:
                    writer.writerow(
                        [
                            record.pseudonym,
                            record.schema_version,
                            record.created_at.isoformat() if record.created_at else "",
                            json.dumps(record.pald_content),
                        ]
                    )

                return output.getvalue()

    def _export_audit_logs(self, start_date, end_date, export_format: str) -> str:
        """Export audit logs."""
        with get_session() as db_session:
            query = """
            SELECT a.operation, a.status, a.model_used, a.latency_ms, a.created_at, u.pseudonym
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.created_at BETWEEN %s AND %s
            ORDER BY a.created_at DESC
            """

            result = db_session.execute(query, (start_date, end_date))
            logs = result.fetchall()

            if export_format == "CSV":
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "Operation",
                        "Status",
                        "Model Used",
                        "Latency (ms)",
                        "Created At",
                        "User Pseudonym",
                    ]
                )

                for log in logs:
                    writer.writerow(
                        [
                            log.operation,
                            log.status,
                            log.model_used or "",
                            log.latency_ms or "",
                            log.created_at.isoformat() if log.created_at else "",
                            log.pseudonym or "",
                        ]
                    )

                return output.getvalue()

            else:  # JSON
                log_data = []
                for log in logs:
                    log_data.append(
                        {
                            "operation": log.operation,
                            "status": log.status,
                            "model_used": log.model_used,
                            "latency_ms": log.latency_ms,
                            "created_at": log.created_at.isoformat() if log.created_at else None,
                            "user_pseudonym": log.pseudonym,
                        }
                    )

                return json.dumps(log_data, indent=2)


def render_admin_ui(admin_user_id: UUID) -> None:
    """
    Main function to render admin UI.

    Args:
        admin_user_id: Admin user identifier
    """
    admin_ui = AdminUI()
    admin_ui.render_admin_dashboard(admin_user_id)
