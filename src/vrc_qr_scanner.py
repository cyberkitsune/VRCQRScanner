import OpenGL.GL as gl
import glfw
from imgui.integrations.glfw import GlfwRenderer
import imgui
import pyperclip
import webbrowser
import time
from websockets.sync.client import connect
import json
from enum import Enum
from vrc_qr_spout_backend import VRCSpoutBackend
from pythonosc.udp_client import SimpleUDPClient


class LogChannel(Enum):
    ERROR = "E"
    DEBUG = "D"
    INFO = "I"

class VRCQRScanner():
    def __init__(self) -> None:
        self.window = None
        self.ui_running = False
        self.qr_backend = VRCSpoutBackend(self._on_code_found)
        self.log_buffer = []

        self.seen_codes = {}

        self.settings = {
            'repeat_delay': 15,
            'output_xsoverlay': True,
            'output_chatbox': True,
            'output_clipboard': True,
            'show_demo_window': False,
        }
        
        self.qr_backend.start()
        self.log(f"Started QR Backend {self.qr_backend.__class__.__name__}", LogChannel.INFO)

    def log(self, text, log_channel=LogChannel.INFO):
        self.log_buffer.append((log_channel.value, text))

    def run_ui(self):
        imgui.create_context()
        window_status = self._setup_glfw()
        if not window_status:
            self.log("Window creation failed!", LogChannel.ERROR)
            return
        
        impl = GlfwRenderer(self.window)
        self.ui_running = True
        io = imgui.get_io()
        self.log("VRChat QR Code Scanner started!")
        # Window render loop
        while not glfw.window_should_close(self.window):
            glfw.poll_events()
            impl.process_inputs()

            imgui.new_frame()
            

            imgui.set_next_window_size(io.display_size[0], io.display_size[1])
            imgui.set_next_window_position(0, 0)

            imgui.begin("VRChat QR Code Scanner", True, imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_TITLE_BAR)

            if self.qr_backend.is_running():
                imgui.text_colored(f"QR Code scanning is enabled with {self.qr_backend.__class__.__name__}", 0, 1, 0)
                imgui.same_line()
                if imgui.button("Stop"):
                    self.qr_backend.stop()
                    self.log(f"Stopped QR backend {self.qr_backend.__class__.__name__}", LogChannel.INFO)
            else:
                imgui.text_colored("QR Code scanning is not running!", 1, 0, 0)
                imgui.same_line()
                if imgui.button("Start"):
                    self.qr_backend.start()
                    self.log(f"Started QR backend {self.qr_backend.__class__.__name__}", LogChannel.INFO)

            with imgui.begin_tab_bar("##MainTabs"):
                if imgui.begin_tab_item("QRCodes").selected:
                    with imgui.begin_table("##QRCodesTable", 2):
                        imgui.table_setup_column("Code", imgui.TABLE_COLUMN_WIDTH_STRETCH)
                        imgui.table_setup_column("Actions", imgui.TABLE_COLUMN_WIDTH_FIXED)
                        imgui.table_headers_row()

                        for code, data in self.seen_codes.items():
                            imgui.table_next_row()
                            imgui.table_next_column()
                            imgui.text(code)
                            imgui.table_next_column()
                            if imgui.button(f"C##{code}"):
                                imgui.set_clipboard_text(code)
                                self.log(f"Copied {code} to clipboard", LogChannel.INFO)
                            if imgui.is_item_hovered():
                                imgui.set_tooltip(f"Copy {code} to clipboard")
                            imgui.same_line()
                            if imgui.button(f"O##{code}"):
                                webbrowser.open(code)
                                self.log(f"Opened {code} in browser", LogChannel.INFO)
                            if imgui.is_item_hovered():
                                imgui.set_tooltip(f"Open {code} in browser")
                    imgui.end_tab_item()

                if imgui.begin_tab_item("Log").selected:
                    if imgui.begin_child("LogChild", imgui.get_content_region_available()[0], imgui.get_content_region_available()[1], True):
                        for line in self.log_buffer:
                            imgui.text_wrapped(f"[{line[0]}] {line[1]}")
                        imgui.end_child()
                    imgui.end_tab_item()
                
                
                if imgui.begin_tab_item("Settings").selected:
                    imgui.text("Settings is WIP!")
                    for key in self.settings:
                        if type(self.settings[key]) == bool:
                            _, self.settings[key] = imgui.checkbox(key, self.settings[key])
                        elif type(self.settings[key]) == int:
                            _, self.settings[key] = imgui.input_int(key, self.settings[key])
                    imgui.end_tab_item()
                
            imgui.end()

            if self.settings['show_demo_window']:
                imgui.show_test_window()

            gl.glClearColor(0, 0, 0, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

            imgui.render()
            impl.render(imgui.get_draw_data())
            glfw.swap_buffers(self.window)
    
        # Exit render loop (we closed the window)
        impl.shutdown()
        glfw.terminate()

    def cleanup(self):
        self.qr_backend.stop()
    
    def _setup_glfw(self):
        width, height = 800, 700
        window_name = "VRChat QR Code Scanner"
        if not glfw.init():
            self.log("Unable to init GLFW!", LogChannel.ERROR)
            return False

        self.window = glfw.create_window(int(width), int(height), window_name, None, None)
        glfw.make_context_current(self.window)

        if not self.window:
            glfw.terminate()
            self.log("Could not init GLFW Window!", LogChannel.ERROR)
            return False

        return True
    
    def _on_code_found(self, code):
        trigger_actions = False
        if code not in self.seen_codes:
            self.seen_codes[code] = {"last_seen": time.time(), "count": 1}
            self.log(f"Found new code {code}", LogChannel.INFO)
            trigger_actions = True
        elif self.seen_codes[code]["last_seen"] + self.settings['repeat_delay'] < time.time():
            self.seen_codes[code]["last_seen"] = time.time()
            self.seen_codes[code]["count"] += 1
            self.log(f"Updated code {code}", LogChannel.DEBUG)
            trigger_actions = True

        if trigger_actions:
            if self.settings['output_xsoverlay']:
                self._send_xs_notification(code)
            if self.settings['output_chatbox']:
                self._send_chatbox(f"Copied: {code}")
            if self.settings['output_clipboard']:
                pyperclip.copy(code)


    def _send_xs_notification(self, text):
        APP_NAME = "VRChatQRScanner"
        msg = {
            'sender': APP_NAME,
            'target': "xsoverlay",
            'command': "SendNotification",
            'jsonData': json.dumps({
                'type': 1,
                'title': "QR Code Copied!",
                'content': text,
                'timeout': 2.5,
                'audioPath': "default"
            }),
            'rawData': None
        }
        message = json.dumps(msg)
        try:
            with connect(f"ws://127.0.0.1:42070/?client={APP_NAME}") as ws:
                self.log(message, LogChannel.DEBUG)
                ws.send(message)
                time.sleep(1)
        except Exception as e:
            self.log(f"Error sending XSO Notification: {e}", LogChannel.ERROR)

    def _send_chatbox(self, text):
        client = SimpleUDPClient("127.0.0.1", 9000)
        client.send_message("/chatbox/input", [f"QR: {text}", True, False])
    

if __name__ == "__main__":
    app = VRCQRScanner()
    app.run_ui()
    app.cleanup()