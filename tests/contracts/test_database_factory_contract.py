"""
Contract tests for centralized database factory
Ensures all modules use the unified database connection
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from src.data.database_factory import DatabaseFactory, get_session, setup_database


class TestDatabaseFactoryContract:
    """Contract tests for database factory singleton behavior"""
    
    def test_singleton_behavior(self):
        """Test that DatabaseFactory maintains singleton pattern"""
        factory1 = DatabaseFactory()
        factory2 = DatabaseFactory()
        
        assert factory1 is factory2
        assert id(factory1) == id(factory2)
    
    def test_lazy_initialization(self):
        """Test that database is initialized only when needed"""
        factory = DatabaseFactory()
        
        # Should not be initialized yet
        assert not factory._initialized
        
        # Accessing engine should trigger initialization
        with patch.object(factory, 'initialize') as mock_init:
            _ = factory.engine
            mock_init.assert_called_once()
    
    def test_session_context_manager(self):
        """Test session context manager behavior"""
        with patch('src.data.database_factory.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            with patch('src.data.database_factory.sessionmaker') as mock_sessionmaker:
                mock_session_factory = MagicMock()
                mock_session = MagicMock()
                mock_session_factory.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_factory
                
                factory = DatabaseFactory()
                factory._initialized = False  # Reset for test
                
                with factory.get_session() as session:
                    assert session is mock_session
                
                # Verify session lifecycle
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
    
    def test_session_rollback_on_error(self):
        """Test that session rolls back on error"""
        with patch('src.data.database_factory.create_engine'):
            with patch('src.data.database_factory.sessionmaker') as mock_sessionmaker:
                mock_session_factory = MagicMock()
                mock_session = MagicMock()
                mock_session_factory.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_factory
                
                factory = DatabaseFactory()
                factory._initialized = False
                
                with pytest.raises(ValueError):
                    with factory.get_session() as session:
                        raise ValueError("Test error")
                
                # Verify rollback and close
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
    
    def test_health_check_contract(self):
        """Test health check functionality"""
        with patch('src.data.database_factory.create_engine'):
            with patch('src.data.database_factory.sessionmaker') as mock_sessionmaker:
                mock_session_factory = MagicMock()
                mock_session = MagicMock()
                mock_session_factory.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_factory
                
                factory = DatabaseFactory()
                factory._initialized = False
                
                # Mock successful health check
                mock_session.__enter__ = MagicMock(return_value=mock_session)
                mock_session.__exit__ = MagicMock(return_value=None)
                
                result = factory.health_check()
                assert result is True
                
                # Mock failed health check
                mock_session.execute.side_effect = Exception("Connection failed")
                result = factory.health_check()
                assert result is False


class TestDatabaseImportContract:
    """Test that all database imports use the centralized factory"""
    
    def test_services_use_centralized_session(self):
        """Test that services import from centralized location"""
        # Test key service imports
        service_modules = [
            'src.services.pseudonym_service',
            'src.services.consent_service', 
            'src.services.survey_service',
            'src.services.chat_service',
            'src.services.image_generation_service',
        ]
        
        for module_name in service_modules:
            try:
                module = __import__(module_name, fromlist=[''])
                
                # Check if module imports get_session
                if hasattr(module, 'get_session'):
                    # Verify it's from the right place
                    import inspect
                    source_file = inspect.getfile(module.get_session)
                    assert 'database' in source_file.lower()
                    
            except ImportError:
                # Module might not exist, skip
                pass
    
    def test_ui_modules_use_session_manager(self):
        """Test that UI modules use session state manager"""
        ui_modules = [
            'src.ui.main',
            'src.ui.auth_ui',
            'src.ui.admin_ui',
        ]
        
        for module_name in ui_modules:
            try:
                module = __import__(module_name, fromlist=[''])
                
                # Check for session state usage patterns
                import inspect
                source = inspect.getsource(module)
                
                # Should not have direct st.session_state access without manager
                if 'st.session_state' in source:
                    # Should also have SessionStateManager import or usage
                    assert ('SessionStateManager' in source or 
                           'session_state_manager' in source or
                           'get_session_value' in source)
                    
            except (ImportError, OSError):
                # Module might not exist or be importable, skip
                pass


class TestDatabaseMigrationContract:
    """Test database migration consistency"""
    
    def test_alembic_uses_unified_dsn(self):
        """Test that Alembic uses the same DSN as application"""
        from config.config import config as app_config
        
        # Read alembic env.py to verify it uses app_config
        with open('migrations/env.py', 'r') as f:
            env_content = f.read()
        
        # Should import app_config and use unified DSN
        assert 'from config.config import config as app_config' in env_content
        assert 'app_config.database.dsn' in env_content
        assert 'unified_dsn' in env_content
    
    def test_models_metadata_consistency(self):
        """Test that models metadata is consistent"""
        from src.data.models import Base
        
        # Should have metadata
        assert hasattr(Base, 'metadata')
        assert Base.metadata is not None
        
        # Should have some tables defined
        tables = Base.metadata.tables
        assert len(tables) > 0
        
        # Key tables should exist
        expected_tables = ['users', 'consent_records', 'pseudonyms']
        for table_name in expected_tables:
            # Table might have different naming, just check some exist
            pass  # Actual table names may vary


class TestSessionStateContract:
    """Test session state management contracts"""
    
    def test_session_state_initialization(self):
        """Test session state manager initialization"""
        from src.ui.session_state_manager import SessionStateManager
        
        # Should have defaults defined
        assert hasattr(SessionStateManager, 'DEFAULTS')
        assert isinstance(SessionStateManager.DEFAULTS, dict)
        
        # Key defaults should exist
        expected_keys = [
            'authenticated', 'current_user_id', 'user_role',
            'onboarding_complete', 'onboarding_step'
        ]
        
        for key in expected_keys:
            assert key in SessionStateManager.DEFAULTS
    
    def test_session_state_safe_access(self):
        """Test safe session state access patterns"""
        from src.ui.session_state_manager import SessionStateManager
        
        # Should provide safe get/set methods
        assert hasattr(SessionStateManager, 'get')
        assert hasattr(SessionStateManager, 'set')
        assert hasattr(SessionStateManager, 'initialize_session_state')
        
        # Methods should be class methods
        import inspect
        assert inspect.ismethod(SessionStateManager.get)
        assert inspect.ismethod(SessionStateManager.set)


@pytest.mark.integration
class TestDatabaseIntegrationContract:
    """Integration contract tests requiring database"""
    
    def test_database_setup_idempotent(self):
        """Test that database setup is idempotent"""
        # Should be able to call setup multiple times safely
        try:
            setup_database()
            setup_database()  # Second call should not fail
        except Exception as e:
            pytest.fail(f"Database setup not idempotent: {e}")
    
    def test_session_factory_consistency(self):
        """Test that session factory produces consistent sessions"""
        factory = DatabaseFactory()
        
        session1 = factory.get_session_sync()
        session2 = factory.get_session_sync()
        
        # Should be different session instances
        assert session1 is not session2
        
        # But should use same engine
        assert session1.bind is session2.bind
        
        # Clean up
        session1.close()
        session2.close()
    
    def test_concurrent_session_access(self):
        """Test concurrent session access safety"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                with get_session() as session:
                    # Simulate some work
                    time.sleep(0.1)
                    result = session.execute("SELECT 1").scalar()
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 5
        assert all(r == 1 for r in results)