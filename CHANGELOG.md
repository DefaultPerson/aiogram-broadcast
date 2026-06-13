# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - Unreleased

### Added
- PostgreSQL storage backend `PostgresBroadcastStorage` (backed by `asyncpg`),
  a drop-in alternative to Redis. Includes `create_schema()` for one-time table
  setup and a `from_dsn()` convenience constructor.
- `examples/postgres.py` and a "Storage" section in the README.

### Changed
- **Breaking:** `redis` is no longer a hard dependency. Install a backend
  explicitly with `aiogram-broadcast[redis]` or `aiogram-broadcast[postgres]`.
  The `[all]` extra now bundles both backends plus the scheduler/UI.
- The package version is now single-sourced from `aiogram_broadcast/__init__.py`
  (hatch dynamic version), preventing future drift.
- Constrained `redis` to `<8` for now: redis-py 8.x ships reworked type stubs
  that are not yet compatible with our strict type checking.

### Fixed
- Version mismatch between `aiogram_broadcast/__init__.py` (`0.1.0`) and the
  packaged metadata (`0.1.1`).

## [0.1.1] - 2026-03-11

### Changed
- Documentation and packaging tweaks.

## [0.1.0] - 2026-03-11

### Added
- Initial release: subscriber middleware, rate-limited broadcasting, APScheduler
  integration, Redis storage, progress callbacks and an interactive UI menu.
