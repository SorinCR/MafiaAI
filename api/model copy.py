import random
import math
# --- MODIFIED: Use a simpler scheduler and control activation manually ---
from mesa import Agent, Model
from mesa.time import BaseScheduler

class PlayerAgent(Agent):
    """An agent representing a player in the Mafia game."""

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.role = "Villager" # Default role
        self.status = "Alive"
        self.knowledge = {} # To store info (e.g., cop's investigation results)
        self.vote_for = None # Who this agent will vote for

    def __repr__(self):
        return f"<PlayerAgent id={self.unique_id} role={self.role} status={self.status}>"

    def discuss(self):
        """Placeholder for the discussion phase. AI logic will go here."""
        if self.status == "Alive":
            self.model.log_event(f"Player {self.unique_id} ({self.role}) is thinking about what to say...")


    def vote(self):
        """Placeholder for the voting phase. AI logic will go here."""
        if self.status == "Alive":
            possible_targets = [agent for agent in self.model.schedule.agents if agent.status == "Alive" and agent.unique_id != self.unique_id]
            
            if not possible_targets:
                self.vote_for = None
                return

            if self.role == "Mafia":
                non_mafia_targets = [agent for agent in possible_targets if agent.role != "Mafia"]
                if non_mafia_targets:
                    self.vote_for = self.random.choice(non_mafia_targets).unique_id
                else: 
                    self.vote_for = self.random.choice(possible_targets).unique_id
            else:
                self.vote_for = self.random.choice(possible_targets).unique_id
            
            self.model.log_event(f"Player {self.unique_id} ({self.role}) has decided to vote for Player {self.vote_for}.")


    def act(self):
        """Placeholder for the night action phase. AI logic will go here."""
        if self.status == "Alive":
            targets = [agent for agent in self.model.schedule.agents if agent.status == "Alive" and agent.unique_id != self.unique_id]
            if not targets and self.role not in ["Doctor"]: return
            
            action = ""
            if self.role == "Mafia":
                # Ensure mafia members exist before accessing index
                if self.model.mafia_members and self.unique_id == self.model.mafia_members[0]:
                    non_mafia_targets = [agent for agent in targets if agent.role != "Mafia"]
                    if non_mafia_targets:
                        target = self.random.choice(non_mafia_targets)
                        self.model.night_kill_target = target
                        action = f"Player {self.unique_id} (Mafia) targets Player {target.unique_id} for elimination."
            elif self.role == "Doctor":
                # Doctor can save themselves, so include self in potential targets
                possible_saves = [agent for agent in self.model.schedule.agents if agent.status == "Alive"]
                if possible_saves:
                    target = self.random.choice(possible_saves)
                    self.model.night_save_target = target
                    action = f"Player {self.unique_id} (Doctor) chooses to protect Player {target.unique_id}."
            elif self.role == "Cop":
                if targets: # Ensure there is someone to investigate
                    target = self.random.choice(targets)
                    self.knowledge[f"night_{self.model.day_count}"] = f"Investigated Player {target.unique_id}, who is a {target.role}."
                    action = f"Player {self.unique_id} (Cop) investigates Player {target.unique_id}."
            
            if action:
                self.model.log_event(action)


class MafiaModel(Model):
    """The main model for the Mafia game simulation."""

    def __init__(self, num_agents):
        super().__init__()
        self.num_agents = num_agents
        # --- MODIFIED: Use BaseScheduler ---
        self.schedule = BaseScheduler(self)
        self.game_phase = "Setup"
        self.day_count = 0
        self.event_log = []
        
        self.night_kill_target = None
        self.night_save_target = None
        self.mafia_members = []

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
                agent.knowledge['teammates'] = self.mafia_members
        
        self.log_event("Game starting! Roles have been assigned.")
        self.game_phase = "Day"


    def _determine_roles(self, n):
        """Determine the number of each role based on player count."""
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
        
        if not votes:
            self.log_event("No one was voted out.")
            return

        max_votes = max(votes.values())
        voted_out_ids = [pid for pid, v_count in votes.items() if v_count == max_votes]
        
        if len(voted_out_ids) == 1:
            voted_out_id = voted_out_ids[0]
            # --- MODIFIED: Safer way to get agent to prevent errors ---
            try:
                # Find the agent with the matching unique_id
                voted_out_agent = next(a for a in self.schedule.agents if a.unique_id == voted_out_id)
                voted_out_agent.status = "Dead"
                self.log_event(f"Vote result: Player {voted_out_id} ({voted_out_agent.role}) has been eliminated.")
            except StopIteration:
                self.log_event(f"Error: Could not find agent with ID {voted_out_id} to eliminate.")
        else:
            self.log_event("Vote resulted in a tie! No one is eliminated.")


    def _execute_night_actions(self):
        """Execute the results of the night actions."""
        self.log_event("Night falls...")
        
        if self.night_kill_target:
            if self.night_kill_target == self.night_save_target:
                self.log_event(f"Player {self.night_kill_target.unique_id} was attacked, but the Doctor saved them!")
            else:
                self.night_kill_target.status = "Dead"
                self.log_event(f"A body has been discovered... Player {self.night_kill_target.unique_id} ({self.night_kill_target.role}) was killed during the night.")
        else:
            self.log_event("The Mafia did not kill anyone.")

        self.night_kill_target = None
        self.night_save_target = None


    def _check_win_condition(self):
        """Check if a win condition has been met."""
        alive_agents = [a for a in self.schedule.agents if a.status == "Alive"]
        alive_mafia = [a for a in alive_agents if a.role == "Mafia"]
        alive_non_mafia = [a for a in alive_agents if a.role != "Mafia"]

        if len(alive_mafia) == 0:
            self.game_phase = "End"
            self.log_event("Game Over! The Villagers have won.")
            return True
        
        if len(alive_mafia) >= len(alive_non_mafia):
            self.game_phase = "End"
            self.log_event("Game Over! The Mafia have won.")
            return True
        
        return False

    def log_event(self, message):
        """Adds a message to the event log."""
        self.event_log.append({"day": self.day_count, "phase": self.game_phase, "message": message})


    def step(self):
        """Advance the model by one step, with manual phase control."""
        if self.game_phase == "End":
            return

        if self.game_phase == "Day":
            self.day_count += 1
            self.log_event(f"--- Day {self.day_count} ---")
            
            # --- MODIFIED: Manually call agent methods for each stage ---
            for agent in self.schedule.agents:
                agent.discuss()
            
            for agent in self.schedule.agents:
                agent.vote()
                
            self._tally_votes()
            if not self._check_win_condition():
                self.game_phase = "Night"
        
        elif self.game_phase == "Night":
            for agent in self.schedule.agents:
                agent.act()
                
            self._execute_night_actions()
            if not self._check_win_condition():
                self.game_phase = "Day"
        
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
