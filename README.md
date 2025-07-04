# JARVIS Sprachsteuerung

## Alexa-Integration

- Ein lokaler Webserver läuft auf Port 5050 (`/alexa`).
- Du kannst einen eigenen Alexa-Skill (Custom Skill) anlegen, der einen HTTPS-Webhook auf deinen Rechner (z.B. via ngrok) schickt.
- Beispiel-Request:

```json
POST http://localhost:5050/alexa
Content-Type: application/json
{
  "command": "öffne explorer"
}
```

- Im Alexa Developer Console: Skill anlegen, Intent mit Slot `command` definieren, Endpoint auf deinen Webhook (z.B. ngrok Forwarding) setzen.
- Im Skill-Backend einfach den Text aus dem Slot an `/alexa` schicken.
- JARVIS verarbeitet den Befehl und zeigt einen GUI-Hinweis an.

## Plugins

- Lege Python-Dateien im Ordner `plugins/` an.
- Jede Datei muss eine Funktion `register(text, app)` bereitstellen.
- Beispiel:

```python
def register(text, app):
    if text.strip().lower() == "hallo plugin":
        app.append_text("Plugin sagt: Hallo!")
        return True
    return False
```

- Plugins werden automatisch geladen und bei Änderung neu geladen.
- Im Plugin-Tab der GUI siehst du alle aktiven Plugins.

# Jarvis Plugin Store

Hier findest du offizielle und Community-Plugins für das Jarvis Sprachassistenzsystem.

## Plugins

| Name           | Beschreibung                                 | Ordner         |
|----------------|----------------------------------------------|---------------|
| Hello World    | Gibt „Hello World“ aus (Beispiel)            | hello_world/  |
| System Monitor | Zeigt CPU- und RAM-Auslastung an             | system_monitor/|

## Struktur
- `plugins.json`: Übersicht und Metadaten aller Plugins
- Ein Ordner pro Plugin mit Quellcode und optionaler Info-Datei

## Nutzung
1. Klone dieses Repository oder lade es als ZIP herunter.
2. Kopiere die gewünschten Plugin-Ordner in deinen lokalen Jarvis-Plugin-Ordner.
3. Starte Jarvis – die Plugins werden automatisch erkannt und geladen.

## Eigene Plugins hinzufügen
- Lege einen neuen Ordner mit deinem Plugin-Namen an.
- Erstelle darin mindestens eine `__init__.py` mit einer `run()`-Funktion.
- Ergänze dein Plugin in der `plugins.json` mit allen wichtigen Metadaten.
- Optional: Füge eine `plugin_info.md` für eine Beschreibung hinzu.

## Mitmachen
Pull Requests für neue Plugins sind willkommen! 