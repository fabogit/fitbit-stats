# Fitbit Personal Health Analytics & Dashboard (V3.0 Desktop)

A comprehensive, **cross-platform Desktop Application** designed to locally analyze, visualize, and benchmark personal health data exported from Fitbit.

**V3.0 Update:** The project has successfully completed its evolution into a standalone Desktop Application. Built with **Tauri v2**, **React/Redux**, and a **Python PyInstaller** analytics engine acting as a sidecar. No Docker, no manual script executions, and no dependency setup required for the end user.

## 🚀 Features & Architecture

### 🏗 Native Desktop Architecture

- **Tauri v2 Wrapper:** Provides a lightweight native OS window with full filesystem sandboxing capabilities and native directory pickers.
- **Python Sidecar (Engine):** A standalone executable compiled with PyInstaller. It heavily utilizes Pandas for ETL and metabolic math without requiring the user to have Python installed.
- **Privacy-First (100% Offline):** Your health data never leaves your computer. The Python engine computes the metrics and safely writes them to your highly-isolated local `AppData` directory (`$APPDATA/com.fitstats.app`). React reads it from there seamlessly.

### 📊 Analytics & Metrics

- **Readiness Score (Z-Score):** Custom algorithm combining Sleep Quality and Resting Heart Rate deviation.
- **Metabolic Analysis:** **BMR** (Mifflin-St Jeor) vs **Active Calories** breakdown.
- **Physiology & Sleep:** Tracking of **HRV**, **Stress Score**, and deep breakdown of Sleep architecture.
- **Advanced Training Load:** **TRIMP** (Training Impulse), **Training Monotony**, and **Strain** derived from detailed Heart Rate Zones and workout parsing (Steps/Distance/Exercises).
- **Illness Predictor:** Dual-flag early warning system tracking abnormal short-term (Daily) and long-term (Trend) deviations in Nightly Skin Temperature and Respiratory Rate.
- **HRV Coefficient of Variation (CV):** Dynamic tracking of autonomous nervous system adaptability and recovery capacity.

### ⚡ Server Architecture

The internal backend leverages an Event-Driven, highly asynchronous design:
- Heavy Data Merging (ETL) is spawned seamlessly into **BackgroundTasks**, eliminating HTTP route blocking.
- A persistent, full-duplex **WebSocket (`/ws/status`)** continuously streams real-time status updates directly to the Frontend (React hooks / Angular observables). This eliminates polling and provides robust scalability even for datasets spanning multiple years.

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

_(Note: The app remembers your biometrics and folder path securely inside your OS's AppData for subsequent launches!)_

---

## 🛠️ Developer Setup

If you wish to modify the code, you will need to run the hybrid stack locally.

### Prerequisites

1. **Python 3.14+**
2. **Node.js 24.12+** & **pnpm 10+**
3. **Rust Toolchain** (cargo) & Tauri dependencies

### 1. Compile the Python Sidecar

Tauri absolutely needs the Python engine compiled as a binary in its `bin/` folder before launching.

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

# Compile standalone executable
pyinstaller --clean fitstats-engine.spec

# Move the executable to Tauri's bin directory with the correct target-triple specific name
# e.g., on Linux x86_64:
mkdir -p ../client/src-tauri/bin
cp dist/fitstats-engine ../client/src-tauri/bin/fitstats-engine-x86_64-unknown-linux-gnu
```

### 2. Run the Tauri App

```bash
cd client
pnpm install
# Start the Vite development server + Tauri Window
pnpm tauri dev
```

---

## ☁️ CI/CD Workflow (GitHub Actions)

This repository is equipped with a fully automated Release Pipeline designed to cross-compile the application for all major Operating Systems at once without needing physical hardware.

- **Trigger:** The workflow is triggered automatically when a new Git tag starting with `v` is pushed to the repository (e.g., `git tag v1.0.0 && git push --tags`).
- **Matrix Strategy:** It spins up three parallel cloud instances (`ubuntu-latest`, `macos-latest`, `windows-latest`).
- **Build Flow:** For each OS, it installs Python & Node, compiles the Python engine via PyInstaller into its native flavor (`.exe` on Win, macOS binary, Linux ELF), bundles it into the Tauri workflow utilizing `tauri-apps/tauri-action`, and uploads the final installers directly to the GitHub Release page.

---

## 📄 License

Personal Use.
