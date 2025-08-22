# GITTE UI Tooltip Documentation

This document describes all available tooltips in the GITTE user interface.

## Registration & Authentication

### `username_input`
**Title:** Username
**Description:** Choose a unique username for your GITTE account. This will be used to identify you in the system.
**Action:** Must be 3-50 characters, letters, numbers, and underscores only

---

### `email_input`
**Title:** Email Address
**Description:** Your email address for account verification and important notifications. We'll never share your email with third parties.
**Action:** Must be a valid email address format

---

### `password_input`
**Title:** Password
**Description:** Create a secure password to protect your account. Your password is encrypted and stored securely.
**Action:** Minimum 8 characters with letters, numbers, and special characters

---

### `confirm_password_input`
**Title:** Confirm Password
**Description:** Re-enter your password to ensure it was typed correctly.
**Action:** Must match the password entered above

---

### `register_submit_button`
**Title:** Create Account
**Description:** Complete your registration and create your GITTE learning assistant account.
**Action:** Complete all required fields and accept terms to enable

---

### `login_button`
**Title:** Sign In
**Description:** Access your existing GITTE account with your username and password.
**Action:** Enter valid credentials to sign in

---

### `forgot_password_link`
**Title:** Forgot Password
**Description:** Reset your password if you can't remember it. We'll send reset instructions to your email.
**Help Link:** /help/password-reset

---

### `role_select`
**Title:** Account Type
**Description:** Choose your account type. Participants have access to learning features, while Admins can manage the system.
**Action:** Most users should select 'Participant'

---

### `terms_checkbox`
**Title:** Terms and Conditions
**Description:** By checking this box, you agree to our Terms of Service and Privacy Policy. This is required to create an account.
**Action:** Review the terms before accepting
**Help Link:** /terms-of-service

---

## Consent & Privacy

### `data_processing_consent`
**Title:** Data Processing Consent
**Description:** Required to use GITTE's AI features. We process your data to provide personalized learning experiences and generate responses.
**Action:** Check this box to enable AI features like chat and image generation
**Help Link:** /privacy-policy

---

### `llm_interaction_consent`
**Title:** AI Chat Consent
**Description:** Allows GITTE to process your messages and provide AI-powered responses. Your conversations help improve your learning experience.
**Action:** Required to use the chat feature with your learning assistant
**Help Link:** /privacy-policy#ai-interaction

---

### `image_generation_consent`
**Title:** Image Generation Consent
**Description:** Enables creation of visual representations for your learning assistant. Images are generated based on your preferences.
**Action:** Required to create and customize your assistant's appearance
**Help Link:** /privacy-policy#image-generation

---

### `analytics_consent`
**Title:** Analytics Consent (Optional)
**Description:** Helps us understand how GITTE is used to improve the learning experience. All analytics data is anonymized.
**Action:** Optional - you can use GITTE without enabling analytics
**Help Link:** /privacy-policy#analytics

---

### `consent_settings_button`
**Title:** Manage Consent
**Description:** Review and modify your consent preferences. You can change these settings at any time.
**Action:** Click to open consent management interface
**Help Link:** /privacy-policy#consent-management

---

## Embodiment Design

### `character_name_input`
**Title:** Assistant Name
**Description:** Give your learning assistant a name. This personalizes your interaction and makes the experience more engaging.
**Action:** Choose any name you like - you can change it later

---

### `character_age_slider`
**Title:** Apparent Age
**Description:** Set the apparent age for your learning assistant's visual representation. This affects the generated appearance but not the AI capabilities.
**Action:** Slide to select age range from 18 to 65

---

### `character_gender_select`
**Title:** Gender Presentation
**Description:** Choose how you'd like your assistant to be visually represented. This only affects appearance, not personality or capabilities.
**Action:** Select from available options or choose 'Other' for non-binary representation

---

### `character_style_select`
**Title:** Visual Style
**Description:** Choose the artistic style for your assistant's appearance. Different styles create different visual aesthetics.
**Action:** Preview different styles to see which you prefer

---

### `personality_traits_input`
**Title:** Personality Traits
**Description:** Describe personality characteristics you'd like your assistant to embody. This influences both appearance and interaction style.
**Action:** Use descriptive words like 'friendly', 'professional', 'creative', etc.

---

### `subject_expertise_select`
**Title:** Subject Expertise
**Description:** Choose areas where you'd like your assistant to be particularly knowledgeable. This helps tailor responses to your learning needs.
**Action:** Select one or more subject areas

---

### `generate_preview_button`
**Title:** Generate Preview
**Description:** Create a preview of your learning assistant based on your current settings. You can regenerate if you're not satisfied.
**Action:** Complete the form fields above to enable preview generation

---

## Chat Interface

### `chat_input_field`
**Title:** Message Input
**Description:** Type your message or question here. Your learning assistant can help with explanations, answer questions, or discuss topics.
**Action:** Press Enter to send, Shift+Enter for new line

---

### `send_message_button`
**Title:** Send Message
**Description:** Send your message to your learning assistant. You'll receive a personalized response based on your question.
**Action:** Type a message first to enable sending

---

### `clear_chat_button`
**Title:** Clear Conversation
**Description:** Clear the current conversation history. This starts a fresh conversation but doesn't affect your learning progress.
**Action:** Click to clear all messages in this session

---

### `chat_history_button`
**Title:** Conversation History
**Description:** View your previous conversations with your learning assistant. This helps track your learning journey.
**Action:** Click to view conversation history

---

### `export_chat_button`
**Title:** Export Conversation
**Description:** Download your conversation as a text file for your records or further study.
**Action:** Click to download conversation as text file

---

### `chat_settings_button`
**Title:** Chat Settings
**Description:** Adjust chat preferences like response length, formality level, and interaction style.
**Action:** Click to open chat configuration

---

## Image Generation

### `image_prompt_input`
**Title:** Image Description
**Description:** Describe what you'd like to see in the generated image. Be specific about details, style, and composition.
**Action:** Use descriptive language like 'a professional woman in business attire, smiling, office background'

---

### `image_style_select`
**Title:** Image Style
**Description:** Choose the artistic style for the generated image. Different styles produce different visual aesthetics.
**Action:** Select from realistic, artistic, cartoon, or other available styles

---

### `image_quality_select`
**Title:** Image Quality
**Description:** Higher quality takes longer to generate but produces better results. Choose based on your needs and patience.
**Action:** Standard quality is usually sufficient for most purposes

---

### `generate_image_button`
**Title:** Generate Image
**Description:** Create an image based on your description and settings. This may take 30-60 seconds depending on quality settings.
**Action:** Provide a description first to enable generation

---

### `regenerate_image_button`
**Title:** Regenerate Image
**Description:** Create a new image with the same settings. Each generation produces a unique result.
**Action:** Click to generate a different version

---

### `save_image_button`
**Title:** Save Image
**Description:** Save the current image to your account. Saved images can be used as your assistant's appearance.
**Action:** Click to save image to your account

---

### `download_image_button`
**Title:** Download Image
**Description:** Download the image to your device. The image will be saved in high quality PNG format.
**Action:** Click to download image to your device

---

## Navigation & General

### `home_nav_button`
**Title:** Home
**Description:** Return to the main dashboard where you can access all GITTE features and see your learning progress.
**Action:** Click to navigate to home dashboard

---

### `profile_nav_button`
**Title:** Profile
**Description:** View and edit your account information, preferences, and learning assistant settings.
**Action:** Click to open profile settings

---

### `settings_nav_button`
**Title:** Settings
**Description:** Configure GITTE preferences, privacy settings, and system options.
**Action:** Click to open system settings

---

### `help_nav_button`
**Title:** Help & Support
**Description:** Access documentation, tutorials, FAQs, and contact support for assistance.
**Action:** Click to open help documentation
**Help Link:** /help

---

### `logout_button`
**Title:** Sign Out
**Description:** Safely sign out of your GITTE account. Your progress and settings will be saved.
**Action:** Click to sign out of your account

---

### `theme_toggle_button`
**Title:** Toggle Theme
**Description:** Switch between light and dark themes for better visibility and comfort.
**Action:** Click to switch between light and dark themes

---

### `language_select`
**Title:** Language
**Description:** Change the interface language. Your learning assistant will also respond in the selected language.

---

### `export_button`
**Title:** Export Data
**Description:** Download your data in a portable format for backup or transfer purposes
**Action:** Click to generate and download your data export

---

## Admin & Settings

### `admin_dashboard_button`
**Title:** Admin Dashboard
**Description:** Access administrative functions and system monitoring tools. Available only to administrators.
**Action:** Click to open admin dashboard (admin access required)

---

### `user_management_button`
**Title:** User Management
**Description:** Manage user accounts, permissions, and system access. Administrative function only.
**Action:** Click to manage user accounts and permissions

---

### `system_settings_button`
**Title:** System Settings
**Description:** Configure system-wide settings, feature flags, and operational parameters.
**Action:** Click to configure system settings (admin only)

---

### `backup_button`
**Title:** Backup Data
**Description:** Create a backup of user data and system configuration. Important for data protection.
**Action:** Click to create system backup

---

### `logs_button`
**Title:** System Logs
**Description:** View system logs for troubleshooting and monitoring. Contains technical information.
**Action:** Click to view system logs and diagnostics

---
