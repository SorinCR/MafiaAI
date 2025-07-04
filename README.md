# LLM-Powered Mafia Game

This project is a simulation of the classic social deduction game "Mafia" (also known as "Werewolf"). It uses the Mesa agent-based modeling framework to structure the game and Google's Gemini API to power the decision-making and dialogue of the individual player agents.

Agents are assigned roles (Mafia, Doctor, Cop, Villager), given unique personalities, and use an LLM to interact, discuss, and vote based on the evolving game state.

## Features

- **AI-Powered Agents**: Each agent uses the Gemini API to generate dialogue, make accusations, vote for eliminations, and perform night actions based on their role, personality, and knowledge of the game.
- **Dynamic Role Assignment**: Roles are automatically assigned based on the number of players to ensure a balanced game.
- **Turn-Based Game Flow**: The simulation follows the classic Day/Night cycle of Mafia, including discussion, voting, and night actions.
- **Event Logging**: The entire game, from discussions to eliminations, is logged to the console and saved to a `mafia_game_log.json` file for post-game analysis.

## How to Run

1.  **Prerequisites**: Ensure you have Python 3 installed and NodeJS > 22. You will need the `mesa` and `google-generativeai` libraries.

2.  **Installation**: Install the required libraries using pip.

    ```bash
    cd ./api
    pip install -r requirements.txt
    ```

3.  **Set API Key**: Create an env file and replace `"YOUR_GEMINI_API_KEY"` with your actual Google Gemini API key.

    ```python
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```

4.  **Run the server**: Run the API from your terminal.

    ```bash
    python app.py
    ```

5.  **Install the npm depencies**: Install the required depencies for the Vite app.

    ```bash
    cd ..
    npm i
    ```

6.  **Run the frontend**: Run the frontend from your terminal.
    ```bash
    npm run dev
    ```
