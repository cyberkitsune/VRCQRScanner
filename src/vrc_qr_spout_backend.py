from vrc_qr_backend import VRCQRBackend
import threading

from itertools import repeat

import SpoutGL
from OpenGL import GL

import array
import numpy as np

import cv2

import time

RECEIVER_NAME = "VRCSender1"

class VRCSpoutBackend(VRCQRBackend):
    def __init__(self, discovered_callback):
        super().__init__(discovered_callback)
        self.spout = None
        self.spout_thread = None
        self.spout_running = False 

    def is_running(self):
        return self.spout_running

    def start(self):
        if not self.spout_running:
            self.spout_thread = threading.Thread(target=self._spout_thread)
            self.spout_thread.start()
            self.spout_running = True

    def stop(self):
        if self.spout_running:
            self.spout_running = False
            self.spout_thread.join()

    def _spout_thread(self):
        with SpoutGL.SpoutReceiver() as receiver:
            receiver.setReceiverName(RECEIVER_NAME)

            buffer = None
            found_codes = []
            while self.spout_running:
                result = receiver.receiveImage(buffer, GL.GL_RGBA, False, 0)

                if receiver.isUpdated():
                    width = receiver.getSenderWidth()
                    height = receiver.getSenderHeight()
                    buffer = array.array('B', repeat(0, width * height * 4))

                if buffer and result and not SpoutGL.helpers.isBufferEmpty(buffer):
                    # Convert the buffer to a numpy array and reshape it
                    # to the correct dimensions for OpenCV
                    img_data = np.array(buffer, np.uint8)
                    img_data = img_data.reshape((height, width, 4))
                    ocvImg = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            
                    qcd = cv2.QRCodeDetector()
                    retval, decoded_info, points, straight_qrcode = qcd.detectAndDecodeMulti(ocvImg)
                    
                    # Iterate thought detected codes and fire the callback
                    if retval:
                        for info in decoded_info:
                            if info not in found_codes:
                                if info != "":
                                    self.discovered_callback(info)
                
                # Sleep for a bit to avoid leaving the CPU on 100%
                # This should provide around 2FPS of input
                time.sleep(0.5)

                # Wait and sync back up with the video data
                receiver.waitFrameSync(RECEIVER_NAME, 10000)

                    

