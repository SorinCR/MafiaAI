from flask import Flask, request, jsonify
from flask_cors import CORS
from model import MafiaModel

# --- Configuration ---
# It's better to use a more robust way to store the model instance in a real application,
# but a global variable is fine for this prototype.
model_instance = None

# --- Flask App Initialization ---
app = Flask(__name__)
# Allow requests from our React frontend (which will be on a different port)
CORS(app) 

# --- API Endpoints ---

@app.route("/api/game/start", methods=["POST"])
def start_game():
    """
    Initializes a new Mafia game model.
    Expects a JSON payload with 'num_agents'.
    e.g., {"num_agents": 8}
    """
    global model_instance
    data = request.get_json()

    if not data or "num_agents" not in data:
        return jsonify({"error": "Missing 'num_agents' in request body"}), 400

    try:
        num_agents = int(data["num_agents"])
        if num_agents < 4:
            return jsonify({"error": "Number of agents must be at least 4."}), 400
            
        # Create a new model instance
        model_instance = MafiaModel(num_agents=num_agents)
        app.logger.info(f"New game started with {num_agents} agents.")
        
        # Return the initial state of the new game
        return jsonify(model_instance.get_state())

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid 'num_agents' format. Must be an integer."}), 400


@app.route("/api/game/state", methods=["GET"])
def get_game_state():
    """
    Returns the current state of the game model.
    """
    global model_instance
    if model_instance is None:
        return jsonify({"error": "Game not started. Please POST to /api/game/start first."}), 404
    
    return jsonify(model_instance.get_state())


@app.route("/api/game/step", methods=["POST"])
def step_game():
    """
    Advances the game by one step (e.g., from Day to Night).
    """
    global model_instance
    if model_instance is None:
        return jsonify({"error": "Game not started."}), 404

    if model_instance.game_phase == "End":
        return jsonify({"error": "Game has ended.", "state": model_instance.get_state()}), 400

    app.logger.info(f"Stepping model from phase: {model_instance.game_phase}")
    model_instance.step()
    app.logger.info(f"Model stepped to phase: {model_instance.game_phase}")
    
    return jsonify(model_instance.get_state())


# --- Main Execution ---
if __name__ == "__main__":
    # Note: `debug=True` is great for development as it enables auto-reloading.
    # Do not use it in a production environment.
    app.run(debug=True, port=5000)