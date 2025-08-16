# Accessible Form Components Migration Guide

This guide explains how to migrate from standard Streamlit buttons (`st.button()`) to accessible form components for improved user experience and accessibility compliance.

## Overview

The accessible form components system provides alternatives to `st.button()` that:
- Improve accessibility for screen readers and keyboard navigation
- Reduce form submission issues and page reloads
- Provide better validation and error handling
- Support progressive enhancement

## Migration Patterns

### 1. Form Submit Buttons

**Before (using st.button):**
```python
if st.button("Submit Form"):
    # Process form data
    process_form_data()
```

**After (using accessible components):**
```python
from src.ui.accessible_form_components import accessible_form_components

with st.form("my_form"):
    # Form fields here
    name = st.text_input("Name")
    email = st.text_input("Email")
    
    # Use form_submit_handler instead of st.button
    submitted = accessible_form_components.form_submit_handler(
        form_key="my_form",
        submit_label="Submit Form",
        callback=lambda: process_form_data(name, email),
        validation_callback=lambda: validate_form_data(name, email)
    )
```

### 2. Action Buttons

**Before (using st.button):**
```python
if st.button("🔄 Refresh Data"):
    refresh_data()
```

**After (using accessible components):**
```python
accessible_form_components.accessible_action_button(
    label="Refresh Data",
    key="refresh_btn",
    callback=refresh_data,
    help_text="Refresh the data display",
    icon="🔄"
)
```

### 3. Confirmation Dialogs

**Before (using st.button):**
```python
if st.button("Delete Item"):
    if st.button("Confirm Delete"):
        delete_item()
```

**After (using accessible components):**
```python
confirmation = accessible_form_components.confirmation_dialog(
    message="Are you sure you want to delete this item?",
    confirm_label="Delete",
    cancel_label="Cancel",
    key="delete_confirm"
)

if confirmation is True:
    delete_item()
```

### 4. File Upload Actions

**Before (using st.button):**
```python
uploaded_file = st.file_uploader("Choose file")
if uploaded_file and st.button("Process File"):
    process_file(uploaded_file)
```

**After (using accessible components):**
```python
accessible_form_components.accessible_file_uploader(
    label="Choose file to process",
    key="file_upload",
    accepted_types=["csv", "xlsx"],
    callback=process_file,
    help_text="Select a CSV or Excel file to process"
)
```

### 5. Multi-Step Forms

**Before (using st.button):**
```python
if st.button("Next Step"):
    st.session_state.step += 1
if st.button("Previous Step"):
    st.session_state.step -= 1
```

**After (using accessible components):**
```python
with st.form("step_form"):
    # Form content here
    
    navigation = accessible_form_components.progress_indicator(
        current_step=st.session_state.step,
        total_steps=5,
        step_names=["Info", "Preferences", "Review", "Payment", "Complete"],
        show_navigation=True
    )
    
    if navigation == "next":
        st.session_state.step += 1
        st.rerun()
    elif navigation == "previous":
        st.session_state.step -= 1
        st.rerun()
```

## Complete Form Example

Here's a complete example showing how to create an accessible form:

```python
from src.ui.accessible_form_components import accessible_form_components, ValidationResult

def render_user_profile_form():
    """Render accessible user profile form."""
    
    # Define form fields
    fields = [
        {
            "type": "text",
            "key": "full_name",
            "label": "Full Name",
            "help": "Enter your full name as it appears on official documents",
            "placeholder": "John Doe"
        },
        {
            "type": "text",
            "key": "email",
            "label": "Email Address",
            "help": "Enter a valid email address for notifications",
            "placeholder": "john@example.com"
        },
        {
            "type": "number",
            "key": "age",
            "label": "Age",
            "help": "Enter your age in years",
            "min_value": 13,
            "max_value": 120,
            "step": 1
        },
        {
            "type": "selectbox",
            "key": "country",
            "label": "Country",
            "options": ["USA", "Canada", "UK", "Germany", "France"],
            "help": "Select your country of residence"
        },
        {
            "type": "multiselect",
            "key": "interests",
            "label": "Interests",
            "options": ["Technology", "Science", "Arts", "Sports", "Music"],
            "help": "Select your areas of interest (optional)"
        },
        {
            "type": "checkbox",
            "key": "newsletter",
            "label": "Subscribe to newsletter",
            "help": "Receive updates about new features and improvements"
        }
    ]
    
    def validate_profile_data(data):
        """Validate profile form data."""
        errors = []
        warnings = []
        
        # Required field validation
        if not data.get("full_name", "").strip():
            errors.append("Full name is required")
        
        if not data.get("email", "").strip():
            errors.append("Email address is required")
        elif "@" not in data.get("email", ""):
            errors.append("Please enter a valid email address")
        
        if not data.get("age"):
            errors.append("Age is required")
        
        if not data.get("country"):
            errors.append("Please select your country")
        
        # Warnings for optional fields
        if not data.get("interests"):
            warnings.append("Consider selecting some interests to personalize your experience")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def save_profile_data(data):
        """Save profile data."""
        # Process and save the data
        st.success("✅ Profile saved successfully!")
        # Additional processing logic here
    
    # Render the accessible form
    form_data = accessible_form_components.create_accessible_form(
        form_key="user_profile",
        title="User Profile Information",
        fields=fields,
        submit_callback=save_profile_data,
        validation_callback=validate_profile_data
    )
    
    return form_data
```

## Accessibility Benefits

### 1. Screen Reader Support
- Clear labels and help text for all form elements
- Proper ARIA attributes and semantic HTML
- Descriptive error messages and validation feedback

### 2. Keyboard Navigation
- Full keyboard accessibility with Tab navigation
- Enter key support for form submission
- Logical tab order through form elements

### 3. Error Handling
- Clear, actionable error messages
- Validation feedback with visual and text indicators
- Graceful degradation when JavaScript is disabled

### 4. Progressive Enhancement
- Works without JavaScript for basic functionality
- Enhanced experience with JavaScript enabled
- Responsive design for different screen sizes

## Migration Checklist

When migrating existing UI components:

- [ ] Replace all `st.button()` calls with appropriate accessible alternatives
- [ ] Add proper labels and help text to all form elements
- [ ] Implement validation callbacks for form data
- [ ] Add error handling and user feedback
- [ ] Test with keyboard navigation only
- [ ] Test with screen reader software
- [ ] Verify form submission works correctly
- [ ] Update any related tests

## Testing Accessibility

### Manual Testing
1. **Keyboard Navigation**: Navigate through forms using only the Tab key
2. **Screen Reader**: Test with NVDA, JAWS, or VoiceOver
3. **High Contrast**: Test with high contrast mode enabled
4. **Zoom**: Test at 200% zoom level

### Automated Testing
```python
def test_form_accessibility():
    """Test form accessibility compliance."""
    # Test that all form elements have labels
    # Test that error messages are descriptive
    # Test that help text is provided
    # Test keyboard navigation order
```

## Common Pitfalls to Avoid

1. **Missing Labels**: Always provide clear, descriptive labels
2. **Poor Error Messages**: Make error messages specific and actionable
3. **No Help Text**: Provide context and guidance for form fields
4. **Inaccessible Colors**: Ensure sufficient color contrast
5. **Missing Validation**: Always validate user input and provide feedback

## Resources

- [Web Content Accessibility Guidelines (WCAG) 2.1](https://www.w3.org/WAI/WCAG21/quickref/)
- [Streamlit Accessibility Documentation](https://docs.streamlit.io/library/advanced-features/accessibility)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)

## Support

For questions about accessible form components:
1. Check the component documentation in `src/ui/accessible_form_components.py`
2. Review the test examples in `tests/test_accessible_form_components.py`
3. See the integration examples in `tests/test_accessible_form_integration.py`