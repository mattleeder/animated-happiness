from player import Player
import cmdargparse
from elo import Elo

import pandas as pd

import dash
from dash import html
from dash import dcc
import plotly.graph_objects as go
import plotly.express as px
from dash.dependencies import Input, Output

app = dash.Dash(__name__, title = "CSGO Dashboard", update_title="Loading...")
player_dict, match_list, match_dict, default_player = cmdargparse.main()
colours = {
    "background" : "#111111",
    "text" : "#7FDBFF"
}

@app.callback(Output(component_id='scatter', component_property= 'figure'),
        [Input(component_id='player_name_dropdown', component_property= 'value'),
        Input(component_id='stat_name_dropdown', component_property= 'value'),
        Input(component_id="n_recent_matches", component_property="value")])
def graph_update(player_name_dropdown, stat_name_dropdown, n_recent_matches):

    n = n_recent_matches

    data = {}
    data["Player"] = []
    data["Match Number"] = []
    data[stat_name_dropdown] = []

    for player in player_name_dropdown:

        matches = min(n, len(player_dict[player].stats["Match ID"]))
        data["Player"].extend([player] * matches)
        data["Match Number"].extend(list(range(n - matches, n)))

        stat_list = player_dict[player].stats[stat_name_dropdown][-n:]
        data[stat_name_dropdown].extend(stat_list)

    df = pd.DataFrame(data)

    fig = px.line(df,x = "Match Number", y = stat_name_dropdown, color = "Player")
        
    fig.update_layout(
        plot_bgcolor = colours["background"],
        paper_bgcolor = colours["background"],
        font_color = colours["text"]
    )

    return fig

def average_actual_rating():
    actuals = []
    for match in match_dict:
        for player in match_dict[match].player_elo_data.keys():
            actuals.append(match_dict[match].player_elo_data[player]["Performance Actual"])
    return sum(actuals) / len(actuals)

    


@app.callback(Output(component_id='div2', component_property= 'children'),
            [Input(component_id='player_name_dropdown', component_property= 'value'),
            Input(component_id='stat_name_dropdown', component_property= 'value'),
            Input(component_id="n_recent_matches", component_property="value")])
def stat_order_grid(player_name_dropdown, stat_name_dropdown, n_recent_matches, denominator_stat = None):
    
    d = Player.order_players_by_stat(player_dict, player_name_dropdown, n_recent_matches, stat_name_dropdown, denominator_stat)
    data = [{stat_name_dropdown : round(key,2), "Player" : d[key]} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)

@app.callback(Output(component_id='match-selector', component_property= 'children'),
            [Input(component_id='player_filter', component_property='value')])
def match_selector(player_filter):
    if player_filter == "All":
        return html.Div([dcc.Dropdown(id = "match_selector",
                                    options = [{"label" : x, "value" : x} for x in match_list],
                                    multi = False,
                                    value = match_list[0])
                                    ])

    # ops = [{"label" : x, "value" : x} for x in match_list if player_filter in match_dict[x].players]
    ops = []
    for x in match_list:
        match = match_dict.get(x, None)
        if match is not None:
            if player_filter in match_dict[x].players:
                ops.append({"label" : x, "value" : x})

    return html.Div([dcc.Dropdown(id = "match_selector",
                                options = ops,
                                multi = False,
                                value = ops[0]["value"])
                                ])

@app.callback(Output(component_id='scoreboard-container', component_property= 'children'),
            [Input(component_id='match_selector', component_property= 'value')])
def display_scoreboard(match_selector):

    current_match = match_dict[match_selector]    
    team_one_data, team_two_data = current_match.scoreboard_data()
    player_elos = pd.DataFrame.from_dict(current_match.player_elo_data).T.reset_index()
    player_elos = player_elos.round({'Elo': 0, 'Elo Change': 1, "Performance Target" : 2, "Performance Actual" : 2})
    team_one_df = pd.DataFrame(team_one_data).T.reset_index()
    team_two_df = pd.DataFrame(team_two_data).T.reset_index()
    team_one_df.rename(columns = {"index" : "Player"}, inplace = True)
    team_two_df.rename(columns = {"index" : "Player"}, inplace = True)
    player_elos.rename(columns = {"index" : "Player"}, inplace = True)
    cols_order= ["Player", "Kills", "Assists", "Deaths", "Headshots", "Headshots %", "K/D Ratio", "K/R Ratio", "MVPs", "Triple Kills", "Quadro Kills", "Penta Kills", "Result"]
    team_one_df = team_one_df[cols_order]
    team_two_df = team_two_df[cols_order]

    return html.Div([html.H3(f"Team One - Average Elo : {round(current_match.team_one_elo)}"),
                   dash.dash_table.DataTable(
                                    id='table',
                                    columns=[{"name": i, "id": i} for i in team_one_df.columns],
                                    data=team_one_df.to_dict('records'),
                                    sort_action = "native",
                                    sort_mode = "single",
                                    sort_by = ["Kills"]
                                ),
                    html.H3(f"Team Two - Average Elo : {round(current_match.team_two_elo)}"),
                    dash.dash_table.DataTable(
                                    id='table',
                                    columns=[{"name": i, "id": i} for i in team_two_df.columns],
                                    data=team_two_df.to_dict('records'),
                                    sort_action = "native",
                                    sort_mode = "single",
                                    sort_by = ["Kills"]
                                ),
                    html.H6(f"https://www.faceit.com/en/csgo/room/{match_selector}/scoreboard"),
                    dash.dash_table.DataTable(
                                    id = "table",
                                    columns=[{"name": i, "id": i} for i in player_elos.columns],
                                    data = player_elos.to_dict("records"),
                                    sort_action = "native",
                                    sort_mode = "single",
                                    sort_by = ["Elo"]
                    )
                                ])


    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)

    # data = [{stat_name_dropdown : round(key,2), "Player" : d[key]} for key in sorted(d.keys(), reverse = True)]
    # columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

   


@app.callback(Output(component_id='div3', component_property= 'children'),
            [Input(component_id='player_name_dropdown', component_property= 'value'),
            Input(component_id='stat_name_dropdown', component_property= 'value'),
            Input(component_id="n_recent_matches", component_property="value")])
def linear_regression(player_name_dropdown, stat_name_dropdown, n_recent_matches, per_round = False):
    per_round = True
    d = {player : player_dict[player].linear_regression(stat_name_dropdown, n_recent_matches, per_round).round(2) for player in player_name_dropdown}
    if per_round:
        stat_name_dropdown += " Per Round"
    stat_name_dropdown = "Linear Regression " + stat_name_dropdown
    data = [{"Player" : key, stat_name_dropdown : d[key]} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)

@app.callback(Output(component_id='elo-div', component_property= 'children'),
            [Input(component_id='player_name_dropdown', component_property= 'value')])
def elo_table(player_name_dropdown):
    d = {player : player_dict[player].elo for player in player_name_dropdown}
    data = [{"Player" : key, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(id = "table-output",
                                    columns = columns,
                                    data = data,
                                    sort_action = "native",
                                    sort_mode = "single")

def full_elo_table():

    d = {player : player_dict[player].elo for player in player_dict}
    data = [{"Player" : key, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(id = "table-output",
                                    columns = columns,
                                    data = data,
                                    sort_action = "native",
                                    sort_mode = "single")

@app.callback(Output(component_id='match-explorer-h3', component_property= 'children'),
            [Input(component_id='player_filter', component_property='value')])
def match_explorer_h3_func(player_filter):

    if player_filter == "All":
        return html.Div([html.H3(f"Match Explorer: {len(match_list)} matches found")])
    ops = []
    for x in match_list:
        try:
            if player_filter in match_dict[x].players:
                ops.append({"label" : x, "value" : x})
        except KeyError:
            pass


    return html.Div([html.H3(f"Match Explorer: {len(ops)} matches found")])

@app.callback(Output(component_id='match-create', component_property='children'),
            [Input(component_id = 'elo-filter', component_property='value')])
def match_create(players):
    player_data = [player_dict[player] for player in players]
    df = Elo.even_match(player_data)
    data = df.to_dict('records')
    columns=[{"name": i, "id": i} for i in df.columns]

    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)    



@app.callback(Output('tabs-content', 'children'),
              Input('tab-selector', 'value'))
def render_content(tab):
    if tab == 'homepage':
        return html.Div(id = "parent", style = {"backgroundColor" : colours["background"]}, className = "stylesheet--eight columns",
                        children = [html.Div([
                                            html.Div([html.H2()]),
                                            html.Div([
                                                    dcc.Dropdown(id = 'player_name_dropdown', 
                                                                options = [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                                                multi = True,
                                                                value = [default_player]
                                                                )],
                                                    style={"backgroundColor" : colours["background"]},
                                                    className = "stylesheet--eight columns"
                                                    ),
                                            html.Div([
                                                    dcc.Dropdown(id = "stat_name_dropdown", 
                                                                options = [{"label" : x, "value" : x} for x in sorted(Player("").stats.keys())],
                                                                multi = False,
                                                                value = "Kills"
                                                                )],
                                                    style={"backgroundColor" : colours["background"]},
                                                    className = "stylesheet--eight columns"
                                                    ),
                                            html.Div([
                                                    dcc.Graph(id = 'scatter')],
                                                    className = "stylesheet--eight columns"
                                                    ),
                                            html.Div([
                                                    dcc.Slider(id = "n_recent_matches",
                                                            min=1,
                                                            max = 20,
                                                            marks={i : f"{i}" for i in range(1, 21)},
                                                            value=10
                                                            )],
                                                    className = "stylesheet--eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    ),
                                            html.Div(id = "div2", children = [
                                                    dash.dash_table.DataTable(id='ordered_stat_table')
                                                    ],
                                                    className = "stylesheet--eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    ),
                                            html.Div(id = "div3", children = [
                                                    dash.dash_table.DataTable(id='regression_table')
                                                    ],
                                                    className = "stylesheet--eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    ),
                                            html.Div(id = "elo-div", children = [
                                                    dash.dash_table.DataTable(id='elo-table')
                                                    ],
                                                    className = "stylesheet--eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    )
                                    ])
                                ]
                )

    elif tab == 'match_explorer':
        return html.Div(id = "match-explorer-main", children = [
                        html.Div(id = 'match-explorer-h3', children = [
                                ]),
                        html.H3("TESTING"),
                        html.Div([dcc.Dropdown(id = "player_filter",
                                            options = [{"label" : "All", "value" : "All"}] + [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                            multi = False,
                                            value = "All")
                                            ]),
                        html.Div(id = 'match-selector', children = [
                                ]),

                        html.Div(id = "scoreboard-container", children = [
                                # dash.dash_table.DataTable(id = "scoreboard")
                                ])
        ])
    
    elif tab == 'elo-tab':
        return html.Div(id = 'elo-tab-main', children = [
            html.H3("Elo"),
            html.Div(id = 'elo-table-container', children = full_elo_table())
        ])

    elif tab == 'match-create':
        return html.Div(id = 'match-create-main', children = [
                                                            html.Div([dcc.Dropdown(id = "elo-filter",
                                                                                options = [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                                                                multi = True)
                                                                                ]),
                                                            html.Div(id = 'match-create')
        ])


def main():
    
    # app.css.append_css({'external_url': '/assets/stylesheet.css'})
    # app.server.static_folder = 'static'  # if you run app.py from 'root-dir-name' you don't need to specify

    app.layout = html.Div([
        html.Div([
            html.H1(f"CSGO Dashboard - Number of matches: {len(match_list)}, average rating: {average_actual_rating()}", className = "banner")
        ]),
        html.Div([
            html.Div([], className = "stylesheet--four columns"),
            html.Div([
                dcc.Tabs(id="tab-selector", value='homepage', children=[
                    dcc.Tab(label='Homepage', value='homepage'),
                    dcc.Tab(label='Match Explorer', value='match_explorer'),
                    dcc.Tab(label='Elo', value='elo-tab'),
                    dcc.Tab(label='Match Create', value='match-create')
                ])
            ], className = "stylesheet--eight columns"),
            html.Div([], className = "stylesheet--two columns")
        ]),
        html.Div(id='tabs-content')
    ])

    return app

if __name__ == "__main__":
    main()