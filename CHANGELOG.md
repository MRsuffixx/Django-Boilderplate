# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and semantic versioning.

## [Unreleased]

### Changed

- Made SQLite/no-Redis/no-Celery the default zero-infrastructure mode.
- Added explicit PostgreSQL, Redis, Celery, and S3 dependency extras and feature switches.
- Added database-backed brute-force counters and synchronous task dispatch fallbacks.
- Documented minimal, standard, and advanced infrastructure modes.

### Added

- Added canonical AI-agent instructions, focused module guidance, AI project context/workflow/security/testing rules, current project state, and architecture decision records.
- Added minimal Claude, Cursor, and GitHub Copilot pointers to the canonical `AGENTS.md` instructions.

## [0.1.0] - 2026-08-12

### Added

- Initial reusable Django foundation with accounts, authentication, RBAC, audit, notifications, API keys, file storage, webhooks, Celery, Docker, tests, and documentation.
