from dash import Dash, dcc, html, Input, Output, callback, clientside_callback, ClientsideFunction

from layouts import stat_page, match_page, elo_page, match_balance_page, elo_high_score_page, data_retrieve_page
import callbacks

app = Dash(__name__, suppress_callback_exceptions = True)
server = app.server

colours = {
    "background" : "#272b30",
    "text" : "#FFFFFF"
}

content = html.Div(id="page-content", children = [], style = {"background-color" : colours["background"]})

app.layout = html.Div([
    dcc.Store(id = "player-dict", storage_type='session'),
    dcc.Store(id = "match-dict", storage_type='session'),
    dcc.Store(id = "match-list", storage_type='session'),
    dcc.Store(id = "player-name-lookup", storage_type='session'),
    dcc.Store(id = "submitted-store"),
    dcc.Store(id = "finished-store"),
    dcc.Store(id = 'elo-data'),
    dcc.Interval(id="interval", interval=1000),
    dcc.Location(id='url'),
    html.Div(id = "navbar"),
    content
    ])

@callback(
	Output("page-content", "children"),
	Input("url", "pathname")
)
def render_page_content(pathname):
    page_dict = {
        "/stats" : stat_page,
        "/match-explorer" : match_page,
        "/current-elo" : elo_page,
        "/match-create" : match_balance_page,
        "/elo-hi-scores" : elo_high_score_page,
        "/data" : data_retrieve_page,
    }
    return page_dict.get(pathname, None)

if __name__ == '__main__':
    app.run_server(debug=True)