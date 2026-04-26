# 'class' Application: File Reference Guide

This guide explains the purpose and production status of every file in the `class` app.

## 1. Core Django Files (Essential)
These files are the heart of the Django application and must always be in production.

*   **`models/` (Directory)**: Defines your database structure (Schools, Students, Sessions, etc.).
*   **`views.py`**: The primary logic file. Handles main admin dashboards and core features.
*   **`urls.py`**: The "traffic controller." Maps web addresses (URLs) to their respective Python functions.
*   **`apps.py`**: Configuration for the "class" application itself.
*   **`admin.py`**: Configuration for how your data appears in the `/admin` portal.
*   **`forms.py`**: Contains the logic for data input forms (like adding a student or school).
*   **`migrations/` (Directory)**: The history of your database changes. Essential for setting up new servers.

## 2. Business & Role Logic (Essential)
These files handle specific features for different user roles.

*   **`facilitator_views.py`**: Specific logic for the Facilitator Dashboard and student management.
*   **`supervisor_views.py`**: Specific logic for the Supervisor Dashboard and school monitoring.
*   **`admin_session_views.py`**: Handles bulk generation and management of academic sessions.
*   **`reports_views.py`**: powers the data analytics and reporting dashboard.
*   **`views_auth.py`**: Handles login, logout, and session security.
*   **`facilitator_task_views.py`**: Manages the uploading of photos, videos, and tasks by facilitators.
*   **`step_status_views.py`**: Powers the interactive "steps" when a facilitator is conducting a session.

## 3. Middleware & System Infrastructure (Useful for Production)
These files run in the background on every request to keep the site fast and secure.

*   **`cache_control_middleware.py`**: Ensures that browsers only cache what they are supposed to.
*   **`db_connection_middleware.py`**: Manages the connection to the Neon/PostgreSQL database.
*   **`performance_middleware.py`**: Tracks how long pages take to load so you can find slow spots.
*   **`pwa_middleware.py`**: Helps the site act like a mobile app (PWA).
*   **`session_timeout_middleware.py`**: Automatically logs users out after inactivity for security.
*   **`file_upload_middleware.py`**: Optimizes how large photos and videos are uploaded.

## 4. Utilities & Performance (Optimization)
Helper files that make the code cleaner and faster.

*   **`cache_utils.py`**: Functions to save complex data in "fast memory" (Redis/Cache) to speed up the UI.
*   **`query_optimizations.py`**: Contains specialized database queries that reduce load times from seconds to milliseconds.
*   **`signals_optimization.py`** & **`signals.py`**: Automatically triggers actions (like updating counts) when data changes.
*   **`decorators.py`**: Simple tags like `@login_required` used to protect views.
*   **`mixins.py`**: Reusable code snippets used across different view classes.
*   **`message_utils.py`**: Simplifies showing "Success" or "Error" popups to users.

## 5. Miscellaneous
*   **`views_optimized.py`**: A reference file containing the "Optimized" versions of your views. (Kept for safety/backup).
*   **`error_handlers.py`**: Custom "Page Not Found" (404) and "Server Error" (500) pages.
