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
    print(f"\n=======================================================")
    print(f"🚀 {Config.RESTAURANT_NAME} is starting up!")
    print(f"🌐 Serving at: http://{host}:{port}")
    print(f"👥 Default Demo Accounts:")
    print(f"   - Admin:      admin / admin")
    print(f"   - Manager:    manager / manager")
    print(f"   - Staff:      staff / staff")
    print(f"   - Customer:   customer / customer")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=Config.DEBUG)
