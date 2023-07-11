from dashboard import app

if __name__ == "__main__":
    init_dashboard()
    UPDATE = check_update()
    config = configparser.ConfigParser(strict=False)
    config.read('wg-dashboard.ini')
    # global app_ip
    app_ip = config.get("Server", "app_ip")
    # global app_port
    app_port = config.get("Server", "app_port")
    WG_CONF_PATH = config.get("Server", "wg_conf_path")
    config.clear()
    app.run(host=app_ip, debug=False, port=app_port)