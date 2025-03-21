use crate::models::{
    game::{get_available_games, get_game_version},
    rules::{get_available_rulesets, get_ruleset},
};
use crate::templates::{IndexTemplate, RulesetDetailsTemplate, RulesetSelectorTemplate};

use actix_web::{HttpResponse, Responder, error::ErrorInternalServerError, get, post, web::Form};
use rinja::Template;
use serde::Deserialize;

#[derive(Deserialize)]
struct GameRulesetForm {
    game: String,
    ruleset: Option<String>,
}

#[derive(Deserialize)]
struct ViewRulesetForm {
    game: String,
    ruleset: String,
}

#[get("/")]
async fn index() -> actix_web::Result<impl Responder> {
    let games = get_available_games();
    let template = IndexTemplate { games };
    let html = template.render().map_err(|e| {
        eprintln!("Template error: {}", e);
        ErrorInternalServerError("Template error")
    })?;
    Ok(HttpResponse::Ok().content_type("text/html").body(html))
}

#[post("/select-game-ruleset")]
async fn select_game_ruleset(form: Form<GameRulesetForm>) -> actix_web::Result<impl Responder> {
    let game = match get_game_version(&form.game) {
        Some(g) => g,
        None => return Ok(HttpResponse::BadRequest().body("Invalid game selection")),
    };
    let rulesets = get_available_rulesets(game.generation);
    let template = RulesetSelectorTemplate {
        game: form.game.clone(),
        rulesets,
    };
    let html = template.render().map_err(|e| {
        eprintln!("Template error: {}", e);
        ErrorInternalServerError("Template error")
    })?;
    Ok(HttpResponse::Ok().content_type("text/html").body(html))
}

#[post("/show-ruleset")]
async fn show_ruleset(form: Form<ViewRulesetForm>) -> actix_web::Result<impl Responder> {
    let ruleset = match get_ruleset(&form.ruleset) {
        Some(r) => r,
        None => return Ok(HttpResponse::BadRequest().body("Invalid ruleset selection")),
    };
    let template = RulesetDetailsTemplate {
        game: form.game.clone(),
        ruleset_name: form.ruleset.clone(),
        ruleset,
    };
    let html = template.render().map_err(|e| {
        eprintln!("Template error: {}", e);
        ErrorInternalServerError("Template error")
    })?;
    Ok(HttpResponse::Ok().content_type("text/html").body(html))
}
