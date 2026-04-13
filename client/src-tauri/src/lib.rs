use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_fs::init())
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
      
      let sidecar = app.shell().sidecar("fitstats-server").expect("failed to construct server sidecar");
      let (mut _rx, _child) = sidecar.spawn().expect("failed to spawn server sidecar");
      
      // Let it run in background. child process handle guarantees it's tracked by the OS/Tauri.
      
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
