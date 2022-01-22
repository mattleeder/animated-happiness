import requests
from elo import Elo

class Match:

    def __init__(self, match_id, api_key):
        self.api_key = api_key

        self.match_id = match_id
        self.game_mode = None
        self.map = None
        self.number_of_rounds = None
        self.team_one_score = None
        self.team_two_score = None
        self.players = []
        self.team_one = []
        self.team_two = []
        self.winner = None
        self.player_stats = {}
        self.player_elos = {}

        self.match_elo = None
        self.team_one_elo = None
        self.team_two_elo = None

    def match_parse(self, data):
        
        self.game_mode = data["game_mode"]
        self.number_of_rounds = int(data["round_stats"]["Rounds"])
        self.map = data["round_stats"]["Map"].split("/")[-1]
        self.team_one_score = data["teams"][0]["team_stats"]["Final Score"]
        self.team_two_score = data["teams"][1]["team_stats"]["Final Score"]
        self.team_one = [player["nickname"] for player in data["teams"][0]["players"]]
        self.team_two = [player["nickname"] for player in data["teams"][1]["players"]]
        self.players = self.team_one + self.team_two

        self.winner = 1 + (int(self.team_two_score) > int(self.team_one_score))

        self.player_stat_parse(data, 1)
        self.player_stat_parse(data, 2)

    def player_stat_parse(self, data, team):

        num_team_players = len([self.team_one, self.team_two][team - 1]) # Teams may not always show as 5 due to abandons

        for i in range(num_team_players):

            player = data["teams"][team - 1]["players"][i]["nickname"]
            player_stats = data["teams"][team - 1]["players"][i]["player_stats"]

            self.player_stats[player] = player_stats

            for stat in self.player_stats[player].keys():
                self.player_stats[player][stat] = float(self.player_stats[player][stat])

    def player_elo_reward_calc(self, player, performance_target, team):
        
        performance_ratio = min(1.5, max(0.5, ((self.player_stats[player]["Kills"] / self.number_of_rounds) / performance_target))) # Between 0.5 and 1.5
        

        win = performance_ratio * [self.team_one_elo, self.team_two_elo][team - 1]
        loss = - (abs(performance_ratio - 2)) * [self.team_two_elo, self.team_one_elo][team - 1]

        return (loss, win)

    def scoreboard_data(self):

        team_one_data = {player : self.player_stats[player] for player in self.team_one}
        team_two_data = {player : self.player_stats[player] for player in self.team_two}

        return team_one_data, team_two_data


    @classmethod
    def full_parse(self, api_key, match_id, match_data, player_dict, match_dict):
        if match_data is None:
            return None
        current_match = Match(match_id, api_key)
        current_match.match_parse(match_data)
        current_match_elo = Elo(current_match.team_one, current_match.team_two, player_dict)
        current_match.match_elo = current_match_elo._match_elo
        current_match.team_one_elo = current_match_elo.team_one_elo
        current_match.team_two_elo = current_match_elo.team_two_elo
        winning_team = [current_match.team_one, current_match.team_two][current_match.winner - 1]
        for player in current_match.players:
            current_match.player_elos[player] = [player_dict[player].elo]
            elo_change = current_match_elo.elo_changes(player, current_match.player_stats[player], (player in winning_team))
            player_dict[player].elo += elo_change
            player_dict[player].elo_history.append(player_dict[player].elo)
        match_dict[match_id] = current_match



    @classmethod
    def match_list_parse(self, match_list):
        match_dict= {}

        pass

    def match_stats(self):
        """
        Gets full match stats (game_id, best_of, player stats etc.) for a specific match on faceit.

        Returns
        -------

        match_data : dict JSON
                JSON containing statistics about the match.
        """
        
        url = f"https://open.faceit.com/data/v4/matches/{self.match_id}/stats"
        response = requests.get(url, headers = {"Authorization" : "Bearer " + self.api_key})
        
        # Why is this here? To catch KeyError when response does not contain "rounds"

        try:

            match_data = response.json()["rounds"][0]
            if response.status_code == 404:
                    return None
            return match_data
        
        except:
            
            return None