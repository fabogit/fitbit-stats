# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `LICENSE` file with the MIT License terms.
- Progress banner with step and percentage, shown above every view while the ETL runs.
- `pytest` setup for the server, with a first test for the ETL date range.

### Changed

- Version 3.0.2 is now used consistently in `package.json`, `tauri.conf.json`, `Cargo.toml` and `Cargo.lock`; Cargo package metadata filled in; the web page title and icon replaced with the FitStats ones.
- README developer setup rewritten around the `fitstats-server` sidecar, and its macOS and Docker watcher notes corrected.
- `client/README.md` replaced the Vite template text with a description of this client.

### Fixed

- The dashboard refreshes after a recalculation or a reset instead of keeping stale data, and shows the empty state when no data is left.
- The ETL date range is taken from the merged data instead of from the names of the calories files, which cut the output at the first day of the last monthly file. `START_DATE` and `END_DATE` apply only when set explicitly, and the detected range is no longer written to the configuration, so a later run is not pinned to the dates of the first one.
- Docker: the `api-server` health check used `curl`, which the image does not contain, so the service never became healthy and the frontend never started. It now uses the Python interpreter in the image.

### Removed

- The unused `fitstats-engine` sidecar, from the Tauri configuration, the capabilities, the release workflow and the PyInstaller spec.

## [3.0.2] - 2026-04-16

### Fixed

- Windows: the client now reaches the local API at `127.0.0.1` instead of `localhost`, which could resolve to IPv6 while the server listened on IPv4 only. The Content Security Policy was updated to match.

### Changed

- Client package version set to 3.0.2 and Tauri package version to 3.0.0.

## [3.0.1] - 2026-04-13

### Added

- Real-time ETL progress over WebSocket, shown during the first calculation; the ETL runs in the background.
- Daily Brief returned as structured JSON by a Python module, with an error and empty state in the Brief view.
- New charts: RHR correlation and sedentary trend. Recovery Score calculated per day.
- Advanced metrics: sleep efficiency, sleep debt, autonomic balance, TRIMP, training monotony and strain, illness flags, HRV variation and ACWR flags; parsers for steps, distance and exercise sessions.
- Factory reset and Python 3.14 support.
- Release workflow builds for Linux x64, macOS arm64 (ad-hoc signed) and Windows x64, and builds the `fitstats-server` sidecar.
- Version synchronised from `client/package.json` into the Tauri configuration during release builds.
- Health checks for the Docker services; backend services renamed (`api-server`, `engine-watcher`).
- Minimum and maximum data dates tracked in the dashboard state.

### Changed

- Client and server communicate only through the backend API; the native Tauri sidecar logic was removed.
- Application identifier changed to `com.fitstats`.
- Biometric inputs are now required for the metabolic metrics.
- Chart components memoized; tooltip component improved.
- Analytics dashboard layout and chart sizing revised; pnpm workspace configured.
- `standalone` branch merged into `main`.

### Removed

- The `visualize.py` plotting script and the subprocess-based daily briefing script.
- The macOS Intel (`x86_64`) build target from the release workflow.
- Unused deployment CLI dependencies.

## [3.0.0] - 2026-03-25

The release was published on 2026-04-13. Its tag points to a commit made on 2026-03-25, and its installers were published with the version label 1.0.0.

### Added

- Client-server architecture: FastAPI backend, Docker stack (API, watcher, Nginx frontend) and an onboarding flow.
- Tauri v2 desktop application with a PyInstaller sidecar, and a release workflow that builds it.
- Content Security Policy for the web client.

### Changed

- BMR uses the age on each record's date.
- Dashboard KPI calculations and charts memoized to avoid unnecessary re-renders; chart tooltips are keyboard accessible, with better placement and value precision.
- Chart type errors fixed.

### Removed

- The previous V1 dashboard code.

## [2.1] - 2025-12-16

### Added

- Data Grid view, activity heatmap, advanced analytics view.
- Light and dark themes, responsive layout, sidebar redesign.
- Data caching in the client store.

### Changed

- Chart tooltips restyled.

## [2.0] - 2025-12-11

### Added

- React, TypeScript, Redux Toolkit and Recharts front end with sidebar navigation, KPI grid and synchronised charts.
- Backend split into `etl`, `parsers` and `metrics` modules.
- Parsers for sleep stages, HRV and stress.

### Changed

- Project restructured into `server`, `client` and `dashboard-v1` folders; V1 kept as a legacy branch.

## [1.0] - 2025-12-08

### Added

- `analyze.py` ETL script that merges the Fitbit export, computes a readiness score, Basal Metabolic Rate, active calories and an intensity index, and exports the result to JSON and CSV.
- `visualize.py` script producing matplotlib and seaborn charts, and `daily_brief.py` command-line summary.
- Local Chart.js dashboard.

[Unreleased]: https://github.com/fabogit/fitbit-stats/compare/v3.0.2...HEAD
[3.0.2]: https://github.com/fabogit/fitbit-stats/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/fabogit/fitbit-stats/compare/v3.0.0...v3.0.1
[3.0.0]: https://github.com/fabogit/fitbit-stats/compare/v2.1...v3.0.0
[2.1]: https://github.com/fabogit/fitbit-stats/compare/v2.0...v2.1
[2.0]: https://github.com/fabogit/fitbit-stats/compare/v1.0...v2.0
[1.0]: https://github.com/fabogit/fitbit-stats/releases/tag/v1.0
