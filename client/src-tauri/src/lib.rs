mod sidecar;

use sidecar::{ApiToken, Supervisor};
use tauri::{Manager, RunEvent};
use tauri_plugin_log::{RotationStrategy, Target, TargetKind};
/// A log file is closed at this size; a few older files are kept (the plugin keeps up to three, about 4 MB in all).
const LOG_FILE_MAX_BYTES: u128 = 1_000_000;
const LOG_FILES_KEPT: usize = 3;

/// The log of the application, in release builds too: it is where the output of
/// the server goes, and the only trace a user can send when the server fails.
fn log_plugin<R: tauri::Runtime>() -> tauri::plugin::TauriPlugin<R> {
  let mut targets = vec![Target::new(TargetKind::LogDir { file_name: Some(sidecar::LOG_FILE_NAME.into()) })];
  if cfg!(debug_assertions) {
    targets.push(Target::new(TargetKind::Stdout));
  }
  tauri_plugin_log::Builder::new()
    .targets(targets)
    .level(log::LevelFilter::Info)
    .max_file_size(LOG_FILE_MAX_BYTES)
    // KeepOne (the default) deletes the file when it is full: the log would be lost
    // just when it is needed.
    .rotation_strategy(RotationStrategy::KeepSome(LOG_FILES_KEPT))
    .build()
}

/// 256 random bits from the OS generator, hex encoded.
fn generate_token() -> String {
  let mut bytes = [0u8; 32];
  getrandom::fill(&mut bytes).expect("failed to read OS random generator");
  bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![
      sidecar::get_api_token,
      sidecar::server_endpoint,
      sidecar::restart_server,
      sidecar::log_location
    ])
    // First, so that everything after it can be logged.
    .plugin(log_plugin())
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      app.manage(ApiToken(generate_token()));
      app.manage(Supervisor::new());
      sidecar::start(app.handle());

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(|app, event| {
      if let RunEvent::Exit = event {
        app.state::<Supervisor>().shutdown();
      }
    });
}
