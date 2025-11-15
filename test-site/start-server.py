#!/usr/bin/env python3
import http.server
import socketserver
import webbrowser
import os

PORT = 3000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"🚀 Serveur démarré sur {url}")
        print(f"📂 Ouvrez {url} dans votre navigateur")
        print("⚠️  Assurez-vous que le backend est démarré sur http://localhost:8000")
        print("\nAppuyez sur Ctrl+C pour arrêter le serveur\n")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Serveur arrêté")

if __name__ == "__main__":
    main()

