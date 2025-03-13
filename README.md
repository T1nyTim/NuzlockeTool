# NuzlockeTool
The NuzlockeTool is a Python-based Nuzlocke Companion tool built with PyQt6 designed to help you manage and track your Pokemon Nuzlocke runs. It provides out-of-game tracking for various Nuzlocke rulesets and integrates additional tools such as random decision generation and best-move calculation.

## Features
- Autosave your progress - including party data, encounters, decisions
- Loading a previous session to resume progress
- Track party, box and dead Pokemon
- Record encounter locations and prevents duplicate encounters
- Maintains a separate journal of your progress throughout the run, such as catches, transfers, evolution, random decisions
- Tool for randomly making decisions for you when you can't decide, or want to leave it to fate to decide, some example decisions are:
    - Decide what Starter Pokemon to use
    - Decide what Fossile to pick
    - Decide which Eeveelution to evolve into
- Tool for determining your current parties most damaging move for a given Pokemon. Currently accounts for:
    - Stat stages
    - Reflect/Light Screen effects
    - Critical hits
    - Accuracy
    - Variety of move-specific modifiers (eg multi-hit, OHKO, static-damage)

## Nuzlocke Varients
Initially the application only supports Generation 1 games and the standard Nuzlocke, however support for more games, and many many more rulesets will be added in future updates.

## Installation
To install the NuzlockeTool, you need to have Python installed on your system. Clone this repository to your local machine using:

`git clone https://github.com/T1nyTim/NuzlockeTool.git`

Navigate to the project directory and install the required dependencies:

```
cd NuzlockeTool
pip install -e .
```

## Usage
To run the application, use the following command in the project directory:

`NuzlockeTool`

### To Start a New Session
Select New from under the under the File session

### Directory Explanations
log files for debugging purposes will be generated under the `logs` directory

journal files for keeping track of a players progress for a given playthrough will be generated under the `journal` directory

save files for loading previous sessions will be auto-saved and kept in the `save` directory
