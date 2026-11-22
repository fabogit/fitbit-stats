use std::sync::Mutex;
use std::time::Duration;
use tauri::{path::BaseDirectory, Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

/// Per-launch API token, shared with the sidecar and the frontend.
struct ApiToken(String);

/// 256 random bits from the OS generator, hex encoded.
fn generate_token() -> String {
  let mut bytes = [0u8; 32];
  getrandom::fill(&mut bytes).expect("failed to read OS random generator");
  bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

#[tauri::command]
fn get_api_token(token: tauri::State<'_, ApiToken>) -> String {
  token.0.clone()
}

/// Handle of the Python sidecar, kept so it can be stopped on exit.
struct Sidecar(Mutex<Option<CommandChild>>);

/// Location of the sidecar inside the bundled resources: the one-directory
/// PyInstaller build, copied next to the application by the bundler.
const SIDECAR_PATH: &str = if cfg!(windows) {
  "fitstats-server/fitstats-server.exe"
} else {
  "fitstats-server/fitstats-server"
};

/// Stop the sidecar.
///
/// The sidecar is a single process, so a plain termination signal is enough.
fn stop_sidecar(child: CommandChild) {
  let pid = child.pid().to_string();
  #[cfg(unix)]
  {
    use std::process::Command;
    let _ = Command::new("kill").args(["-TERM", &pid]).status();
    for _ in 0..30 {
      let alive = Command::new("kill").args(["-0", &pid]).output().map(|o| o.status.success()).unwrap_or(false);
      if !alive {
        return;
      }
      std::thread::sleep(Duration::from_millis(100));
    }
  }
  #[cfg(windows)]
  {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    // /T also ends the worker processes of the server's process pool.
    let _ = std::process::Command::new("taskkill")
      .args(["/PID", &pid, "/T", "/F"])
      .creation_flags(CREATE_NO_WINDOW)
      .status();
  }
  let _ = child.kill();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![get_api_token])
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
      
      // Passed by environment, not argument: arguments show up in process lists.
      let token = generate_token();
      // A resource, not an `externalBin`: the sidecar is a folder, not one file.
      let sidecar_path = app
        .path()
        .resolve(SIDECAR_PATH, BaseDirectory::Resource)
        .expect("failed to locate server sidecar");
      let sidecar = app
        .shell()
        .command(sidecar_path)
        .env("FITSTATS_API_TOKEN", &token);
      app.manage(ApiToken(token));
      let (_rx, child) = sidecar.spawn().expect("failed to spawn server sidecar");
      app.manage(Sidecar(Mutex::new(Some(child))));

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(|app, event| {
      if let RunEvent::Exit = event {
        if let Some(child) = app.state::<Sidecar>().0.lock().ok().and_then(|mut c| c.take()) {
          stop_sidecar(child);
        }
      }
    });
}
