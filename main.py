import os
import sys
import ctypes
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import difflib
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import pyttsx3
import logging
import requests
from flask import Flask, request as flask_request, jsonify
import importlib.util
import glob
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import zipfile
import io
import shutil

# Admin-Check (Windows)
def check_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

is_admin = check_admin()
if not is_admin:
    print("Warnung: Nicht mit Admin-Rechten gestartet. Einige Befehle werden nicht funktionieren.")
else:
    print("Admin-Rechte erkannt.")

# Vosk Model laden (ggf. vorher herunterladen und entpacken)
MODEL_PATH = "vosk-model-small-de-0.15"  # Passe ggf. an
if not os.path.exists(MODEL_PATH):
    print(f"Vosk-Modell nicht gefunden: {MODEL_PATH}")
    sys.exit(1)

model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, 16000)
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def execute_command(text):
    # Hotword-Check
    try:
        if hasattr(app, 'use_hotword') and app.use_hotword.get():
            lowered = text.lower().strip()
            hotword = app.hotword_var.get().strip().lower()
            hotwords = [hotword, f"hey {hotword}", f"hi {hotword}"]
            found = False
            for hw in hotwords:
                if lowered.startswith(hw):
                    text = lowered[len(hw):].strip()
                    found = True
                    break
            if not found:
                print("Hotword nicht erkannt. Befehl ignoriert.")
                try:
                    app.append_text(f"Hotword nicht erkannt. Bitte mit '{hotword.capitalize()}' beginnen.\n")
                except:
                    pass
                return
    except Exception as e:
        print(f"Fehler bei Hotword-Check: {e}")
    text = text.lower()
    # Liste aller unterstützten Befehle und deren Synonyme
    commands = {
        "notepad": ["öffne editor", "starte editor", "notepad", "öffne notepad", "starte notepad", "editor öffnen"],
        "chrome": ["starte chrome", "öffne chrome", "chrome öffnen", "öffne den chrome", "starte den chrome", "google chrome"],
        "explorer": ["öffne explorer", "starte explorer", "explorer öffnen", "dateimanager", "dateien anzeigen"],
        "taskmgr": ["öffne taskmanager", "starte taskmanager", "taskmanager", "task-manager", "task manager"],
        "calc": ["öffne rechner", "starte rechner", "rechner", "calculator", "calc"],
        "shutdown": ["fahre herunter", "herunterfahren", "pc herunterfahren", "computer ausschalten", "shutdown"],
        "restart": ["starte neu", "neustarten", "pc neustarten", "computer neu starten", "restart"],
        "lock": ["sperre pc", "bildschirm sperren", "sperren", "lock"],
        "sysinfo": ["zeige systeminfo", "systeminfo", "system informationen", "system anzeigen"],
        "volup": ["lauter", "lautstärke lauter", "volume up", "lauter machen"],
        "voldown": ["leiser", "lautstärke leiser", "volume down", "leiser machen"],
        "mute": ["stummschalten", "lautstärke aus", "mute", "ton aus"],
        "maxvol": ["lautstärke maximal", "lautstärke auf maximum", "maximale lautstärke", "volume max"],
        "minimize": ["fenster minimieren", "minimiere fenster", "alles minimieren", "minimize window"],
        "maximize": ["fenster maximieren", "maximiere fenster", "maximize window"],
        "showdesktop": ["desktop anzeigen", "zeige desktop", "zeige den desktop", "show desktop"],
        "screenshot": ["screenshot", "bildschirmfoto", "screenshot machen", "screenshot erstellen"],
        "recyclebin": ["papierkorb leeren", "leere papierkorb", "recycle bin leeren", "papierkorb löschen"],
        "time": ["wie spät ist es", "uhrzeit", "wie viel uhr", "zeit anzeigen", "datum anzeigen", "welches datum"],
        "wlanoff": ["wlan deaktivieren", "wlan aus", "wifi aus", "wifi deaktivieren"],
        "wlanon": ["wlan aktivieren", "wlan an", "wifi an", "wifi aktivieren"],
        "monoff": ["bildschirm ausschalten", "monitor aus", "display aus", "bildschirm aus"],
        "clipboard": ["zwischenablage anzeigen", "zeige zwischenablage", "clipboard anzeigen"],
        "spotify": ["öffne spotify", "starte spotify", "spotify"],
        "outlook": ["öffne outlook", "starte outlook", "outlook"],
        "word": ["öffne word", "starte word", "word"],
        "excel": ["öffne excel", "starte excel", "excel"],
        "paint": ["öffne paint", "starte paint", "paint"],
        "cmd": ["öffne cmd", "starte cmd", "eingabeaufforderung", "command prompt"],
        "powershell": ["öffne powershell", "starte powershell", "powershell"],
        "control": ["öffne systemsteuerung", "systemsteuerung", "control panel"],
        "devmgmt": ["öffne geräte-manager", "geräte-manager", "device manager"],
        "bton": ["bluetooth aktivieren", "bluetooth an", "bluetooth einschalten"],
        "btoff": ["bluetooth deaktivieren", "bluetooth aus", "bluetooth ausschalten"],
        "firefox": ["öffne firefox", "starte firefox", "firefox"],
        "edge": ["öffne edge", "starte edge", "microsoft edge", "edge"],
        "teams": ["öffne teams", "starte teams", "microsoft teams", "teams"],
        "zoom": ["öffne zoom", "starte zoom", "zoom"],
        "discord": ["öffne discord", "starte discord", "discord"],
        "steam": ["öffne steam", "starte steam", "steam"],
        "vlc": ["öffne vlc", "starte vlc", "vlc", "vlc player"],
        "calendar": ["öffne kalender", "starte kalender", "kalender", "calendar"],
        "snipping": ["öffne snipping tool", "starte snipping tool", "snipping tool", "ausschnitt tool"],
        "settings": ["öffne einstellungen", "starte einstellungen", "einstellungen", "settings"],
        "powercfg": ["energieoptionen", "energieoptionen öffnen", "power options"],
        "brightnessup": ["bildschirm heller", "helligkeit erhöhen", "bildschirmhelligkeit erhöhen", "heller machen"],
        "brightnessdown": ["bildschirm dunkler", "helligkeit verringern", "bildschirmhelligkeit verringern", "dunkler machen"],
        "airplaneon": ["flugmodus aktivieren", "flugmodus an", "airplane mode on", "flugmodus einschalten"],
        "airplaneoff": ["flugmodus deaktivieren", "flugmodus aus", "airplane mode off", "flugmodus ausschalten"],
        "speakermute": ["lautsprecher stummschalten", "lautsprecher aus", "speaker mute"],
        "speakeron": ["lautsprecher aktivieren", "lautsprecher an", "speaker on"],
        "netreset": ["netzwerk zurücksetzen", "netzwerk reset", "network reset"],
        "winupdate": ["windows update starten", "starte windows update", "update starten", "windows update"],
        "rotate": ["bildschirm drehen", "bildschirm rotieren", "screen rotate"],
        "clearclipboard": ["zwischenablage leeren", "clipboard leeren", "clear clipboard"],
        "downloads": ["öffne downloads", "downloads anzeigen", "explorer downloads"],
        "documents": ["öffne dokumente", "dokumente anzeigen", "explorer dokumente"],
        "desktop": ["öffne desktop", "desktop anzeigen", "explorer desktop"],
        "pictures": ["öffne bilder", "bilder anzeigen", "explorer bilder"],
        "music": ["öffne musik", "musik anzeigen", "explorer musik"],
        "videos": ["öffne videos", "videos anzeigen", "explorer videos"],
        "adduser": ["benutzer anlegen", "benutzerkonto erstellen", "neuen benutzer erstellen", "add user"],
        "deluser": ["benutzer löschen", "benutzerkonto löschen", "user löschen", "delete user"],
        "renamepc": ["computer umbenennen", "pc umbenennen", "rename computer", "rename pc"],
        "startservice": ["dienst starten", "service starten", "starte dienst", "starte service"],
        "stopservice": ["dienst stoppen", "service stoppen", "stoppe dienst", "stoppe service"],
        "firewallenable": ["firewall aktivieren", "firewall einschalten", "firewall enable"],
        "firewalldisable": ["firewall deaktivieren", "firewall ausschalten", "firewall disable"],
        "mapdrive": ["netzlaufwerk verbinden", "netzlaufwerk zuordnen", "netzlaufwerk verbinden"],
        "disconnectdrive": ["netzlaufwerk trennen", "netzlaufwerk entfernen", "netzlaufwerk trennen"],
        "sfc": ["systemdateien prüfen", "sfc scannow", "systemdateien überprüfen"],
        "chkdsk": ["festplatte prüfen", "chkdsk", "festplatte überprüfen"],
        "restore": ["systemwiederherstellung", "system wiederherstellen", "system restore"],
        "driverupdate": ["treiber aktualisieren", "treiber updaten", "update treiber"],
        "gpedit": ["gruppenrichtlinien öffnen", "gruppenrichtlinien", "gpedit"],
        "regedit": ["registry editor öffnen", "regedit", "registry editor"],
        "taskschd": ["aufgabenplanung öffnen", "aufgabenplanung", "task scheduler"],
        "defenderscan": ["windows defender scan", "defender scan", "windows defender durchsuchen"],
        "renewip": ["ip adresse erneuern", "ip erneuern", "renew ip"],
        "flushdns": ["dns cache leeren", "dns leeren", "flush dns"],
        "eventvwr": ["systemprotokolle anzeigen", "ereignisanzeige öffnen", "event viewer"],
        "showcommands": ["befehle anzeigen", "zeige befehle", "alle befehle", "hilfe", "was kann ich sagen"]
    }
    # Flache Liste aller Synonyme
    all_phrases = [syn for syns in commands.values() for syn in syns]
    # Unscharfe Suche
    match = difflib.get_close_matches(text, all_phrases, n=1, cutoff=0.6)
    if match:
        phrase = match[0]
        # Finde den Befehlstyp
        for cmd, syns in commands.items():
            if phrase in syns:
                command = cmd
                break
    else:
        command = None

    if command == "notepad":
        print("Starte Notepad...")
        subprocess.Popen(["notepad.exe"])
    elif command == "chrome":
        print("Starte Google Chrome...")
        chrome_paths = [
            "chrome.exe",
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ]
        started = False
        for path in chrome_paths:
            try:
                subprocess.Popen([path])
                started = True
                break
            except FileNotFoundError:
                continue
        if not started:
            msg = "Chrome konnte nicht gefunden werden! Bitte prüfe die Installation."
            print(msg)
            try:
                app.append_text(msg + "\n")
            except:
                pass
    elif command == "explorer":
        print("Öffne Explorer...")
        subprocess.Popen(["explorer.exe"])
    elif command == "taskmgr":
        print("Öffne Task-Manager...")
        subprocess.Popen(["taskmgr.exe"])
    elif command == "calc":
        print("Öffne Rechner...")
        subprocess.Popen(["calc.exe"])
    elif command == "shutdown":
        if is_admin:
            print("Fahre PC herunter...")
            os.system("shutdown /s /t 1")
        else:
            print("Befehl benötigt Admin-Rechte!")
            try:
                app.append_text("Befehl benötigt Admin-Rechte!\n")
            except:
                pass
    elif command == "restart":
        if is_admin:
            print("Starte PC neu...")
            os.system("shutdown /r /t 1")
        else:
            print("Befehl benötigt Admin-Rechte!")
            try:
                app.append_text("Befehl benötigt Admin-Rechte!\n")
            except:
                pass
    elif command == "lock":
        print("Sperre Bildschirm...")
        ctypes.windll.user32.LockWorkStation()
    elif command == "sysinfo":
        print("Zeige Systeminformationen...")
        os.system("systeminfo | more")
    elif command == "volup":
        print("Lautstärke lauter...")
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumeup")
        except Exception as e:
            print(f"Fehler bei Lautstärke: {e}")
    elif command == "voldown":
        print("Lautstärke leiser...")
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumedown")
        except Exception as e:
            print(f"Fehler bei Lautstärke: {e}")
    elif command == "mute":
        print("Stummschalten...")
        try:
            import pyautogui
            pyautogui.press("volumemute")
        except Exception as e:
            print(f"Fehler bei Lautstärke: {e}")
    elif command == "maxvol":
        print("Lautstärke auf Maximum...")
        try:
            import pyautogui
            for _ in range(50):
                pyautogui.press("volumeup")
        except Exception as e:
            print(f"Fehler bei Lautstärke: {e}")
    elif command == "minimize":
        print("Alle Fenster minimieren...")
        try:
            import pyautogui
            pyautogui.hotkey('win', 'd')
            pyautogui.hotkey('win', 'm')
        except Exception as e:
            print(f"Fehler beim Minimieren: {e}")
    elif command == "maximize":
        print("Aktuelles Fenster maximieren...")
        try:
            import pyautogui
            pyautogui.hotkey('win', 'up')
        except Exception as e:
            print(f"Fehler beim Maximieren: {e}")
    elif command == "showdesktop":
        print("Desktop anzeigen...")
        try:
            import pyautogui
            pyautogui.hotkey('win', 'd')
        except Exception as e:
            print(f"Fehler beim Desktop anzeigen: {e}")
    elif command == "screenshot":
        print("Screenshot wird erstellt...")
        try:
            import pyautogui
            pyautogui.screenshot('screenshot.png')
            print("Screenshot gespeichert als screenshot.png")
            try:
                app.append_text("Screenshot gespeichert als screenshot.png\n")
            except:
                pass
        except Exception as e:
            print(f"Fehler beim Screenshot: {e}")
    elif command == "recyclebin":
        print("Papierkorb leeren...")
        try:
            import winshell
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=True)
        except Exception as e:
            print(f"Fehler beim Papierkorb leeren: {e}")
    elif command == "time":
        import datetime
        now = datetime.datetime.now()
        msg = f"Es ist {now.strftime('%H:%M:%S')} am {now.strftime('%d.%m.%Y')}"
        print(msg)
        try:
            app.append_text(msg + "\n")
        except:
            pass
    elif command == "wlanoff":
        print("WLAN deaktivieren...")
        os.system("netsh interface set interface 'Wi-Fi' admin=disable")
    elif command == "wlanon":
        print("WLAN aktivieren...")
        os.system("netsh interface set interface 'Wi-Fi' admin=enable")
    elif command == "monoff":
        print("Bildschirm ausschalten...")
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SYSCOMMAND = 0x0112
        SC_MONITORPOWER = 0xF170
        ctypes.windll.user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
    elif command == "clipboard":
        print("Zeige Zwischenablage...")
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            clipboard = r.clipboard_get()
            r.destroy()
            try:
                app.append_text("Zwischenablage: " + clipboard + "\n")
            except:
                pass
        except Exception as e:
            print(f"Fehler bei Zwischenablage: {e}")
    elif command == "spotify":
        print("Starte Spotify...")
        subprocess.Popen(["spotify.exe"])
    elif command == "outlook":
        print("Starte Outlook...")
        subprocess.Popen(["outlook.exe"])
    elif command == "word":
        print("Starte Word...")
        subprocess.Popen(["winword.exe"])
    elif command == "excel":
        print("Starte Excel...")
        subprocess.Popen(["excel.exe"])
    elif command == "paint":
        print("Starte Paint...")
        subprocess.Popen(["mspaint.exe"])
    elif command == "cmd":
        print("Starte Eingabeaufforderung...")
        subprocess.Popen(["cmd.exe"])
    elif command == "powershell":
        print("Starte Powershell...")
        subprocess.Popen(["powershell.exe"])
    elif command == "control":
        print("Öffne Systemsteuerung...")
        subprocess.Popen(["control.exe"])
    elif command == "devmgmt":
        print("Öffne Geräte-Manager...")
        subprocess.Popen(["devmgmt.msc"])
    elif command == "bton":
        print("Bluetooth aktivieren...")
        os.system("powershell.exe Start-Process powershell -Verb runAs -ArgumentList 'Start-Service bthserv'")
    elif command == "btoff":
        print("Bluetooth deaktivieren...")
        os.system("powershell.exe Start-Process powershell -Verb runAs -ArgumentList 'Stop-Service bthserv'")
    elif command == "firefox":
        print("Starte Firefox...")
        subprocess.Popen(["firefox.exe"])
    elif command == "edge":
        print("Starte Microsoft Edge...")
        subprocess.Popen(["msedge.exe"])
    elif command == "teams":
        print("Starte Microsoft Teams...")
        subprocess.Popen(["Teams.exe"])
    elif command == "zoom":
        print("Starte Zoom...")
        subprocess.Popen(["Zoom.exe"])
    elif command == "discord":
        print("Starte Discord...")
        subprocess.Popen(["Discord.exe"])
    elif command == "steam":
        print("Starte Steam...")
        subprocess.Popen(["Steam.exe"])
    elif command == "vlc":
        print("Starte VLC Player...")
        subprocess.Popen(["vlc.exe"])
    elif command == "calendar":
        print("Öffne Kalender...")
        os.system("start outlookcal:")
    elif command == "snipping":
        print("Starte Snipping Tool...")
        subprocess.Popen(["SnippingTool.exe"])
    elif command == "settings":
        print("Öffne Einstellungen...")
        os.system("start ms-settings:")
    elif command == "powercfg":
        print("Öffne Energieoptionen...")
        subprocess.Popen(["powercfg.cpl"])
    elif command == "brightnessup":
        print("Bildschirm heller...")
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.hotkey('fn', 'f7')  # ggf. anpassen je nach Gerät
        except Exception as e:
            print(f"Fehler bei Helligkeit: {e}")
    elif command == "brightnessdown":
        print("Bildschirm dunkler...")
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.hotkey('fn', 'f6')  # ggf. anpassen je nach Gerät
        except Exception as e:
            print(f"Fehler bei Helligkeit: {e}")
    elif command == "airplaneon":
        print("Flugmodus aktivieren...")
        os.system("start ms-settings:network-airplanemode")
    elif command == "airplaneoff":
        print("Flugmodus deaktivieren...")
        os.system("start ms-settings:network-airplanemode")
    elif command == "speakermute":
        print("Lautsprecher stummschalten...")
        try:
            import pyautogui
            pyautogui.press("volumemute")
        except Exception as e:
            print(f"Fehler bei Lautsprecher: {e}")
    elif command == "speakeron":
        print("Lautsprecher aktivieren...")
        try:
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumeup")
        except Exception as e:
            print(f"Fehler bei Lautsprecher: {e}")
    elif command == "netreset":
        print("Netzwerk zurücksetzen...")
        os.system("netsh int ip reset")
    elif command == "winupdate":
        print("Starte Windows Update...")
        os.system("start ms-settings:windowsupdate")
    elif command == "rotate":
        print("Bildschirm drehen...")
        try:
            import pyautogui
            pyautogui.hotkey('ctrl', 'alt', 'right')
        except Exception as e:
            print(f"Fehler beim Drehen: {e}")
    elif command == "clearclipboard":
        print("Leere Zwischenablage...")
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.destroy()
            try:
                app.append_text("Zwischenablage geleert\n")
            except:
                pass
        except Exception as e:
            print(f"Fehler beim Leeren der Zwischenablage: {e}")
    elif command == "downloads":
        print("Öffne Downloads...")
        subprocess.Popen(["explorer", os.path.expanduser("~\\Downloads")])
    elif command == "documents":
        print("Öffne Dokumente...")
        subprocess.Popen(["explorer", os.path.expanduser("~\\Documents")])
    elif command == "desktop":
        print("Öffne Desktop...")
        subprocess.Popen(["explorer", os.path.expanduser("~\\Desktop")])
    elif command == "pictures":
        print("Öffne Bilder...")
        subprocess.Popen(["explorer", os.path.expanduser("~\\Pictures")])
    elif command == "music":
        print("Öffne Musik...")
        subprocess.Popen(["explorer", os.path.expanduser("~\\Music")])
    elif command == "videos":
        print("Öffne Videos...")
        subprocess.Popen(["explorer", os.path.expanduser("~\\Videos")])
    elif command == "adduser":
        if is_admin:
            print("Neuen Benutzer anlegen...")
            os.system("net user NeuerBenutzer Passwort123 /add")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "deluser":
        if is_admin:
            print("Benutzer löschen...")
            os.system("net user NeuerBenutzer /delete")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "renamepc":
        if is_admin:
            print("Computer umbenennen...")
            os.system("WMIC computersystem where name='%computername%' call rename name='NeuerPCName'")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "startservice":
        if is_admin:
            print("Dienst starten...")
            os.system("net start wuauserv")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "stopservice":
        if is_admin:
            print("Dienst stoppen...")
            os.system("net stop wuauserv")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "firewallenable":
        if is_admin:
            print("Firewall aktivieren...")
            os.system("netsh advfirewall set allprofiles state on")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "firewalldisable":
        if is_admin:
            print("Firewall deaktivieren...")
            os.system("netsh advfirewall set allprofiles state off")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "mapdrive":
        if is_admin:
            print("Netzlaufwerk verbinden...")
            os.system("net use Z: \\netzwerkpfad\freigabe")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "disconnectdrive":
        if is_admin:
            print("Netzlaufwerk trennen...")
            os.system("net use Z: /delete")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "sfc":
        if is_admin:
            print("Systemdateien werden geprüft...")
            os.system("sfc /scannow")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "chkdsk":
        if is_admin:
            print("Festplatte wird geprüft...")
            os.system("chkdsk C: /f /r")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "restore":
        if is_admin:
            print("Systemwiederherstellung wird gestartet...")
            os.system("rstrui.exe")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "driverupdate":
        if is_admin:
            print("Treiber werden aktualisiert...")
            os.system("devmgmt.msc")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "gpedit":
        if is_admin:
            print("Gruppenrichtlinien werden geöffnet...")
            os.system("gpedit.msc")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "regedit":
        if is_admin:
            print("Registry Editor wird geöffnet...")
            os.system("regedit.exe")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "taskschd":
        if is_admin:
            print("Aufgabenplanung wird geöffnet...")
            os.system("taskschd.msc")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "defenderscan":
        if is_admin:
            print("Windows Defender Scan wird gestartet...")
            os.system("start cmd /k '"'"'"C:\\Program Files\\Windows Defender\\MpCmdRun.exe"'"'"' -Scan -ScanType 2'")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "renewip":
        if is_admin:
            print("IP-Adresse wird erneuert...")
            os.system("ipconfig /release && ipconfig /renew")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "flushdns":
        if is_admin:
            print("DNS-Cache wird geleert...")
            os.system("ipconfig /flushdns")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "eventvwr":
        if is_admin:
            print("Systemprotokolle werden angezeigt...")
            os.system("eventvwr.msc")
        else:
            print("Admin-Rechte benötigt!")
            try:
                app.append_text("Admin-Rechte benötigt!\n")
            except:
                pass
    elif command == "showcommands":
        print("Verfügbare Sprachbefehle:")
        try:
            befehlliste = []
            for cmd, syns in commands.items():
                if cmd != "showcommands":
                    befehlliste.append(f"{cmd}: {', '.join(syns)}")
            msg = "Verfügbare Befehle:\n" + "\n".join(befehlliste) + "\n"
            print(msg)
            app.append_text(msg)
        except Exception as e:
            print(f"Fehler beim Anzeigen der Befehle: {e}")
    else:
        print("Befehl nicht erkannt oder noch nicht implementiert.")
        try:
            app.append_text("Befehl nicht erkannt oder noch nicht implementiert.\n")
        except:
            pass

# Logging einrichten
logging.basicConfig(filename='jarvis.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Plugin-System
PLUGINS = {}
PLUGIN_STATUS = {}
def load_plugins():
    PLUGINS.clear()
    for plugin_path in glob.glob('plugins/*.py'):
        name = os.path.splitext(os.path.basename(plugin_path))[0]
        spec = importlib.util.spec_from_file_location(name, plugin_path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            if hasattr(mod, 'register'):
                PLUGINS[name] = mod.register
                if name not in PLUGIN_STATUS:
                    PLUGIN_STATUS[name] = True  # Standard: aktiv
                logging.info(f'Plugin geladen: {name}')
        except Exception as e:
            logging.error(f'Fehler beim Laden von Plugin {name}: {e}')
    if 'app' in globals() and hasattr(app, 'update_plugin_gui'):
        app.update_plugin_gui()

# Update-Check (Dummy-URL, anpassbar)
def check_for_update():
    try:
        resp = requests.get('https://api.github.com/repos/deinuser/deinrepo/releases/latest', timeout=3)
        if resp.status_code == 200:
            latest = resp.json()['tag_name']
            current = 'v1.0.0'  # Deine aktuelle Version
            if latest != current:
                logging.info(f'Update verfügbar: {latest}')
                return latest
    except Exception as e:
        logging.warning(f'Update-Check fehlgeschlagen: {e}')
    return None

# Flask-Server für Alexa/Webhook
flask_app = Flask(__name__)
@flask_app.route('/alexa', methods=['POST'])
def alexa_webhook():
    data = flask_request.json
    cmd = data.get('command', '')
    logging.info(f'Alexa-Webhook: {cmd}')
    if 'app' in globals():
        try:
            app.show_alexa_hint(cmd)
        except Exception:
            pass
    return jsonify({'status': 'ok', 'received': cmd})

def start_flask_server():
    flask_app.run(port=5050, debug=False, use_reloader=False)

# Starte Flask-Server im Hintergrund
threading.Thread(target=start_flask_server, daemon=True).start()

# Performance: TTS und Plugin-Calls in Threads
class VoiceControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jarvis Sprachsteuerung")
        self.device_list = sd.query_devices()
        self.input_devices = [(i, d['name']) for i, d in enumerate(self.device_list) if d['max_input_channels'] > 0]
        self.selected_device = tb.StringVar()
        self.is_listening = False
        self.stream = None
        self.listen_thread = None
        self.use_hotword = tb.BooleanVar(value=False)
        self.hotword_var = tb.StringVar(value="Jarvis")
        self.history = []  # Verlauf der letzten Sprachbefehle
        self.mini_mode = False
        self.tts_engine = pyttsx3.init()
        self.plugins_tab = None
        self.plugins_listbox = None
        self.update_gui_shown = False
        self.alexa_gui_msg = None
        self.plugin_store_tab = None
        self.build_gui()
        if check_for_update() and not self.update_gui_shown:
            self.show_update_hint(check_for_update())
            self.update_gui_shown = True

    def speak(self, text):
        def tts_thread():
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                logging.error(f'TTS Fehler: {e}')
        threading.Thread(target=tts_thread, daemon=True).start()

    def build_gui(self):
        self.root.configure(bg="#181c29")
        for widget in self.root.winfo_children():
            widget.destroy()
        # Tabs für Hauptbereiche
        self.tab_control = tb.Notebook(self.root, bootstyle="info")
        self.tab_control.pack(fill="both", expand=True)
        # Sprachsteuerung-Tab
        self.main_tab = tb.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="Sprachsteuerung")
        # Verlauf-Tab
        self.history_tab = tb.Frame(self.tab_control)
        self.tab_control.add(self.history_tab, text="Verlauf")
        # Plugins-Tab
        self.plugins_tab = tb.Frame(self.tab_control)
        self.tab_control.add(self.plugins_tab, text="Plugins")
        # Plugin Store Tab
        self.plugin_store_tab = tb.Frame(self.tab_control)
        self.tab_control.add(self.plugin_store_tab, text="Plugin Store")
        # Einstellungen-Tab
        self.settings_tab = tb.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="Einstellungen")
        # Status-Kreis (animiert)
        self.status_canvas = tk.Canvas(self.main_tab, width=60, height=60, bg="#181c29", highlightthickness=0)
        self.status_canvas.pack(pady=(10, 0))
        self.pulse_radius = 20
        self.pulse_grow = True
        self.animate_pulse = True
        self.draw_status_circle()
        self.animate_status_circle()
        # Mini-Mode Button
        self.mini_btn = tb.Button(self.main_tab, text="Mini-Mode", command=self.toggle_mini_mode, bootstyle="secondary-outline")
        self.mini_btn.pack(pady=(0, 5))
        self.create_tooltip(self.mini_btn, "Kompakte Mini-Ansicht umschalten")
        if self.mini_mode:
            self.build_mini_gui()
            return
        frame = tb.Frame(self.main_tab, padding=20, bootstyle="dark")
        frame.pack(fill="both", expand=True)
        # Überschrift
        title = tb.Label(frame, text="JARVIS Sprachsteuerung", font=("Segoe UI", 22, "bold"), bootstyle="info-inverse")
        title.pack(pady=(0, 10))
        # Mikrofon-Auswahl
        mic_group = tb.Labelframe(frame, text="Audio-Eingabe", padding=10, bootstyle="primary")
        mic_group.pack(fill="x", pady=5)
        tb.Label(mic_group, text="Mikrofon auswählen:", bootstyle="secondary").pack(anchor="w")
        device_options = [f"{name} (Index {idx})" for idx, name in self.input_devices]
        self.device_combo = tb.Combobox(mic_group, values=device_options, textvariable=self.selected_device, state="readonly", bootstyle="info")
        self.device_combo.pack(fill="x", pady=2)
        # Standardgerät automatisch auswählen
        default_index = None
        try:
            default_input = sd.default.device[0]
            for i, (idx, name) in enumerate(self.input_devices):
                if idx == default_input:
                    default_index = i
                    break
        except Exception:
            pass
        if default_index is not None:
            self.device_combo.current(default_index)
        elif device_options:
            self.device_combo.current(0)
        # Hotword-Optionen
        hotword_group = tb.Labelframe(frame, text="Hotword (Aktivierungswort)", padding=10, bootstyle="primary")
        hotword_group.pack(fill="x", pady=5)
        self.hotword_check = tb.Checkbutton(hotword_group, text="Hotword am Anfang verlangen (z.B. 'Jarvis')", variable=self.use_hotword, bootstyle="danger-round-toggle")
        self.hotword_check.pack(anchor="w", pady=2)
        hotword_row = tb.Frame(hotword_group)
        hotword_row.pack(anchor="w", pady=2, fill="x")
        self.hotword_label = tb.Label(hotword_row, text=f"Aktuelles Hotword: {self.hotword_var.get()}", font=("Segoe UI", 10, "italic"), bootstyle="info-inverse")
        self.hotword_label.pack(side="left")
        self.rename_btn = tb.Button(hotword_row, text=f"{self.hotword_var.get()} umbenennen", command=self.rename_hotword, bootstyle="danger-outline")
        self.rename_btn.pack(side="left", padx=10)
        self.create_tooltip(self.rename_btn, "Hotword ändern")
        # Button-Leiste
        button_row = tb.Frame(frame, bootstyle="dark")
        button_row.pack(fill="x", pady=(10, 0))
        self.start_btn = tb.Button(button_row, text="Spracherkennung starten", command=self.toggle_listen, bootstyle="info-outline", width=22)
        self.start_btn.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.create_tooltip(self.start_btn, "Spracherkennung starten/stoppen")
        self.commands_btn = tb.Button(button_row, text="Befehle anzeigen", command=self.show_commands_popup, bootstyle="primary-outline", width=18)
        self.commands_btn.pack(side="left", fill="x", expand=True)
        self.create_tooltip(self.commands_btn, "Alle Sprachbefehle anzeigen")
        # Textfeld für Ausgaben
        output_group = tb.Labelframe(frame, text="Ausgabe", padding=10, bootstyle="primary")
        output_group.pack(fill="both", expand=True, pady=10)
        self.textbox = tb.Text(output_group, height=8, state="disabled", font=("Consolas", 11), background="#232b3a", foreground="#00eaff", borderwidth=0, highlightthickness=0)
        self.textbox.pack(fill="both", expand=True)
        self.append_text("Gefundene Mikrofone:\n" + "\n".join(device_options) + "\n\n")
        # Verlauf
        history_group = tb.Labelframe(frame, text="Verlauf", padding=8, bootstyle="info")
        history_group.pack(fill="x", pady=(5, 0))
        self.history_listbox = tk.Listbox(history_group, height=5, bg="#232b3a", fg="#00eaff", font=("Consolas", 10), borderwidth=0, highlightthickness=0)
        self.history_listbox.pack(fill="x", expand=True)
        self.update_history()
        self.build_plugins_tab()
        self.build_plugin_store_tab()
        self.build_settings_tab()

    def build_mini_gui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.status_canvas = tk.Canvas(self.root, width=60, height=60, bg="#181c29", highlightthickness=0)
        self.status_canvas.pack(pady=(10, 0))
        self.pulse_radius = 20
        self.pulse_grow = True
        self.animate_pulse = True
        self.draw_status_circle()
        self.animate_status_circle()
        self.mini_btn = tb.Button(self.root, text="Zurück", command=self.toggle_mini_mode, bootstyle="secondary-outline")
        self.mini_btn.pack(pady=(0, 5))
        self.create_tooltip(self.mini_btn, "Zurück zur Vollansicht")
        self.start_btn = tb.Button(self.root, text="Spracherkennung starten", command=self.toggle_listen, bootstyle="info-outline", width=22)
        self.start_btn.pack(pady=(0, 5))
        self.create_tooltip(self.start_btn, "Spracherkennung starten/stoppen")
        # Verlauf
        self.history_listbox = tk.Listbox(self.root, height=5, bg="#232b3a", fg="#00eaff", font=("Consolas", 10), borderwidth=0, highlightthickness=0)
        self.history_listbox.pack(fill="x", expand=True, padx=10, pady=(0, 10))
        self.update_history()

    def toggle_mini_mode(self):
        self.mini_mode = not self.mini_mode
        self.build_gui()

    def draw_status_circle(self):
        self.status_canvas.delete("all")
        x, y = 30, 30
        r = self.pulse_radius
        color = "#00eaff" if self.is_listening else "#444a5a"
        self.status_canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="#00eaff", width=3)
        self.status_canvas.create_oval(x - 10, y - 10, x + 10, y + 10, fill="#181c29", outline="#00eaff", width=2)
        if self.is_listening:
            self.status_canvas.create_text(x, y, text="●", fill="#00eaff", font=("Segoe UI", 18, "bold"))
        else:
            self.status_canvas.create_text(x, y, text="", fill="#00eaff")

    def animate_status_circle(self):
        if self.animate_pulse:
            if self.is_listening:
                if self.pulse_grow:
                    self.pulse_radius += 1
                    if self.pulse_radius >= 28:
                        self.pulse_grow = False
                else:
                    self.pulse_radius -= 1
                    if self.pulse_radius <= 20:
                        self.pulse_grow = True
            else:
                self.pulse_radius = 20
            self.draw_status_circle()
            self.root.after(60, self.animate_status_circle)

    def create_tooltip(self, widget, text):
        tooltip = tk.Toplevel(widget)
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        label = tk.Label(tooltip, text=text, background="#232b3a", foreground="#00eaff", font=("Segoe UI", 9), borderwidth=1, relief="solid")
        label.pack()
        def enter(event):
            x = widget.winfo_rootx() + 40
            y = widget.winfo_rooty() + 20
            tooltip.geometry(f"+{x}+{y}")
            tooltip.deiconify()
        def leave(event):
            tooltip.withdraw()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def update_history(self):
        self.history_listbox.delete(0, tk.END)
        for entry in self.history[-10:][::-1]:
            self.history_listbox.insert(tk.END, entry)

    def append_text(self, msg):
        self.textbox.config(state="normal")
        self.textbox.insert(tk.END, msg)
        self.textbox.see(tk.END)
        self.textbox.config(state="disabled")
        if msg.strip():
            self.speak(msg.strip().split("\n")[-1])
        logging.info(msg.strip())

    def toggle_listen(self):
        if not self.is_listening:
            self.is_listening = True
            self.start_btn.config(text="Stopp")
            self.textbox.config(state="normal")
            self.textbox.insert(tk.END, "Spracherkennung läuft...\n")
            self.textbox.config(state="disabled")
            self.listen_thread = threading.Thread(target=self.listen_loop, daemon=True)
            self.listen_thread.start()
        else:
            self.is_listening = False
            self.start_btn.config(text="Spracherkennung starten")

    def listen_loop(self):
        # Index aus Auswahl extrahieren
        sel = self.device_combo.current()
        if sel < 0 or sel >= len(self.input_devices):
            self.append_text("Fehler: Kein Mikrofon ausgewählt!\n")
            return
        device_index = self.input_devices[sel][0]
        q = queue.Queue()
        def callback(indata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            q.put(bytes(indata))
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback, device=device_index):
                rec = KaldiRecognizer(model, 16000)
                while self.is_listening:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result = rec.Result()
                        text = json.loads(result)["text"]
                        self.append_text(f"Erkannt: {text}\n")
                        execute_command(text)
        except Exception as e:
            self.append_text(f"Fehler beim Starten des Mikrofons: {e}\n")

    def rename_hotword(self):
        def apply_new_hotword():
            new_word = entry.get().strip()
            if new_word:
                self.hotword_var.set(new_word)
                self.hotword_label.config(text=f"Aktuelles Hotword: {new_word}")
                self.rename_btn.config(text=f"{new_word} umbenennen")
                popup.destroy()
        popup = tb.Toplevel(self.root)
        popup.title("Hotword ändern")
        popup.geometry("300x100")
        popup.resizable(False, False)
        ttk.Label(popup, text="Neues Hotword eingeben:").pack(pady=10)
        entry = ttk.Entry(popup)
        entry.insert(0, self.hotword_var.get())
        entry.pack(pady=2)
        ttk.Button(popup, text="Übernehmen", command=apply_new_hotword).pack(pady=5)
        entry.focus()

    def show_commands_popup(self):
        # Admin-Befehle (benötigen erhöhte Rechte)
        admin_cmds = [
            "shutdown", "restart", "adduser", "deluser", "renamepc", "startservice", "stopservice", "firewallenable", "firewalldisable", "mapdrive", "disconnectdrive", "sfc", "chkdsk", "restore", "driverupdate", "gpedit", "regedit", "taskschd", "defenderscan", "renewip", "flushdns", "eventvwr"
        ]
        admin_categories = [
            ("shutdown", "PC herunterfahren"),
            ("restart", "PC neu starten"),
            ("adduser", "Benutzer anlegen"),
            ("deluser", "Benutzer löschen"),
            ("renamepc", "PC umbenennen"),
            ("startservice", "Dienst starten"),
            ("stopservice", "Dienst stoppen"),
            ("firewallenable", "Firewall aktivieren"),
            ("firewalldisable", "Firewall deaktivieren"),
            ("mapdrive", "Netzlaufwerk verbinden"),
            ("disconnectdrive", "Netzlaufwerk trennen"),
            ("sfc", "Systemdateien prüfen"),
            ("chkdsk", "Festplatte prüfen"),
            ("restore", "Systemwiederherstellung"),
            ("driverupdate", "Treiber aktualisieren"),
            ("gpedit", "Gruppenrichtlinien öffnen"),
            ("regedit", "Registry Editor öffnen"),
            ("taskschd", "Aufgabenplanung öffnen"),
            ("defenderscan", "Windows Defender Scan"),
            ("renewip", "IP-Adresse erneuern"),
            ("flushdns", "DNS-Cache leeren"),
            ("eventvwr", "Systemprotokolle anzeigen")
        ]
        # Icons für Kategorien und Befehle
        cat_icons = {
            "System": "🖥️",
            "Programme": "📦",
            "Internet & Netzwerk": "🌐",
            "Medien & Anzeige": "🖼️",
            "Audio & Lautstärke": "🔊",
            "Sonstiges": "✨",
            "Normale Befehle": "✅",
            "Admin-Befehle": "🔒"
        }
        cmd_icons = {
            "shutdown": "⏻", "restart": "🔄", "lock": "🔒", "sysinfo": "ℹ️", "renamepc": "🖥️", "adduser": "➕", "deluser": "➖", "sfc": "🛠️", "chkdsk": "💽", "restore": "⏪", "driverupdate": "⬆️", "gpedit": "⚙️", "regedit": "📝", "taskschd": "⏰", "defenderscan": "🛡️", "eventvwr": "📋",
            "notepad": "📝", "calc": "🧮", "explorer": "🗂️", "cmd": "💻", "powershell": "💻", "control": "⚙️", "devmgmt": "🖧", "paint": "🎨", "snipping": "✂️", "settings": "⚙️", "powercfg": "🔋", "taskmgr": "📊", "calendar": "📅", "downloads": "⬇️", "documents": "📄", "desktop": "🖥️", "pictures": "🖼️", "music": "🎵", "videos": "🎬",
            "chrome": "🌐", "firefox": "🦊", "edge": "🌀", "teams": "👥", "zoom": "🎥", "discord": "💬", "steam": "🎮", "spotify": "🎵", "outlook": "📧", "wlanon": "📶", "wlanoff": "📶", "netreset": "🔄", "winupdate": "⬆️", "airplaneon": "✈️", "airplaneoff": "✈️", "renewip": "🔄", "flushdns": "💧", "mapdrive": "🗃️", "disconnectdrive": "❌",
            "vlc": "🎬", "word": "📄", "excel": "📊", "screenshot": "📸", "showdesktop": "🖥️", "minimize": "➖", "maximize": "➕", "brightnessup": "🔆", "brightnessdown": "🔅", "monoff": "🖥️", "rotate": "🔃",
            "volup": "🔊", "voldown": "🔉", "mute": "🔇", "maxvol": "📢", "speakermute": "🔇", "speakeron": "🔊",
            "clipboard": "📋", "clearclipboard": "🧹", "recyclebin": "🗑️", "bton": "📶", "btoff": "📶", "time": "⏰", "startservice": "▶️", "stopservice": "⏹️"
        }
        # Kategorien für normale Befehle
        categories = {
            "System": [
                ("lock", "PC sperren"),
                ("sysinfo", "Systeminformationen anzeigen"),
                ("speakermute", "Lautsprecher stummschalten"),
                ("speakeron", "Lautsprecher aktivieren"),
                ("time", "Uhrzeit/Datum anzeigen"),
            ],
            "Programme": [
                ("notepad", "Editor"),
                ("calc", "Rechner"),
                ("explorer", "Explorer"),
                ("cmd", "Eingabeaufforderung"),
                ("powershell", "Powershell"),
                ("control", "Systemsteuerung"),
                ("devmgmt", "Geräte-Manager"),
                ("paint", "Paint"),
                ("snipping", "Snipping Tool"),
                ("settings", "Einstellungen"),
                ("powercfg", "Energieoptionen"),
                ("taskmgr", "Taskmanager"),
                ("calendar", "Kalender"),
                ("downloads", "Downloads-Ordner"),
                ("documents", "Dokumente-Ordner"),
                ("desktop", "Desktop-Ordner"),
                ("pictures", "Bilder-Ordner"),
                ("music", "Musik-Ordner"),
                ("videos", "Videos-Ordner"),
            ],
            "Internet & Netzwerk": [
                ("chrome", "Google Chrome"),
                ("firefox", "Firefox"),
                ("edge", "Microsoft Edge"),
                ("teams", "Microsoft Teams"),
                ("zoom", "Zoom"),
                ("discord", "Discord"),
                ("steam", "Steam"),
                ("spotify", "Spotify"),
                ("outlook", "Outlook"),
                ("wlanon", "WLAN aktivieren"),
                ("wlanoff", "WLAN deaktivieren"),
                ("netreset", "Netzwerk zurücksetzen"),
                ("winupdate", "Windows Update"),
                ("airplaneon", "Flugmodus an"),
                ("airplaneoff", "Flugmodus aus"),
            ],
            "Medien & Anzeige": [
                ("vlc", "VLC Player"),
                ("word", "Word"),
                ("excel", "Excel"),
                ("screenshot", "Screenshot"),
                ("showdesktop", "Desktop anzeigen"),
                ("minimize", "Alle Fenster minimieren"),
                ("maximize", "Fenster maximieren"),
                ("brightnessup", "Bildschirm heller"),
                ("brightnessdown", "Bildschirm dunkler"),
                ("monoff", "Bildschirm ausschalten"),
                ("rotate", "Bildschirm drehen"),
            ],
            "Audio & Lautstärke": [
                ("volup", "Lauter"),
                ("voldown", "Leiser"),
                ("mute", "Stummschalten"),
                ("maxvol", "Maximale Lautstärke"),
            ],
            "Sonstiges": [
                ("clipboard", "Zwischenablage anzeigen"),
                ("clearclipboard", "Zwischenablage leeren"),
                ("recyclebin", "Papierkorb leeren"),
                ("bton", "Bluetooth aktivieren"),
                ("btoff", "Bluetooth deaktivieren"),
            ]
        }
        # Synonyme wie in execute_command
        commands = {
            "notepad": ["öffne editor", "starte editor", "notepad", "öffne notepad", "starte notepad", "editor öffnen"],
            "chrome": ["starte chrome", "öffne chrome", "chrome öffnen", "öffne den chrome", "starte den chrome", "google chrome"],
            "explorer": ["öffne explorer", "starte explorer", "explorer öffnen", "dateimanager", "dateien anzeigen"],
            "taskmgr": ["öffne taskmanager", "starte taskmanager", "taskmanager", "task-manager", "task manager"],
            "calc": ["öffne rechner", "starte rechner", "rechner", "calculator", "calc"],
            "shutdown": ["fahre herunter", "herunterfahren", "pc herunterfahren", "computer ausschalten", "shutdown"],
            "restart": ["starte neu", "neustarten", "pc neustarten", "computer neu starten", "restart"],
            "lock": ["sperre pc", "bildschirm sperren", "sperren", "lock"],
            "sysinfo": ["zeige systeminfo", "systeminfo", "system informationen", "system anzeigen"],
            "volup": ["lauter", "lautstärke lauter", "volume up", "lauter machen"],
            "voldown": ["leiser", "lautstärke leiser", "volume down", "leiser machen"],
            "mute": ["stummschalten", "lautstärke aus", "mute", "ton aus"],
            "maxvol": ["lautstärke maximal", "lautstärke auf maximum", "maximale lautstärke", "volume max"],
            "minimize": ["fenster minimieren", "minimiere fenster", "alles minimieren", "minimize window"],
            "maximize": ["fenster maximieren", "maximiere fenster", "maximize window"],
            "showdesktop": ["desktop anzeigen", "zeige desktop", "zeige den desktop", "show desktop"],
            "screenshot": ["screenshot", "bildschirmfoto", "screenshot machen", "screenshot erstellen"],
            "recyclebin": ["papierkorb leeren", "leere papierkorb", "recycle bin leeren", "papierkorb löschen"],
            "time": ["wie spät ist es", "uhrzeit", "wie viel uhr", "zeit anzeigen", "datum anzeigen", "welches datum"],
            "wlanoff": ["wlan deaktivieren", "wlan aus", "wifi aus", "wifi deaktivieren"],
            "wlanon": ["wlan aktivieren", "wlan an", "wifi an", "wifi aktivieren"],
            "monoff": ["bildschirm ausschalten", "monitor aus", "display aus", "bildschirm aus"],
            "clipboard": ["zwischenablage anzeigen", "zeige zwischenablage", "clipboard anzeigen"],
            "spotify": ["öffne spotify", "starte spotify", "spotify"],
            "outlook": ["öffne outlook", "starte outlook", "outlook"],
            "word": ["öffne word", "starte word", "word"],
            "excel": ["öffne excel", "starte excel", "excel"],
            "paint": ["öffne paint", "starte paint", "paint"],
            "cmd": ["öffne cmd", "starte cmd", "eingabeaufforderung", "command prompt"],
            "powershell": ["öffne powershell", "starte powershell", "powershell"],
            "control": ["öffne systemsteuerung", "systemsteuerung", "control panel"],
            "devmgmt": ["öffne geräte-manager", "geräte-manager", "device manager"],
            "bton": ["bluetooth aktivieren", "bluetooth an", "bluetooth einschalten"],
            "btoff": ["bluetooth deaktivieren", "bluetooth aus", "bluetooth ausschalten"],
            "firefox": ["öffne firefox", "starte firefox", "firefox"],
            "edge": ["öffne edge", "starte edge", "microsoft edge", "edge"],
            "teams": ["öffne teams", "starte teams", "microsoft teams", "teams"],
            "zoom": ["öffne zoom", "starte zoom", "zoom"],
            "discord": ["öffne discord", "starte discord", "discord"],
            "steam": ["öffne steam", "starte steam", "steam"],
            "vlc": ["öffne vlc", "starte vlc", "vlc", "vlc player"],
            "calendar": ["öffne kalender", "starte kalender", "kalender", "calendar"],
            "snipping": ["öffne snipping tool", "starte snipping tool", "snipping tool", "ausschnitt tool"],
            "settings": ["öffne einstellungen", "starte einstellungen", "einstellungen", "settings"],
            "powercfg": ["energieoptionen", "energieoptionen öffnen", "power options"],
            "brightnessup": ["bildschirm heller", "helligkeit erhöhen", "bildschirmhelligkeit erhöhen", "heller machen"],
            "brightnessdown": ["bildschirm dunkler", "helligkeit verringern", "bildschirmhelligkeit verringern", "dunkler machen"],
            "airplaneon": ["flugmodus aktivieren", "flugmodus an", "airplane mode on", "flugmodus einschalten"],
            "airplaneoff": ["flugmodus deaktivieren", "flugmodus aus", "airplane mode off", "flugmodus ausschalten"],
            "speakermute": ["lautsprecher stummschalten", "lautsprecher aus", "speaker mute"],
            "speakeron": ["lautsprecher aktivieren", "lautsprecher an", "speaker on"],
            "netreset": ["netzwerk zurücksetzen", "netzwerk reset", "network reset"],
            "winupdate": ["windows update starten", "starte windows update", "update starten", "windows update"],
            "rotate": ["bildschirm drehen", "bildschirm rotieren", "screen rotate"],
            "clearclipboard": ["zwischenablage leeren", "clipboard leeren", "clear clipboard"],
            "downloads": ["öffne downloads", "downloads anzeigen", "explorer downloads"],
            "documents": ["öffne dokumente", "dokumente anzeigen", "explorer dokumente"],
            "desktop": ["öffne desktop", "desktop anzeigen", "explorer desktop"],
            "pictures": ["öffne bilder", "bilder anzeigen", "explorer bilder"],
            "music": ["öffne musik", "musik anzeigen", "explorer musik"],
            "videos": ["öffne videos", "videos anzeigen", "explorer videos"],
            "adduser": ["benutzer anlegen", "benutzerkonto erstellen", "neuen benutzer erstellen", "add user"],
            "deluser": ["benutzer löschen", "benutzerkonto löschen", "user löschen", "delete user"],
            "renamepc": ["computer umbenennen", "pc umbenennen", "rename computer", "rename pc"],
            "startservice": ["dienst starten", "service starten", "starte dienst", "starte service"],
            "stopservice": ["dienst stoppen", "service stoppen", "stoppe dienst", "stoppe service"],
            "firewallenable": ["firewall aktivieren", "firewall einschalten", "firewall enable"],
            "firewalldisable": ["firewall deaktivieren", "firewall ausschalten", "firewall disable"],
            "mapdrive": ["netzlaufwerk verbinden", "netzlaufwerk zuordnen", "netzlaufwerk verbinden"],
            "disconnectdrive": ["netzlaufwerk trennen", "netzlaufwerk entfernen", "netzlaufwerk trennen"],
            "sfc": ["systemdateien prüfen", "sfc scannow", "systemdateien überprüfen"],
            "chkdsk": ["festplatte prüfen", "chkdsk", "festplatte überprüfen"],
            "restore": ["systemwiederherstellung", "system wiederherstellen", "system restore"],
            "driverupdate": ["treiber aktualisieren", "treiber updaten", "update treiber"],
            "gpedit": ["gruppenrichtlinien öffnen", "gruppenrichtlinien", "gpedit"],
            "regedit": ["registry editor öffnen", "regedit", "registry editor"],
            "taskschd": ["aufgabenplanung öffnen", "aufgabenplanung", "task scheduler"],
            "defenderscan": ["windows defender scan", "defender scan", "windows defender durchsuchen"],
            "renewip": ["ip adresse erneuern", "ip erneuern", "renew ip"],
            "flushdns": ["dns cache leeren", "dns leeren", "flush dns"],
            "eventvwr": ["systemprotokolle anzeigen", "ereignisanzeige öffnen", "event viewer"],
            "showcommands": ["befehle anzeigen", "zeige befehle", "alle befehle", "hilfe", "was kann ich sagen"]
        }
        popup = tb.Toplevel(self.root)
        popup.title("Alle Sprachbefehle")
        popup.geometry("750x700")
        popup.resizable(True, True)
        popup.configure(bg="#181c29")
        label = tb.Label(popup, text="Alle verfügbaren Sprachbefehle", font=("Segoe UI", 16, "bold"), bootstyle="info-inverse", background="#181c29")
        label.pack(pady=(15, 5))
        # Suchfeld
        search_var = tk.StringVar()
        search_entry = tb.Entry(popup, textvariable=search_var, font=("Segoe UI", 12), bootstyle="info", width=40)
        search_entry.pack(pady=(0, 10))
        # Canvas/Scroll
        canvas = tb.Canvas(popup, background="#181c29", borderwidth=0, highlightthickness=0)
        scrollbar = tb.Scrollbar(popup, orient="vertical", command=canvas.yview, bootstyle="info-round")
        scroll_frame = tb.Frame(canvas, bootstyle="dark")
        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(20,0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        # Rendering-Funktion
        def render_commands():
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            # Normale Befehle
            norm_label = tb.Label(scroll_frame, text=f"{cat_icons['Normale Befehle']} Normale Befehle", font=("Segoe UI", 14, "bold"), bootstyle="success-inverse", background="#232b3a")
            norm_label.pack(anchor="w", pady=(10, 3), padx=10)
            filter_text = search_var.get().lower()
            for cat, items in categories.items():
                cat_label = tb.Label(scroll_frame, text=f"{cat_icons.get(cat, '')} {cat}", font=("Segoe UI", 13, "bold"), bootstyle="primary-inverse", background="#232b3a")
                cat_label.pack(anchor="w", pady=(15, 3), padx=10)
                for cmd, beschr in items:
                    if cmd in admin_cmds:
                        continue
                    syns = commands.get(cmd, [])
                    # Filter
                    if filter_text and not (filter_text in beschr.lower() or filter_text in cmd.lower() or any(filter_text in s.lower() for s in syns)):
                        continue
                    icon = cmd_icons.get(cmd, "•")
                    cmd_label = tb.Label(scroll_frame, text=f"{icon} {beschr}  [{cmd}]", font=("Segoe UI", 11, "bold"), bootstyle="secondary", background="#232b3a")
                    cmd_label.pack(anchor="w", padx=25)
                    syn_label = tb.Label(scroll_frame, text="Synonyme: " + ", ".join(syns), font=("Segoe UI", 9), bootstyle="info", background="#232b3a")
                    syn_label.pack(anchor="w", padx=40, pady=(0, 5))
            # Admin-Befehle nur wenn Admin
            if is_admin:
                admin_label = tb.Label(scroll_frame, text=f"{cat_icons['Admin-Befehle']} Admin-Befehle (benötigen Administratorrechte)", font=("Segoe UI", 14, "bold"), bootstyle="danger-inverse", background="#232b3a")
                admin_label.pack(anchor="w", pady=(20, 3), padx=10)
                for cmd, beschr in admin_categories:
                    syns = commands.get(cmd, [])
                    # Filter
                    if filter_text and not (filter_text in beschr.lower() or filter_text in cmd.lower() or any(filter_text in s.lower() for s in syns)):
                        continue
                    icon = cmd_icons.get(cmd, "•")
                    cmd_label = tb.Label(scroll_frame, text=f"{icon} {beschr}  [{cmd}]", font=("Segoe UI", 11, "bold"), bootstyle="warning", background="#232b3a")
                    cmd_label.pack(anchor="w", padx=25)
                    syn_label = tb.Label(scroll_frame, text="Synonyme: " + ", ".join(syns), font=("Segoe UI", 9), bootstyle="info", background="#232b3a")
                    syn_label.pack(anchor="w", padx=40, pady=(0, 5))
            else:
                admin_label = tb.Label(scroll_frame, text=f"{cat_icons['Admin-Befehle']} Admin-Befehle werden nur mit Administratorrechten angezeigt!", font=("Segoe UI", 12, "bold"), bootstyle="danger-inverse", background="#232b3a")
                admin_label.pack(anchor="w", pady=(20, 3), padx=10)
        render_commands()
        search_var.trace_add("write", lambda *args: render_commands())
        tb.Button(popup, text="Schließen", command=popup.destroy, bootstyle="danger-outline").pack(pady=10)

    def execute_plugin_command(self, text):
        for name, func in PLUGINS.items():
            if not PLUGIN_STATUS.get(name, True):
                continue
            try:
                if func(text, self):
                    logging.info(f'Plugin {name} hat Befehl verarbeitet: {text}')
                    return True
            except Exception as e:
                logging.error(f'Plugin {name} Fehler: {e}')
        return False

    def show_update_hint(self, version):
        tb.Messagebox.ok(f'Neue Version verfügbar: {version}\nBitte aktualisiere über GitHub!', title='Update verfügbar', alert=True)

    def show_alexa_hint(self, cmd):
        if self.alexa_gui_msg:
            self.alexa_gui_msg.destroy()
        self.alexa_gui_msg = tb.Label(self.root, text=f'Alexa-Befehl empfangen: {cmd}', bootstyle='success', font=("Segoe UI", 10, "bold"), background="#181c29")
        self.alexa_gui_msg.pack(pady=5)
        self.root.after(3000, lambda: self.alexa_gui_msg.destroy())

    def build_plugins_tab(self):
        for widget in self.plugins_tab.winfo_children():
            widget.destroy()
        tb.Label(self.plugins_tab, text="Geladene Plugins:", font=("Segoe UI", 13, "bold"), bootstyle="primary").pack(anchor="w", pady=(10, 5), padx=10)
        for name in PLUGINS:
            frame = tb.Frame(self.plugins_tab, bootstyle="dark")
            frame.pack(fill="x", padx=10, pady=3)
            status = PLUGIN_STATUS.get(name, True)
            color = "success" if status else "danger"
            status_label = tb.Label(frame, text="aktiv" if status else "deaktiviert", bootstyle=f"{color}-inverse", width=10)
            status_label.pack(side="left", padx=(0, 8))
            name_label = tb.Label(frame, text=name, font=("Consolas", 11, "bold"), bootstyle="secondary")
            name_label.pack(side="left", padx=(0, 8))
            tb.Button(frame, text="Details", command=lambda n=name: self.show_plugin_details(n), bootstyle="info-outline").pack(side="left", padx=2)
            if status:
                tb.Button(frame, text="Deaktivieren", command=lambda n=name: self.toggle_plugin(n, False), bootstyle="danger-outline").pack(side="left", padx=2)
            else:
                tb.Button(frame, text="Aktivieren", command=lambda n=name: self.toggle_plugin(n, True), bootstyle="success-outline").pack(side="left", padx=2)
            tb.Button(frame, text="Reload", command=lambda n=name: self.reload_plugin(n), bootstyle="warning-outline").pack(side="left", padx=2)
    def update_plugin_gui(self):
        self.build_plugins_tab()
    def toggle_plugin(self, name, active):
        PLUGIN_STATUS[name] = active
        self.update_plugin_gui()
    def reload_plugin(self, name):
        path = f'plugins/{name}.py'
        if not os.path.exists(path):
            return
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, 'register'):
                PLUGINS[name] = mod.register
                logging.info(f'Plugin neu geladen: {name}')
        except Exception as e:
            logging.error(f'Fehler beim Reload von Plugin {name}: {e}')
        self.update_plugin_gui()
    def show_plugin_details(self, name):
        path = f'plugins/{name}.py'
        doc = ""
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
                if lines and lines[0].startswith('"""'):
                    doc = lines[0].strip('"\n ')
        except Exception:
            pass
        mtime = os.path.getmtime(path) if os.path.exists(path) else 0
        import datetime
        popup = tb.Toplevel(self.root)
        popup.title(f"Plugin-Details: {name}")
        popup.geometry("400x250")
        popup.configure(bg="#181c29")
        tb.Label(popup, text=f"Name: {name}", font=("Segoe UI", 12, "bold"), bootstyle="primary", background="#181c29").pack(anchor="w", pady=(15, 2), padx=15)
        tb.Label(popup, text=f"Pfad: {path}", font=("Consolas", 9), background="#181c29", foreground="#00eaff").pack(anchor="w", padx=15)
        tb.Label(popup, text=f"Letzte Änderung: {datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S') if mtime else 'unbekannt'}", font=("Segoe UI", 9), background="#181c29", foreground="#00eaff").pack(anchor="w", padx=15, pady=(0, 8))
        tb.Label(popup, text=f"Docstring: {doc if doc else '---'}", font=("Segoe UI", 10), background="#181c29", foreground="#00eaff", wraplength=360, justify="left").pack(anchor="w", padx=15, pady=(0, 8))
        tb.Button(popup, text="Schließen", command=popup.destroy, bootstyle="danger-outline").pack(pady=10)

    def build_settings_tab(self):
        for widget in self.settings_tab.winfo_children():
            widget.destroy()
        tb.Label(self.settings_tab, text="Einstellungen (in Entwicklung)", font=("Segoe UI", 13, "bold"), bootstyle="primary").pack(pady=20)

    def fetch_plugin_list(self):
        try:
            response = requests.get(PLUGIN_STORE_URL)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.append_text(f"Fehler beim Laden des Plugin Stores: {e}\n")
            return []

    def build_plugin_store_tab(self):
        for widget in self.plugin_store_tab.winfo_children():
            widget.destroy()
        tb.Label(self.plugin_store_tab, text="Plugin Store", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor="w", pady=(10, 5), padx=10)
        plugins = self.fetch_plugin_list()
        for plugin in plugins:
            frame = tb.Frame(self.plugin_store_tab, bootstyle="dark")
            frame.pack(fill="x", padx=10, pady=3)
            tb.Label(frame, text=plugin["name"], font=("Consolas", 11, "bold"), bootstyle="secondary").pack(side="left", padx=(0, 8))
            tb.Label(frame, text=plugin["description"], bootstyle="info").pack(side="left", padx=(0, 8))
            install_btn = tb.Button(frame, text="Installieren", command=lambda p=plugin: self.install_plugin(p), bootstyle="success-outline")
            install_btn.pack(side="right", padx=2)
            uninstall_btn = tb.Button(frame, text="Deinstallieren", command=lambda p=plugin: self.uninstall_plugin(p), bootstyle="danger-outline")
            uninstall_btn.pack(side="right", padx=2)

    def install_plugin(self, plugin):
        try:
            response = requests.get(PLUGIN_REPO_ZIP)
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                plugin_path = plugin["path"].strip("/")
                found = False
                for member in z.namelist():
                    if member.startswith(f"Jarvis-Plugins-main/{plugin_path}/"):
                        z.extract(member, "plugins_temp")
                        found = True
                if not found:
                    self.append_text(f"Plugin-Ordner nicht im ZIP gefunden: {plugin_path}\n")
                    return
                src = os.path.join("plugins_temp", "Jarvis-Plugins-main", plugin_path)
                dst = os.path.join("plugins", plugin_path)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
            shutil.rmtree("plugins_temp")
            self.append_text(f"Plugin '{plugin['name']}' installiert!\n")
            self.load_plugins()
        except Exception as e:
            self.append_text(f"Fehler bei Installation: {e}\n")

    def uninstall_plugin(self, plugin):
        try:
            dst = os.path.join("plugins", plugin["path"].strip("/"))
            if os.path.exists(dst):
                shutil.rmtree(dst)
                self.append_text(f"Plugin '{plugin['name']}' deinstalliert!\n")
                self.load_plugins()
            else:
                self.append_text(f"Plugin nicht gefunden: {plugin['name']}\n")
        except Exception as e:
            self.append_text(f"Fehler bei Deinstallation: {e}\n")

class PluginReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            load_plugins()
            if 'app' in globals() and hasattr(app, 'update_plugin_gui'):
                app.update_plugin_gui()

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = VoiceControlApp(root)
    root.mainloop()

# Starte Plugin-Überwachung
observer = Observer()
observer.schedule(PluginReloadHandler(), path='plugins', recursive=False)
observer.start() 