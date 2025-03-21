use std::{
    collections::HashMap,
    fs,
    sync::{Arc, LazyLock},
};

use serde::Deserialize;

static GAME_VERSIONS: LazyLock<Arc<HashMap<String, GameVersion>>> =
    LazyLock::new(|| Arc::new(load_game_versions()));

#[derive(Clone, Deserialize)]
pub struct GameVersion {
    pub generation: u8,
}

pub fn get_available_games() -> Vec<String> {
    let mut games: Vec<String> = GAME_VERSIONS.keys().cloned().collect();
    games.sort();
    games
}

pub fn get_game_version(name: &str) -> Option<GameVersion> {
    GAME_VERSIONS.get(name).cloned()
}

fn load_game_versions() -> HashMap<String, GameVersion> {
    let content =
        fs::read_to_string("resources/versions.yaml").expect("Failed to read versions.yaml file");
    serde_yaml_ng::from_str(&content).expect("Failed to parse versions.yaml file")
}
