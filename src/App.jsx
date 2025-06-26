import React, { useState, useRef, useEffect } from "react";

// --- Helper Components & Icons ---

const Icon = ({ role }) => {
  const icons = {
    Mafia: " M ",
    Doctor: " D ",
    Cop: " C ",
    Villager: " V ",
    Unknown: " ? ",
  };
  const colors = {
    Mafia: "bg-red-500",
    Doctor: "bg-blue-500",
    Cop: "bg-sky-500",
    Villager: "bg-green-500",
    Unknown: "bg-gray-400",
  };
  return (
    <span
      className={`inline-block w-6 h-6 text-center text-sm font-bold text-white rounded-full ${
        colors[role] || "bg-gray-400"
      }`}
    >
      {icons[role] || "?"}
    </span>
  );
};

const AgentCard = ({ agent }) => {
  const isDead = agent.status === "Dead";
  const cardBg = isDead ? "bg-gray-700/50" : "bg-gray-800";
  const textOpacity = isDead ? "opacity-50" : "";

  return (
    <div
      className={`p-4 rounded-lg shadow-md transition-all duration-300 ${cardBg} ${textOpacity}`}
    >
      <div className="flex items-center justify-between">
        <p className="text-lg font-bold text-white">Player {agent.id}</p>
        <p
          className={`px-2 py-1 text-xs font-semibold rounded-full ${
            isDead ? "bg-red-800 text-red-200" : "bg-green-800 text-green-200"
          }`}
        >
          {agent.status}
        </p>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <Icon role={agent.role} />
        <p className="text-gray-300">{agent.role}</p>
      </div>
    </div>
  );
};

const EventLog = ({ log }) => {
  const endOfLogRef = useRef(null);
  useEffect(() => {
    endOfLogRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  return (
    <div className="bg-gray-900/50 p-4 rounded-lg h-96 overflow-y-auto border border-gray-700">
      <h3 className="text-xl font-bold text-white mb-4 sticky top-0 bg-gray-900/50 py-2">
        Event Log
      </h3>
      <div className="space-y-3">
        {log.map((event, index) => (
          <div key={index}>
            {event.message.startsWith("---") ? (
              <p className="text-center font-bold text-sky-400 my-2">
                {event.message}
              </p>
            ) : (
              <p className="text-gray-300 text-sm">
                <span className="font-semibold text-gray-500 mr-2">
                  [{event.phase} {event.day}]
                </span>
                {event.message}
              </p>
            )}
          </div>
        ))}
      </div>
      <div ref={endOfLogRef} />
    </div>
  );
};

// --- Main App Component ---

export default function App() {
  // --- State Management ---
  const [numAgents, setNumAgents] = useState(8);
  const [gameState, setGameState] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const API_BASE_URL = "http://127.0.0.1:5000";

  // --- API Handlers ---
  const handleStartGame = async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/game/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ num_agents: parseInt(numAgents, 10) }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to start game.");
      }
      setGameState(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNextStep = async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/game/step`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to advance game state.");
      }
      setGameState(data.state || data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    async function fetchState() {
      const response = await fetch("http://127.0.0.1:5000/api/game/state");
      const data = await response.json();
      if (response.ok) {
        setGameState(data);
      }
    }

    const interval = setInterval(() => {
      fetchState();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const isGameOver = gameState?.game_phase === "End";

  // --- Render ---
  return (
    <div className="min-h-screen min-w-screen bg-gray-900 text-white font-sans p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl sm:text-5xl font-bold text-sky-400">
            AI Mafia
          </h1>
        </header>

        {/* Controls */}
        {!gameState && (
          <div className="max-w-md mx-auto bg-gray-800 p-6 rounded-lg shadow-2xl">
            <h2 className="text-2xl font-bold text-center mb-4">New Game</h2>
            <div className="flex flex-col gap-4">
              <label
                htmlFor="numAgents"
                className="font-semibold text-gray-300"
              >
                Number of Players (4-16)
              </label>
              <input
                type="number"
                id="numAgents"
                value={numAgents}
                onChange={(e) => setNumAgents(e.target.value)}
                min="4"
                max="16"
                className="p-3 bg-gray-700 rounded-lg text-white border border-gray-600 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                disabled={isLoading}
              />
              <button
                onClick={handleStartGame}
                disabled={isLoading}
                className="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold py-3 px-4 rounded-lg transition duration-300 disabled:bg-gray-500 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? "Starting..." : "Start Game"}
              </button>
            </div>
          </div>
        )}

        {error && (
          <p className="text-red-400 bg-red-900/50 p-3 rounded-lg text-center my-4">
            {error}
          </p>
        )}

        {/* Game Display */}
        {gameState && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Panel: Agents & Controls */}
            <div className="lg:col-span-1 space-y-6">
              <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
                <h2 className="text-2xl font-bold mb-4">Game Status</h2>
                <div className="space-y-2">
                  <p>
                    <span className="font-bold text-gray-400">Day:</span>{" "}
                    {gameState.day_count}
                  </p>
                  <p>
                    <span className="font-bold text-gray-400">Phase:</span>{" "}
                    {gameState.game_phase}
                  </p>
                </div>
                {isGameOver && (
                  <div className="mt-4 p-3 bg-yellow-800/80 rounded-lg text-center font-bold text-yellow-200">
                    {
                      gameState.event_log[gameState.event_log.length - 1]
                        .message
                    }
                  </div>
                )}
              </div>

              <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
                <h2 className="text-2xl font-bold mb-4">Controls</h2>
                <button
                  onClick={handleNextStep}
                  disabled={isLoading || isGameOver}
                  className="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold py-3 px-4 rounded-lg transition duration-300 disabled:bg-gray-500 disabled:cursor-not-allowed"
                >
                  {isLoading
                    ? "Processing..."
                    : `Advance to ${
                        gameState.game_phase === "Day" ? "Night" : "Day"
                      }`}
                </button>
                <button
                  onClick={() => setGameState(null)}
                  className="w-full mt-4 bg-red-600 hover:bg-red-500 text-white font-bold py-3 px-4 rounded-lg transition duration-300"
                >
                  End Game & Start New
                </button>
              </div>

              <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
                <h2 className="text-2xl font-bold mb-4">
                  Players ({gameState.agents.length})
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-2 gap-3">
                  {gameState.agents.map((agent) => (
                    <AgentCard key={agent.id} agent={agent} />
                  ))}
                </div>
              </div>
            </div>

            {/* Right Panel: Event Log */}
            <div className="lg:col-span-2">
              <EventLog log={gameState.event_log} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
