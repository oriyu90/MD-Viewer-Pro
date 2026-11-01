#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod menu;
mod state;

use std::path::PathBuf;

use tauri::{Emitter, Manager};

use state::AppState;

fn selftest_mode() -> bool {
    std::env::args().any(|a| a == "--selftest")
}

fn initial_path() -> Option<PathBuf> {
    std::env::args()
        .skip(1)
        .find(|a| !a.starts_with('-'))
        .map(PathBuf::from)
        .filter(|p| p.exists())
}

fn main() {
    commands::mark_start();
    let initial = initial_path();

    let app = tauri::Builder::default()
        .manage(AppState::new())
        .setup(move |app| {
            menu::install(app.handle())?;

            // macOS: 既に起動中のインスタンスがあればファイルを渡して終了する。
            #[cfg(target_os = "macos")]
            {
                if state::forward_to_running_instance(&initial) {
                    std::process::exit(0);
                }
                state::start_instance_listener(app.handle().clone());
            }

            if let Some(shot) = commands::screenshot_args() {
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_millis(2600));
                    let _ = commands::take_screenshot(handle.clone(), shot.output.clone());
                    std::thread::sleep(std::time::Duration::from_millis(400));
                    handle.exit(0);
                });
            }

            if std::env::args().any(|a| a == "--open-windows") {
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_millis(1500));
                    let _ = commands::new_window(handle);
                });
            }

            if selftest_mode() {
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_millis(1200));
                    let _ = handle.emit("selftest", ());
                });
                let handle2 = app.handle().clone();
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_secs(30));
                    let p = crate::state::app_dir().join("selftest.json");
                    if !p.exists() {
                        let _ = std::fs::write(&p, r#"{"ok":false,"error":"timeout"}"#);
                    }
                    handle2.exit(2);
                });
            }

            if let Some(path) = initial.clone() {
                let handle = app.handle().clone();
                // フロントエンドの準備を待ってから開く。
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_millis(350));
                    let _ = handle.emit("open-path", path.to_string_lossy().to_string());
                });
            }
            Ok(())
        })
        .on_menu_event(|app, event| {
            let _ = app.emit("menu", event.id().0.clone());
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let _ = commands::persist_window_state(window.app_handle());
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::bootstrap,
            commands::open_path,
            commands::pick_file,
            commands::pick_save,
            commands::read_file_text,
            commands::render,
            commands::save_document,
            commands::save_text,
            commands::save_settings,
            commands::copy_text,
            commands::open_external,
            commands::reveal_path,
            commands::clips_get,
            commands::clip_add,
            commands::clip_remove,
            commands::fonts_list,
            commands::font_add,
            commands::font_remove,
            commands::themes_list,
            commands::open_themes_dir,
            commands::print_page,
            commands::export_pdf,
            commands::new_window,
            commands::system_theme_dark,
            commands::app_paths,
            commands::selftest_report,
            commands::ui_ready,
            commands::palette_for_theme,
            commands::take_screenshot,
        ])
        .build(tauri::generate_context!())
        .expect("error while building MD Viewer Pro");

    app.run(|app_handle, event| {
        #[cfg(target_os = "macos")]
        if let tauri::RunEvent::Opened { urls } = event {
            for url in urls {
                if let Ok(path) = url.to_file_path() {
                    let _ = app_handle.emit("open-path", path.to_string_lossy().to_string());
                }
            }
        }
        #[cfg(not(target_os = "macos"))]
        let _ = (app_handle, event);
    });
}
