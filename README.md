# NuzlockeTool
The NuzlockeTool is a Nuzlocke Companion application, primarily for complex rulesets that require the player to keep track of various aspects of their playthrough. The kinds of things I intend on supporting from the outset consist of:
- Tracking the Pokemon you have caught, and tracking their progress, things like:
    - Level
    - Evolution
    - Moves
- Tracking where you have already encountered a Pokemon
- Tool for randomly making decisions for you when you can't decide, or want to leave it to fate to decide, some example decisions are:
    - Decide what Starter Pokemon to use
    - Decide what Fossile to pick
    - Decide which Eeveelution to evolve into
- Tool for determining your current parties most damaging move for a given Pokemon

## Nuzlocke Varients
Initially the application only supports Generation 1 games and the standard Nuzlocke, however support for more games, and many many more rulesets will be added in future updates.

## Installation
To install the NuzlockeTool, you need to have Python installed on your system. Clone this repository to your local machine using:
`git clone https://github.com/T1nyTim/NuzlockeTool.git`
Navigate to the project directory and install the required dependencies:
`cd NuzlockeTool`
`pip install -r requirements.txt`

## Usage
To run the application, use the following command in the project directory:
`python -m nuzlocke_tool`

log files for debugging purposes will be generated under the `logs` directory
journal files for keeping track of a players progress for a given playthrough will be generated under the `journal` directory
save files for loading previous sessions will be auto-saved and kept in the `save` directory
