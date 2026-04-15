# Implementation Plan - Log Sync & Profile Management

## Problem
1. **Log Desync**: Users only see generic "high-level" logs in the UI, missing technical details (errors, Gemini 503s, etc.) that are visible in the terminal.
2. **Missing UI**: The dashboard lacks a section to manage Chrome Profiles for YouTube uploads.
3. **Multi-Tenant Setup**: No way for users to trigger the `setup_chrome_profile.py` script from the web.

## Proposed Changes

### 1. Backend: Unified Logging Context
Modify `PipelineRunner` to use a custom `logging.Handler` that captures all logs from the `modules.*` namespace and appends them to `self.state["logs"]` during a run.

### 2. Backend: Profile Setup Endpoint
#### [MODIFY] [main.py](file:///D:/AI-projects/YT_Generator/Hunter-Ghost-Creator/SaaS_Project/backend/main.py)
Add `@app.post("/api/settings/setup_profile")` to:
- Run `setup_chrome_profile.py` as a subprocess.
- Return the new profile configuration.

### 3. Frontend: Chrome Profile Manager
#### [MODIFY] [page.tsx](file:///D:/AI-projects/YT_Generator/Hunter-Ghost-Creator/SaaS_Project/frontend/app/page.tsx)
- Add a "CHROME PROFILES" section in settings.
- Display a list of profiles with "Active" toggle.
- Add "SETUP NEW PROFILE" button that calls the new backend endpoint.

### 4. Backend: Dynamic Profile Passing
Ensure `uploader.py` correctly uses the profile path from the `user_config` passed to it (already mostly implemented).

## Verification Plan
1. Start a pipeline run and verify that technical logs (e.g., "Gemini API call...") appear in the UI terminal.
2. Go to Settings and create a new Chrome profile. Verify it syncs to Supabase.
3. Run an upload and verify it uses the correct profile from the user's cloud config.
