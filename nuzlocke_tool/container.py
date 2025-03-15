from dependency_injector import containers, providers

from nuzlocke_tool.data_loader import GameDataLoader
from nuzlocke_tool.models.view_models import ViewModelFactory
from nuzlocke_tool.repositories import LocationRepository, MoveRepository, PokemonRepository
from nuzlocke_tool.services.journal_service import JournalService
from nuzlocke_tool.services.save_service import SaveService


class Container(containers.DeclarativeContainer):
    game_data_loader = providers.Singleton(GameDataLoader)
    journal_service_factory = providers.Factory(JournalService)
    save_service = providers.Singleton(SaveService)
    location_repository = providers.Singleton(LocationRepository, game_data_loader=game_data_loader)
    move_repository = providers.Singleton(MoveRepository, game_data_loader=game_data_loader)
    pokemon_repository = providers.Singleton(PokemonRepository, game_data_loader=game_data_loader)
    view_model_factory = providers.Singleton(
        ViewModelFactory,
        container=providers.Self(),
        pokemon_repository=pokemon_repository,
    )
