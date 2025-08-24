"""
Hook loader service for managing Kiro hooks.
Handles loading, ordering, and execution of hooks from configured folders.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HookLoadError(Exception):
    """Raised when a hook cannot be loaded."""
    pass


class HookLoader:
    """Service for loading and managing Kiro hooks."""
    
    # Enforced hook execution order
    HOOK_ORDER = [
        "06-config-validator.kiro.hook",
        "12-security+dependency.kiro.hook",  # merged former 07 & 12
        "11-determinism.kiro.hook", 
        "10-ensure-test-kinds.kiro.hook",
        "08-ban-mocks.kiro.hook",
        "09-ban-large-fixtures.kiro.hook",
        "13-consent-contract-audit.kiro.hook",
        "15-database-manager-ban.kiro.hook"
    ]
    
    def __init__(self, hook_folder: str = ".kiro/hooks"):
        self.hook_folder = Path(hook_folder)
        self.loaded_hooks: Dict[str, Dict] = {}
        self.failed_hooks: Dict[str, str] = {}
        
    def scan_and_load_hooks(self) -> Tuple[List[str], Dict[str, str]]:
        """
        Scan hook folder and load all .kiro.hook files.
        
        Returns:
            Tuple of (loaded_hook_names, failed_hooks_with_reasons)
        """
        logger.info("hook_loader: scanning hooks folder...")
        
        if not self.hook_folder.exists():
            logger.warning(f"hook_loader: hooks folder {self.hook_folder} does not exist")
            return [], {}
        
        # Find all .kiro.hook files
        hook_files = list(self.hook_folder.glob("*.kiro.hook"))
        
        loaded_hooks = []
        failed_hooks = {}
        
        for hook_file in hook_files:
            try:
                hook_info = self._load_hook_file(hook_file)
                self.loaded_hooks[hook_file.name] = hook_info
                loaded_hooks.append(hook_file.name)
                logger.debug(f"hook_loader: loaded {hook_file.name}")
                
            except Exception as e:
                reason = str(e)
                failed_hooks[hook_file.name] = reason
                self.failed_hooks[hook_file.name] = reason
                logger.warning(f"hook_loader: skipped {hook_file.name}: {reason}")
        
        # Log execution order
        ordered_hooks = self._get_execution_order(loaded_hooks)
        logger.info(f"hook_loader: execution order => {ordered_hooks}")
        
        return loaded_hooks, failed_hooks
    
    def _load_hook_file(self, hook_file: Path) -> Dict:
        """
        Load and validate a single hook file.
        
        Args:
            hook_file: Path to the hook file
            
        Returns:
            Dict with hook information
            
        Raises:
            HookLoadError: If hook cannot be loaded
        """
        try:
            # Check if file is executable
            if not os.access(hook_file, os.X_OK):
                # Try to make it executable
                try:
                    os.chmod(hook_file, 0o755)
                except Exception as e:
                    raise HookLoadError(f"Cannot make executable: {e}")
            
            # Read hook content for basic validation
            try:
                content = hook_file.read_text(encoding='utf-8')
            except Exception as e:
                raise HookLoadError(f"Cannot read file: {e}")
            
            # Basic validation - check for shebang or python content
            if not (content.startswith('#!') or 'python' in content.lower()):
                raise HookLoadError("Not a valid executable hook (missing shebang or python content)")
            
            # Try a dry run to validate syntax
            try:
                result = subprocess.run([
                    sys.executable, str(hook_file), "--dry-run"
                ], capture_output=True, text=True, timeout=10)
                
                # If dry-run is not supported, that's okay
                if result.returncode != 0 and "--dry-run" in result.stderr:
                    # Hook doesn't support dry-run, try basic validation
                    result = subprocess.run([
                        sys.executable, "-m", "py_compile", str(hook_file)
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode != 0:
                        raise HookLoadError(f"Syntax error: {result.stderr}")
                        
            except subprocess.TimeoutExpired:
                raise HookLoadError("Validation timeout")
            except Exception as e:
                # If validation fails, still allow loading but note the issue
                logger.debug(f"Hook validation warning for {hook_file.name}: {e}")
            
            return {
                "name": hook_file.name,
                "path": str(hook_file),
                "size": hook_file.stat().st_size,
                "executable": os.access(hook_file, os.X_OK),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
            
        except HookLoadError:
            raise
        except Exception as e:
            raise HookLoadError(f"Unexpected error: {e}")
    
    def _get_execution_order(self, loaded_hooks: List[str]) -> List[str]:
        """
        Get hooks in enforced execution order.
        
        Args:
            loaded_hooks: List of loaded hook names
            
        Returns:
            List of hook names in execution order
        """
        ordered = []
        
        # Add hooks in enforced order if they exist
        for hook_name in self.HOOK_ORDER:
            if hook_name in loaded_hooks:
                ordered.append(hook_name)
        
        # Add any remaining hooks not in the enforced order
        for hook_name in loaded_hooks:
            if hook_name not in ordered:
                ordered.append(hook_name)
        
        return ordered
    
    def execute_hooks(self, repo_path: str = ".") -> Dict[str, Dict]:
        """
        Execute all loaded hooks in order.
        
        Args:
            repo_path: Path to repository root
            
        Returns:
            Dict mapping hook names to execution results
        """
        results = {}
        ordered_hooks = self._get_execution_order(list(self.loaded_hooks.keys()))
        
        logger.info(f"hook_loader: executing {len(ordered_hooks)} hooks in order")
        
        for hook_name in ordered_hooks:
            if hook_name not in self.loaded_hooks:
                continue
                
            hook_info = self.loaded_hooks[hook_name]
            
            try:
                result = self._execute_single_hook(hook_info["path"], repo_path)
                results[hook_name] = {
                    "success": result["returncode"] == 0,
                    "returncode": result["returncode"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "duration": result.get("duration", 0)
                }
                
                if result["returncode"] == 0:
                    logger.debug(f"hook_loader: {hook_name} passed")
                else:
                    logger.error(f"hook_loader: {hook_name} failed with code {result['returncode']}")
                    
            except Exception as e:
                logger.error(f"hook_loader: {hook_name} execution error: {e}")
                results[hook_name] = {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": str(e),
                    "duration": 0
                }
        
        return results
    
    def _execute_single_hook(self, hook_path: str, repo_path: str) -> Dict:
        """
        Execute a single hook.
        
        Args:
            hook_path: Path to hook file
            repo_path: Repository root path
            
        Returns:
            Dict with execution results
        """
        import time
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                sys.executable, hook_path
            ], cwd=repo_path, capture_output=True, text=True, timeout=60)
            
            duration = time.time() - start_time
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "returncode": -2,
                "stdout": "",
                "stderr": "Hook execution timeout",
                "duration": duration
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": duration
            }
    
    def dry_run_hooks(self, repo_path: str = ".") -> Dict[str, bool]:
        """
        Perform a dry run to show which hooks would fire.
        
        Args:
            repo_path: Repository root path
            
        Returns:
            Dict mapping hook names to whether they would execute
        """
        dry_run_results = {}
        ordered_hooks = self._get_execution_order(list(self.loaded_hooks.keys()))
        
        logger.info("hook_loader: performing dry run...")
        
        for hook_name in ordered_hooks:
            if hook_name not in self.loaded_hooks:
                continue
                
            hook_info = self.loaded_hooks[hook_name]
            
            try:
                # Try to run with --dry-run flag
                result = subprocess.run([
                    sys.executable, hook_info["path"], "--dry-run"
                ], cwd=repo_path, capture_output=True, text=True, timeout=30)
                
                # If dry-run is supported, use its result
                if result.returncode == 0:
                    dry_run_results[hook_name] = True
                elif "--dry-run" in result.stderr:
                    # Hook doesn't support dry-run, assume it would execute
                    dry_run_results[hook_name] = True
                else:
                    dry_run_results[hook_name] = False
                    
            except Exception as e:
                logger.debug(f"Dry run error for {hook_name}: {e}")
                # Assume it would execute if we can't determine otherwise
                dry_run_results[hook_name] = True
        
        return dry_run_results
    
    def get_hook_status(self) -> Dict:
        """
        Get current status of all hooks.
        
        Returns:
            Dict with hook status information
        """
        return {
            "loaded_hooks": list(self.loaded_hooks.keys()),
            "failed_hooks": self.failed_hooks,
            "execution_order": self._get_execution_order(list(self.loaded_hooks.keys())),
            "total_loaded": len(self.loaded_hooks),
            "total_failed": len(self.failed_hooks)
        }
    
    def reload_hooks(self) -> Tuple[List[str], Dict[str, str]]:
        """
        Reload all hooks from the folder.
        
        Returns:
            Tuple of (loaded_hook_names, failed_hooks_with_reasons)
        """
        logger.info("hook_loader: reloading hooks...")
        
        # Clear current state
        self.loaded_hooks.clear()
        self.failed_hooks.clear()
        
        # Rescan and load
        return self.scan_and_load_hooks()


# Global hook loader instance
_hook_loader = None


def get_hook_loader(hook_folder: str = ".kiro/hooks") -> HookLoader:
    """Get the global hook loader instance."""
    global _hook_loader
    if _hook_loader is None:
        _hook_loader = HookLoader(hook_folder)
    return _hook_loader


def initialize_hooks(hook_folder: str = ".kiro/hooks") -> Dict:
    """
    Initialize the hook system and load all hooks.
    
    Args:
        hook_folder: Path to hooks folder
        
    Returns:
        Dict with initialization results
    """
    hook_loader = get_hook_loader(hook_folder)
    loaded_hooks, failed_hooks = hook_loader.scan_and_load_hooks()
    
    return {
        "loaded_hooks": loaded_hooks,
        "failed_hooks": failed_hooks,
        "execution_order": hook_loader._get_execution_order(loaded_hooks),
        "hook_loader": hook_loader
    }