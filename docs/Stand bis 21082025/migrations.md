# Database Migrations Guide

This document describes the database migration system for GITTE and the PALD Enhancement feature.

## Overview

GITTE uses Alembic for database schema migrations. The PALD Enhancement feature introduces several new tables for schema evolution tracking, processing logs, and bias analysis job management.

## Migration Files

### 001_pald_enhancement_tables.py

This migration adds the core tables for PALD Enhancement:

#### schema_field_candidates
Tracks potential new fields detected in PALD data for schema evolution.

**Columns:**
- `id` (UUID): Primary key
- `field_name` (String): Name of the detected field
- `field_category` (String): Categorization (demographic, gender, ethnicity, etc.)
- `mention_count` (Integer): Number of times field has been detected
- `first_detected` (DateTime): When field was first detected
- `last_mentioned` (DateTime): Most recent detection
- `threshold_reached` (Boolean): Whether field has reached inclusion threshold
- `added_to_schema` (Boolean): Whether field has been added to schema
- `schema_version_added` (String): Schema version when field was added

**Indexes:**
- `idx_schema_field_name`: On field_name for lookups
- `idx_schema_field_threshold`: On threshold_reached for querying candidates
- `idx_schema_field_added`: On added_to_schema for filtering
- `idx_schema_field_category`: On field_category for categorization queries

#### pald_processing_logs
Tracks PALD processing stages and operations for debugging and monitoring.

**Columns:**
- `id` (UUID): Primary key
- `session_id` (String): Session identifier for tracking
- `processing_stage` (String): Stage of processing (extraction, validation, etc.)
- `operation` (String): Specific operation (field_detection, schema_validation, etc.)
- `status` (String): Operation status (started, completed, failed)
- `start_time` (DateTime): When operation started
- `end_time` (DateTime): When operation completed
- `duration_ms` (Integer): Processing duration in milliseconds
- `details` (JSON): Stage-specific details
- `error_message` (Text): Error details if operation failed

**Indexes:**
- `idx_pald_log_session`: On session_id for session tracking
- `idx_pald_log_stage`: On processing_stage for filtering by stage
- `idx_pald_log_status`: On status for monitoring
- `idx_pald_log_created`: On created_at for time-based queries

#### bias_analysis_jobs
Manages deferred bias analysis jobs for background processing.

**Columns:**
- `id` (UUID): Primary key
- `session_id` (String): Session identifier
- `pald_data` (JSON): PALD data to analyze
- `analysis_types` (JSON): List of analysis types to perform
- `priority` (Integer): Job priority (1=highest, 10=lowest)
- `status` (String): Job status (pending, running, completed, failed, etc.)
- `retry_count` (Integer): Number of retry attempts
- `max_retries` (Integer): Maximum retry attempts allowed
- `scheduled_at` (DateTime): When job was scheduled
- `started_at` (DateTime): When job processing started
- `completed_at` (DateTime): When job completed
- `error_message` (Text): Error details if job failed

#### bias_analysis_results
Stores results of bias analysis operations.

**Columns:**
- `id` (UUID): Primary key
- `job_id` (UUID): Foreign key to bias_analysis_jobs
- `session_id` (String): Session identifier
- `analysis_type` (String): Type of analysis performed
- `bias_detected` (Boolean): Whether bias was detected
- `confidence_score` (Float): Confidence score (0.0 to 1.0)
- `bias_indicators` (JSON): Specific bias indicators found
- `analysis_details` (JSON): Detailed analysis results
- `processing_time_ms` (Integer): Processing time in milliseconds

## Running Migrations

```bash
