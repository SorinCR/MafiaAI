import random
import math
import os
import json
import time

from google import genai
from mesa import Agent, Model
from mesa.time import BaseScheduler

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class PlayerAgent(Agent):
    """An agent representing a player in the Mafia game, powered by Gemini."""

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.role = "Villager"
        self.status = "Alive"
        self.knowledge = {}
        self.vote_for = None
        
        if self.unique_id % 3 == 0:
            self.personality = "You are an outspoken and sometimes accusatory person. You are quick to point fingers."
        elif self.unique_id % 3 == 1:
            self.personality = "You are a quiet observer. You speak only when you think you have something important to say."
        else:
            self.personality = "You are a cautious but logical person. You tend to analyze situations before speaking."


    def __repr__(self):
        return f"<PlayerAgent id={self.unique_id} role={self.role} status={self.status}>"

    def _get_game_context(self, objective):
        """Builds a comprehensive summary of the current game state for the AI."""
        alive_players = [a.unique_id for a in self.model.schedule.agents if a.status == "Alive"]
        dead_players_info = [f"Player {a.unique_id} (was {a.role})" for a in self.model.schedule.agents if a.status == "Dead"]
        
        
        recent_events = [e['message'] for e in self.model.event_log[-15:]] 

        context = f"""
        You are Player {self.unique_id}, your role is: {self.role}.
        Your personality is: "{self.personality}"
        ---
        CURRENT GAME SITUATION:
        - It is Day {self.model.day_count}.
        - These players are ALIVE: {alive_players}.
        - These players are DEAD: {dead_players_info or 'None so far'}.
        - Your secret knowledge: {json.dumps(self.knowledge) if self.knowledge else 'You have no special information.'}
        ---
        RECENT CONVERSATION AND EVENTS:
        {json.dumps(recent_events, indent=2)}
        ---
        YOUR TASK:
        {objective}
        """
        return context

    
    def _call_gemini_api(self, prompt, is_json_response=False):
        """Makes a call to the Gemini API using the official SDK client and returns the response."""
        
        if not self.model.gemini_client:
            if is_json_response:
                return {"error": "API Key not configured"}
            return "I'm not sure what to say. The pressure is getting to me."

        try:
            
            
            chat = self.model.gemini_client.chats.create(model='gemini-2.5-flash')
            response = chat.send_message(prompt)
            
            
            
            if not response.text:
                 raise ValueError("API returned no text content. This may be due to a safety filter.")

            text_response = response.text
            
            if is_json_response:
                
                clean_text = text_response.strip().lstrip('```json').lstrip('```').rstrip('```')
                return json.loads(clean_text)
            return text_response.strip().replace('"', '') 

        except Exception as e:
            
            print(f"Error calling Gemini API for Player {self.unique_id}: {e}")
            if is_json_response:
                return {"error": f"Error during API call: {e}"}
            return f"I'm speechless... (An error occurred)"

    def discuss(self):
        """Uses Gemini to generate discussion based on the agent's role and knowledge."""
        if self.status != "Alive":
            return

        self.model.log_event(f"Player {self.unique_id} is thinking...")
        
        objective = "Based on the situation, your role, and personality, what is one thing you will say to the group? Speak in the first person. Be brief and direct. Do not announce your role. Your goal is to help your team win."
        prompt = self._get_game_context(objective)
        
        discussion_point = self._call_gemini_api(prompt)
        self.model.update_last_log_entry(f"Player {self.unique_id}: \"{discussion_point}\"")

    def vote(self):
        """Uses Gemini to decide who to vote for."""
        if self.status != "Alive":
            return
            
        self.model.log_event(f"Player {self.unique_id} is considering their vote...")

        alive_players_to_vote = [a for a in self.model.schedule.agents if a.status == "Alive" and a.unique_id != self.unique_id]
        if not alive_players_to_vote: return
        
        alive_players_ids = [a.unique_id for a in alive_players_to_vote]

        objective = f"""
        Based on the discussion and your goals, who will you vote to eliminate?
        Choose exactly one player ID from this list: {alive_players_ids}.
        Your response MUST be a JSON object with a single key "vote_for" and the player number as an integer.
        Example: {{"vote_for": 5}}
        """
        prompt = self._get_game_context(objective)
        
        response = self._call_gemini_api(prompt, is_json_response=True)
        
        if isinstance(response, dict) and "vote_for" in response and response['vote_for'] in alive_players_ids:
            self.vote_for = response['vote_for']
            self.model.update_last_log_entry(f"Player {self.unique_id} has cast a vote for Player {self.vote_for}.")
        else:
            
            self.vote_for = random.choice(alive_players_ids)
            self.model.update_last_log_entry(f"Player {self.unique_id} (AI error/fallback) randomly voted for Player {self.vote_for}.")


    def act(self):
        """Uses Gemini for night actions based on role."""
        if self.status != "Alive":
            return

        objective = ""
        alive_agents = [a for a in self.model.schedule.agents if a.status == "Alive"]
        other_alive_agents = [a for a in alive_agents if a.unique_id != self.unique_id]
        
        alive_agent_ids = [a.unique_id for a in alive_agents]
        other_alive_agent_ids = [a.unique_id for a in other_alive_agents]

        if self.role == "Mafia":
             if not other_alive_agents: return
             objective = f"You are Mafia. Choose one player to eliminate from this list: {other_alive_agent_ids}. Respond in JSON with a 'target' key. Example: {{'target': 3}}"
        elif self.role == "Doctor":
             if not alive_agents: return
             objective = f"You are the Doctor. Choose one player to save (you can save yourself). Alive players: {alive_agent_ids}. Respond in JSON with a 'target' key. Example: {{'target': 7}}"
        elif self.role == "Cop":
             if not other_alive_agents: return
             objective = f"You are the Cop. Choose one player to investigate from this list: {other_alive_agent_ids}. Respond in JSON with a 'target' key. Example: {{'target': 2}}"
        else:
            return

        prompt = self._get_game_context(objective)
        response = self._call_gemini_api(prompt, is_json_response=True)
        
        target_id = None
        if isinstance(response, dict) and "target" in response:
            
            valid_targets = alive_agent_ids if self.role == "Doctor" else other_alive_agent_ids
            if response.get('target') in valid_targets:
                target_id = response.get('target')
        
        
        if target_id is None:
            if self.role == "Doctor" and alive_agents:
                target_id = random.choice(alive_agent_ids)
            elif other_alive_agents:
                target_id = random.choice(other_alive_agent_ids)

        if target_id is None: return

        try:
            target_agent = next(a for a in self.model.schedule.agents if a.unique_id == target_id)
            action_log = ""
            if self.role == "Mafia":
                
                if not self.model.night_kill_target and self.unique_id in self.model.mafia_members:
                    self.model.night_kill_target = target_agent
                    action_log = "The Mafia have chosen their target."
            elif self.role == "Doctor":
                self.model.night_save_target = target_agent
                action_log = "The Doctor has chosen someone to protect."
            elif self.role == "Cop":
                self.knowledge[f"night_{self.model.day_count}"] = f"Investigated Player {target_agent.unique_id}, who is a {target_agent.role}."
                action_log = "The Cop has chosen someone to investigate."
            
            
            if action_log and not any(action_log in e['message'] for e in self.model.event_log[-3:]):
                self.model.log_event(action_log)

        except StopIteration:
            self.model.log_event(f"Player {self.unique_id} ({self.role}) tried to target non-existent player {target_id}.")

class MafiaModel(Model):
    """The main model for the Mafia game simulation."""

    def __init__(self, num_agents):
        super().__init__()
        self.num_agents = num_agents
        self.schedule = BaseScheduler(self)
        self.game_phase = "Setup"
        self.day_count = 0
        self.event_log = []
        
        self.night_kill_target = None
        self.night_save_target = None
        self.mafia_members = []

        
        self.gemini_client = None
        if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
            try:
                
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
                print("Gemini Client initialized successfully.")
            except Exception as e:
                
                print(f"CRITICAL: Failed to initialize Gemini Client: {e}")
                self.gemini_client = None
        else:
            print("WARNING: Gemini API Key not provided. Agents will use fallback logic.")


        self._assign_roles_and_create_agents()

    def _assign_roles_and_create_agents(self):
        """Creates agents and assigns roles."""
        roles = self._determine_roles(self.num_agents)
        random.shuffle(roles)

        for i in range(self.num_agents):
            agent = PlayerAgent(i + 1, self)
            agent.role = roles[i]
            if agent.role == "Mafia":
                self.mafia_members.append(agent.unique_id)
            self.schedule.add(agent)
            
        
        for agent in self.schedule.agents:
            if agent.role == "Mafia":
                agent.knowledge['teammates'] = [m for m in self.mafia_members if m != agent.unique_id]
        
        self.log_event("Game starting! Roles have been assigned.")
        self.game_phase = "Day"

    def _determine_roles(self, n):
        """Determine the number of each role based on player count."""
        if n < 3:
            
            raise ValueError("Mafia game requires at least 3 players.")
        num_mafia = math.ceil(n / 4)
        num_doctor = 1 if n >= 5 else 0
        num_cop = 1 if n >= 6 else 0
        num_villagers = n - num_mafia - num_doctor - num_cop

        roles = ["Mafia"] * num_mafia + ["Doctor"] * num_doctor + ["Cop"] * num_cop + ["Villager"] * num_villagers
        return roles

    def _tally_votes(self):
        """Tally the votes and determine who is eliminated."""
        votes = {}
        for agent in self.schedule.agents:
            if agent.status == "Alive" and agent.vote_for is not None:
                target_id = agent.vote_for
                votes[target_id] = votes.get(target_id, 0) + 1
        
        self.log_event(f"The votes are in: {votes}")
        if not votes:
            self.log_event("No one was voted out.")
            return

        max_votes = max(votes.values())
        voted_out_ids = [pid for pid, v_count in votes.items() if v_count == max_votes]
        
        
        if len(voted_out_ids) == 1:
            voted_out_id = voted_out_ids[0]
            try:
                voted_out_agent = next(a for a in self.schedule.agents if a.unique_id == voted_out_id)
                voted_out_agent.status = "Dead"
                self.log_event(f"Vote result: Player {voted_out_id} ({voted_out_agent.role}) has been eliminated.")
            except StopIteration:
                self.log_event(f"Error: Could not find agent with ID {voted_out_id} to eliminate.")
        else:
            self.log_event("Vote resulted in a tie! No one is eliminated.")

    def _execute_night_actions(self):
        """Execute the results of the night actions."""
        self.log_event("Night falls... Actions are being taken in secret.")
        
        if self.night_kill_target:
            if self.night_kill_target == self.night_save_target:
                self.log_event(f"Someone was attacked, but the Doctor saved them!")
            else:
                self.night_kill_target.status = "Dead"
                self.log_event(f"A body has been discovered... Player {self.night_kill_target.unique_id} (was a {self.night_kill_target.role}) was killed during the night.")
        else:
            self.log_event("The night was quiet... surprisingly.")

        
        self.night_kill_target = None
        self.night_save_target = None

    def _check_win_condition(self):
        """Check if a win condition has been met."""
        alive_agents = [a for a in self.schedule.agents if a.status == "Alive"]
        alive_mafia = [a for a in alive_agents if a.role == "Mafia"]
        alive_non_mafia = [a for a in alive_agents if a.role != "Mafia"]

        if len(alive_mafia) == 0:
            self.game_phase = "End"
            self.log_event("Game Over! The Town has eliminated the Mafia and won!")
            return True
        
        if len(alive_mafia) >= len(alive_non_mafia):
            self.game_phase = "End"
            self.log_event("Game Over! The Mafia have taken over and won!")
            return True
        
        return False

    def log_event(self, message):
        """Adds a message to the event log."""
        self.event_log.append({"day": self.day_count, "phase": self.game_phase, "message": message})
        print(message) 

    def update_last_log_entry(self, message):
        """Updates the most recent log entry, useful for 'thinking' -> 'dialogue' effect."""
        if self.event_log:
            self.event_log[-1]["message"] = message
        print(message) 

    def step(self):
        """Advance the model by one step (one full day/night cycle or phase)."""
        if self.game_phase == "End":
            return

        
        self.day_count += 1
        self.game_phase = "Day"
        self.log_event(f"--- Day {self.day_count} ---")
        
        
        for agent in list(self.schedule.agents):
            agent.discuss()
            time.sleep(1) 
        
        
        for agent in list(self.schedule.agents):
            agent.vote()
        
        self._tally_votes()
        if self._check_win_condition():
            return

        
        self.game_phase = "Night"
        self.log_event(f"--- Night {self.day_count} ---")
        
        
        for agent in list(self.schedule.agents):
            agent.act()
            
        self._execute_night_actions()
        if self._check_win_condition():
            return
        
        
        self.game_phase = "Day"
    
    def run_model(self):
        """Run the simulation until a win condition is met."""
        while self.game_phase != "End":
            self.step()
        
        self.log_event("Final Roles:")
        for agent in self.schedule.agents:
            self.log_event(f"  - Player {agent.unique_id} was {agent.role}")

    def get_state(self):
        """Return the current state of the model as a dictionary."""
        return {
            "num_agents": self.num_agents,
            "game_phase": self.game_phase,
            "day_count": self.day_count,
            "event_log": self.event_log,
            "agents": [
                {
                    "id": agent.unique_id,
                    "status": agent.status,
                    
                    "role": agent.role if self.game_phase == "End" or agent.status == "Dead" else "Unknown",
                    "knowledge": agent.knowledge if self.game_phase == "End" else {}
                }
                for agent in self.schedule.agents
            ]
        }

if __name__ == '__main__':
    
    
    
    
    NUMBER_OF_PLAYERS = 7 
    
    print(f"Starting a new Mafia game with {NUMBER_OF_PLAYERS} players.")
    
    
    mafia_game = MafiaModel(NUMBER_OF_PLAYERS)
    
    
    mafia_game.run_model()
    
    
    final_state = mafia_game.get_state()
    with open('mafia_game_log.json', 'w') as f:
        json.dump(final_state, f, indent=4)
        
    print("\nSimulation finished. Check 'mafia_game_log.json' for the detailed game log.")