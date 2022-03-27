from layout import main as appmain

app = appmain()
server = app.server
app.run_server(debug = True)

def main():
    pass

if __name__ == "__main__":
    main()