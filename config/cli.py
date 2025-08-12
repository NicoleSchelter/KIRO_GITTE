#!/usr/bin/env python3
"""
Configuration management CLI for GITTE.
Provides command-line tools for managing configuration, feature flags, and validation.
"""

import argparse
import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import config
from config.environments import create_environment_configs, environment_manager
from config.feature_flags import feature_flag_manager
from config.text_management import text_manager
from config.validation import validate_configuration, validate_runtime


def cmd_validate(args) -> None:
    """Validate configuration."""
    print("Validating GITTE configuration...")
    print("=" * 50)

    # Validate configuration
    config_result = validate_configuration(config)

    print(f"Environment: {config.environment}")
    print(f"Configuration valid: {config_result.is_valid}")
    print()

    if config_result.errors:
        print("ERRORS:")
        for error in config_result.errors:
            print(f"  ❌ {error}")
        print()

    if config_result.warnings:
        print("WARNINGS:")
        for warning in config_result.warnings:
            print(f"  ⚠️  {warning}")
        print()

    if config_result.info:
        print("INFO:")
        for info in config_result.info:
            print(f"  ℹ️  {info}")
        print()

    # Validate runtime
    if args.runtime:
        print("Validating runtime requirements...")
        print("-" * 30)

        runtime_result = validate_runtime()

        if runtime_result.errors:
            print("RUNTIME ERRORS:")
            for error in runtime_result.errors:
                print(f"  ❌ {error}")
            print()

        if runtime_result.warnings:
            print("RUNTIME WARNINGS:")
            for warning in runtime_result.warnings:
                print(f"  ⚠️  {warning}")
            print()

        if runtime_result.info:
            print("RUNTIME INFO:")
            for info in runtime_result.info:
                print(f"  ℹ️  {info}")
            print()

    # Exit with error code if validation failed
    if not config_result.is_valid:
        sys.exit(1)


def cmd_show_config(args) -> None:
    """Show current configuration."""
    print("Current GITTE Configuration")
    print("=" * 40)

    config_dict = {
        "environment": config.environment,
        "debug": config.debug,
        "log_level": config.log_level,
        "app_name": config.app_name,
        "app_version": config.app_version,
        "database": {
            "dsn": config.database.dsn,
            "pool_size": config.database.pool_size,
            "max_overflow": config.database.max_overflow,
            "echo": config.database.echo,
        },
        "llm": {
            "ollama_url": config.llm.ollama_url,
            "models": config.llm.models,
            "timeout_seconds": config.llm.timeout_seconds,
            "max_retries": config.llm.max_retries,
        },
        "image_generation": {
            "model_name": config.image_generation.model_name,
            "device": config.image_generation.device,
            "image_size": config.image_generation.image_size,
            "num_inference_steps": config.image_generation.num_inference_steps,
        },
        "storage": {
            "use_minio": config.storage.use_minio,
            "minio_endpoint": config.storage.minio_endpoint,
            "minio_bucket": config.storage.minio_bucket,
            "local_storage_path": config.storage.local_storage_path,
        },
        "security": {
            "password_hash_rounds": config.security.password_hash_rounds,
            "session_timeout_hours": config.security.session_timeout_hours,
        },
        "federated_learning": {
            "enabled": config.federated_learning.enabled,
            "server_url": config.federated_learning.server_url,
            "aggregation_rounds": config.federated_learning.aggregation_rounds,
        },
    }

    if args.format == "json":
        print(json.dumps(config_dict, indent=2))
    else:
        for section, values in config_dict.items():
            print(f"\n[{section.upper()}]")
            if isinstance(values, dict):
                for key, value in values.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {values}")


def cmd_feature_flags(args) -> None:
    """Manage feature flags."""
    if args.action == "list":
        print("Feature Flags")
        print("=" * 30)

        all_flags = feature_flag_manager.get_all_flags()
        for name, value in all_flags.items():
            flag_info = feature_flag_manager.get_flag_info(name)
            status = "✅" if value else "❌"
            print(f"{status} {name}: {value}")
            if flag_info:
                print(f"    Description: {flag_info['description']}")
                print(f"    Category: {flag_info['category']}")
                if flag_info["requires_restart"]:
                    print("    ⚠️  Requires restart")
                print()

    elif args.action == "get":
        if not args.name:
            print("Error: Flag name is required for 'get' action")
            sys.exit(1)

        value = feature_flag_manager.get_flag(args.name)
        flag_info = feature_flag_manager.get_flag_info(args.name)

        if flag_info:
            print(f"Flag: {args.name}")
            print(f"Current value: {value}")
            print(f"Default value: {flag_info['default_value']}")
            print(f"Type: {flag_info['type']}")
            print(f"Description: {flag_info['description']}")
            print(f"Category: {flag_info['category']}")
            print(f"Set by: {flag_info['set_by']}")
            if flag_info["requires_restart"]:
                print("⚠️  Requires restart to take effect")
        else:
            print(f"Flag '{args.name}' not found")
            sys.exit(1)

    elif args.action == "set":
        if not args.name or args.value is None:
            print("Error: Flag name and value are required for 'set' action")
            sys.exit(1)

        # Convert string value to appropriate type
        value = args.value
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        elif "," in value:
            value = [item.strip() for item in value.split(",")]

        success = feature_flag_manager.set_flag(args.name, value, "cli")
        if success:
            print(f"✅ Flag '{args.name}' set to: {value}")

            # Save to file if requested
            if args.save:
                if feature_flag_manager.save_flags_to_file():
                    print("✅ Flags saved to file")
                else:
                    print("❌ Failed to save flags to file")
        else:
            print(f"❌ Failed to set flag '{args.name}'")
            sys.exit(1)


def cmd_environments(args) -> None:
    """Manage environment configurations."""
    if args.action == "list":
        print("Available Environments")
        print("=" * 30)

        environments = environment_manager.list_environments()
        current_env = config.environment

        for env in environments:
            marker = "👉" if env == current_env else "  "
            print(f"{marker} {env}")

        if not environments:
            print("No environment configurations found")
            print("Run 'python -m config.cli environments create-defaults' to create them")

    elif args.action == "create-defaults":
        print("Creating default environment configurations...")
        create_environment_configs()
        print("✅ Default environment configurations created")

    elif args.action == "show":
        if not args.name:
            print("Error: Environment name is required for 'show' action")
            sys.exit(1)

        env_config = environment_manager.get_environment_config(args.name)
        if env_config:
            print(f"Environment: {args.name}")
            print("=" * 30)
            print(json.dumps(env_config.overrides, indent=2))
        else:
            print(f"Environment '{args.name}' not found")
            sys.exit(1)


def cmd_text(args) -> None:
    """Manage text and localization."""
    if args.action == "languages":
        print("Available Languages")
        print("=" * 30)

        languages = text_manager.get_available_languages()
        current_lang = text_manager.current_language

        for lang in languages:
            marker = "👉" if lang == current_lang else "  "
            print(f"{marker} {lang}")

    elif args.action == "get":
        if not args.key:
            print("Error: Text key is required for 'get' action")
            sys.exit(1)

        text = text_manager.get_text(args.key, args.language)
        print(f"Key: {args.key}")
        print(f"Language: {args.language or text_manager.current_language}")
        print(f"Text: {text}")

    elif args.action == "export":
        if not args.language:
            print("Error: Language is required for 'export' action")
            sys.exit(1)

        texts = text_manager.export_texts(args.language)
        if texts:
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(texts, f, indent=2, ensure_ascii=False)
                print(f"✅ Texts exported to {args.output}")
            else:
                print(json.dumps(texts, indent=2, ensure_ascii=False))
        else:
            print(f"Language '{args.language}' not found")
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="GITTE Configuration Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument(
        "--runtime", action="store_true", help="Also validate runtime requirements"
    )
    validate_parser.set_defaults(func=cmd_validate)

    # Show config command
    config_parser = subparsers.add_parser("config", help="Show current configuration")
    config_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    config_parser.set_defaults(func=cmd_show_config)

    # Feature flags command
    flags_parser = subparsers.add_parser("flags", help="Manage feature flags")
    flags_parser.add_argument("action", choices=["list", "get", "set"], help="Action to perform")
    flags_parser.add_argument("--name", help="Flag name")
    flags_parser.add_argument("--value", help="Flag value (for set action)")
    flags_parser.add_argument(
        "--save", action="store_true", help="Save flags to file after setting"
    )
    flags_parser.set_defaults(func=cmd_feature_flags)

    # Environments command
    env_parser = subparsers.add_parser("environments", help="Manage environment configurations")
    env_parser.add_argument(
        "action", choices=["list", "show", "create-defaults"], help="Action to perform"
    )
    env_parser.add_argument("--name", help="Environment name")
    env_parser.set_defaults(func=cmd_environments)

    # Text management command
    text_parser = subparsers.add_parser("text", help="Manage text and localization")
    text_parser.add_argument(
        "action", choices=["languages", "get", "export"], help="Action to perform"
    )
    text_parser.add_argument("--key", help="Text key")
    text_parser.add_argument("--language", help="Language code")
    text_parser.add_argument("--output", help="Output file for export")
    text_parser.set_defaults(func=cmd_text)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
