# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-05-07

### Added

- Atkinson Hyperlegible as default body font, loaded from bundled TTFs via GDI
- OpenDyslexic opt-in toggle in the toolbar, saved to settings.json

## [1.2.0] - 2026-04-09

### Added

- Cross-reference mod `extends` declarations against RTV.pck vanilla script list
- Unit tests for `vmz_scanner`, `analyzer`, and `config_io` (41 tests)

### Changed

- Migrated project to UV

### Fixed

- CI workflow stability
- Path auto-detect validation
- Priority dupe save blocker and 999 cap collision
- Comment stripping and lock hint display
- `heapq` topological sort correctness

## [1.1.1] - 2026-03-15

### Added

- Manual priority lock
- Steam install auto-detect
- Priority cap enforcement
- Splash screen on startup

### Changed

- Lighter `ModRow` rendering
- Throttled scroll performance

## [1.1.0] - 2026-02-01

### Added

- Support for Metro Mod Loader v3.x profile-based `mod_config.cfg` format
- Rename `.zip` button
- Stale entry cleanup on load

## [1.0.0] - 2025-12-01

### Added

- Initial release: load-order editor for RtV mod list with conflict detection and update-link tracking

[1.2.1]: https://github.com/jonigirl/RtV-Load-Order-Editor/releases/tag/v1.2.1
[1.2.0]: https://github.com/jonigirl/RtV-Load-Order-Editor/releases/tag/v1.2.0
[1.1.1]: https://github.com/jonigirl/RtV-Load-Order-Editor/releases/tag/v1.1.1
[1.1.0]: https://github.com/jonigirl/RtV-Load-Order-Editor/releases/tag/v1.1.0
[1.0.0]: https://github.com/jonigirl/RtV-Load-Order-Editor/releases/tag/v1.0.0
