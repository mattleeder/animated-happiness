from turtle import st
from dash import Input, Output, State, callback, clientside_callback, dash_table, dcc, html, ClientsideFunction
import dash_bootstrap_components as dbc
import dash
import base64
import pandas as pd
import plotly.express as px
from elo import Elo
import io
import os
from hubmatches import HubMatches
from player import Player

import json
from dotenv import load_dotenv

from rq import Queue, get_current_job
from rq.job import Job
from rq.exceptions import NoSuchJobError
from worker import conn
import uuid

import logging

from match import Match

logging.basicConfig(level = logging.DEBUG)

q = Queue(connection=conn)

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
    "css" : [{"selector": "tr:hover", "rule": 'background-color: grey;'}],
    'cell_selectable' : False,
    'row_selectable' : False,
    'column_selectable' : False,
    'editable' : False
}

def average_actual_rating(match_dict):
    actuals = []
    for match in match_dict:
        for player in match_dict[match]["player_elo_data"]:
            actuals.append(match_dict[match]["player_elo_data"][player]["Performance Actual"])
    return sum(actuals) / len(actuals)

@callback(
	Output("navbar", "children"),
    Input("match-dict", "data"),
    Input("match-list", "data")
)
def render_navbar(match_dict, match_list):

    if match_dict is not None:

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
                dbc.NavItem(dbc.NavLink("Stats Explorer", href="/stats", active='exact')),
                dbc.NavItem(dbc.NavLink("Match Explorer", href="/match-explorer", active='exact')),
                dbc.NavItem(dbc.NavLink("Current Elo", href="/current-elo", active='exact')),
                dbc.NavItem(dbc.NavLink("Match Create", href="/match-create", active='exact')),
                dbc.NavItem(dbc.NavLink("Elo Hi-Scores", href="/elo-hi-scores", active='exact')),
                dbc.NavItem(dbc.NavLink("Get Data", href="/data", active='exact')),
            ],
            brand=f"CSGO Dashboard - Number of matches: {len(match_list)}, average rating: {avg_rating}",
            brand_href="",
            color="primary",
            dark=True,
        )
    ]

@callback(
    Output('player-name-dropdown', 'options'),
    Input('player-name-lookup', 'data')
)
def player_dropdown_options_stat_page(player_name_lookup):
    return [{"label" : x, "value" : player_name_lookup[x]} for x in sorted(player_name_lookup.keys())]

# clientside_callback(
#     ClientsideFunction(
#         namespace = "clientside",
#         function_name = "player_dropdown_options_stat_page"
#     ),
#     Output('player-name-dropdown', 'options'),
#     Input('player-name-lookup', 'data')
# )

clientside_callback(
    ClientsideFunction(
        namespace = "clientside",
        function_name = "get_elo_data"
    ),
    Output('elo-data', 'data'),
    Input('player-dict', 'data')
)

@callback(
    Output('player-filter', 'options'),
    Input('player-name-lookup', 'data')
)
def player_dropdown_options_match_page(player_name_lookup):
    options = [{"label" : "All", "value" : "All"}]
    options += [{"label" : x, "value" : player_name_lookup[x]} for x in sorted(player_name_lookup.keys())]
    return options

@callback(
    Output('elo-filter', 'options'),
    Input('player-name-lookup', 'data')
)
def player_dropdown_options_match_page(player_name_lookup):
    return [{"label" : x, "value" : player_name_lookup[x]} for x in sorted(player_name_lookup.keys())]

@callback(
    Output("full-elo-table", "children"),
    Input("elo-data", "data")
)
def full_elo_table(data):

    df = pd.DataFrame(data)
    df["Rank"] = df["Current Elo"].rank(ascending = False, method = "first")
    df["Current Elo"] = df["Current Elo"].round()
    df = df.sort_values(by = "Rank", ascending = True)
    columns = [{"name" : "Rank", "id" : "Rank"}, {"name" : "Current Elo", "id" : "Current Elo"}, {"name" : "Player", "id" : "Player"}]


    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = df[["Rank", "Player", "Current Elo"]].to_dict("records"),
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

@callback(
    Output("elo-hiscores-table", "children"),
    Input("elo-data", "data")
)
def elo_hiscores(data):

    df = pd.DataFrame(data)[["Player", "Max Elo"]]
    df["Rank"] = df["Max Elo"].rank(ascending = False, method = "first")
    df["Max Elo"] = df["Max Elo"].round()
    df = df.sort_values(by = "Rank", ascending = True)
    columns = [{"name" : "Rank", "id" : "Rank"}, {"name" : "Max Elo", "id" : "Max Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = df[["Rank", "Player", "Max Elo"]].to_dict("records"),
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

clientside_callback(
    ClientsideFunction(
        namespace = "clientside",
        function_name = "get_player_stat_data"
    ),
    Output('stat-data', 'data'),
    Input('player-name-dropdown', 'value'),
    Input('stat-name-dropdown', 'value'),
    Input("n-recent-matches", "value"),
    Input("player-dict", "data")
)

@callback(
    Output('scatter', 'figure'),
    Input('stat-data', 'data'),
    Input('stat-name-dropdown', 'value'),
)
def player_stat_graph(data, stat_name_dropdown):
    df = pd.DataFrame(data)

    fig = px.line(df,x = "Match Number", y = stat_name_dropdown, color = "Player")
        
    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor= 'rgba(0, 0, 0, 0)',
        paper_bgcolor= 'rgba(0, 0, 0, 0)'
    )

    return fig

@callback(
    Output('stat-table', 'children'),
    Input('stat-data', 'data'),
    Input('stat-name-dropdown', 'value'),
)
def stat_order_grid(data, stat_name_dropdown):

    df = pd.DataFrame(data)
    table_data = df.groupby("Player").mean().reset_index()[["Player", stat_name_dropdown]]
    df = df.sort_values(by = stat_name_dropdown)
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return [
        dash_table.DataTable(
        id = "player-stat-table", 
        columns = columns, 
        data = table_data.to_dict('records'),
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
        )
    ]

clientside_callback(
    ClientsideFunction(
        namespace = "clientside",
        function_name = "get_match_choices"
    ),
    Output('match-choices', 'options'),
    Output("match-choices", "value"),
    Input('player-filter', 'value'),
    Input("match-dict", "data"),
    Input("match-list", "data")
)

clientside_callback(
    ClientsideFunction(
        namespace = "clientside",
        function_name = "get_chosen_match_data"
    ),
    Output("chosen-match-data", "data"),
    Input('match-choices', 'value'),
    Input("match-dict", "data")
)

import time

@callback(
    Output('scoreboard-container', 'children'),
    Input('chosen-match-data', 'data'),
    Input("player-dict", "data")
)
def display_scoreboard(match_data, player_dict):
    start = time.perf_counter()

    chosen_match = match_data[0]
    current_match = match_data[1]
    if current_match is None:
        return [
            html.H3("Error, match not found")
        ]

    post_get = time.perf_counter()

    mapper = {player_id : player_data["name"] for player_id, player_data in player_dict.items()}

    post_map = time.perf_counter()

    team_one_data, team_two_data = Match.scoreboard_data(current_match)
    team_one_df = pd.DataFrame(team_one_data).T.reset_index()
    team_two_df = pd.DataFrame(team_two_data).T.reset_index()
    team_one_df["index"] = team_one_df["index"].map(mapper)
    team_two_df["index"] = team_two_df["index"].map(mapper)
    team_one_df = team_one_df.rename(columns = {"index" : "Player"})
    team_two_df = team_two_df.rename(columns = {"index" : "Player"})
    cols_order= ["Player", "Kills", "Assists", "Deaths", "Headshots", "Headshots %", "K/D Ratio", "K/R Ratio", "MVPs", "Triple Kills", "Quadro Kills", "Penta Kills", "Result"]
    team_one_df = team_one_df[cols_order]
    team_two_df = team_two_df[cols_order]

    player_elos = pd.DataFrame.from_dict(current_match["player_elo_data"]).T.reset_index()
    player_elos = player_elos.round({'Elo': 0, 'Elo Change': 1, "Performance Target" : 2, "Performance Actual" : 2})
    player_elos["index"] = player_elos["index"].map(mapper)
    player_elos = player_elos.rename(columns = {"index" : "Player"})

    pre_return = time.perf_counter()

    logging.debug(f"TIMER: display_scoreboard, get runtime {post_get - start:0.4f}s, map runtime {post_map - post_get:0.4f}s, calcs runtime {pre_return - post_map:0.4f}s")

    return [
        html.H3(f"Team One - Average Elo : {round(current_match['team_one_elo'])}"),
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
        html.H3(f"Team Two - Average Elo : {round(current_match['team_two_elo'])}"),
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
   


@callback(
    Output('linear-regression-table', 'children'),
    Input('player_name_dropdown', 'value'),
    Input('stat_name_dropdown', 'value'),
    Input("n_recent_matches", "value"),
    Input("player-dict", "data")
)
def linear_regression(player_name_dropdown, stat_name_dropdown, n_recent_matches, player_dict, per_round = False):

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

@callback(
    Output('elo-div', 'children'),
    Input('stat-data', 'data'),
)
def elo_table(data):
    df = pd.DataFrame(data)
    table_data = df.groupby("Player").max().reset_index()[["Player", "Elo"]]
    df = df.sort_values(by = "Elo")
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = table_data.to_dict('records'),
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
        )

@callback(
    Output('match-explorer-h3', 'children'),
    Input('player-filter', 'value'),
    Input("match-dict", "data"),
    Input("match-list", "data")
)
def match_explorer_h3_func(player_filter, match_dict, match_list):
    if player_filter == "All":
        return [
            html.H3(f"Match Explorer: {len(match_list)} matches found")
        ]
    ops = []
    for x in match_list:
        try:
            if player_filter in match_dict[x]["players"]:
                ops.append({"label" : x, "value" : x})
        except KeyError:
            pass

    return [
        html.H3(f"Match Explorer: {len(ops)} matches found")
    ]

@callback(
    Output('match-create', 'children'),
    Input('elo-filter', 'value'),
    Input("player-dict", "data")
)
def match_create(players, player_dict):
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

    data = {
        "player_dict" : player_dict,
        "match_dict" : match_dict,
        "match_list" : match_list
    }
    with open("dashboard_data.json", "w") as f:
        json.dump(data, f, indent = 4)
    return dcc.send_file(
        "./dashboard_data.json"
    )

def fetch_func(hub_id):

    logging.debug("Fetching")

    hub = HubMatches(hub_id)
    match_list = hub.full_match_loop(offset, actual_limit)
    player_name_lookup = {hub.player_json[player]["name"] : player for player in hub.player_json}
    logging.debug("Fetch Finished")

    return (
        f"Found {len(match_list)} matches",
        hub.player_json,
        hub.match_json,
        match_list,
        player_name_lookup
    )

def update_func(hub_id, player_json, match_json, match_list):

    logging.debug("Updating!")
    print(f"{hub_id}")

    print("Data loaded")

    hub = HubMatches(hub_id, player_json, match_json)
    old_match_list = match_list.copy()
    match_list = hub.partial_match_loop(offset, actual_limit, old_match_list)
    player_name_lookup = {hub.player_json[player]["name"] : player for player in hub.player_json}
    print("Update finished")
    
    return (
        f"Found {len(match_list) - len(old_match_list)} new matches",
        hub.player_json,
        hub.match_json,
        match_list,
        player_name_lookup
    )


def upload_func(data):
    logging.debug("Uploading")
    
    job = get_current_job()
    job.meta["progress"] = "Starting Upload"
    job.save_meta()
    content_type, content_string = data.split(',')
    decoded = base64.b64decode(content_string)
    data = json.loads(decoded)
    
    job.meta["progress"] = "Data decoded"
    job.save_meta()

    player_json = data["player_dict"]
    match_dict = data["match_dict"]
    match_list = data["match_list"]
    player_name_lookup = {player_json[player]["name"] : player for player in player_json}
    job.meta["progress"] = f"Assignment completed, {len(match_list)} matches found"
    logging.debug(f"Upload contains {len(match_list)} matches")

    return (
        f"Upload contains {len(match_list)} matches",
        player_json,
        match_dict,
        match_list,
        player_name_lookup
    )

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
def submit(fetch_clicks, update_clicks, upload_clicks, hub_id, player_json, match_json, match_list, uploaded_data):
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
        # log process id in dcc.Store
        return {"id": id_}
    elif ctx.triggered[0]["prop_id"] == "update-button.n_clicks":
        if ctx.triggered[0]["prop_id"] != "update-button.n_clicks":
            raise dash.exceptions.PreventUpdate
        q.enqueue(update_func, hub_id, player_json, match_json, match_list, job_id = id_)
        # log process id in dcc.Store
        return {"id": id_}
    elif ctx.triggered[0]["prop_id"] == "data-upload.contents":
        print("Master upload")
        q.enqueue(upload_func, uploaded_data, job_id = id_)
        # log process id in dcc.Store
        return {"id": id_}
    raise dash.exceptions.PreventUpdate

    # log process id in dcc.Store

@callback(
    Output("data-retrieve-msg", "children"),
    Output("player-dict", "data"),
    Output("match-dict", "data"),
    Output("match-list", "data"),
    Output("player-name-lookup", "data"),
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
            logging.debug(f"Job status: {job.get_status()}")
            if job.get_status() == "finished":
                # job is finished, return result, and store id
                logging.debug("Attempting to retrieve job results")
                msg = job.result[0]
                player_json = job.result[1]
                match_json = job.result[2]
                match_list = job.result[3]
                player_name_lookup = job.result[4]

                return (
                    msg,
                    player_json,
                    #json.dumps(player_json, check_circular=False),
                    match_json,
                    match_list,
                    player_name_lookup,
                    {"id": submitted["id"]},
                )

            # job is still running, get progress and update progress bar
            progress = job.meta.get("progress", 0)
            length = job.meta.get("length", 0)
            return (
                f"In progress: {progress} matches out of {length}, job status {job.get_status()}, last_hearbeat {job.last_heartbeat}",
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
    Input("submitted-store", "data"), 
    Input("finished-store", "data")
)
def disable_interval(submitted, finished):
    logging.debug(f"Disabled finished: {finished}")
    if submitted:
        if finished and submitted["id"] == finished["id"]:
            # most recently submitted job has finished, no need for interval
            return True
        # most recent job has not yet finished, keep interval going
        return False
    # no jobs submitted yet, disable interval
    return True