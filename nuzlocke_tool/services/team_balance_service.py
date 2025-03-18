from nuzlocke_tool.constants import TYPE_CHART
from nuzlocke_tool.container import Container
from nuzlocke_tool.models.models import GameState, Pokemon, PokemonStatus, PokemonTypeCoverage
from nuzlocke_tool.models.view_models import TeamBalanceViewModel


class TeamBalanceService:
    def __init__(self, container: Container, game_state: GameState) -> None:
        self._container = container
        self._event_manager = self._container.event_manager()
        self._game_state = game_state
        self._move_repository = self._container.move_repository()
        self._pokemon_repository = self._container.pokemon_repository()

    @property
    def active_pokemon(self) -> list[Pokemon]:
        return [p for p in self._game_state.pokemon if p.status == PokemonStatus.ACTIVE]

    @property
    def all_type_combinations(self) -> list[tuple[str, ...]]:
        combinations = set()
        species_list = self._pokemon_repository.get_all_species()
        for species in species_list:
            pokemon_data = self._pokemon_repository.get_by_id(species)
            sorted_types = tuple(sorted(pokemon_data["type"]))
            combinations.add(sorted_types)
        return sorted(combinations)

    def _calculate_pokemon_defensive_coverage(self, pokemon: Pokemon) -> dict[str, float]:
        coverage = {}
        pokemon_types = self._get_pokemon_types(pokemon)
        for attack_type in TYPE_CHART:
            multiplier = self._calculate_type_effectiveness(attack_type, pokemon_types)
            coverage[attack_type] = multiplier
        return coverage

    def _calculate_pokemon_offensive_coverage(
        self,
        pokemon: Pokemon,
        type_combinations: list[tuple[str, ...]],
    ) -> dict[str, dict[str, float]]:
        coverage = {}
        pokemon_types = self._get_pokemon_types(pokemon)
        for type_combo in type_combinations:
            combo_key = ",".join(type_combo)
            coverage[combo_key] = {}
        for move_name in pokemon.moves:
            if not move_name:
                continue
            move_type = self._get_move_type(move_name)
            move_data = self._move_repository.get_by_id(move_name)
            move_power = int(move_data["power"])
            if move_power == 0:
                continue
            stab = 1.5 if move_type in pokemon_types else 1.0
            for type_combo in type_combinations:
                combo_key = ",".join(type_combo)
                effectiveness = self._calculate_type_effectiveness(move_type, list(type_combo))
                move_effectiveness = effectiveness * stab
                coverage[combo_key][move_name] = move_effectiveness
        return coverage

    def _calculate_team_offensive_scores(
        self,
        pokemon_best_moves: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        team_scores = {}
        for type_combo, pokemon_scores in pokemon_best_moves.items():
            team_score = 1.0
            for effectiveness in pokemon_scores.values():
                team_score *= effectiveness
            team_scores[type_combo] = team_score
        return team_scores

    def _calculate_type_effectiveness(self, attack_type: str, defense_types: list[str]) -> float:
        type_chart = TYPE_CHART[attack_type]
        multi = 1.0
        for defense_type in defense_types:
            type_multi = type_chart.get(defense_type, 1.0)
            if type_multi == 0:
                type_multi = 0.125
            multi *= type_multi
        return multi

    def _get_best_move_per_pokemon(
        self,
        active_pokemon: list[Pokemon],
        type_combinations: list[tuple[str, ...]],
    ) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, tuple[str, float]]]]:
        pokemon_best_moves = {}
        pokemon_best_move_details = {}
        for type_combo in type_combinations:
            combo_key = ",".join(type_combo)
            pokemon_best_moves[combo_key] = {}
            pokemon_best_move_details[combo_key] = {}
        for pokemon in active_pokemon:
            offensive_coverage = self._calculate_pokemon_offensive_coverage(pokemon, type_combinations)
            for type_combo in type_combinations:
                combo_key = ",".join(type_combo)
                move_dict = offensive_coverage[combo_key]
                best_move = ""
                best_effectiveness = 0.0
                for move_name, effectiveness in move_dict.items():
                    if effectiveness > best_effectiveness:
                        best_effectiveness = effectiveness
                        best_move = move_name
                if not best_move or best_effectiveness == 0:
                    best_effectiveness = 1.0
                pokemon_best_moves[combo_key][pokemon.nickname] = best_effectiveness
                if best_move:
                    pokemon_best_move_details[combo_key][pokemon.nickname] = (best_move, best_effectiveness)
        return pokemon_best_moves, pokemon_best_move_details

    def _get_move_type(self, move_name: str) -> str:
        move_data = self._move_repository.get_by_id(move_name)
        return move_data["type"]

    def _get_pokemon_types(self, pokemon: Pokemon) -> list[str]:
        pokemon_data = self._pokemon_repository.get_by_id(pokemon.species)
        return pokemon_data["type"]

    def calculate_team_balance(self) -> TeamBalanceViewModel:
        active_pokemon = self.active_pokemon
        if not active_pokemon:
            return TeamBalanceViewModel.create_empty()
        view_model = TeamBalanceViewModel()
        for attack_type in TYPE_CHART:
            team_multi = 1.0
            for pokemon in active_pokemon:
                pokemon_coverage = self._calculate_pokemon_defensive_coverage(pokemon)
                team_multi *= pokemon_coverage[attack_type]
            view_model.defensive_coverage[attack_type] = team_multi
        type_combinations = self.all_type_combinations
        all_moves_coverage = {}
        for type_combo in type_combinations:
            combo_key = ",".join(type_combo)
            all_moves_coverage[combo_key] = {}
        for pokemon in active_pokemon:
            pokemon_coverage = PokemonTypeCoverage(pokemon)
            pokemon_coverage.defensive_coverage = self._calculate_pokemon_defensive_coverage(pokemon)
            pokemon_offensive = self._calculate_pokemon_offensive_coverage(pokemon, type_combinations)
            for combo_key, move_dict in pokemon_offensive.items():
                for move_name, effectiveness in move_dict.items():
                    move_key = f"{pokemon.nickname}|{move_name}"
                    all_moves_coverage[combo_key][move_key] = effectiveness
            view_model.pokemon_coverage.append(pokemon_coverage)
        pokemon_best_moves, pokemon_best_move_details = self._get_best_move_per_pokemon(
            active_pokemon,
            type_combinations,
        )
        team_offensive_scores = self._calculate_team_offensive_scores(pokemon_best_moves)
        view_model.offensive_coverage = all_moves_coverage
        view_model.offensive_best_scores = team_offensive_scores
        view_model.pokemon_best_moves = pokemon_best_moves
        view_model.pokemon_best_move_details = pokemon_best_move_details
        return view_model
