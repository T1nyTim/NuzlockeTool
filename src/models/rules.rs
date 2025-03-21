use std::{
    collections::HashMap,
    fs,
    sync::{Arc, LazyLock},
};

use serde::Deserialize;

pub static RULESETS: LazyLock<Arc<HashMap<String, Ruleset>>> =
    LazyLock::new(|| Arc::new(load_rulesets()));

#[derive(Clone, Deserialize)]
pub struct Ruleset {
    pub earliest_gen: u8,
    pub rules: Vec<String>,
}

pub fn get_available_rulesets(game_generation: u8) -> Vec<String> {
    let mut available_rulesets: Vec<String> = RULESETS
        .iter()
        .filter(|(_, ruleset)| ruleset.earliest_gen <= game_generation)
        .map(|(name, _)| name.clone())
        .collect();
    available_rulesets.sort();
    available_rulesets
}

pub fn get_ruleset(name: &str) -> Option<Ruleset> {
    RULESETS.get(name).cloned()
}

fn load_rulesets() -> HashMap<String, Ruleset> {
    let content =
        fs::read_to_string("resources/rules.yaml").expect("Failed to read rules.yaml file");
    serde_yaml_ng::from_str(&content).expect("Failed to parse rules.yaml file")
}
