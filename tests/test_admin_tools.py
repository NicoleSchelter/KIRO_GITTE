"""
Tests for administrative tools and monitoring functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from src.services.admin_statistics_service import AdminStatisticsService
from src.services.monitoring_service import HealthStatus, MonitoringService
from src.ui.admin_ui import AdminUI


class TestMonitoringService:
    """Test monitoring service functionality."""

    def test_monitoring_service_initialization(self):
        """Test monitoring service initializes correctly."""
        monitoring_service = MonitoringService()

        assert monitoring_service.audit_service is not None
        assert monitoring_service.metrics_history == []
        assert monitoring_service.active_alerts == {}
        assert monitoring_service.health_checks == {}
        assert not monitoring_service._monitoring_active

    def test_collect_system_metrics(self):
        """Test system metrics collection."""
        monitoring_service = MonitoringService()

        with (
            patch("psutil.cpu_percent", return_value=45.5),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("psutil.net_io_counters") as mock_network,
            patch("psutil.net_connections", return_value=[1, 2, 3]),
        ):

            # Mock memory object
            mock_memory.return_value.percent = 68.2

            # Mock disk object
            mock_disk_obj = Mock()
            mock_disk_obj.total = 1000000000
            mock_disk_obj.used = 300000000
            mock_disk.return_value = mock_disk_obj

            # Mock network object
            mock_network_obj = Mock()
            mock_network_obj.bytes_sent = 1000
            mock_network_obj.bytes_recv = 2000
            mock_network_obj.packets_sent = 10
            mock_network_obj.packets_recv = 20
            mock_network.return_value = mock_network_obj

            # Mock database methods
            with (
                patch.object(
                    monitoring_service, "_get_recent_response_times", return_value={"chat": 1500.0}
                ),
                patch.object(
                    monitoring_service, "_get_recent_error_rates", return_value={"chat": 2.5}
                ),
            ):

                metrics = monitoring_service.collect_system_metrics()

                assert metrics.cpu_percent == 45.5
                assert metrics.memory_percent == 68.2
                assert metrics.disk_percent == 30.0  # 300M/1000M * 100
                assert metrics.active_connections == 3
                assert metrics.response_times == {"chat": 1500.0}
                assert metrics.error_rates == {"chat": 2.5}

    def test_health_checks(self):
        """Test health check functionality."""
        monitoring_service = MonitoringService()

        with (
            patch.object(monitoring_service, "_check_database_health") as mock_db,
            patch.object(monitoring_service, "_check_llm_health") as mock_llm,
            patch.object(monitoring_service, "_check_image_generation_health") as mock_img,
            patch.object(monitoring_service, "_check_storage_health") as mock_storage,
        ):

            # Mock health check results
            mock_db.return_value.status = HealthStatus.HEALTHY
            mock_llm.return_value.status = HealthStatus.HEALTHY
            mock_img.return_value.status = HealthStatus.WARNING
            mock_storage.return_value.status = HealthStatus.HEALTHY

            health_checks = monitoring_service.perform_health_checks()

            assert len(health_checks) == 4
            assert "database" in health_checks
            assert "llm_service" in health_checks
            assert "image_generation" in health_checks
            assert "storage" in health_checks

    def test_alert_creation(self):
        """Test alert creation and management."""
        monitoring_service = MonitoringService()

        # Create mock metrics that should trigger alerts
        mock_metrics = Mock()
        mock_metrics.cpu_percent = 96.0  # Above critical threshold
        mock_metrics.memory_percent = 75.0  # Normal
        mock_metrics.disk_percent = 85.0  # Normal
        mock_metrics.response_times = {"chat": 12000.0}  # Above critical threshold
        mock_metrics.error_rates = {"chat": 15.0}  # Above critical threshold

        alerts = monitoring_service.check_alerts(mock_metrics)

        # Should create alerts for CPU, response time, and error rate
        assert len(alerts) >= 3

        # Check that alerts were added to active alerts
        assert len(monitoring_service.active_alerts) >= 3

        # Test alert resolution
        first_alert_id = alerts[0].id
        success = monitoring_service.resolve_alert(first_alert_id)
        assert success
        assert monitoring_service.active_alerts[first_alert_id].resolved

    def test_system_status(self):
        """Test system status aggregation."""
        monitoring_service = MonitoringService()

        with patch.object(monitoring_service, "perform_health_checks") as mock_health:
            # Mock health checks
            mock_health.return_value = {
                "database": Mock(
                    status=HealthStatus.HEALTHY,
                    response_time_ms=5.0,
                    message="OK",
                    details={},
                    timestamp=datetime.now(),
                ),
                "llm_service": Mock(
                    status=HealthStatus.WARNING,
                    response_time_ms=2000.0,
                    message="Slow",
                    details={},
                    timestamp=datetime.now(),
                ),
            }

            status = monitoring_service.get_system_status()

            assert "overall_status" in status
            assert "health_checks" in status
            assert "metrics" in status
            assert status["overall_status"] == "warning"  # Should be warning due to LLM service


class TestAdminStatisticsService:
    """Test admin statistics service functionality."""

    def test_statistics_service_initialization(self):
        """Test statistics service initializes correctly."""
        stats_service = AdminStatisticsService()

        assert stats_service.audit_service is not None

    @patch("src.services.admin_statistics_service.get_session")
    def test_user_statistics(self, mock_db_session):
        """Test user statistics collection."""
        stats_service = AdminStatisticsService()

        # Mock database session and results
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=lambda: 100),  # total users
            Mock(scalar=lambda: 5),  # admin users
            Mock(scalar=lambda: 95),  # participant users
            Mock(scalar=lambda: 3),  # new users today
            Mock(scalar=lambda: 12),  # new users this week
            Mock(scalar=lambda: 25),  # new users this month
            Mock(scalar=lambda: 15),  # active users today
            Mock(scalar=lambda: 45),  # active users this week
            Mock(scalar=lambda: 78),  # active users this month
        ]

        user_stats = stats_service.get_user_statistics()

        assert user_stats.total_users == 100
        assert user_stats.admin_users == 5
        assert user_stats.participant_users == 95
        assert user_stats.new_users_today == 3
        assert user_stats.active_users_this_week == 45

    @patch("src.services.admin_statistics_service.get_session")
    def test_system_statistics(self, mock_db_session):
        """Test system statistics collection."""
        stats_service = AdminStatisticsService()

        # Mock database session and results
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Mock query results
        mock_session.execute.side_effect = [
            Mock(scalar=lambda: 250),  # chat sessions
            Mock(scalar=lambda: 150),  # images generated
            Mock(scalar=lambda: 75),  # pald records
            Mock(scalar=lambda: 1000),  # audit logs
            Mock(scalar=lambda: 100),  # consent records
            Mock(scalar=lambda: 1500.0),  # avg response time
            Mock(scalar=lambda: 1000),  # total operations
            Mock(scalar=lambda: 25),  # error operations
        ]

        system_stats = stats_service.get_system_statistics()

        assert system_stats.total_chat_sessions == 250
        assert system_stats.total_images_generated == 150
        assert system_stats.total_pald_records == 75
        assert system_stats.avg_response_time_ms == 1500.0
        assert system_stats.error_rate_percent == 2.5  # 25/1000 * 100

    @patch("src.services.admin_statistics_service.get_session")
    def test_activity_trends(self, mock_db_session):
        """Test activity trends collection."""
        stats_service = AdminStatisticsService()

        # Mock database session and results
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Mock query results with proper iteration
        mock_result = Mock()
        mock_rows = [
            Mock(
                date=datetime.now().date(),
                chat_sessions=10,
                images_generated=5,
                active_users=8,
                avg_response_time=1200.0,
            ),
            Mock(
                date=(datetime.now() - timedelta(days=1)).date(),
                chat_sessions=12,
                images_generated=7,
                active_users=10,
                avg_response_time=1100.0,
            ),
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        mock_session.execute.return_value = mock_result

        trends = stats_service.get_activity_trends(7)

        assert len(trends) == 2
        assert trends[0]["chat_sessions"] == 10
        assert trends[0]["images_generated"] == 5
        assert trends[0]["active_users"] == 8
        assert trends[1]["chat_sessions"] == 12

    def test_dashboard_statistics_integration(self):
        """Test dashboard statistics integration."""
        stats_service = AdminStatisticsService()

        with (
            patch.object(stats_service, "get_user_statistics") as mock_user,
            patch.object(stats_service, "get_system_statistics") as mock_system,
            patch.object(stats_service, "get_pald_statistics") as mock_pald,
            patch.object(stats_service, "get_performance_statistics") as mock_perf,
        ):

            # Mock return values
            mock_user.return_value = Mock(total_users=100, admin_users=5, new_users_today=3)
            mock_system.return_value = Mock(total_chat_sessions=250, error_rate_percent=2.5)
            mock_pald.return_value = Mock(total_pald_records=75, unique_schema_versions=3)
            mock_perf.return_value = Mock(avg_llm_response_time_ms=1500.0, peak_concurrent_users=20)

            dashboard_stats = stats_service.get_dashboard_statistics()

            assert "users" in dashboard_stats
            assert "system" in dashboard_stats
            assert "pald" in dashboard_stats
            assert "performance" in dashboard_stats
            assert dashboard_stats["users"]["total"] == 100
            assert dashboard_stats["system"]["chat_sessions"] == 250


class TestAdminUI:
    """Test admin UI functionality."""

    def test_admin_ui_initialization(self):
        """Test admin UI initializes correctly."""
        admin_ui = AdminUI()

        assert admin_ui.auth_logic is not None
        assert admin_ui.audit_service is not None
        assert admin_ui.monitoring_service is not None
        assert admin_ui.statistics_service is not None

    @patch("streamlit.header")
    @patch("streamlit.columns")
    @patch("streamlit.metric")
    def test_dashboard_overview_rendering(self, mock_metric, mock_columns, mock_header):
        """Test dashboard overview rendering."""
        admin_ui = AdminUI()

        # Mock statistics service
        mock_stats = {
            "users": {"total": 100, "new_today": 3, "active_today": 25, "active_this_week": 60},
            "system": {
                "chat_sessions": 250,
                "images_generated": 150,
                "error_rate_percent": 2.5,
                "uptime_hours": 72.0,
            },
            "pald": {
                "total_records": 75,
                "schema_versions": 3,
                "avg_coverage_percent": 78.5,
                "attribute_candidates": 12,
            },
            "performance": {
                "avg_llm_response_time_ms": 1500.0,
                "peak_concurrent_users": 20,
                "requests_per_hour": 45.2,
                "cache_hit_rate_percent": 85.5,
            },
        }

        # Create mock column objects with context manager support
        mock_col = Mock()
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)

        with (
            patch.object(
                admin_ui.statistics_service, "get_dashboard_statistics", return_value=mock_stats
            ),
            patch.object(admin_ui.statistics_service, "get_activity_trends", return_value=[]),
            patch.object(
                admin_ui.monitoring_service,
                "get_system_status",
                return_value={"overall_status": "healthy", "health_checks": {}, "active_alerts": 0},
            ),
            patch.object(
                admin_ui.statistics_service, "get_user_engagement_metrics", return_value={}
            ),
            patch("streamlit.subheader"),
            patch("streamlit.success"),
            patch("streamlit.write"),
            patch("streamlit.info"),
            patch("streamlit.plotly_chart"),
        ):

            # Mock columns to return appropriate number based on call
            def mock_columns_side_effect(num_cols):
                return [mock_col] * num_cols

            mock_columns.side_effect = mock_columns_side_effect

            # This should not raise an exception
            admin_ui._render_dashboard_overview(uuid4())

            # Verify that header was called
            mock_header.assert_called_with("System Overview")

    def test_export_data_generation(self):
        """Test data export functionality."""
        admin_ui = AdminUI()

        start_date = datetime.now().date() - timedelta(days=7)
        end_date = datetime.now().date()

        with patch.object(
            admin_ui, "_export_user_data", return_value="mock_csv_data"
        ) as mock_export:
            result = admin_ui._generate_export_data("User Data", start_date, end_date, "CSV")

            assert result == "mock_csv_data"
            mock_export.assert_called_once_with(start_date, end_date, "CSV")


class TestIntegration:
    """Integration tests for admin tools."""

    def test_monitoring_and_statistics_integration(self):
        """Test integration between monitoring and statistics services."""
        monitoring_service = MonitoringService()
        stats_service = AdminStatisticsService()

        # Test that both services can be initialized together
        assert monitoring_service is not None
        assert stats_service is not None

        # Test that system status can be retrieved
        with patch.object(monitoring_service, "perform_health_checks", return_value={}):
            status = monitoring_service.get_system_status()
            assert isinstance(status, dict)

    def test_admin_ui_with_services(self):
        """Test admin UI integration with services."""
        admin_ui = AdminUI()

        # Test that all required services are available
        assert admin_ui.monitoring_service is not None
        assert admin_ui.statistics_service is not None

        # Create mock column objects with context manager support
        mock_col = Mock()
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)

        # Mock columns to return appropriate number based on call
        def mock_columns_side_effect(num_cols):
            return [mock_col] * num_cols

        # Test that dashboard can be rendered without errors
        with (
            patch("streamlit.header"),
            patch("streamlit.columns", side_effect=mock_columns_side_effect),
            patch("streamlit.metric"),
            patch("streamlit.subheader"),
            patch("streamlit.success"),
            patch("streamlit.plotly_chart"),
            patch("streamlit.write"),
            patch("streamlit.info"),
        ):

            # Mock service responses with proper structure
            mock_dashboard_stats = {
                "users": {"total": 100, "new_today": 3, "active_today": 25, "active_this_week": 60},
                "system": {
                    "chat_sessions": 250,
                    "images_generated": 150,
                    "error_rate_percent": 2.5,
                    "uptime_hours": 72.0,
                },
                "pald": {
                    "total_records": 75,
                    "schema_versions": 3,
                    "avg_coverage_percent": 78.5,
                    "attribute_candidates": 12,
                },
                "performance": {
                    "avg_llm_response_time_ms": 1500.0,
                    "peak_concurrent_users": 20,
                    "requests_per_hour": 45.2,
                    "cache_hit_rate_percent": 85.5,
                },
            }

            with (
                patch.object(
                    admin_ui.statistics_service,
                    "get_dashboard_statistics",
                    return_value=mock_dashboard_stats,
                ),
                patch.object(admin_ui.statistics_service, "get_activity_trends", return_value=[]),
                patch.object(
                    admin_ui.monitoring_service,
                    "get_system_status",
                    return_value={
                        "overall_status": "healthy",
                        "health_checks": {},
                        "active_alerts": 0,
                    },
                ),
                patch.object(
                    admin_ui.statistics_service, "get_user_engagement_metrics", return_value={}
                ),
            ):

                # This should not raise an exception
                admin_ui._render_dashboard_overview(uuid4())
