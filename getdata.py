import requests
from player import Player
from match import Match


def get_hub_match_id(api_key, hub_id, offset, display_limit):
    """
    This function returns a list containing the match IDs from a specified Faceit Hub.

    Paramters
    ---------

    api_key : str
            Api key given by the Faceit Developer hub.
    hub_id : str
            The ID of the hub you wish to get the match IDs from.
    offset : int
            The number of the earliest match to fetch. 
    display_limit : int
            The number of matches to fetch per api call. Maximum is 200.

    Returns
    -------
    
    match_id_list : list
            A list containing the IDs of the matches.
    """
    
    url = f"https://open.faceit.com/data/v4/hubs/{hub_id}/matches?type=past&offset={offset}&limit={display_limit}"
    response = requests.get(url, headers = {"Authorization" : "Bearer " + api_key})
    data = response.json()
    
    match_id_list = []
    
    for item in data["items"]:
        match_id_list.append(item["match_id"])
    
    return match_id_list

def get_full_match_list(api_key, hub_id, offset, actual_limit):
    """
    This function returns a list containing all Match IDs from a specified Faceit Hub. Can only return a maximum of 200 match IDs.

    Paramters
    ---------

    api_key : str
            Api key given by the Faceit Developer hub.
    hub_id : str
            The ID of the hub you wish to get the match IDs from.
    offset : int
            Text
    actual_limit : int
            Text

    Returns
    -------

    full_match_list : list
            List containing all Match IDs from the specified Faceit Hub.
    """
    
    full_match_list = []
    
    if actual_limit <= 100:
        full_match_list = get_hub_match_id(api_key, hub_id, offset, actual_limit)
    
    else:
        while True:
            
            if actual_limit <= 100:
                match_id_list = get_hub_match_id(api_key, hub_id, offset, actual_limit)
                full_match_list.extend(match_id_list)
                break
                
            match_id_list = get_hub_match_id(api_key, hub_id, offset, 100)
            
            if len(match_id_list) == 0:
                break

            offset += 100
            actual_limit -= 100
            full_match_list.extend(match_id_list)
            
    return full_match_list

def get_match_stats(api_key, match_id):
    """
    Gets full match stats (game_id, best_of, player stats etc.) for a specific match on faceit.

    Parameters
    ----------

    api_key : str
            Api key given by the Faceit Developer hub.
    match_id : str
             The ID of the match to retrieve stats for.

    Returns
    -------

    match_data : dict JSON
            JSON containing statistics about the match.
    """
    
    url = f"https://open.faceit.com/data/v4/matches/{match_id}/stats"
    response = requests.get(url, headers = {"Authorization" : "Bearer " + api_key})
    
    try:

        match_data = response.json()["rounds"][0]
        if response.status_code == 404:
                return None
        return match_data
    
    except:
        
        return None

    
def parse_match_data(match_id, match_data, player_dict, insert = False):
    """
    Retrieves player stats from match data and adds them to player_dict.

    Parameters
    ----------

    match_id : str
            text
    match_data : dict, JSON
            text
    player_dict : dict
            text
    insert : bool False
            text

    Returns
    -------

    None

    """
    
    if match_data == None:
        
        return None
    
    total_rounds = match_data["round_stats"]["Rounds"]
    match_map = match_data["round_stats"]["Map"]
    
    for team in match_data["teams"]:
         for player in team["players"]:
                if player["nickname"] not in player_dict.keys():
                    player_dict[player["nickname"]] = Player(player["nickname"])
                player_dict[player["nickname"]].stat_parse(match_id, total_rounds, match_map, player["player_stats"], insert)

    return None
            
            
def match_data_to_class(api_key, match_id, player_dict, match_dict, insert = False):
    """
    Text
    """
    
    match_data = get_match_stats(api_key, match_id)
    parse_match_data(match_id, match_data, player_dict, insert)
    # Create match objects
    Match.full_parse(match_id, match_data, player_dict, match_dict)
    
    
def full_match_loop(api_key, hub_id, offset, actual_limit, player_dict, match_dict):
    """
    Text
    """
    
    match_id_list = get_full_match_list(api_key, hub_id, offset, actual_limit)
    
    for match_id in match_id_list[::-1]:
        print(match_id)
        match_data_to_class(api_key, match_id, player_dict, match_dict)

    return match_id_list
    
def partial_match_loop(api_key, hub_id, offset, actual_limit, player_dict, match_dict, old_match_id_list):
    
    """
    Checks the hub matches and compares the IDs to matches already parsed to only get
    new match IDs, then parses through the new match IDs and adds them to the list.
    """
    
    old_length = len(old_match_id_list)
    match_id_list = get_full_match_list(api_key, hub_id, offset, actual_limit)
    new_length = len(match_id_list)
    length_diff = new_length - old_length
    
    new_match_id_list = match_id_list[:length_diff]
    new_match_id_list.reverse() #Reversing for insert to maintain order
    
    for match_id in new_match_id_list:
        print(match_id)
        match_data_to_class(api_key, match_id, player_dict, match_dict, insert = True)

    return match_id_list
    
    
    
    