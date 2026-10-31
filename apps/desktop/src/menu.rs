//! macOS ネイティブメニュー。

use tauri::menu::{MenuBuilder, MenuItemBuilder, SubmenuBuilder};
use tauri::{AppHandle, Runtime};

pub fn install<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    let app_menu = SubmenuBuilder::new(app, "MD Viewer Pro")
        .about(None)
        .separator()
        .services()
        .separator()
        .hide()
        .hide_others()
        .show_all()
        .separator()
        .quit()
        .build()?;

    let file = SubmenuBuilder::new(app, "ファイル")
        .item(
            &MenuItemBuilder::with_id("new", "新規作成")
                .accelerator("CmdOrCtrl+N")
                .build(app)?,
        )
        .item(
            &MenuItemBuilder::with_id("new-window", "新規ウィンドウ")
                .accelerator("CmdOrCtrl+Shift+N")
                .build(app)?,
        )
        .item(
            &MenuItemBuilder::with_id("open", "開く…")
                .accelerator("CmdOrCtrl+O")
                .build(app)?,
        )
        .separator()
        .item(
            &MenuItemBuilder::with_id("save", "保存")
                .accelerator("CmdOrCtrl+S")
                .build(app)?,
        )
        .item(
            &MenuItemBuilder::with_id("save-as", "名前を付けて保存…")
                .accelerator("CmdOrCtrl+Shift+S")
                .build(app)?,
        )
        .separator()
        .item(&MenuItemBuilder::with_id("export-pdf", "PDFとして書き出し…").build(app)?)
        .item(&MenuItemBuilder::with_id("export-html", "HTMLとして書き出し…").build(app)?)
        .separator()
        .item(&MenuItemBuilder::with_id("reveal", "Finderに表示").build(app)?)
        .separator()
        .item(
            &MenuItemBuilder::with_id("close", "ウインドウを閉じる")
                .accelerator("CmdOrCtrl+W")
                .build(app)?,
        )
        .build()?;

    let edit = SubmenuBuilder::new(app, "編集")
        .undo()
        .redo()
        .separator()
        .cut()
        .copy()
        .paste()
        .select_all()
        .separator()
        .item(&MenuItemBuilder::with_id("find", "検索…").accelerator("CmdOrCtrl+F").build(app)?)
        .build()?;

    let view = SubmenuBuilder::new(app, "表示")
        .item(
            &MenuItemBuilder::with_id("toggle-toc", "目次パネル")
                .accelerator("CmdOrCtrl+Shift+T")
                .build(app)?,
        )
        .item(
            &MenuItemBuilder::with_id("toggle-clip", "クリップパネル")
                .accelerator("CmdOrCtrl+Shift+C")
                .build(app)?,
        )
        .separator()
        .item(&MenuItemBuilder::with_id("zoom-in", "拡大").accelerator("CmdOrCtrl+Plus").build(app)?)
        .item(&MenuItemBuilder::with_id("zoom-out", "縮小").accelerator("CmdOrCtrl+-").build(app)?)
        .item(&MenuItemBuilder::with_id("zoom-reset", "実際のサイズ").accelerator("CmdOrCtrl+0").build(app)?)
        .separator()
        .item(&MenuItemBuilder::with_id("page-free", "フリー表示").build(app)?)
        .item(&MenuItemBuilder::with_id("page-a4", "A4文書").build(app)?)
        .build()?;

    let window = SubmenuBuilder::new(app, "ウインドウ")
        .minimize()
        .separator()
        .item(&MenuItemBuilder::with_id("settings", "詳細設定…").accelerator("CmdOrCtrl+,").build(app)?)
        .build()?;

    let menu = MenuBuilder::new(app)
        .items(&[&app_menu, &file, &edit, &view, &window])
        .build()?;
    app.set_menu(menu)?;
    Ok(())
}
