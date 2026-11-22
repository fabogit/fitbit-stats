//! The Python server ("sidecar"): where it is, how it is started, which port it listens on.
//!
//! The contract with `server/api.py` (change both sides together):
//!
//! * the shell sets `FITSTATS_PORT=0`, so the server binds a free port on
//!   127.0.0.1 by itself and nobody can take it in between;
//! * once the socket accepts connections the server prints one line,
//!   `FITSTATS_READY {"port":N,"pid":P}`, on stdout: this is the only way the
//!   port reaches the shell, and it comes from our own pipe, not from the
//!   network, so another program answering on some port cannot be mistaken
//!   for the server.

use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{path::BaseDirectory, AppHandle, Emitter, Manager};
use tauri_plugin_shell::{
  process::{CommandChild, CommandEvent},
  ShellExt,
};
use tokio::sync::watch;

/// Per-launch API token, shared with the sidecar and the frontend.
pub struct ApiToken(pub String);

/// Location of the sidecar inside the bundled resources: the one-directory
/// PyInstaller build, copied next to the application by the bundler.
const SIDECAR_PATH: &str = if cfg!(windows) {
  "fitstats-server/fitstats-server.exe"
} else {
  "fitstats-server/fitstats-server"
};

const READY_PREFIX: &str = "FITSTATS_READY ";
/// Event sent to the webview at every change of the state.
pub const STATE_EVENT: &str = "server-state";
/// How long `server_endpoint` waits for a starting server before answering anyway.
const ENDPOINT_WAIT: Duration = Duration::from_secs(2);
/// A server that has printed nothing like READY after this long is given up.
const START_TIMEOUT: Duration = Duration::from_secs(60);

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Phase {
  Starting,
  Ready,
  Failed,
}

/// What the webview learns about the server: sent as the event payload and as
/// the answer of `server_endpoint`. `generation` grows with every start.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ServerInfo {
  pub generation: u64,
  pub state: Phase,
  #[serde(skip_serializing_if = "Option::is_none")]
  pub port: Option<u16>,
  #[serde(skip_serializing_if = "Option::is_none")]
  pub message: Option<String>,
}

impl ServerInfo {
  fn starting(generation: u64) -> Self {
    Self { generation, state: Phase::Starting, port: None, message: None }
  }
  fn ready(generation: u64, port: u16) -> Self {
    Self { generation, state: Phase::Ready, port: Some(port), message: None }
  }
  fn failed(generation: u64, message: String) -> Self {
    Self { generation, state: Phase::Failed, port: None, message: Some(message) }
  }
}

#[derive(Deserialize)]
struct Handshake {
  port: u16,
}

/// The port of a `FITSTATS_READY {"port":N,"pid":P}` line; `None` for any other line
/// (a zero port is not a port the server can be reached on).
fn parse_ready(line: &str) -> Option<u16> {
  let json = line.trim_end().strip_prefix(READY_PREFIX)?;
  serde_json::from_str::<Handshake>(json).ok().map(|h| h.port).filter(|p| *p != 0)
}

/// A line of the sidecar is cut to this many characters before it is logged.
const MAX_LINE_CHARS: usize = 2000;

/// The level of a line of the server's output, and the line without its level prefix.
///
/// uvicorn's format starts a line with the level (`INFO:     text`). A line without
/// one (a traceback, the output of the interpreter) takes the level of the line
/// before it on the same stream, or `default` when there is none.
fn classify(line: &str, previous: Option<log::Level>, default: log::Level) -> (log::Level, &str) {
  for (prefix, level) in [
    ("DEBUG:", log::Level::Debug),
    ("INFO:", log::Level::Info),
    ("WARNING:", log::Level::Warn),
    ("ERROR:", log::Level::Error),
    ("CRITICAL:", log::Level::Error),
  ] {
    if let Some(rest) = line.strip_prefix(prefix) {
      return (level, rest.trim_start());
    }
  }
  (previous.unwrap_or(default), line)
}

/// `text` with the home folder of the user replaced by `~`, and cut to a sane length.
/// The server already hides the folders it knows about; this is the second line of defence.
fn tidy(text: &str, home: Option<&str>) -> String {
  let mut text = text.trim_end().to_string();
  if let Some(home) = home.filter(|h| h.trim_end_matches(['/', '\\']).len() > 1) {
    let home = home.trim_end_matches(['/', '\\']);
    text = text.replace(home, "~");
    if home.contains('\\') {
      text = text.replace(&home.replace('\\', "/"), "~");
    }
  }
  if text.chars().count() > MAX_LINE_CHARS {
    text = text.chars().take(MAX_LINE_CHARS).collect::<String>() + "…";
  }
  text
}

/// Where the lines of one stream of the sidecar go, with the level of the last one.
struct Forwarder {
  default: log::Level,
  last: Option<log::Level>,
  home: Option<String>,
}

impl Forwarder {
  fn new(default: log::Level, home: Option<String>) -> Self {
    Self { default, last: None, home }
  }

  fn forward(&mut self, bytes: &[u8]) {
    let line = String::from_utf8_lossy(bytes);
    let (level, text) = classify(line.trim_end(), self.last, self.default);
    self.last = Some(level);
    log::log!(target: "sidecar", level, "{}", tidy(text, self.home.as_deref()));
  }
}

struct Inner {
  generation: u64,
  child: Option<CommandChild>,
}

/// The sidecar and its state, managed by the application.
pub struct Supervisor {
  inner: Mutex<Inner>,
  state: watch::Sender<ServerInfo>,
}

impl Supervisor {
  pub fn new() -> Self {
    let (state, _) = watch::channel(ServerInfo::starting(0));
    Self { inner: Mutex::new(Inner { generation: 0, child: None }), state }
  }

  /// Publishes `info` unless a newer generation has started since.
  fn publish(&self, app: &AppHandle, info: ServerInfo) {
    let current = self.inner.lock().map(|i| i.generation).unwrap_or(info.generation);
    if info.generation != current {
      return;
    }
    self.state.send_replace(info.clone());
    let _ = app.emit(STATE_EVENT, info);
  }

  /// Takes the child out of the supervisor, for the exit of the application.
  pub fn take_child(&self) -> Option<CommandChild> {
    self.inner.lock().ok().and_then(|mut i| i.child.take())
  }
}

#[tauri::command]
pub fn get_api_token(token: tauri::State<'_, ApiToken>) -> String {
  token.0.clone()
}

/// The state of the server. While it is starting, waits a moment for it to be
/// ready, so the first request goes out as soon as the server can take it.
#[tauri::command]
pub async fn server_endpoint(supervisor: tauri::State<'_, Supervisor>) -> Result<ServerInfo, String> {
  let mut rx = supervisor.state.subscribe();
  if rx.borrow().state == Phase::Starting {
    let _ = tokio::time::timeout(ENDPOINT_WAIT, rx.wait_for(|i| i.state != Phase::Starting)).await;
  }
  let info = rx.borrow().clone();
  Ok(info)
}

/// Starts the sidecar (generation 1). Called once, from the application setup.
pub fn start(app: &AppHandle) {
  let generation = {
    let supervisor = app.state::<Supervisor>();
    let mut inner = supervisor.inner.lock().expect("sidecar state poisoned");
    inner.generation += 1;
    inner.generation
  };
  app.state::<Supervisor>().publish(app, ServerInfo::starting(generation));
  spawn_generation(app, generation);
}

/// Why the sidecar could not be started, in a few words for the user.
fn describe_spawn_error(error: &tauri_plugin_shell::Error) -> String {
  use std::io::ErrorKind::*;
  match error {
    tauri_plugin_shell::Error::Io(e) => match e.kind() {
      NotFound => "The server program was not found.".into(),
      PermissionDenied => "The server program could not be run (permission denied).".into(),
      _ => format!("The server program could not be run ({}).", e.kind()),
    },
    _ => "The server program could not be run.".into(),
  }
}

fn spawn_generation(app: &AppHandle, generation: u64) {
  let supervisor = app.state::<Supervisor>();
  let path = match app.path().resolve(SIDECAR_PATH, BaseDirectory::Resource) {
    Ok(path) => path,
    Err(e) => {
      log::error!("cannot locate the server: {e}");
      supervisor.publish(app, ServerInfo::failed(generation, "The server program was not found.".into()));
      return;
    }
  };
  // Passed by environment, not argument: arguments show up in process lists.
  let command = app
    .shell()
    .command(path)
    .env("FITSTATS_API_TOKEN", &app.state::<ApiToken>().0)
    // A free port picked by the server itself, whatever the environment says.
    .env("FITSTATS_PORT", "0");
  let (rx, child) = match command.spawn() {
    Ok(spawned) => spawned,
    Err(e) => {
      log::error!("cannot start the server: {e}");
      supervisor.publish(app, ServerInfo::failed(generation, describe_spawn_error(&e)));
      return;
    }
  };
  match supervisor.inner.lock() {
    Ok(mut inner) if inner.generation == generation => inner.child = Some(child),
    _ => {
      let _ = child.kill();
      return;
    }
  }
  let app = app.clone();
  tauri::async_runtime::spawn(watch_events(app.clone(), generation, rx));
  tauri::async_runtime::spawn(watch_start_timeout(app, generation));
}

/// Reads everything the sidecar says, for as long as it lives. It must never
/// stop reading: the channel holds one message, and a sidecar whose output is
/// not taken blocks on its next `print`.
async fn watch_events(app: AppHandle, generation: u64, mut rx: tauri::async_runtime::Receiver<CommandEvent>) {
  let home = app.path().home_dir().ok().map(|p| p.to_string_lossy().into_owned());
  let mut stdout = Forwarder::new(log::Level::Info, home.clone());
  let mut stderr = Forwarder::new(log::Level::Warn, home);
  let mut ready = false;
  while let Some(event) = rx.recv().await {
    let supervisor = app.state::<Supervisor>();
    match event {
      CommandEvent::Stdout(bytes) => match parse_ready(&String::from_utf8_lossy(&bytes)) {
        Some(port) if !ready => {
          ready = true;
          log::info!(target: "sidecar", "sidecar ready on port {port}");
          supervisor.publish(&app, ServerInfo::ready(generation, port));
        }
        _ => stdout.forward(&bytes),
      },
      CommandEvent::Stderr(bytes) => stderr.forward(&bytes),
      CommandEvent::Error(message) => log::error!(target: "sidecar", "{message}"),
      CommandEvent::Terminated(payload) => {
        log::warn!(target: "sidecar", "sidecar exited (code {:?}, signal {:?})", payload.code, payload.signal);
        let message = match (payload.code, payload.signal) {
          (Some(code), _) => format!("The server stopped with code {code}."),
          (None, Some(signal)) => format!("The server was ended by signal {signal}."),
          _ => "The server stopped.".to_string(),
        };
        supervisor.publish(&app, ServerInfo::failed(generation, message));
        break;
      }
      _ => {}
    }
  }
}

/// Gives up on a server that never says it is ready.
async fn watch_start_timeout(app: AppHandle, generation: u64) {
  tokio::time::sleep(START_TIMEOUT).await;
  let supervisor = app.state::<Supervisor>();
  if supervisor.state.borrow().generation == generation && supervisor.state.borrow().state == Phase::Starting {
    log::error!("the server did not become ready in {} s", START_TIMEOUT.as_secs());
    supervisor.publish(&app, ServerInfo::failed(generation, "The server did not answer in 60 seconds.".into()));
    if let Some(child) = supervisor.take_child() {
      let _ = child.kill();
    }
  }
}

/// Stop the sidecar.
///
/// The sidecar is a single process, so a plain termination signal is enough.
pub fn stop_sidecar(child: CommandChild) {
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

#[cfg(test)]
mod tests {
  use super::*;

  #[test]
  fn ready_line_gives_the_port() {
    assert_eq!(parse_ready(r#"FITSTATS_READY {"port":43125,"pid":88}"#), Some(43125));
    assert_eq!(parse_ready("FITSTATS_READY {\"port\":8000,\"pid\":1}\r\n"), Some(8000));
  }

  #[test]
  fn other_lines_are_not_a_handshake() {
    assert_eq!(parse_ready("INFO:     Started server process [12]"), None);
    assert_eq!(parse_ready("FITSTATS_READY"), None);
    assert_eq!(parse_ready("FITSTATS_READY not json"), None);
    assert_eq!(parse_ready(r#"FITSTATS_READY {"port":0,"pid":1}"#), None);
    assert_eq!(parse_ready(r#"FITSTATS_READY {"port":70000,"pid":1}"#), None);
    assert_eq!(parse_ready(r#" FITSTATS_READY {"port":8000}"#), None);
  }

  #[test]
  fn uvicorn_prefix_sets_the_level_and_is_removed() {
    use log::Level::*;
    assert_eq!(classify("INFO:     Started server process [12]", None, Warn), (Info, "Started server process [12]"));
    assert_eq!(classify("WARNING:  Could not save", Some(Info), Info), (Warn, "Could not save"));
    assert_eq!(classify("ERROR:    ETL run failed", None, Info), (Error, "ETL run failed"));
    assert_eq!(classify("CRITICAL: out of memory", None, Info), (Error, "out of memory"));
    assert_eq!(classify("DEBUG:    Skipped a.json", None, Info), (Debug, "Skipped a.json"));
  }

  #[test]
  fn a_line_without_a_prefix_follows_the_line_before_it() {
    use log::Level::*;
    assert_eq!(classify("Traceback (most recent call last):", Some(Error), Info), (Error, "Traceback (most recent call last):"));
    assert_eq!(classify("plain output", None, Info), (Info, "plain output"));
    assert_eq!(classify("plain error", None, Warn), (Warn, "plain error"));
    // A prefix is only a prefix at the start of the line.
    assert_eq!(classify("see INFO: here", None, Warn), (Warn, "see INFO: here"));
  }

  #[test]
  fn home_folder_is_replaced_by_a_tilde() {
    assert_eq!(tidy("open /home/someone/x/a.json", Some("/home/someone")), "open ~/x/a.json");
    assert_eq!(tidy("open /home/someone/x/a.json", Some("/home/someone/")), "open ~/x/a.json");
    assert_eq!(tidy(r"open C:\Users\someone\a.json", Some(r"C:\Users\someone")), r"open ~\a.json");
    assert_eq!(tidy("open C:/Users/someone/a.json", Some(r"C:\Users\someone")), "open ~/a.json");
  }

  #[test]
  fn a_home_that_is_the_root_is_left_alone() {
    assert_eq!(tidy("open /usr/lib/a", Some("/")), "open /usr/lib/a");
    assert_eq!(tidy("open /usr/lib/a", Some("")), "open /usr/lib/a");
    assert_eq!(tidy("open /usr/lib/a", None), "open /usr/lib/a");
  }

  #[test]
  fn a_long_line_is_cut() {
    let line = "x".repeat(5000);
    let out = tidy(&line, None);
    assert_eq!(out.chars().count(), MAX_LINE_CHARS + 1);
    assert!(out.ends_with('…'));
  }
}
