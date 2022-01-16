import getdata
import matchlistpickle

import argparse

def main():

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('update', metavar='U', nargs = "?", type=str, default = "scratch", choices= ["scratch", "update", "pickle"], 
                        help="Specifies whether to generate the match list from scratch [scratch], update from the pickled file [update] or use only what's in the pickled file already [pickle].")
    parser.add_argument('-pickle', '--p', nargs = "?", type=str, choices = ["T", "F"], default = "F", help='Whether or not to save the match list as a pickle')
    args = parser.parse_args()

    print(args)


    offset = 0
    actual_limit = 1000

    with open("keys.txt", "r") as f:
        keys_dict = {}
        for line in f:
            key, val = line.split()
            keys_dict[key] = val
    
    hub_id = keys_dict["hub_id"]
    api_key = keys_dict["api_key"]
    default_player = keys_dict["default_player"]

    if args.update == "scratch":
        player_dict = {}
        match_dict = {}
        match_list = getdata.full_match_loop(api_key, hub_id, offset, actual_limit, player_dict, match_dict)
    elif args.update == "update":
        player_dict = matchlistpickle.pickle_read(f"stats-{hub_id}")
        match_dict = matchlistpickle.pickle_read(f"matchdict-{hub_id}")
        old_match_list = matchlistpickle.pickle_read(f"matches-{hub_id}")
        match_list = getdata.partial_match_loop(api_key, hub_id, offset, actual_limit, player_dict, match_dict, old_match_list)
    elif args.update == "pickle":
        player_dict = matchlistpickle.pickle_read(f"stats-{hub_id}")
        match_list = matchlistpickle.pickle_read(f"matches-{hub_id}")
        match_dict = matchlistpickle.pickle_read(f"matchdict-{hub_id}")

    if args.p == "T":
        matchlistpickle.pickle_write(f"stats-{hub_id}", player_dict)
        matchlistpickle.pickle_write(f"matches-{hub_id}", match_list)
        matchlistpickle.pickle_write(f"matchdict-{hub_id}", match_dict)

    return (player_dict, match_list, match_dict)

if __name__ == "__main__":
    main()