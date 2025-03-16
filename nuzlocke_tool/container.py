from dependency_injector import containers, providers

from nuzlocke_tool.data_loader import GameDataLoader
from nuzlocke_tool.events import EventManager
from nuzlocke_tool.models.models import GameState
from nuzlocke_tool.repositories import LocationRepository, MoveRepository, PokemonRepository
from nuzlocke_tool.services.journal_service import JournalService
from nuzlocke_tool.services.save_service import SaveService


class Container(containers.DeclarativeContainer):
    event_manager = providers.Singleton(EventManager)
    game_data_loader = providers.Singleton(GameDataLoader)
    game_state = providers.Singleton(GameState, "", "", False, None, None, None, [], [], [], {})
    journal_service_factory = providers.Factory(JournalService)
    location_repository = providers.Singleton(LocationRepository, game_data_loader=game_data_loader)
    move_repository = providers.Singleton(MoveRepository, game_data_loader=game_data_loader)
    pokemon_repository = providers.Singleton(PokemonRepository, game_data_loader=game_data_loader)
    save_service = providers.Singleton(SaveService)
