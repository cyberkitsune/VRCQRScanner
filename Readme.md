# VRCQRScanner
This project is a VRChat companion utility -- the goal is to allow you to scan QR codes from within VRChat!

Currently, this is done by using the "Spout Stream" feature of the VRC camera. Every half a second, a frame is collected for QR Code recognition using OpenCV.

The detected QR Codes go into the application, where you can copy them to your clipboard or open them in a browser. (They do not open in a browser automatically)

Additionally, the following is also supported:
- Automatically copy the QR code to the clipboard
- Send the QR code to your chatbox
- Send the QR code as an XSOverlay notification

## Usage
I will set up a binary release in the future, for now, run from source as described below

## Running from Source
### Requirements
- Python3 in path
### Instructions
Clone the repo, and open a terminal in the repo's folder. Then run the following:
```
pip install -r Requirements.txt
python src\vrc_qr_scanner.py
```

## Known Issues
- The GUI is not complete and has many issues! I will clean it up later.
- QR Codes with non-standard tracking points may not scan.
- Some QR codes with standard tracking points but have row resolution may not scan.