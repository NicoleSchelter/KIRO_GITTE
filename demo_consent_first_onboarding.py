#!/usr/bin/env python3
"""
Demo script for consent-first onboarding flow in GITTE.
Shows the new UX where consents are collected first, then pseudonym is created.
"""

import streamlit as st
from uuid import uuid4

# Import the new onboarding UI
from src.ui.onboarding_ui import render_consent_first_onboarding, render_onboarding_status

def main():
    """Main demo application."""
    st.set_page_config(
        page_title="GITTE - Consent-First Onboarding Demo",
        page_icon="🔐",
        layout="wide"
    )
    
    st.title("🔐 GITTE - Consent-First Onboarding Demo")
    
    st.markdown("""
    This demo shows the new consent-first onboarding flow where:
    1. **Consents are collected first** and buffered in UI state
    2. **Pseudonym is created** with user guidance
    3. **Finalization** persists buffered consents with the pseudonym in one transaction
    """)
    
    # Simulate user authentication
    if "demo_user_id" not in st.session_state:
        st.session_state.demo_user_id = str(uuid4())
    
    user_id = st.session_state.demo_user_id
    
    st.sidebar.markdown(f"**Demo User ID:** `{user_id[:8]}...`")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Choose Demo Page:",
        ["Onboarding Flow", "Status Check", "Reset Demo"]
    )
    
    if page == "Onboarding Flow":
        st.header("Consent-First Onboarding Flow")
        
        # Show the consent-first onboarding
        completed = render_consent_first_onboarding(user_id)
        
        if completed:
            st.balloons()
            st.success("🎉 Onboarding completed successfully!")
            
    elif page == "Status Check":
        st.header("Onboarding Status")
        
        # Show onboarding status
        render_onboarding_status(user_id)
        
    elif page == "Reset Demo":
        st.header("Reset Demo")
        
        st.warning("This will reset all demo data and start fresh.")
        
        if st.button("Reset Demo Data", type="secondary"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Demo reset! Please refresh the page.")
            st.rerun()
    
    # Debug information
    with st.sidebar.expander("Debug Info"):
        st.json({
            "user_id": user_id,
            "session_keys": list(st.session_state.keys()),
            "onboarding_step": st.session_state.get("onboarding_step", "not_started"),
            "buffered_consents": st.session_state.get("buffered_consents", {}),
            "created_pseudonym_id": st.session_state.get("created_pseudonym_id", None)
        })


if __name__ == "__main__":
    main()