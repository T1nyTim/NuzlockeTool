import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox
from rich.console import Console
from rich.theme import Theme

THEME = Theme(
    {
        "logging.level.debug": "dim white",
        "logging.level.info": "white",
        "logging.level.warning": "yellow",
        "logging.level.error": "red",
        "logging.level.critical": "bold bright_red",
    },
)
CONSOLE = Console(theme=THEME)
LOG_FILE_LIMIT = 20
LOGGER = logging.getLogger(__name__)

ACTIVE_PARTY_LIMIT = 6
ONE_BYTE = 255
POKEMON_DV_MIN = 0
POKEMON_DV_MAX = 15
POKEMON_LEVEL_MAX = 100
POKEMON_LEVEL_MIN = 1
POKEMON_MOVES_LIMIT = 4
POKEMON_STAT_STAGE_MAX = 6
POKEMON_STAT_STAGE_MIN = -6

DOUBLE_ATTACK_MOVES = {"Bonemerang", "Double Kick", "Twineedle"}
FLINCH_10_MOVES = {"Bite", "Bone Club", "Hyper Fang"}
FLINCH_30_MOVES = {"Headbutt", "Low Kick", "Rolling Kick", "Stomp"}
HIGH_CRIT_MOVES = {"Crabhammer", "Karate Chop", "Razor Leaf", "Slash"}
MULTI_HIT_MOVES = {
    "Barrage",
    "Bind",
    "Clamp",
    "Comet Punch",
    "Doubleslap",
    "Fire Spin",
    "Fury Attack",
    "Fury Swipes",
    "Pin Missile",
    "Spike Cannon",
    "Wrap",
}
OHKO_MOVES = {"Fissure", "Guillotine", "Horn Drill"}
SELFDESTRUCT_MOVES = {"Explosion", "Selfdestruct"}
SPECIAL_TYPES = {"Dragon", "Electric", "Fire", "Grass", "Ice", "Psychic", "Water"}
STAT_STAGE_MULTIPLIER = {
    -6: 0.25,
    -5: 0.28,
    -4: 0.33,
    -3: 0.4,
    -2: 0.5,
    -1: 0.66,
    0: 1,
    1: 1.5,
    2: 2,
    3: 2.5,
    4: 3,
    5: 3.5,
    6: 4,
}
STATIC_DAMAGE_MOVES = {"Dragon Rage", "Night Shade", "Psywave", "Seismic Toss", "Sonicboom"}
SWIFT_MOVES = {"Swift"}
TYPE_CHART = {
    "Normal": {"Rock": 0.5, "Ghost": 0},
    "Fighting": {
        "Normal": 2,
        "Flying": 0.5,
        "Poison": 0.5,
        "Rock": 2,
        "Bug": 0.5,
        "Ghost": 0,
        "Psychic": 0.5,
        "Ice": 2,
    },
    "Flying": {"Fighting": 2, "Rock": 0.5, "Bug": 2, "Grass": 2, "Electric": 0.5},
    "Poison": {"Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Bug": 2, "Ghost": 0.5, "Grass": 2},
    "Ground": {"Flying": 0, "Poison": 2, "Rock": 2, "Bug": 0.5, "Fire": 2, "Grass": 0.5, "Electric": 2},
    "Rock": {"Fighting": 0.5, "Flying": 2, "Ground": 0.5, "Bug": 2, "Fire": 2, "Ice": 2},
    "Bug": {
        "Fighting": 0.5,
        "Flying": 0.5,
        "Poison": 2,
        "Ghost": 0.5,
        "Fire": 0.5,
        "Grass": 2,
        "Psychic": 2,
    },
    "Ghost": {"Normal": 0, "Ghost": 2, "Psychic": 0},
    "Fire": {"Rock": 0.5, "Bug": 2, "Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 2, "Dragon": 0.5},
    "Water": {"Ground": 2, "Rock": 2, "Fire": 2, "Water": 0.5, "Grass": 0.5, "Dragon": 0.5},
    "Grass": {
        "Flying": 0.5,
        "Poison": 0.5,
        "Ground": 2,
        "Rock": 2,
        "Bug": 0.5,
        "Fire": 0.5,
        "Water": 2,
        "Grass": 0.5,
        "Dragon": 0.5,
    },
    "Electric": {"Flying": 2, "Ground": 0, "Water": 2, "Grass": 0.5, "Electric": 0.5, "Dragon": 0.5},
    "Psychic": {"Fighting": 2, "Poison": 2, "Psychic": 0.5},
    "Ice": {"Flying": 2, "Ground": 2, "Water": 0.5, "Grass": 2, "Ice": 0.5, "Dragon": 2},
    "Dragon": {"Dragon": 2},
}

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
ALIGN_H_CENTER = Qt.AlignmentFlag.AlignHCenter
ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
ALIGN_TOP = Qt.AlignmentFlag.AlignTop
BUTTON_CANCEL = QDialogButtonBox.StandardButton.Cancel
BUTTON_OK = QDialogButtonBox.StandardButton.Ok

SPACING = 5
IMAGE_SIZE_POKEMON = 56
LABEL_POKEMON_CARD_WIDTH = 60
LINE_HEIGHT = 25
NO_SPACING = 0
RESIZE_DELAY = 200
WIDGET_POKEMON_CARD_WIDTH = 137

OBJECT_NAME_CARD_WIDGET = "card-widget"
OBJECT_NAME_LABEL_OUTCOME = "outcome-label"

STYLE_SHEET_COMBO_BOX = "QComboBox { combobox-popup: 0; }"
STYLE_SHEET_LABEL_OUTCOME = "#outcome-label { border: 1px solid; border-radius: 4px; }"
STYLE_SHEET_WIDGET_CARD = "#card-widget { border: 1px solid; border-radius: 4px; }"

TABLE_COLOR_PARTY = "#388e3c"
TABLE_COLOR_BOXED = "#1976d2"
TABLE_COLOR_DEAD = "#424242"

DIALOG_ADD_POKEMON_TITLE = "Add New Pokemon"
DIALOG_NEW_SESSION_TITLE = "Start New Session"
MAIN_WINDOW_TITLE = "Nuzlocke Tracker"

MENU_ACTION_EDIT_NAME = "Edit"
MENU_ACTION_EXIT_NAME = "Exit"
MENU_ACTION_LOAD_NAME = "Load"
MENU_ACTION_NEW_NAME = "New"
MENU_FILE_NAME = "File"

TAB_BOXED_NAME = "Box"
TAB_DEAD_NAME = "Graveyard"
TAB_ENCOUNTER_NAME = "Encounters"
TAB_PARTY_NAME = "Party"
TAB_RULES_NAME = "Rules"
TAB_TOOLS_NAME = "Tools"

BUTTON_ADD_POKEMON = "Add Pokemon"
BUTTON_CALC_MOVE = "Calculate Best Moves"

LABEL_ATTACK = "Attack"
LABEL_ATTACK_SHORT = "Atk"
LABEL_CHECKBOX_LIGHT_SCREEN = "Light Screen"
LABEL_CHECKBOX_REFLECT = "Reflect"
LABEL_CHECKBOX_SUBREGIONS = "Enable Multiple Floors Clause"
LABEL_DECISION_CINNABAR_ENCOUNTER = "Amber, Fossil or Wild Encounter"
LABEL_DECISION_DOJO_GIFT = "Hitmon Family Member"
LABEL_DECISION_EEVEELUTION = "an Eeveelution"
LABEL_DECISION_FOSSIL = "a Fossil"
LABEL_DECISION_SAFFRON_GIFT = "Fighting Dojo or Silph Co. gift"
LABEL_DECISION_STARTER = "a Starter"
LABEL_DEFENDING_POKEMON = "Select Defending Pokemon:"
LABEL_DEFENSE_SHORT = "Def"
LABEL_DEFENSE_STAGE = "Defense Stage:"
LABEL_DETERMINANT_VALUES_SHORT = "DVs:"
LABEL_ENCOUNTER = "Encountered:"
LABEL_GAME_VERSION = "Game Version:"
LABEL_HEALTH_SHORT = "HP"
LABEL_LEVEL = "Level:"
LABEL_LOCATION = "Location"
LABEL_MOVES = "Moves:"
LABEL_NICKNAME = "Nickname:"
LABEL_NO_DEFENDING_POKEMON = "No data for defending Pokemon."
LABEL_NO_MOVES = "No valid moves found."
LABEL_PARTY_MEMBER = "Party Member"
LABEL_POKEMON = "Pokemon"
LABEL_RULESET = "Ruleset:"
LABEL_SPECIAL = "Special"
LABEL_SPECIAL_SHORT = "Spe"
LABEL_SPECIAL_STAGE = "Special Stage:"
LABEL_SPECIES = "Species:"
LABEL_SPEED = "Speed"
LABEL_SPEED_SHORT = "Spd"
LABEL_STATUS = "Status"
LABEL_TOOL_BEST_MOVE = "Best Move"
LABEL_TOOL_RANDOM_DECISION = "Randomize a Decision"

MSG_BOX_TITLE_INPUT_ERR = "Input Error"
MSG_BOX_TITLE_NO_FILE = "File Not Found"
MSG_BOX_TITLE_PARTY_FULL = "Active Party Full"

MSG_BOX_MSG_INVALID_ENCOUNTER = "Encounter needs to be a string"
MSG_BOX_MSG_INVALID_MOVE = "Move is not allowed for the selected Pokemon Species"
MSG_BOX_MSG_INVALID_NICKNAME = "Nickname needs to be a string"
MSG_BOX_MSG_INVALID_SPECIES = "Pokemon Species is not allowed for the selected Generation"
MSG_BOX_MSG_NO_ENCOUNTER = "An Encounter location is required."
MSG_BOX_MSG_NO_MOVE_FILE = "Could not find the Move data file at: "
MSG_BOX_MSG_NO_MOVE_FIRST_ONLY = "1 Move is required."
MSG_BOX_MSG_NO_NICKNAME = "A Nickname is required."
MSG_BOX_MSG_NO_SPECIES = "A Species is required."
MSG_BOX_MSG_NO_POKEMON_FILE = "Could not find the Pokemon data file at: "
MSG_BOX_MSG_NO_RULESET = "A Ruleset is required."
MSG_BOX_MSG_NO_VERSION = "A Game Version is required."
MSG_BOX_MSG_PARTY_FULL = "Your active party can only have 6 Pokemon."

TOOLTIP_CHECKBOX_SUBREGIONS = (
    "When enabled, each sub-region (for example, each floor in Mt. Moon) counts as its own catching region."
)
