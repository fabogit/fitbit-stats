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
//!   for the server;
//! * the shell tells the server where to keep its files with `CLIENT_PUBLIC_DIR`
//!   (its own data folder), so both always mean the same folder.

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
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

/// Name of the log file, without `.log` (see `log_plugin` in lib.rs).
pub const LOG_FILE_NAME: &str = "FitStats";

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

/// Restarts after an unexpected exit of a server that had been ready: the wait
/// before each one, and how many are allowed in `RESTART_WINDOW`.
const RESTART_DELAYS: [Duration; 2] = [Duration::from_secs(1), Duration::from_secs(5)];
const RESTART_WINDOW: Duration = Duration::from_secs(5 * 60);
/// A server that exits before it was ready gets one more try, after this wait.
const EARLY_RETRY_DELAY: Duration = Duration::from_secs(1);
/// On exit the server is asked to stop and given this long before it is killed.
const STOP_GRACE: Duration = Duration::from_secs(3);

#[derive(Debug, PartialEq, Eq)]
enum Decision {
  Restart(Duration),
  GiveUp,
}

/// When an unexpected exit of the server is answered with a new start, and when not.
///
/// * Before it was ready: it fails the same way every time (a missing library, a
///   damaged folder), so there is one more try and then it is given up.
/// * After it was ready: at most two restarts in five minutes, after 1 s and
///   after 5 s; a server that keeps dying is not restarted forever.
#[derive(Default)]
struct RestartPolicy {
  restarts: Vec<Instant>,
  retried_start: bool,
}

impl RestartPolicy {
  fn on_ready(&mut self) {
    self.retried_start = false;
  }

  fn on_exit(&mut self, now: Instant, was_ready: bool) -> Decision {
    if !was_ready {
      if self.retried_start {
        return Decision::GiveUp;
      }
      self.retried_start = true;
      return Decision::Restart(EARLY_RETRY_DELAY);
    }
    self.restarts.retain(|t| now.saturating_duration_since(*t) < RESTART_WINDOW);
    match RESTART_DELAYS.get(self.restarts.len()) {
      Some(delay) => {
        self.restarts.push(now);
        Decision::Restart(*delay)
      }
      None => Decision::GiveUp,
    }
  }
}

/// A running sidecar: the handle and a flag that its exit has been seen.
struct Running {
  child: CommandChild,
  exited: Arc<AtomicBool>,
}

struct Inner {
  generation: u64,
  running: Option<Running>,
  /// The application is closing: an exit of the server is expected.
  stopping: bool,
  policy: RestartPolicy,
}

/// The sidecar and its state, managed by the application.
pub struct Supervisor {
  inner: Mutex<Inner>,
  state: watch::Sender<ServerInfo>,
}

impl Supervisor {
  pub fn new() -> Self {
    let (state, _) = watch::channel(ServerInfo::starting(0));
    let inner = Inner { generation: 0, running: None, stopping: false, policy: RestartPolicy::default() };
    Self { inner: Mutex::new(inner), state }
  }

  fn lock(&self) -> std::sync::MutexGuard<'_, Inner> {
    self.inner.lock().unwrap_or_else(|poisoned| poisoned.into_inner())
  }

  // The three methods below change the generation and the published state together, under the
  // `inner` lock, and hand the new state to `emit` before the lock is released: a report about
  // an old generation can never overwrite a newer one, and events leave in the order of the changes.

  /// Publishes `info` if it belongs to the current generation. True if it was written.
  fn publish(&self, emit: &dyn Fn(ServerInfo), info: ServerInfo) -> bool {
    let inner = self.lock();
    if info.generation != inner.generation {
      return false;
    }
    self.state.send_replace(info.clone());
    emit(info);
    true
  }

  /// Starts a new generation: `Starting` is published and the number is returned.
  fn next_generation(&self, emit: &dyn Fn(ServerInfo)) -> u64 {
    let mut inner = self.lock();
    inner.generation += 1;
    let info = ServerInfo::starting(inner.generation);
    self.state.send_replace(info.clone());
    emit(info);
    inner.generation
  }

  /// The server of `generation` said it is ready. Ignored if that generation is over, or has
  /// been given up on already.
  fn mark_ready(&self, emit: &dyn Fn(ServerInfo), generation: u64, port: u16) -> bool {
    let mut inner = self.lock();
    let starting = {
      let current = self.state.borrow();
      current.generation == generation && current.state == Phase::Starting
    };
    if inner.generation != generation || !starting {
      return false;
    }
    inner.policy.on_ready();
    let info = ServerInfo::ready(generation, port);
    self.state.send_replace(info.clone());
    emit(info);
    true
  }

  /// The start of `generation` took too long: if it is still starting (not ready, not replaced
  /// by a newer one), it is marked failed, and its process is handed back to be ended.
  /// `None` when nothing was done.
  fn give_up_start(&self, emit: &dyn Fn(ServerInfo), generation: u64, message: &str) -> Option<Option<Running>> {
    let mut inner = self.lock();
    let starting = {
      let current = self.state.borrow();
      current.generation == generation && current.state == Phase::Starting
    };
    if inner.generation != generation || !starting {
      return None;
    }
    let info = ServerInfo::failed(generation, message.to_string());
    self.state.send_replace(info.clone());
    emit(info);
    Some(inner.running.take())
  }

  /// Called when the application is closing: asks the server to stop, and kills it
  /// if it has not after a few seconds.
  pub fn shutdown(&self) {
    let running = {
      let mut inner = self.lock();
      inner.stopping = true;
      inner.running.take()
    };
    if let Some(running) = running {
      stop_running(running);
    }
  }
}

/// What goes to the webview at every change of the state.
fn emitter(app: &AppHandle) -> impl Fn(ServerInfo) + '_ {
  move |info| {
    let _ = app.emit(STATE_EVENT, info);
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

/// Starts the server again, whatever state it is in (the button of the failure screens).
#[tauri::command]
pub fn restart_server(app: AppHandle) {
  let supervisor = app.state::<Supervisor>();
  let old = {
    let mut inner = supervisor.lock();
    inner.policy = RestartPolicy::default();
    inner.running.take()
  };
  if let Some(old) = old {
    // Its exit is not news: the generation it belongs to is over.
    std::thread::spawn(move || stop_running(old));
  }
  let generation = supervisor.next_generation(&emitter(&app));
  spawn_generation(&app, generation);
}

/// Full path of the log file, for the screens that tell the user where it is.
#[tauri::command]
pub fn log_location(app: AppHandle) -> Result<String, String> {
  let dir = app.path().app_log_dir().map_err(|e| e.to_string())?;
  Ok(dir.join(format!("{LOG_FILE_NAME}.log")).to_string_lossy().into_owned())
}

/// Starts the sidecar (generation 1). Called once, from the application setup.
pub fn start(app: &AppHandle) {
  let generation = app.state::<Supervisor>().next_generation(&emitter(app));
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

/// How an exit of the server is told to the user.
fn describe_exit(code: Option<i32>, signal: Option<i32>, was_ready: bool) -> String {
  let what = if was_ready { "stopped" } else { "stopped before it was ready" };
  match (code, signal) {
    (Some(code), _) => format!("The server {what} (code {code})."),
    (None, Some(signal)) => format!("The server {what} (signal {signal})."),
    _ => format!("The server {what}."),
  }
}

fn spawn_generation(app: &AppHandle, generation: u64) {
  let supervisor = app.state::<Supervisor>();
  let path = match app.path().resolve(SIDECAR_PATH, BaseDirectory::Resource) {
    Ok(path) => path,
    Err(e) => {
      log::error!("cannot locate the server: {e}");
      supervisor.publish(&emitter(app), ServerInfo::failed(generation, "The server program was not found.".into()));
      return;
    }
  };
  let data_dir = app.path().app_data_dir().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default();
  // Passed by environment, not argument: arguments show up in process lists.
  let command = app
    .shell()
    .command(path)
    .env("FITSTATS_API_TOKEN", &app.state::<ApiToken>().0)
    // A free port picked by the server itself, whatever the environment says.
    .env("FITSTATS_PORT", "0")
    // The folder this shell calls its data folder; the server keeps its files there.
    // Always set, so a value inherited from the environment never counts (empty
    // means "use your own default" to the server).
    .env("CLIENT_PUBLIC_DIR", data_dir)
    // The server stops when its input closes, which is what happens if this
    // application dies without a chance to stop it (a crash, a kill).
    .env("FITSTATS_EXIT_ON_STDIN_EOF", "1");
  let (rx, child) = match command.spawn() {
    Ok(spawned) => spawned,
    Err(e) => {
      log::error!("cannot start the server: {e}");
      supervisor.publish(&emitter(app), ServerInfo::failed(generation, describe_spawn_error(&e)));
      return;
    }
  };
  let exited = Arc::new(AtomicBool::new(false));
  {
    let mut inner = supervisor.lock();
    if inner.generation != generation || inner.stopping {
      drop(inner);
      let _ = child.kill();
      return;
    }
    // Nothing should be here; if something is, it must not be left running unseen.
    let replaced = inner.running.replace(Running { child, exited: exited.clone() });
    drop(inner);
    if let Some(old) = replaced {
      log::warn!("a server process was still registered; stopping it");
      std::thread::spawn(move || stop_running(old));
    }
  }
  tauri::async_runtime::spawn(watch_events(app.clone(), generation, rx, exited));
  tauri::async_runtime::spawn(watch_start_timeout(app.clone(), generation));
}

/// Reads everything the sidecar says, for as long as it lives. It must never
/// stop reading: the channel holds one message, and a sidecar whose output is
/// not taken blocks on its next `print`.
async fn watch_events(
  app: AppHandle,
  generation: u64,
  mut rx: tauri::async_runtime::Receiver<CommandEvent>,
  exited: Arc<AtomicBool>,
) {
  let home = app.path().home_dir().ok().map(|p| p.to_string_lossy().into_owned());
  let mut stdout = Forwarder::new(log::Level::Info, home.clone());
  let mut stderr = Forwarder::new(log::Level::Warn, home);
  let mut ready = false;
  let mut terminated = false;
  while let Some(event) = rx.recv().await {
    let supervisor = app.state::<Supervisor>();
    match event {
      CommandEvent::Stdout(bytes) => match parse_ready(&String::from_utf8_lossy(&bytes)) {
        Some(port) if !ready => {
          ready = true;
          log::info!(target: "sidecar", "sidecar ready on port {port}");
          supervisor.mark_ready(&emitter(&app), generation, port);
        }
        _ => stdout.forward(&bytes),
      },
      CommandEvent::Stderr(bytes) => stderr.forward(&bytes),
      CommandEvent::Error(message) => log::error!(target: "sidecar", "{message}"),
      CommandEvent::Terminated(payload) => {
        exited.store(true, Ordering::SeqCst);
        log::warn!(target: "sidecar", "sidecar exited (code {:?}, signal {:?})", payload.code, payload.signal);
        terminated = true;
        on_exit(&app, generation, ready, describe_exit(payload.code, payload.signal, ready));
        break;
      }
      _ => {}
    }
  }
  if !terminated {
    // The channel closed without a word about the exit (waiting for the process failed): the
    // server is gone or cannot be watched any more. End it if it is still there, and treat it
    // as an exit, so the state never says "ready" about a server nobody watches.
    log::error!(target: "sidecar", "lost track of the sidecar");
    exited.store(true, Ordering::SeqCst);
    let supervisor = app.state::<Supervisor>();
    let running = {
      let mut inner = supervisor.lock();
      if inner.generation == generation { inner.running.take() } else { None }
    };
    if let Some(running) = running {
      let _ = running.child.kill();
    }
    on_exit(&app, generation, ready, describe_exit(None, None, ready));
  }
}

/// The sidecar exited: restarts it or gives up, unless that exit was expected.
fn on_exit(app: &AppHandle, generation: u64, was_ready: bool, reason: String) {
  let supervisor = app.state::<Supervisor>();
  let decision = {
    let mut inner = supervisor.lock();
    // The application is closing, or a newer start has replaced this one, or this
    // one was already given up on (the start timeout).
    let given_up = {
      let state = supervisor.state.borrow();
      state.generation == generation && state.state == Phase::Failed
    };
    if inner.stopping || inner.generation != generation || given_up {
      return;
    }
    inner.running = None;
    inner.policy.on_exit(Instant::now(), was_ready)
  };
  match decision {
    Decision::Restart(delay) => {
      log::warn!("restarting the server in {} s", delay.as_secs());
      let next = supervisor.next_generation(&emitter(app));
      let app = app.clone();
      tauri::async_runtime::spawn(async move {
        tokio::time::sleep(delay).await;
        let supervisor = app.state::<Supervisor>();
        let current = {
          let inner = supervisor.lock();
          inner.generation == next && !inner.stopping
        };
        if current {
          spawn_generation(&app, next);
        }
      });
    }
    Decision::GiveUp => {
      log::error!("giving up on the server: {reason}");
      supervisor.publish(&emitter(app), ServerInfo::failed(generation, reason));
    }
  }
}

/// Gives up on a server that never says it is ready.
async fn watch_start_timeout(app: AppHandle, generation: u64) {
  tokio::time::sleep(START_TIMEOUT).await;
  let supervisor = app.state::<Supervisor>();
  let message = "The server did not answer in 60 seconds.";
  if let Some(running) = supervisor.give_up_start(&emitter(&app), generation, message) {
    log::error!("the server did not become ready in {} s", START_TIMEOUT.as_secs());
    if let Some(running) = running {
      let _ = running.child.kill();
    }
  }
}

/// Whether the process exists, `None` when that could not be found out (the `kill` command did
/// not run): the caller must not take "unknown" for "gone".
#[cfg(unix)]
fn is_alive(pid: u32) -> Option<bool> {
  std::process::Command::new("kill")
    .args(["-0", &pid.to_string()])
    .output()
    .ok()
    .map(|o| o.status.success())
}

/// Stops a running sidecar: asks it to stop through its input, waits a few
/// seconds, then kills it. On Windows the kill also ends the worker processes
/// of the server's process pool.
fn stop_running(mut running: Running) {
  let pid = running.child.pid();
  if running.child.write(b"shutdown\n").is_err() {
    log::warn!("could not ask the server to stop; ending it");
  }
  let deadline = Instant::now() + STOP_GRACE;
  while Instant::now() < deadline {
    if running.exited.load(Ordering::SeqCst) {
      return;
    }
    #[cfg(unix)]
    if is_alive(pid) == Some(false) {
      return;
    }
    std::thread::sleep(Duration::from_millis(50));
  }
  log::warn!("the server did not stop in {} s; ending it", STOP_GRACE.as_secs());
  #[cfg(windows)]
  {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let _ = std::process::Command::new("taskkill")
      .args(["/PID", &pid.to_string(), "/T", "/F"])
      .creation_flags(CREATE_NO_WINDOW)
      .status();
  }
  let _ = running.child.kill();
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

  fn after(t0: Instant, secs: u64) -> Instant {
    t0 + Duration::from_secs(secs)
  }

  #[test]
  fn a_server_that_exits_before_ready_gets_one_more_try() {
    let (mut policy, t0) = (RestartPolicy::default(), Instant::now());
    assert_eq!(policy.on_exit(t0, false), Decision::Restart(EARLY_RETRY_DELAY));
    assert_eq!(policy.on_exit(after(t0, 2), false), Decision::GiveUp);
  }

  #[test]
  fn ready_clears_the_early_try() {
    let (mut policy, t0) = (RestartPolicy::default(), Instant::now());
    assert_eq!(policy.on_exit(t0, false), Decision::Restart(EARLY_RETRY_DELAY));
    policy.on_ready();
    assert_eq!(policy.on_exit(after(t0, 10), false), Decision::Restart(EARLY_RETRY_DELAY));
  }

  #[test]
  fn a_ready_server_is_restarted_twice_in_five_minutes_after_1_and_5_seconds() {
    let (mut policy, t0) = (RestartPolicy::default(), Instant::now());
    assert_eq!(policy.on_exit(t0, true), Decision::Restart(Duration::from_secs(1)));
    assert_eq!(policy.on_exit(after(t0, 20), true), Decision::Restart(Duration::from_secs(5)));
    assert_eq!(policy.on_exit(after(t0, 40), true), Decision::GiveUp);
    assert_eq!(policy.on_exit(after(t0, 299), true), Decision::GiveUp);
  }

  #[test]
  fn restarts_older_than_five_minutes_stop_counting() {
    let (mut policy, t0) = (RestartPolicy::default(), Instant::now());
    policy.on_exit(t0, true);
    policy.on_exit(after(t0, 20), true);
    assert_eq!(policy.on_exit(after(t0, 301), true), Decision::Restart(Duration::from_secs(5)));
    assert_eq!(policy.on_exit(after(t0, 310), true), Decision::GiveUp);
  }

  #[test]
  fn exits_are_told_in_a_few_words() {
    assert_eq!(describe_exit(Some(1), None, false), "The server stopped before it was ready (code 1).");
    assert_eq!(describe_exit(None, Some(9), true), "The server stopped (signal 9).");
    assert_eq!(describe_exit(None, None, true), "The server stopped.");
  }

  /// A supervisor and the list of what it sent to the webview.
  fn supervisor() -> (Supervisor, std::cell::RefCell<Vec<ServerInfo>>) {
    (Supervisor::new(), std::cell::RefCell::new(Vec::new()))
  }

  fn current(supervisor: &Supervisor) -> ServerInfo {
    supervisor.state.borrow().clone()
  }

  #[test]
  fn a_new_generation_is_published_as_starting() {
    let (sup, sent) = supervisor();
    let emit = |i: ServerInfo| sent.borrow_mut().push(i);
    assert_eq!(sup.next_generation(&emit), 1);
    assert_eq!(sup.next_generation(&emit), 2);
    assert_eq!(*sent.borrow(), vec![ServerInfo::starting(1), ServerInfo::starting(2)]);
    assert_eq!(current(&sup), ServerInfo::starting(2));
  }

  #[test]
  fn a_report_about_an_old_generation_is_dropped_and_not_sent() {
    let (sup, sent) = supervisor();
    let emit = |i: ServerInfo| sent.borrow_mut().push(i);
    sup.next_generation(&emit);
    sup.next_generation(&emit);
    assert!(!sup.publish(&emit, ServerInfo::failed(1, "late".into())));
    assert!(!sup.mark_ready(&emit, 1, 4000));
    assert_eq!(current(&sup), ServerInfo::starting(2));
    assert_eq!(sent.borrow().len(), 2);
  }

  #[test]
  fn the_timeout_of_an_old_start_cannot_fail_the_new_one_and_the_new_one_still_fires() {
    let (sup, sent) = supervisor();
    let emit = |i: ServerInfo| sent.borrow_mut().push(i);
    sup.next_generation(&emit);
    sup.next_generation(&emit); // restarted before the first timer fired
    assert!(sup.give_up_start(&emit, 1, "slow").is_none());
    assert_eq!(current(&sup), ServerInfo::starting(2));
    assert!(sup.give_up_start(&emit, 2, "slow").is_some());
    assert_eq!(current(&sup), ServerInfo::failed(2, "slow".into()));
  }

  #[test]
  fn a_server_that_became_ready_in_time_is_not_failed_by_the_timeout() {
    let (sup, sent) = supervisor();
    let emit = |i: ServerInfo| sent.borrow_mut().push(i);
    sup.next_generation(&emit);
    assert!(sup.mark_ready(&emit, 1, 4000));
    assert!(sup.give_up_start(&emit, 1, "slow").is_none());
    assert_eq!(current(&sup), ServerInfo::ready(1, 4000));
    assert_eq!(sent.borrow().len(), 2);
  }

  #[test]
  fn ready_after_the_timeout_gave_up_is_ignored() {
    let (sup, sent) = supervisor();
    let emit = |i: ServerInfo| sent.borrow_mut().push(i);
    sup.next_generation(&emit);
    assert!(sup.give_up_start(&emit, 1, "slow").is_some());
    assert!(!sup.mark_ready(&emit, 1, 4000));
    assert_eq!(current(&sup), ServerInfo::failed(1, "slow".into()));
  }

  #[test]
  fn ready_clears_the_early_try_of_the_policy_only_for_the_current_generation() {
    let (sup, sent) = supervisor();
    let emit = |i: ServerInfo| sent.borrow_mut().push(i);
    sup.next_generation(&emit);
    sup.lock().policy.on_exit(Instant::now(), false); // the early try is used up
    sup.next_generation(&emit);
    assert!(!sup.mark_ready(&emit, 1, 4000)); // an old generation must not reset it
    assert!(sup.lock().policy.retried_start);
    assert!(sup.mark_ready(&emit, 2, 4001));
    assert!(!sup.lock().policy.retried_start);
  }
}
