#!/usr/bin/env python3
"""
CLI tool for managing UX enhancement configuration.
Provides commands for validation, migration, and configuration management.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import Config
from config.ux_config_validator import UXConfigValidator, validate_ux_config, get_ux_config_summary
from config.ux_config_migration import UXConfigMigration, migrate_ux_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_config(args):
    """Validate UX enhancement configuration."""
    try:
        config = Config()
        result = validate_ux_config(config)
        
        print("=== UX Configuration Validation ===")
        print(f"Status: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
        print(f"Total Issues: {result['total_issues']}")
        
        if result['errors']:
            print(f"\n🔴 Errors ({len(result['errors'])}):")
            for i, error in enumerate(result['errors'], 1):
                print(f"  {i}. {error}")
        
        if result['warnings']:
            print(f"\n🟡 Warnings ({len(result['warnings'])}):")
            for i, warning in enumerate(result['warnings'], 1):
                print(f"  {i}. {warning}")
        
        if not result['errors'] and not result['warnings']:
            print("\n✨ Configuration is perfect!")
        
        # Check runtime dependencies if requested
        if args.check_dependencies:
            print("\n=== Runtime Dependencies ===")
            validator = UXConfigValidator(config)
            deps = validator.validate_runtime_dependencies()
            
            if deps['valid']:
                print("✅ All dependencies satisfied")
            else:
                print("❌ Missing dependencies:")
                for dep in deps['missing_dependencies']:
                    print(f"  - {dep}")
        
        return 0 if result['valid'] else 1
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


def show_config(args):
    """Show current UX configuration."""
    try:
        config = Config()
        summary = get_ux_config_summary(config)
        
        print("=== UX Configuration Summary ===")
        
        if args.format == 'json':
            print(json.dumps(summary, indent=2))
        else:
            for section, settings in summary.items():
                print(f"\n📋 {section.replace('_', ' ').title()}:")
                for key, value in settings.items():
                    status = "✅" if value else "❌" if isinstance(value, bool) else "📝"
                    print(f"  {status} {key}: {value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to show configuration: {e}")
        return 1


def migrate_config(args):
    """Migrate configuration for UX enhancements."""
    try:
        print(f"=== Migrating {args.type.upper()} Configuration ===")
        
        migration = UXConfigMigration(args.config_path)
        
        # Create backup if requested
        if args.backup:
            if migration.create_backup():
                print("✅ Configuration backup created")
            else:
                print("⚠️ Could not create backup")
        
        # Perform migration
        success = False
        if args.type == 'env':
            success = migration.migrate_env_file(args.config_path or '.env')
        elif args.type == 'docker':
            success = migration.migrate_docker_compose(args.config_path or 'docker-compose.yml')
        elif args.type == 'template':
            success = migration.generate_config_template(args.output or 'ux_config_template.json')
        
        if success:
            print("✅ Migration completed successfully")
            
            # Validate migration if requested
            if args.validate:
                print("\n=== Validating Migration ===")
                result = migration.validate_migration()
                
                if result['valid']:
                    print("✅ Migration validation passed")
                else:
                    print("❌ Migration validation failed:")
                    for issue in result['issues']:
                        print(f"  - {issue}")
                
                if result['recommendations']:
                    print("\n💡 Recommendations:")
                    for rec in result['recommendations']:
                        print(f"  - {rec}")
        else:
            print("❌ Migration failed")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


def check_feature_flags(args):
    """Check feature flag status."""
    try:
        config = Config()
        flags = config.feature_flags
        
        print("=== UX Feature Flags Status ===")
        
        ux_flags = [
            ('enable_image_isolation', 'Image Isolation'),
            ('enable_image_quality_detection', 'Image Quality Detection'),
            ('enable_image_correction_dialog', 'Image Correction Dialog'),
            ('enable_tooltip_system', 'Tooltip System'),
            ('enable_prerequisite_checks', 'Prerequisite Checks'),
            ('enable_ux_audit_logging', 'UX Audit Logging'),
        ]
        
        for flag_name, display_name in ux_flags:
            value = getattr(flags, flag_name, False)
            status = "✅ ENABLED" if value else "❌ DISABLED"
            print(f"{status} {display_name}")
        
        # Show environment variable overrides
        if args.show_env:
            print("\n=== Environment Variable Overrides ===")
            import os
            for flag_name, display_name in ux_flags:
                env_var = f"FEATURE_{flag_name.upper()}"
                env_value = os.getenv(env_var)
                if env_value:
                    print(f"🔧 {env_var}={env_value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to check feature flags: {e}")
        return 1


def generate_docs(args):
    """Generate configuration documentation."""
    try:
        config = Config()
        
        docs = []
        docs.append("# UX Enhancement Configuration Documentation")
        docs.append("")
        docs.append("This document describes the configuration options for UX enhancements in GITTE.")
        docs.append("")
        
        # Image Isolation
        docs.append("## Image Isolation Configuration")
        docs.append("")
        docs.append("Controls automatic image isolation and background removal.")
        docs.append("")
        docs.append("| Setting | Default | Description |")
        docs.append("|---------|---------|-------------|")
        docs.append(f"| enabled | {config.image_isolation.enabled} | Enable/disable image isolation |")
        docs.append(f"| detection_confidence_threshold | {config.image_isolation.detection_confidence_threshold} | Confidence threshold for person detection |")
        docs.append(f"| background_removal_method | {config.image_isolation.background_removal_method} | Method for background removal |")
        docs.append(f"| max_processing_time | {config.image_isolation.max_processing_time} | Maximum processing time in seconds |")
        docs.append("")
        
        # Image Correction
        docs.append("## Image Correction Configuration")
        docs.append("")
        docs.append("Controls the image correction dialog and user interaction.")
        docs.append("")
        docs.append("| Setting | Default | Description |")
        docs.append("|---------|---------|-------------|")
        docs.append(f"| enabled | {config.image_correction.enabled} | Enable/disable correction dialog |")
        docs.append(f"| timeout_seconds | {config.image_correction.timeout_seconds} | Dialog timeout in seconds |")
        docs.append(f"| allow_manual_crop | {config.image_correction.allow_manual_crop} | Allow manual crop adjustment |")
        docs.append(f"| allow_regeneration | {config.image_correction.allow_regeneration} | Allow image regeneration |")
        docs.append("")
        
        # Tooltip System
        docs.append("## Tooltip System Configuration")
        docs.append("")
        docs.append("Controls context-sensitive tooltips and help system.")
        docs.append("")
        docs.append("| Setting | Default | Description |")
        docs.append("|---------|---------|-------------|")
        docs.append(f"| enabled | {config.tooltip.enabled} | Enable/disable tooltip system |")
        docs.append(f"| show_delay_ms | {config.tooltip.show_delay_ms} | Delay before showing tooltip |")
        docs.append(f"| max_width | {config.tooltip.max_width} | Maximum tooltip width in pixels |")
        docs.append(f"| track_interactions | {config.tooltip.track_interactions} | Track tooltip interactions |")
        docs.append("")
        
        # Prerequisite Checks
        docs.append("## Prerequisite Checks Configuration")
        docs.append("")
        docs.append("Controls system prerequisite validation.")
        docs.append("")
        docs.append("| Setting | Default | Description |")
        docs.append("|---------|---------|-------------|")
        docs.append(f"| enabled | {config.prerequisite.enabled} | Enable/disable prerequisite checks |")
        docs.append(f"| cache_ttl_seconds | {config.prerequisite.cache_ttl_seconds} | Cache TTL for check results |")
        docs.append(f"| parallel_execution | {config.prerequisite.parallel_execution} | Execute checks in parallel |")
        docs.append(f"| timeout_seconds | {config.prerequisite.timeout_seconds} | Timeout for individual checks |")
        docs.append("")
        
        # Environment Variables
        docs.append("## Environment Variable Overrides")
        docs.append("")
        docs.append("All configuration settings can be overridden using environment variables:")
        docs.append("")
        
        migration = UXConfigMigration()
        env_vars = migration.migrate_environment_variables()
        
        for var_name, default_value in env_vars.items():
            docs.append(f"- `{var_name}`: {default_value}")
        
        docs.append("")
        
        # Write documentation
        output_path = args.output or "UX_CONFIGURATION.md"
        with open(output_path, 'w') as f:
            f.write('\n'.join(docs))
        
        print(f"✅ Documentation generated: {output_path}")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate documentation: {e}")
        return 1


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Manage UX enhancement configuration for GITTE",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate UX configuration')
    validate_parser.add_argument(
        '--check-dependencies', 
        action='store_true',
        help='Also check runtime dependencies'
    )
    validate_parser.set_defaults(func=validate_config)
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show current UX configuration')
    show_parser.add_argument(
        '--format', 
        choices=['table', 'json'], 
        default='table',
        help='Output format'
    )
    show_parser.set_defaults(func=show_config)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate configuration')
    migrate_parser.add_argument(
        'type', 
        choices=['env', 'docker', 'template'],
        help='Type of configuration to migrate'
    )
    migrate_parser.add_argument(
        '--config-path',
        help='Path to configuration file'
    )
    migrate_parser.add_argument(
        '--output',
        help='Output path for template generation'
    )
    migrate_parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before migration'
    )
    migrate_parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate migration after completion'
    )
    migrate_parser.set_defaults(func=migrate_config)
    
    # Feature flags command
    flags_parser = subparsers.add_parser('flags', help='Check feature flag status')
    flags_parser.add_argument(
        '--show-env',
        action='store_true',
        help='Show environment variable overrides'
    )
    flags_parser.set_defaults(func=check_feature_flags)
    
    # Generate docs command
    docs_parser = subparsers.add_parser('docs', help='Generate configuration documentation')
    docs_parser.add_argument(
        '--output',
        help='Output path for documentation'
    )
    docs_parser.set_defaults(func=generate_docs)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())