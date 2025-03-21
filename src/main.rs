mod models;
mod routes;
mod templates;

use std::io::Result;

use actix_files::Files;
use actix_web::{App, HttpServer};

use crate::models::{game::get_available_games, rules::RULESETS};

#[actix_web::main]
async fn main() -> Result<()> {
    println!("Loading game data...");
    let game_count = get_available_games().len();
    let ruleset_count = RULESETS.len();
    println!(
        "Data loaded: {} games and {} rulesets",
        game_count, ruleset_count
    );
    println!("Starting Nuzlocke Tracker server on http://127.0.0.1:8080");
    HttpServer::new(|| {
        App::new()
            .service(Files::new("/static", "./static"))
            .service(routes::index)
            .service(routes::select_game_ruleset)
            .service(routes::show_ruleset)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
