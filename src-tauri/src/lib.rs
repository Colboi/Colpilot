use std::ffi::c_void;
use std::mem::size_of;
use std::io::{BufRead, BufReader};
use std::os::windows::process::CommandExt;
use std::os::windows::io::AsRawHandle;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{atomic::{AtomicBool, Ordering}, Mutex};
use std::time::{Duration, Instant};

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager, State, WindowEvent};

const BACKEND_PORT: u16 = 37651;
const CREATE_NO_WINDOW: u32 = 0x08000000;
const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION: u32 = 9;
const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x2000;

type WinHandle = *mut c_void;

#[repr(C)]
#[derive(Default)]
struct JobObjectBasicLimitInformation {
    per_process_user_time_limit: i64,
    per_job_user_time_limit: i64,
    limit_flags: u32,
    minimum_working_set_size: usize,
    maximum_working_set_size: usize,
    active_process_limit: u32,
    affinity: usize,
    priority_class: u32,
    scheduling_class: u32,
}

#[repr(C)]
#[derive(Default)]
struct IoCounters {
    read_operation_count: u64,
    write_operation_count: u64,
    other_operation_count: u64,
    read_transfer_count: u64,
    write_transfer_count: u64,
    other_transfer_count: u64,
}

#[repr(C)]
#[derive(Default)]
struct JobObjectExtendedLimitInformation {
    basic_limit_information: JobObjectBasicLimitInformation,
    io_info: IoCounters,
    process_memory_limit: usize,
    job_memory_limit: usize,
    peak_job_memory_used: usize,
    peak_process_memory_used: usize,
}

#[link(name = "kernel32")]
unsafe extern "system" {
    fn CreateJobObjectW(attributes: *mut c_void, name: *const u16) -> WinHandle;
    fn SetInformationJobObject(
        job: WinHandle,
        information_class: u32,
        information: *mut c_void,
        information_length: u32,
    ) -> i32;
    fn AssignProcessToJobObject(job: WinHandle, process: WinHandle) -> i32;
    fn CloseHandle(handle: WinHandle) -> i32;
}

struct JobObject {
    handle: WinHandle,
}

unsafe impl Send for JobObject {}
unsafe impl Sync for JobObject {}

impl JobObject {
    fn attach(child: &Child) -> Result<Self, Box<dyn std::error::Error>> {
        let handle = unsafe { CreateJobObjectW(std::ptr::null_mut(), std::ptr::null()) };
        if handle.is_null() {
            return Err(std::io::Error::last_os_error().into());
        }
        let job = Self { handle };
        let mut information = JobObjectExtendedLimitInformation::default();
        information.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let configured = unsafe {
            SetInformationJobObject(
                job.handle,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                (&mut information as *mut JobObjectExtendedLimitInformation).cast(),
                size_of::<JobObjectExtendedLimitInformation>() as u32,
            )
        };
        if configured == 0 {
            return Err(std::io::Error::last_os_error().into());
        }
        let assigned = unsafe {
            AssignProcessToJobObject(job.handle, child.as_raw_handle() as WinHandle)
        };
        if assigned == 0 {
            return Err(std::io::Error::last_os_error().into());
        }
        Ok(job)
    }
}

impl Drop for JobObject {
    fn drop(&mut self) {
        if !self.handle.is_null() {
            unsafe {
                CloseHandle(self.handle);
            }
        }
    }
}

struct BackendProcess {
    child: Child,
    _job: JobObject,
}

struct BackendState {
    child: Mutex<Option<BackendProcess>>,
    port: u16,
    shutdown_requested: AtomicBool,
}

fn tray_icon() -> tauri::image::Image<'static> {
    tauri::image::Image::from_bytes(include_bytes!("../icons/colpilot-icon.png"))
        .expect("ColPilot icon PNG could not be decoded")
}

fn show_main_window(app: &AppHandle) {
    let Some(window) = app.get_webview_window("main") else {
        log::error!("Main window was not found");
        return;
    };

    if let Err(error) = window.show() {
        log::error!("Main window show failed: {error}");
    }
    if let Err(error) = window.unminimize() {
        log::error!("Main window restore failed: {error}");
    }
    if let Err(error) = window.set_focus() {
        log::error!("Main window focus failed: {error}");
    }
}

fn start_backend(app: &AppHandle) -> Result<BackendProcess, Box<dyn std::error::Error>> {
    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or("Project root is unavailable")?
        .to_path_buf();
    let executable_root = std::env::current_exe()?
        .parent()
        .map(Path::to_path_buf)
        .ok_or("Executable directory is unavailable")?;

    let source_backend_script = project_root.join("backend").join("main.py");
    let portable_backend_script = executable_root.join("backend").join("main.py");
    let config_path = if cfg!(debug_assertions) {
        project_root.join("config.ini")
    } else {
        executable_root.join("config.ini")
    };
    let backend_script = if cfg!(debug_assertions) {
        source_backend_script.clone()
    } else if portable_backend_script.exists() {
        portable_backend_script.clone()
    } else {
        let bundled_backend_script = app.path().resource_dir()?.join("backend").join("main.py");
        if bundled_backend_script.exists() {
            bundled_backend_script
        } else {
            source_backend_script
        }
    };

    if !backend_script.exists() {
        return Err(format!("Backend script does not exist: {}", backend_script.display()).into());
    }

    let portable_runtime_root = executable_root.join("runtime");
    let portable_python = portable_runtime_root.join("python.exe");
    let virtual_environment_python = project_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");
    let uses_portable_runtime = !cfg!(debug_assertions) && portable_python.exists();
    let python_program = if uses_portable_runtime {
        portable_python
    } else if virtual_environment_python.exists() {
        virtual_environment_python
    } else {
        PathBuf::from("python")
    };

    let working_root = if portable_backend_script.exists() {
        executable_root
    } else {
        project_root
    };

    let mut command = Command::new(python_program);
    command
        .arg(backend_script)
        .arg("--port")
        .arg(BACKEND_PORT.to_string())
        .arg("--config-path")
        .arg(config_path)
        .current_dir(working_root)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .creation_flags(CREATE_NO_WINDOW);

    if uses_portable_runtime {
        let runtime_library_bin = portable_runtime_root.join("Library").join("bin");
        let mut path_entries = vec![portable_runtime_root, runtime_library_bin];
        if let Some(current_path) = std::env::var_os("PATH") {
            path_entries.extend(std::env::split_paths(&current_path));
        }
        command.env("PATH", std::env::join_paths(path_entries)?);
    }

    let mut child = command.spawn()?;
    log::info!("Backend started pid={}", child.id());
    let stdout = child.stdout.take().ok_or("Backend stdout is unavailable")?;
    let stderr = child.stderr.take().ok_or("Backend stderr is unavailable")?;
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            match line {
                Ok(line) => log::info!(target: "backend.stdout", "{line}"),
                Err(error) => { log::error!("Backend stdout read failed: {error}"); break; }
            }
        }
    });
    std::thread::spawn(move || {
        for line in BufReader::new(stderr).lines() {
            match line {
                Ok(line) => log::warn!(target: "backend.stderr", "{line}"),
                Err(error) => { log::error!("Backend stderr read failed: {error}"); break; }
            }
        }
    });
    let job = match JobObject::attach(&child) {
        Ok(job) => job,
        Err(error) => {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error);
        }
    };
    Ok(BackendProcess { child, _job: job })
}

fn request_backend_exit(port: u16) {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_millis(600))
        .build()
        .expect("Failed to create backend HTTP client");

    let result = client
        .post(format!("http://127.0.0.1:{port}/api/commands"))
        .json(&serde_json::json!({ "command": "exit" }))
        .send();

    if let Err(error) = result {
        log::error!("Backend exit command failed: {error}");
    }
}

fn stop_backend(state: &BackendState) {
    let process = {
        let mut process_slot = state.child.lock().expect("Backend state lock is poisoned");
        process_slot.take()
    };
    if let Some(mut process) = process {
        let deadline = Instant::now() + Duration::from_secs(4);
        loop {
            match process.child.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) if Instant::now() < deadline => {
                    std::thread::sleep(Duration::from_millis(50));
                }
                Ok(None) => {
                    log::error!("Backend graceful shutdown timed out");
                    if let Err(error) = process.child.kill() {
                        eprintln!("Backend process termination failed: {error}");
                    }
                    let _ = process.child.wait();
                    break;
                }
                Err(error) => {
                    eprintln!("Backend process status check failed: {error}");
                    if let Err(kill_error) = process.child.kill() {
                        eprintln!("Backend process termination failed: {kill_error}");
                    }
                    let _ = process.child.wait();
                    break;
                }
            }
        }
    }
}

fn monitor_backend(app: AppHandle) {
    std::thread::spawn(move || loop {
        let backend_exited = {
            let state = app.state::<BackendState>();
            let mut child_slot = state.child.lock().expect("Backend state lock is poisoned");

            match child_slot.as_mut() {
                Some(process) => match process.child.try_wait() {
                    Ok(Some(status)) => {
                        log::info!("Backend process exited with status: {status}");
                        child_slot.take();
                        true
                    }
                    Ok(None) => false,
                    Err(error) => {
                        log::error!("Backend process status check failed: {error}");
                        child_slot.take();
                        true
                    }
                },
                None => true,
            }
        };

        if backend_exited {
            app.exit(0);
            break;
        }

        std::thread::sleep(Duration::from_millis(100));
    });
}

fn shutdown_app(app: &AppHandle) {
    log::info!("Application shutdown requested");
    let state = app.state::<BackendState>();
    if state.shutdown_requested.swap(true, Ordering::AcqRel) {
        return;
    }
    request_backend_exit(state.port);
    stop_backend(&state);
    app.exit(0);
}

#[tauri::command]
fn get_backend_url(state: State<'_, BackendState>) -> String {
    format!("http://127.0.0.1:{}", state.port)
}

#[tauri::command]
fn exit_app(app: AppHandle) {
    shutdown_app(&app);
}

pub fn run() {
    let root = if cfg!(debug_assertions) {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().expect("Project root is unavailable").to_path_buf()
    } else {
        std::env::current_exe().expect("Executable path is unavailable").parent().expect("Executable directory is unavailable").to_path_buf()
    };
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::new()
            .clear_targets()
            .target(tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Folder {
                path: root.join("data").join("logs"),
                file_name: Some("desktop".to_string()),
            }))
            .level(log::LevelFilter::Info)
            .max_file_size(5 * 1024 * 1024)
            .rotation_strategy(tauri_plugin_log::RotationStrategy::KeepSome(10))
            .timezone_strategy(tauri_plugin_log::TimezoneStrategy::UseLocal)
            .build())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            std::panic::set_hook(Box::new(|information| {
                log::error!("Rust panic: {information}");
                log::logger().flush();
            }));
            log::info!("Colpilot starting pid={}", std::process::id());
            let backend = start_backend(app.handle())?;
            app.manage(BackendState {
                child: Mutex::new(Some(backend)),
                port: BACKEND_PORT,
                shutdown_requested: AtomicBool::new(false),
            });
            monitor_backend(app.handle().clone());

            let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&quit_item])?;

            TrayIconBuilder::new()
                .menu(&menu)
                .icon(tray_icon())
                .tooltip("Colpilot")
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| {
                    if event.id() == "quit" {
                        shutdown_app(app);
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if window.label() != "main" {
                return;
            }

            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                if let Err(error) = window.hide() {
                    log::error!("Main window hide failed: {error}");
                }
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_url, exit_app])
        .run(tauri::generate_context!())
        .expect("Error while running Colpilot");
}
