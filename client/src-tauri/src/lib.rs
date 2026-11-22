mod sidecar;

use sidecar::{ApiToken, Supervisor};
use tauri::{Manager, RunEvent};

/// 256 random bits from the OS generator, hex encoded.
fn generate_token() -> String {
  let mut bytes = [0u8; 32];
  getrandom::fill(&mut bytes).expect("failed to read OS random generator");
  bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![sidecar::get_api_token, sidecar::server_endpoint])
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      app.manage(ApiToken(generate_token()));
      app.manage(Supervisor::new());
      sidecar::start(app.handle());

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(|app, event| {
      if let RunEvent::Exit = event {
        if let Some(child) = app.state::<Supervisor>().take_child() {
          sidecar::stop_sidecar(child);
        }
      }
    });
}
