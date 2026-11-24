"""
Smart Restaurant Demand Forecasting & Real-Time Food Waste Management System
Main Application Entry Point.
"""

import os
from backend import create_app
from backend.config import Config

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    print("\n=======================================================")
    print("[STARTUP] %s is starting up!" % Config.RESTAURANT_NAME)
    print("[STARTUP] Serving at: http://%s:%d" % (host, port))
    print("[STARTUP] Default Demo Accounts:")
    print("[STARTUP]   Admin:    admin / admin")
    print("[STARTUP]   Manager:  manager / manager")
    print("[STARTUP]   Staff:    staff / staff")
    print("[STARTUP]   Customer: customer / customer")
    print("=======================================================\n")
    app.run(host=host, port=port, debug=Config.DEBUG)
