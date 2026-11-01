# クロスプラットフォーム・ビルド手順

## 共通

```bash
cargo test --workspace
cargo build --release -p md-viewer-pro
```

UI は `ui/` の静的ファイルを `tauri.conf.json` の `frontendDist` が埋め込むため、
Node/npm は不要です。

## macOS

```bash
./scripts/package_macos.sh
```

- `.app` を組み立て、ad-hoc 署名し、DMG を作成します。
- Apple Developer Program 加入後は `codesign` を Developer ID に、`xcrun notarytool` を追加してください。

## Windows

```powershell
cargo build --release -p md-viewer-pro
```

- WebView2 Runtime が必要です（Windows 11 は標準搭載、Windows 10 は Evergreen を配布）。
- 配布用インストーラーは Tauri CLI（`cargo install tauri-cli`）で
  `cargo tauri build --bundles nsis` を実行してください（`tauri.conf.json` の `bundle.active` を `true` に変更）。
- 署名は Authenticode 証明書（SmartScreen 警告の解除）が必要です。

## Linux

```bash
sudo apt install libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
cargo build --release -p md-viewer-pro
```

- WebKitGTK 4.1 が必要です（Ubuntu 22.04 / Debian 12 以降）。
- 配布は `.deb` / Flatpak を推奨。AppImage は WebKitGTK を同梱できず 70MB+ になります。
- PDF 書き出しは macOS 専用実装です（他 OS では印刷ダイアログを使用）。

## CI

`.github/workflows/build.yml` が macOS / Windows / Ubuntu で
コアテスト・リリースビルド・clippy を実行します。
