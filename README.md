# FitStats: Personal Health Analytics & Dashboard (V3.x Desktop)

A comprehensive, **cross-platform Desktop Application** designed to locally analyze, visualize, and benchmark personal health data exported from Fitbit.

**V3.0 Update:** The project has successfully completed its evolution into a standalone Desktop Application. Built with **Tauri v2**, **React/Redux**, and a **Python PyInstaller** analytics engine acting as a sidecar. No Docker, no manual script executions, and no dependency setup required for the end user.

## 🚀 Features & Architecture

### 🏗 Native Desktop Architecture

- **Tauri v2 Wrapper:** Provides a lightweight native OS window with full filesystem sandboxing capabilities and native directory pickers.
- **Python Sidecar (Engine):** A standalone executable compiled with PyInstaller. It heavily utilizes Pandas for ETL and metabolic math without requiring the user to have Python installed.
- **Privacy-First (100% Offline):** Your health data never leaves your computer. The Python engine computes the metrics and safely writes them to your highly-isolated local `AppData` directory (`$APPDATA/com.fitstats`). React reads it from there seamlessly.

### 📊 Analytics & Metrics

- **Readiness Score (Z-Score):** Custom algorithm combining Sleep Quality and Resting Heart Rate deviation.
- **Metabolic Analysis:** **BMR** (Mifflin-St Jeor) vs **Active Calories** breakdown.
- **Physiology & Sleep:** Tracking of **HRV**, **Stress Score**, and deep breakdown of Sleep architecture.
- **Advanced Training Load:** **TRIMP** (Training Impulse), **Training Monotony**, and **Strain** derived from detailed Heart Rate Zones and workout parsing (Steps/Distance/Exercises).
- **Illness Predictor:** Dual-flag early warning system tracking abnormal short-term (Daily) and long-term (Trend) deviations in Nightly Skin Temperature and Respiratory Rate.
- **HRV Coefficient of Variation (CV):** Dynamic tracking of autonomous nervous system adaptability and recovery capacity.

### ⚡ Server Architecture

The project has evolved into a unified **FastAPI backend** that serves both the Tauri desktop environment and standalone Docker deployments:

- **Unified API:** Centralizes ETL, metabolic math, and health briefing logic.
- **Asynchronous Processing:** Heavy Data Merging (ETL) is spawned seamlessly into **BackgroundTasks**, eliminating HTTP route blocking.
- **Real-time Updates:** A persistent, full-duplex **WebSocket (`/ws/status`)** continuously streams real-time status updates directly to the Frontend, eliminating polling and providing robust scalability.

---

## 🏃‍♂️ End-User Usage

You do **not** need to touch any code or terminal to use this application!

1. Head over to the [**Releases**](../../releases) tab on this GitHub repository.
2. Download the pre-compiled installer for your system:
   - `.exe` / `.msi` for Windows
   - `.dmg` / `.app` for macOS
   - `.AppImage` / `.deb` for Linux
3. Run the application!
4. On the onboarding screen, enter your biometrics (Date of Birth, Height, Weight).
5. **Browse** and select your completely unzipped RAW Fitbit Export folder (the overarching one containing folders like `Physical Activity`, `Sleep`, etc.).
6. Click **Calculate**. The app will do the heavy lifting in the background and load your interactive dashboard.

#### 🍎 Special Note for macOS Users (M1/M2/M3/M4)

As the application is currently distributed without a paid Apple Developer certificate, macOS Gatekeeper may flag it as "damaged" or from an "unidentified developer."

To fix this, open your **Terminal** and run:

```bash
xattr -cr /Applications/FitStats.app
```

_(Or drag the app icon into the terminal after typing `xattr -cr `)._ This removes the quarantine flag and allows the app to start normally.

_(Note: The app remembers your biometrics and folder path securely inside your OS's AppData for subsequent launches!)_

---

## 🐳 Docker Deployment

For users who prefer a web-based interface or home lab deployment, a full Docker stack is provided.

### Quick Start

1. Ensure you have **Docker** and **Docker Compose** installed.
2. Clone this repository.
3. Place your unzipped Fitbit export in a folder named `data` in the project root (or modify the volume mount in `docker-compose.yml`).
4. Run the stack:
   ```bash
   docker-compose up -d --build
   ```
5. Open your browser to [**http://localhost:8080**](http://localhost:8080).

### Services

- **Frontend (port 8080):** The web dashboard served by Nginx.
- **API Server (port 8000):** The Python/FastAPI engine handling calculations.
- **Engine Watcher:** An optional background service that automatically triggers a re-calculate when files in the `data/` directory are modified.

---

## 🛠️ Developer Setup

If you wish to modify the code, you will need to run the hybrid stack locally.

### Prerequisites

1. **Python 3.14+**
2. **Node.js 24.12+** & **pnpm 10+**
3. **Rust Toolchain:** Install via [rustup.rs](https://rustup.rs/).
4. **System Dependencies:**
   - **Linux (Debian/Ubuntu):**
     ```bash
     sudo apt-get update
     sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
     ```
   - **macOS:** Install Xcode Command Line Tools: `xcode-select --install`.
   - **Windows:** Install [WebView2 runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) and C++ Build Tools.

### 1. Compile the Python Sidecar

Tauri absolutely needs the Python engine compiled as a binary in its `bin/` folder before launching.

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
```

# Compile standalone executable

`pyinstaller --clean fitstats-engine.spec`

#### Sidecar Naming Convention

Tauri requires sidecars to have a specific suffix based on the **target triple**. You can find your triple by running `rustc -Vv | grep host`.

Common names:

- **Mac (Silicon):** `fitstats-engine-aarch64-apple-darwin`
- **Mac (Intel):** `fitstats-engine-x86_64-apple-darwin`
- **Linux:** `fitstats-engine-x86_64-unknown-linux-gnu`
- **Windows:** `fitstats-engine-x86_64-pc-windows-msvc.exe`

```bash
# Example for Mac M1/M2/M3/M4:
mkdir -p ../client/src-tauri/bin
cp dist/fitstats-engine ../client/src-tauri/bin/fitstats-engine-aarch64-apple-darwin
```

### 2. Run the Tauri App

```bash
cd client
pnpm install

# Option A: Development mode (with Hot Reload and Debug Console)
pnpm tauri dev

# Option B: Build a final production installer (DMG, MSI, AppImage, etc.)
pnpm tauri build
```

---

## ☁️ CI/CD Workflow (GitHub Actions)

This repository is equipped with a fully automated Release Pipeline designed to cross-compile the application for all major Operating Systems at once without needing physical hardware.

- **Trigger:** The workflow is triggered automatically when a new Git tag starting with `v` is pushed to the repository (e.g., `git tag v3.1.0 && git push origin v3.1.0`).
- **Matrix Strategy:** It spins up three parallel cloud instances (`ubuntu-latest`, `macos-latest`, `windows-latest`).
- **Version Automation:** The CI/CD pipeline uses `client/package.json` as the single source of truth. The version defined there is automatically injected into the Tauri configuration and used to name all generated artifacts (e.g., `FitStats_3.1.0_aarch64.dmg`).
- **Signing:** Includes automated ad-hoc signing for macOS binaries (Sidecars and App Bundle) to ensure compatibility with Apple Silicon security requirements.

---

## 🏛 Legacy Versions

If you are looking for older versions of the project:

- **[v1 (Legacy)](../../tree/v1):** The original Python scripts and basic data parsing.
- **[v2 (Legacy)](../../tree/v2):** The first React web interface with Docker support.
- **[Standalone](../../tree/main):** The current active development branch (v3.x).

---

## 📄 License

Personal Use.
