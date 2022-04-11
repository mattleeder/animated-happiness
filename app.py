from dash import Dash, dcc, html, Input, Output, callback

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
    dcc.Store(id="submitted-store"),
    dcc.Store(id="finished-store"),
    dcc.Interval(id="interval", interval=500),
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
        "/page-1" : stat_page,
        "/page-2" : match_page,
        "/page-3" : elo_page,
        "/page-4" : match_balance_page,
        "/page-5" : elo_high_score_page,
        "/page-6" : data_retrieve_page,
    }
    return page_dict.get(pathname, None)

if __name__ == '__main__':
    app.run_server(debug=False)