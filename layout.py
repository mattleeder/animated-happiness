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
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, title = "CSGO Dashboard", update_title="Loading...")
player_dict, match_list, match_dict, default_player = cmdargparse.main()
colours = {
    "background" : "#272b30",
    "text" : "#FFFFFF"
}

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

@app.callback(Output(component_id='scatter', component_property= 'figure'),
        [Input(component_id='player-name-dropdown', component_property= 'value'),
        Input(component_id='stat-name-dropdown', component_property= 'value'),
        Input(component_id="n-recent-matches", component_property="value")])
def player_stat_graph(player_name_dropdown, stat_name_dropdown, n_recent_matches):

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
        template='plotly_dark',
        plot_bgcolor= 'rgba(0, 0, 0, 0)',
        paper_bgcolor= 'rgba(0, 0, 0, 0)'
    )

    return fig

def average_actual_rating():
    actuals = []
    for match in match_dict:
        for player in match_dict[match].player_elo_data.keys():
            actuals.append(match_dict[match].player_elo_data[player]["Performance Actual"])
    return sum(actuals) / len(actuals)


@app.callback(Output(component_id='stat-table', component_property= 'children'),
            [Input(component_id='player-name-dropdown', component_property= 'value'),
            Input(component_id='stat-name-dropdown', component_property= 'value'),
            Input(component_id="n-recent-matches", component_property="value")])
def stat_order_grid(player_name_dropdown, stat_name_dropdown, n_recent_matches, denominator_stat = None):
    
    d = Player.order_players_by_stat(player_dict, player_name_dropdown, n_recent_matches, stat_name_dropdown, denominator_stat)
    data = [{stat_name_dropdown : round(key,2), "Player" : d[key]} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "player-stat-table", 
        columns = columns, 
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

@app.callback(Output(component_id='match-choices', component_property= 'options'),
            Input(component_id='player-filter', component_property='value'))
def match_selector(player_filter):
    if player_filter == "All":
        return [{"label" : x, "value" : x} for x in match_list]

    ops = []
    for x in match_list:
        match = match_dict.get(x, None)
        if match is not None:
            if player_filter in match_dict[x].players:
                ops.append({"label" : x, "value" : x})

    return ops

@app.callback(Output(component_id='match-choices', component_property= 'value'),
            [Input(component_id='match-choices', component_property= 'options')])
def set_match_choice_value(chosen_match):
    return chosen_match[0]["value"]

@app.callback(Output(component_id='scoreboard-container', component_property= 'children'),
            [Input(component_id='match-choices', component_property= 'value')])
def display_scoreboard(chosen_match):

    if chosen_match is None:
        return None
    current_match = match_dict[chosen_match]    
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

    return [
        html.H3(f"Team One - Average Elo : {round(current_match.team_one_elo)}"),
        dash.dash_table.DataTable(
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
        dash.dash_table.DataTable(
            id='team-two-scoreboard',
            columns=[{"name": i, "id": i} for i in team_two_df.columns],
            data=team_two_df.to_dict('records'),
            sort_action = "native",
            sort_mode = "single",
            **data_table_non_editable_kwargs
        ),
        html.Br(),
        dash.dash_table.DataTable(
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
   


@app.callback(Output(component_id='linear-regression-table', component_property= 'children'),
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

    return dash.dash_table.DataTable(
        id = "table-output", 
        columns = columns, 
        data = data,
        **data_table_non_editable_kwargs
        )

@app.callback(Output(component_id='elo-div', component_property= 'children'),
            [Input(component_id='player-name-dropdown', component_property= 'value')])
def elo_table(player_name_dropdown):
    d = {player : player_dict[player].elo for player in player_name_dropdown}
    data = [{"Player" : key, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
        )

def full_elo_table():

    d = {player : player_dict[player].elo for player in player_dict}
    data = [{"Player" : key, "Elo" : round(d[key])} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : "Elo", "id" : "Elo"}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns,
        data = data,
        sort_action = "native",
        sort_mode = "single",
        **data_table_non_editable_kwargs
    )

@app.callback(Output(component_id='match-explorer-h3', component_property= 'children'),
            [Input(component_id='player-filter', component_property='value')])
def match_explorer_h3_func(player_filter):

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

@app.callback(Output(component_id='match-create', component_property='children'),
            [Input(component_id = 'elo-filter', component_property='value')])
def match_create(players):
    player_data = [player_dict[player] for player in players]
    df = Elo.even_match(player_data)
    data = df.to_dict('records')
    columns=[{"name": i, "id": i} for i in df.columns]

    return dash.dash_table.DataTable(
        id = "table-output",
        columns = columns, 
        data = data
    )    


navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Page 1", href="/page-1", active='exact')),
		dbc.NavItem(dbc.NavLink("Page 2", href="/page-2", active='exact')),
		dbc.NavItem(dbc.NavLink("Page 3", href="/page-3", active='exact')),
		dbc.NavItem(dbc.NavLink("Page 4", href="/page-4", active='exact')),
    ],
    brand=f"CSGO Dashboard - Number of matches: {len(match_list)}, average rating: {round(average_actual_rating(),2 )}",
    brand_href="",
    color="primary",
    dark=True,
)


def build_page_one():
    return [
        html.Div([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                dcc.Dropdown(
                                    id = 'player-name-dropdown',
                                    options = [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                    multi = True,
                                    value = [default_player],
                                    #style={'backgroundColor': 'rgba(0, 0, 0, 0)', 'color': 'black'}
                                ),
                                html.Br(),
                                dcc.Dropdown(
                                    id = "stat-name-dropdown", 
                                    options = [{"label" : x, "value" : x} for x in sorted(Player("").stats.keys())],
                                    multi = False,
                                    value = "Kills"
                                )
                            ])
                        ])
                    ], width = 2),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                dcc.Graph(id = 'scatter'),
                                dcc.Slider(
                                    id = "n-recent-matches",
                                    min=1,
                                    max = 20,
                                    step = 1,
                                    marks={i : f"{i}" for i in range(1, 21)},
                                    value=10
                                )
                            ])
                        ])
                    ], width = 10)
                ], align = "center")
            ])
        ], style = {"background-color" : "dark"}),
        html.Br(),
        html.Div([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div(id = "stat-table", children = [
                                dash.dash_table.DataTable(id='ordered_stat_table')
                            ])
                        ], width = 6),
                        dbc.Col([
                            html.Div(id = "elo-div", children = [
                                dash.dash_table.DataTable(id='ordered_stat_table')
                            ])
                        ], width = 6)
                    ], align = "center")
                ])
            ], style = {"background-color" : "dark"})
        ])
    ]

def build_page_two():
    return [
        html.Div([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div(id = "match-explorer-main", children = [
                            html.Div(id = 'match-explorer-h3'),
                            dbc.Card([
                                dbc.CardBody([
                                    dbc.Row([
                                        dcc.Dropdown(
                                            id = "player-filter",
                                            options = [{"label" : "All", "value" : "All"}] + [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                            multi = False,
                                            value = "All"
                                        )
                                    ]),
                                    dbc.Row([
                                        dcc.Dropdown(
                                            id = 'match-choices'
                                        )
                                    ])
                                ]),
                            ], style = {"background-color" : "dark"}),
                            html.Br([]),
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div(id = "scoreboard-container")
                                ])
                            ], style = {"background-color" : "dark"})
                        ])
                    ])
                ])
            ])
        ])
    ]

def build_page_three():
    return [
        html.Br(),
        html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H3("Elo")
                        ])
                    ]),
                    html.Br(),
                    dbc.Card([
                        dbc.CardBody([
                    html.Div(id = 'elo-table-container', children = full_elo_table())
                        ])
                    ], style = {"background-color" : "dark"})
                ])
            ])
        ])
    ]

def build_page_four():
    return [
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div(id = 'match-create-main', children = [
                            html.Div([
                                dcc.Dropdown(id = "elo-filter",
                                options = [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                multi = True)
                                ]),
                            html.Div(id = 'match-create')
                        ])
                    ])
                ])
            ])
        ])
    ]

page_dict = {
	"/page-1" : build_page_one(),
	"/page-2" : build_page_two(),
	"/page-3" : build_page_three(),
	"/page-4" : build_page_four(),
}

@app.callback(
	Output("page-content", "children"),
	Input("url", "pathname")
)
def render_page_content(pathname):
	return page_dict[pathname]

content = html.Div(id="page-content", children = [], style = {"background-color" : colours["background"]})

def main():

    app.layout = html.Div([
        dcc.Location(id='url'),
        navbar,
        content
    ])

    app.config.suppress_callback_exceptions = True

    return app

if __name__ == "__main__":
    main()