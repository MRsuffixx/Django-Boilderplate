# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and semantic versioning.

## [Unreleased]

### Changed

- Made SQLite/no-Redis/no-Celery the default zero-infrastructure mode.
- Added explicit PostgreSQL, Redis, Celery, and S3 dependency extras and feature switches.
- Added database-backed brute-force counters and synchronous task dispatch fallbacks.
- Documented minimal, standard, and advanced infrastructure modes.

## [0.1.0] - 2026-08-12

### Added

- Initial reusable Django foundation with accounts, authentication, RBAC, audit, notifications, API keys, file storage, webhooks, Celery, Docker, tests, and documentation.
