from dash import Input, Output, State, callback, dash_table, dcc, html
import dash_bootstrap_components as dbc
import dash
import base64
from itsdangerous import base64_decode
import pandas as pd
import plotly.express as px
import matchlistpickle
import pickle
from elo import Elo
import io
import os
from hubmatches import HubMatches
from player import Player
import jsonpickle
import json
from dotenv import load_dotenv

from rq import Queue, get_current_job
from rq.job import Job
from rq.exceptions import NoSuchJobError
from worker import conn
import uuid
from collections import namedtuple

import logging

logging.basicConfig(level = logging.DEBUG)

q = Queue(connection=conn)

Result = namedtuple(
    "Result", ["msg", "player_dict", "match_dict", "match_list", "player_name_lookup", "progress", "collapse_is_open", "finished_data"]
)

load_dotenv()
api_key = os.environ["API_KEY"]
offset = 0
actual_limit = 10_000

data_table_non_editable_kwargs = {
        'style_as_list_view' : True,
        'style_header' : {
            'backgroundColor': 'rgba(30, 30, 30, 1)',
            'color': 'white'
        },
        'style_data' : {
            'backgroundColor': 'rgba(0, 0, 0, 0)',
            'color': 'white'
        },
        'cell_selectable' : False,
        'row_selectable' : False,
        'column_selectable' : False,
        'editable' : False
}

def average_actual_rating(match_dict):
    actuals = []
    for match in match_dict:
        for player in match_dict[match].player_elo_data.keys():
            actuals.append(match_dict[match].player_elo_data[player]["Performance Actual"])
    return sum(actuals) / len(actuals)

@callback(
	Output("navbar", "children"),
    Input("match-dict", "data"),
    Input("match-list", "data")
)
def render_navbar(match_dict, match_list):

    if match_dict is not None:
        match_dict = jsonpickle.decode(json.loads(match_dict))
        match_list = jsonpickle.decode(json.loads(match_list))

        try:
            avg_rating = round(average_actual_rating(match_dict), 2)
        except ZeroDivisionError:
            avg_rating = "Null"

    else:
        avg_rating = "Null"
        match_list = []

    return [
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Page 1", href="/page-1", active='exact')),
                dbc.NavItem(dbc.NavLink("Page 2", href="/page-2", active='exact')),
                dbc.NavItem(dbc.NavLink("Page 3", href="/page-3", active='exact')),
                dbc.NavItem(dbc.NavLink("Page 4", href="/page-4", active='exact')),
                dbc.NavItem(dbc.NavLink("Page 5", href="/page-5", active='exact')),
                dbc.NavItem(dbc.NavLink("Page 6", href="/page-6", active='exact')),
            ],
            brand=f"CSGO Dashboard - Number of matches: {len(match_list)}, average rating: {avg_rating}",
            brand_href="",
            color="primary",
            dark=True,
        )
    ]

@callback(Output(component_id='player-name-dropdown', component_property= 'options'),
            Input(component_id='player-name-lookup', component_property='data'))
def player_dropdown_options_stat_page(player_name_lookup):
    player_name_lookup = jsonpickle.decode(json.loads(player_name_lookup))
    return [{"label" : x, "value" : player_name_lookup[x]} for x in sorted(player_name_lookup.keys())]

@callback(Output(component_id='player-filter', component_property= 'options'),
            Input(component_id='player-name-lookup', component_property='data'))
def player_dropdown_options_match_page(player_name_lookup):
    player_name_lookup = jsonpickle.decode(json.loads(player_name_lookup))
    options = [{"label" : "All", "value" : "All"}]
    options += [{"label" : x, "value" : player_name_lookup[x]} for x in sorted(player_name_lookup.keys())]
    return options

@callback(Output(component_id='elo-filter', component_property= 'options'),
            Input(component_id='player-name-lookup', component_property='data'))
def player_dropdown_options_match_page(player_name_lookup):
    player_name_lookup = jsonpickle.decode(json.loads(player_name_lookup))
    return [{"label" : x, "value" : player_name_lookup[x]} for x in sorted(player_name_lookup.keys())]

@callback(Output("full-elo-table", "children"),
Input("player-dict", "data"))
def full_elo_table(player_dict):

    player_dict = jsonpickle.decode(json.loads(player_dict))
    d = {player : player_dict[player].elo for player in player_dict}
    data = [{"Player" : player_dict[key].name, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

@callback(Output("elo-hiscores-table", "children"),
Input("player-dict", "data"))
def elo_hiscores(player_dict):
    player_dict = jsonpickle.decode(json.loads(player_dict))
    d = {player : max(player_dict[player].elo_history) for player in player_dict}
    data = [{"Player" : player_dict[key].name, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

@callback(Output(component_id='scatter', component_property= 'figure'),
        [Input(component_id='player-name-dropdown', component_property= 'value'),
        Input(component_id='stat-name-dropdown', component_property= 'value'),
        Input(component_id="n-recent-matches", component_property="value"),
        Input("player-dict", "data")])
def player_stat_graph(player_name_dropdown, stat_name_dropdown, n_recent_matches, player_dict):

    player_dict = jsonpickle.decode(json.loads(player_dict))

    n = n_recent_matches

    data = {}
    data["Player"] = []
    data["Match Number"] = []
    data[stat_name_dropdown] = []

    for player in player_name_dropdown:

        matches = min(n, len(player_dict[player].stats["Match ID"]))
        data["Player"].extend([player_dict[player].name] * matches)
        data["Match Number"].extend(list(range(n - matches, n)))

        stat_list = player_dict[player].stats[stat_name_dropdown][-n:]
        data[stat_name_dropdown].extend(stat_list)

    df = pd.DataFrame(data)

    fig = px.line(df,x = "Match Number", y = stat_name_dropdown, color = "Player")
        
    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor= 'rgba(0, 0, 0, 0)',
        paper_bgcolor= 'rgba(0, 0, 0, 0)'
    )

    return fig

@callback(Output(component_id='stat-table', component_property= 'children'),
            [Input(component_id='player-name-dropdown', component_property= 'value'),
            Input(component_id='stat-name-dropdown', component_property= 'value'),
            Input(component_id="n-recent-matches", component_property="value"),
            Input("player-dict", "data")])
def stat_order_grid(player_name_dropdown, stat_name_dropdown, n_recent_matches, player_dict, denominator_stat = None):
    
    player_dict = jsonpickle.decode(json.loads(player_dict))

    d = Player.order_players_by_stat(player_dict, player_name_dropdown, n_recent_matches, stat_name_dropdown, denominator_stat)
    data = [{stat_name_dropdown : round(key,2), "Player" : player_dict[d[key]].name} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash_table.DataTable(
        id = "player-stat-table", 
        columns = columns, 
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

@callback(Output(component_id='match-choices', component_property= 'options'),
            Output("match-choices", "value"),
            Input(component_id='player-filter', component_property='value'),
            Input("match-dict", "data"),
            Input("match-list", "data"))
def match_selector(player_filter, match_dict, match_list):

    match_dict = jsonpickle.decode(json.loads(match_dict))
    match_list = jsonpickle.decode(json.loads(match_list))

    if player_filter == "All":
        return ([{"label" : x, "value" : x} for x in match_list], [{"label" : x, "value" : x} for x in match_list][0]["value"])

    ops = []
    for x in match_list:
        match = match_dict.get(x, None)
        if match is not None:
            if player_filter in match_dict[x].players:
                ops.append({"label" : x, "value" : x})

    return (ops, ops[0]["value"])

@callback(Output(component_id='scoreboard-container', component_property= 'children'),
            [Input(component_id='match-choices', component_property= 'value'),
            Input("player-dict", "data"),
            Input("match-dict", "data")])
def display_scoreboard(chosen_match, player_dict, match_dict):

    player_dict = jsonpickle.decode(json.loads(player_dict))
    match_dict = jsonpickle.decode(json.loads(match_dict))
    if chosen_match is None:
        return None
    current_match = match_dict.get(chosen_match, None)
    if current_match is None:
        return [
            html.H3("Error, match not found")
        ]
    team_one_data, team_two_data = current_match.scoreboard_data()
    player_elos = pd.DataFrame.from_dict(current_match.player_elo_data).T.reset_index()
    player_elos = player_elos.round({'Elo': 0, 'Elo Change': 1, "Performance Target" : 2, "Performance Actual" : 2})
    player_elos["index"] = player_elos["index"].map({player_id : player.name for player_id, player in player_dict.items()})
    team_one_df = pd.DataFrame(team_one_data).T.reset_index()
    team_two_df = pd.DataFrame(team_two_data).T.reset_index()
    team_one_df["index"] = team_one_df["index"].map({player_id : player.name for player_id, player in player_dict.items()})
    team_two_df["index"] = team_two_df["index"].map({player_id : player.name for player_id, player in player_dict.items()})
    team_one_df.rename(columns = {"index" : "Player"}, inplace = True)
    team_two_df.rename(columns = {"index" : "Player"}, inplace = True)
    player_elos.rename(columns = {"index" : "Player"}, inplace = True)
    cols_order= ["Player", "Kills", "Assists", "Deaths", "Headshots", "Headshots %", "K/D Ratio", "K/R Ratio", "MVPs", "Triple Kills", "Quadro Kills", "Penta Kills", "Result"]
    team_one_df = team_one_df[cols_order]
    team_two_df = team_two_df[cols_order]

    return [
        html.H3(f"Team One - Average Elo : {round(current_match.team_one_elo)}"),
        dash_table.DataTable(
            id='team-one-scoreboard',
            columns=[{"name": i, "id": i} for i in team_one_df.columns],
            data=team_one_df.to_dict('records'),
            sort_action = "native",
            sort_mode = "single",
            **data_table_non_editable_kwargs
        ),
        html.Br(),
        html.Br(),
        html.H3(f"Team Two - Average Elo : {round(current_match.team_two_elo)}"),
        dash_table.DataTable(
            id='team-two-scoreboard',
            columns=[{"name": i, "id": i} for i in team_two_df.columns],
            data=team_two_df.to_dict('records'),
            sort_action = "native",
            sort_mode = "single",
            **data_table_non_editable_kwargs
        ),
        html.Br(),
        dash_table.DataTable(
            id = "chosen-match-faceit-link",
            columns=[{"name": i, "id": i} for i in player_elos.columns],
            data = player_elos.to_dict("records"),
            sort_action = "native",
            sort_mode = "single",
            **data_table_non_editable_kwargs
        ),
        html.Br(),
        dcc.Markdown(f'''
            [Faceit Room](https://www.faceit.com/en/csgo/room/{chosen_match}/scoreboard)
        ''')
    ]
   


@callback(Output(component_id='linear-regression-table', component_property= 'children'),
            [Input(component_id='player_name_dropdown', component_property= 'value'),
            Input(component_id='stat_name_dropdown', component_property= 'value'),
            Input(component_id="n_recent_matches", component_property="value"),
            Input("player-dict", "data")])
def linear_regression(player_name_dropdown, stat_name_dropdown, n_recent_matches, player_dict, per_round = False):
    player_dict = jsonpickle.decode(json.loads(player_dict))
    per_round = True
    d = {player : player_dict[player].linear_regression(stat_name_dropdown, n_recent_matches, per_round).round(2) for player in player_name_dropdown}
    if per_round:
        stat_name_dropdown += " Per Round"
    stat_name_dropdown = "Linear Regression " + stat_name_dropdown
    data = [{"Player" : key, stat_name_dropdown : d[key]} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash_table.DataTable(
        id = "table-output", 
        columns = columns, 
        data = data,
        **data_table_non_editable_kwargs
        )

@callback(Output(component_id='elo-div', component_property= 'children'),
            [Input(component_id='player-name-dropdown', component_property= 'value'),
            Input("player-dict", "data")])
def elo_table(player_name_dropdown, player_dict):
    player_dict = jsonpickle.decode(json.loads(player_dict))
    d = {player : player_dict[player].elo for player in player_name_dropdown}
    data = [{"Player" : player_dict[key].name, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
        )

@callback(Output(component_id='match-explorer-h3', component_property= 'children'),
            [Input(component_id='player-filter', component_property='value'),
    Input("match-dict", "data"),
    Input("match-list", "data"),])
def match_explorer_h3_func(player_filter, match_dict, match_list):
    match_dict = jsonpickle.decode(json.loads(match_dict))
    match_list = jsonpickle.decode(json.loads(match_list))
    if player_filter == "All":
        return [
            html.H3(f"Match Explorer: {len(match_list)} matches found")
        ]
    ops = []
    for x in match_list:
        try:
            if player_filter in match_dict[x].players:
                ops.append({"label" : x, "value" : x})
        except KeyError:
            pass

    return [
        html.H3(f"Match Explorer: {len(ops)} matches found")
    ]

@callback(Output(component_id='match-create', component_property='children'),
            [Input(component_id = 'elo-filter', component_property='value'),
            Input("player-dict", "data")])
def match_create(players, player_dict):
    player_dict = jsonpickle.decode(json.loads(player_dict))
    player_data = [player_dict[player] for player in players]
    df = Elo.even_match(player_data)
    data = df.to_dict('records')
    columns=[{"name": i, "id": i} for i in df.columns]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns, 
        data = data
    )    

@callback(
    Output("download-output", "data"),
    Input("download-button", "n_clicks"),
    State("player-dict", "data"),
    State("match-dict", "data"),
    State("match-list", "data"),
    prevent_initial_call=True,
)
def download_func(n_clicks, player_dict, match_dict, match_list):

    ctx = dash.callback_context
    if ctx.triggered[0]["prop_id"] != "download-button.n_clicks":
        print("Fetch Cancelled")
        raise dash.exceptions.PreventUpdate

    player_dict = jsonpickle.decode(json.loads(player_dict))
    match_dict = jsonpickle.decode(json.loads(match_dict))
    match_list = jsonpickle.decode(json.loads(match_list))

    data = [player_dict, match_dict, match_list]
    matchlistpickle.pickle_write("dashboard_data", data)
    return dcc.send_file(
        "./dashboard_data"
    )

def fetch_func(hub_id):

    logging.debug("Fetching")

    hub = HubMatches(hub_id, api_key)
    player_dict = {}
    match_dict = {}
    match_list = hub.full_match_loop(offset, actual_limit, player_dict, match_dict)
    player_name_lookup = {player.name : player.player_id for player in player_dict.values()}
    # default_player = list(player_dict.keys())[0]
    print("Fetch Finished")
    return (
        f"Found {len(match_list)} matches",
        json.dumps(jsonpickle.encode(player_dict)),
        json.dumps(jsonpickle.encode(match_dict)),
        json.dumps(jsonpickle.encode(match_list)),
        json.dumps(jsonpickle.encode(player_name_lookup))
    )

def update_func(ctx, hub_id, player_dict, match_dict, match_list):


    
    logging.debug("Updating!")
    print(f"{hub_id}")

    player_dict = jsonpickle.decode(json.loads(player_dict))
    match_dict = jsonpickle.decode(json.loads(match_dict))
    match_list = jsonpickle.decode(json.loads(match_list))

    print("Data loaded")

    hub = HubMatches(hub_id, api_key)
    old_match_list = match_list.copy()
    match_list = hub.partial_match_loop(offset, actual_limit, player_dict, match_dict, old_match_list)
    player_name_lookup = {player.name : player.player_id for player in player_dict.values()}
    # default_player = list(player_dict.keys())[0]
    print("Update finished")
    
    return (
        f"Found {len(match_list) - len(old_match_list)} new matches",
        json.dumps(jsonpickle.encode(player_dict)),
        json.dumps(jsonpickle.encode(match_dict)),
        json.dumps(jsonpickle.encode(match_list)),
        json.dumps(jsonpickle.encode(player_name_lookup))
    )


def upload_func(data):
    print("Uploading")

    content_type, content_string = data.split(',')
    decoded = base64.b64decode(content_string)
    # df = pd.read_pickle(io.BytesIO(decoded))

    data = pickle.load(io.BytesIO(decoded))

    player_dict = data[0]
    match_dict = data[1]
    match_list = data[2]
    player_name_lookup = {player.name : player.player_id for player in player_dict.values()}
    # default_player = sorted(list(player_dict.keys()))[0]

    return (
        f"Upload contains {len(match_list)} matches",
        json.dumps(jsonpickle.encode(player_dict)),
        json.dumps(jsonpickle.encode(match_dict)),
        json.dumps(jsonpickle.encode(match_list)),
        json.dumps(jsonpickle.encode(player_name_lookup))
    )

# @callback(
#     Output("data-retrieve-msg", "children"),
#     Output("player-dict", "data"),
#     Output("match-dict", "data"),
#     Output("match-list", "data"),
#     Output("player-name-lookup", "data"),
#     Input("fetch-button", "n_clicks"),
#     Input("update-button", "n_clicks"),
#     Input("data-upload-button", "n_clicks"),
#     Input("hub-id", "value"),
#     Input("player-dict", "data"),
#     Input("match-dict", "data"),
#     Input("match-list", "data"),
#     Input("data-upload", "contents"),
#     prevent_initial_call=True,
# )
# def data_master_function(fetch_clicks, update_clicks, upload_clicks, hub_id, player_dict, match_dict, match_list, uploaded_data):
#     ctx = dash.callback_context
#     if ctx.triggered[0]["value"] is None:
#         raise dash.exceptions.PreventUpdate
#     elif ctx.triggered[0]["prop_id"] == "fetch-button.n_clicks":
#         msg, player_dict, match_dict, match_list, player_name_lookup = fetch_func(hub_id)
#     elif ctx.triggered[0]["prop_id"] == "update-button.n_clicks":
#         msg, player_dict, match_dict, match_list, player_name_lookup = update_func(hub_id, player_dict, match_dict, match_list)
#     elif ctx.triggered[0]["prop_id"] == "data-upload.contents":
#         print("Master upload")
#         msg, player_dict, match_dict, match_list, player_name_lookup = upload_func(uploaded_data)
#     else:
#         raise dash.exceptions.PreventUpdate
#     return msg, player_dict, match_dict, match_list, player_name_lookup

# @callback(
#     Output("submitted-store", "data"),
#     [Input("button", "n_clicks")],
#     [State("text", "value")],
# )
@callback(
    Output("submitted-store", "data"),
    Input("fetch-button", "n_clicks"),
    Input("update-button", "n_clicks"),
    Input("data-upload-button", "n_clicks"),
    Input("hub-id", "value"),
    Input("player-dict", "data"),
    Input("match-dict", "data"),
    Input("match-list", "data"),
    Input("data-upload", "contents"),
    prevent_initial_call=True,
)
def submit(fetch_clicks, update_clicks, upload_clicks, hub_id, player_dict, match_dict, match_list, uploaded_data):
    """
    Submit a job to the queue, log the id in submitted-store
    """
    print("Submit called")
    ctx = dash.callback_context

    id_ = str(uuid.uuid4())

    # queue the task
    if ctx.triggered[0]["value"] is None:
        raise dash.exceptions.PreventUpdate
    elif ctx.triggered[0]["prop_id"] == "fetch-button.n_clicks":
        if ctx.triggered[0]["prop_id"] != "fetch-button.n_clicks":
            logging.debug("Fetch Cancelled")
            raise dash.exceptions.PreventUpdate
        q.enqueue(fetch_func, hub_id, job_id = id_, job_timeout = 600)
    elif ctx.triggered[0]["prop_id"] == "update-button.n_clicks":
        if ctx.triggered[0]["prop_id"] != "update-button.n_clicks":
            raise dash.exceptions.PreventUpdate
        q.enqueue(update_func, hub_id, player_dict, match_dict, match_list, job_id = id_)
    elif ctx.triggered[0]["prop_id"] == "data-upload.contents":
        print("Master upload")
        q.enqueue(upload_func, uploaded_data, job_id = id_)
    else:
        return {}
        raise dash.exceptions.PreventUpdate

    # log process id in dcc.Store
    return {"id": id_}

"msg", "player_dict", "match_dict", "match_list", "player_name_lookup"
@callback(
    Output("data-retrieve-msg", "children"),
    Output("player-dict", "data"),
    Output("match-dict", "data"),
    Output("match-list", "data"),
    Output("player-name-lookup", "data"),
    # Output("progress", "value"),
    # Output("collapse", "is_open"),
    Output("finished-store", "data"),
    Input("interval", "n_intervals"),
    State("submitted-store", "data"),
)
def retrieve_output(n, submitted):
    """
    Periodically check the most recently submitted job to see if it has
    completed.
    """
    if n and submitted:
        try:
            job = Job.fetch(submitted["id"], connection=conn)
            if job.get_status() == "finished":
                # job is finished, return result, and store id
                msg = job.result[0]
                player_dict = job.result[1]
                match_dict = job.result[2]
                match_list = job.result[3]
                player_name_lookup = job.result[4]
                return (
                    msg,
                    player_dict,
                    match_dict,
                    match_list,
                    player_name_lookup,
                    {"id": submitted["id"]},
                )

            # job is still running, get progress and update progress bar
            print(submitted)
            return (
                "In progress",
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                )
        except NoSuchJobError:
            # something went wrong, display a simple error message
            return (
                "Error: result not found...",
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
            )
    # nothing submitted yet, return nothing.
    return (
        "Nothing submitted",
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        {},
    )


@callback(
    Output("interval", "disabled"),
    [Input("submitted-store", "data"), Input("finished-store", "data")],
)
def disable_interval(submitted, finished):
    print(finished)
    if submitted:
        if finished and submitted["id"] == finished["id"]:
            # most recently submitted job has finished, no need for interval
            return True
        # most recent job has not yet finished, keep interval going
        return False
    # no jobs submitted yet, disable interval
    return True