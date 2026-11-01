fn main() {
    // UI は frontendDist としてバイナリへ埋め込まれるため、
    // 変更時に確実に再ビルドされるよう監視する。
    println!("cargo:rerun-if-changed=../../ui");
    tauri_build::build()
}
