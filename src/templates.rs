use rinja::Template;

use crate::models::rules::Ruleset;

#[derive(Template)]
#[template(path = "index.html")]
pub struct IndexTemplate {
    pub games: Vec<String>,
}

#[derive(Template)]
#[template(path = "ruleset_selector.html")]
pub struct RulesetSelectorTemplate {
    pub game: String,
    pub rulesets: Vec<String>,
}

#[derive(Template)]
#[template(path = "ruleset_details.html")]
pub struct RulesetDetailsTemplate {
    pub game: String,
    pub ruleset_name: String,
    pub ruleset: Ruleset,
}
