#!/usr/bin/env python3
"""
Tooltip Coverage Validation Script for GITTE UI.
Validates that all critical UI elements have appropriate tooltips.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ui.tooltip_content_manager import get_tooltip_content_manager
from src.ui.tooltip_system import get_tooltip_system


def main():
    """Main validation function."""
    print("🔍 GITTE Tooltip Coverage Validation")
    print("=" * 50)
    
    tooltip_manager = get_tooltip_content_manager()
    tooltip_system = get_tooltip_system()
    
    # Define critical UI elements that should have tooltips
    critical_elements = {
        "Authentication & Registration": [
            "username_input",
            "email_input", 
            "password_input",
            "confirm_password_input",
            "register_submit_button",
            "login_button",
            "role_select",
            "terms_checkbox"
        ],
        
        "Consent & Privacy": [
            "data_processing_consent",
            "llm_interaction_consent",
            "image_generation_consent",
            "analytics_consent",
            "consent_settings_button"
        ],
        
        "Embodiment Design": [
            "character_name_input",
            "character_age_slider",
            "character_gender_select",
            "character_style_select",
            "personality_traits_input",
            "subject_expertise_select",
            "generate_preview_button"
        ],
        
        "Chat Interface": [
            "chat_input_field",
            "send_message_button",
            "clear_chat_button",
            "chat_history_button",
            "export_chat_button",
            "chat_settings_button"
        ],
        
        "Image Generation": [
            "image_prompt_input",
            "image_style_select",
            "image_quality_select",
            "generate_image_button",
            "regenerate_image_button",
            "save_image_button",
            "download_image_button"
        ],
        
        "Navigation & General": [
            "home_nav_button",
            "profile_nav_button",
            "settings_nav_button",
            "help_nav_button",
            "logout_button",
            "save_button",
            "delete_button",
            "export_button"
        ]
    }
    
    # Validate coverage for each category
    total_elements = 0
    total_covered = 0
    issues = []
    
    for category, elements in critical_elements.items():
        print(f"\n📋 {category}")
        print("-" * len(category))
        
        category_covered = 0
        category_total = len(elements)
        
        for element_id in elements:
            total_elements += 1
            tooltip = tooltip_system.get_tooltip(element_id)
            
            if tooltip:
                total_covered += 1
                category_covered += 1
                print(f"  ✅ {element_id}")
            else:
                issues.append(f"{category}: {element_id}")
                print(f"  ❌ {element_id} - MISSING TOOLTIP")
        
        coverage_pct = (category_covered / category_total) * 100
        print(f"  📊 Coverage: {category_covered}/{category_total} ({coverage_pct:.1f}%)")
    
    # Overall summary
    print(f"\n📈 Overall Summary")
    print("=" * 20)
    overall_coverage = (total_covered / total_elements) * 100
    print(f"Total Elements: {total_elements}")
    print(f"Covered Elements: {total_covered}")
    print(f"Missing Elements: {total_elements - total_covered}")
    print(f"Overall Coverage: {overall_coverage:.1f}%")
    
    # Detailed issues
    if issues:
        print(f"\n⚠️  Missing Tooltips ({len(issues)} issues)")
        print("-" * 30)
        for issue in issues:
            print(f"  • {issue}")
    else:
        print(f"\n🎉 Perfect Coverage!")
        print("All critical UI elements have tooltips!")
    
    # Tooltip system statistics
    stats = tooltip_system.get_system_stats()
    print(f"\n🔧 System Statistics")
    print("-" * 20)
    print(f"Tooltip System Enabled: {stats['enabled']}")
    print(f"CSS Injected: {stats['css_injected']}")
    print(f"Accessibility Enabled: {stats['accessibility_enabled']}")
    print(f"Total Registered Tooltips: {stats['registered_tooltips']}")
    
    # Quality checks
    print(f"\n🔍 Quality Checks")
    print("-" * 15)
    
    quality_issues = []
    registered_elements = tooltip_system.registry.list_registered()
    
    for element_id in registered_elements:
        tooltip = tooltip_system.get_tooltip(element_id)
        if tooltip:
            # Check for minimum content quality
            if len(tooltip.description) < 20:
                quality_issues.append(f"{element_id}: Description too short")
            
            if not tooltip.accessibility_label:
                quality_issues.append(f"{element_id}: Missing accessibility label")
            
            # Check for action text on buttons
            if "button" in element_id and not tooltip.action_text:
                quality_issues.append(f"{element_id}: Button missing action text")
    
    if quality_issues:
        print(f"⚠️  Quality Issues Found ({len(quality_issues)})")
        for issue in quality_issues:
            print(f"  • {issue}")
    else:
        print("✅ All tooltips meet quality standards")
    
    # Generate documentation
    print(f"\n📚 Documentation Generation")
    print("-" * 25)
    
    try:
        doc = tooltip_manager.generate_tooltip_documentation()
        doc_path = Path(__file__).parent.parent / "docs" / "tooltip_documentation.md"
        doc_path.write_text(doc, encoding="utf-8")
        print(f"✅ Documentation generated: {doc_path}")
    except Exception as e:
        print(f"❌ Documentation generation failed: {e}")
    
    # Exit code based on coverage
    if overall_coverage >= 95.0:
        print(f"\n🎯 Excellent coverage! ({overall_coverage:.1f}%)")
        return 0
    elif overall_coverage >= 85.0:
        print(f"\n👍 Good coverage ({overall_coverage:.1f}%), but room for improvement")
        return 0
    else:
        print(f"\n⚠️  Coverage below target ({overall_coverage:.1f}% < 85%)")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)