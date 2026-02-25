// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
// [cfg_attr... ] 는 무슨 의미지?

fn main() {
    chzzkchattauri_lib::run()
}
