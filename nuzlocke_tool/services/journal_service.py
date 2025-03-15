from nuzlocke_tool.models.models import GameState, Pokemon, PokemonStatus


class JournalService:
    def __init__(self, game_state: GameState) -> None:
        self._journal_file = game_state.journal_file

    def _append_entry(self, entry: str) -> None:
        with self._journal_file.open("a") as f:
            f.write(f"{entry}\n")

    def add_capture_entry(self, pokemon: Pokemon) -> None:
        status_map = {PokemonStatus.ACTIVE: "Party", PokemonStatus.BOXED: "Box"}
        entry = f"Caught {pokemon} in {pokemon.encountered}. Added to {status_map[pokemon.status]}."
        self._append_entry(entry)

    def add_clause_entry(self, clause: str) -> None:
        entry = f"New session is using the {clause} clause."
        self._append_entry(entry)

    def add_dead_entry(self, pokemon: Pokemon) -> None:
        entry = f"{pokemon} has Died."
        self._append_entry(entry)

    def add_decision_entry(self, decision: str, outcome: str) -> None:
        entry = f"Randomly pick {decision}: {outcome}"
        self._append_entry(entry)

    def add_delete_move_entry(self, nickname: str, move: str) -> None:
        entry = f"{nickname} deleted move: {move}"
        self._append_entry(entry)

    def add_evolved_entry(self, pokemon: Pokemon, old_species: str) -> None:
        entry = f"{pokemon.nickname} evolved from {old_species} to {pokemon.species}"
        self._append_entry(entry)

    def add_learn_move_entry(self, nickname: str, move: str, old_move: str | None = None) -> None:
        entry = f"{nickname} learned move: {move}"
        if old_move:
            entry += f" (replacing {old_move})"
        self._append_entry(entry)

    def add_new_session_entry(self, game: str, ruleset: str) -> None:
        entry = f"Started new session in {game}."
        self._append_entry(entry)
        entry = f"New session is utilising the {ruleset} ruleset."
        self._append_entry(entry)

    def add_transfer_entry(self, pokemon: Pokemon, target: str) -> None:
        entry = f"Transferred {pokemon} to {target}."
        self._append_entry(entry)
