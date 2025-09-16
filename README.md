# PhoneWave

SIP-based Smart Plug Controller for Raspberry Pi. Spiritual successor to [SIP-Pi](https://github.com/KawaiiFiveO/SIP-Pi), remade from the ground up.

Can be modified to support other types of smart plugs or displays.

Currently in development. Expect breaking changes.

### Requirements

- Raspberry Pi (tested on Pi 4 Model B) or other device capable of Python and PJSIP
- [EZPlug v2](https://www.th3dstudio.com/product/ezplug-open-source-wifi-smart-plug/) or other smart plug with open API
- [PiOLED](https://www.amazon.com/dp/B07V4FRSKK) or other display (optional)
- Any appliance you want to control, such as a microwave with a mechanical timer
- A SIP account, such as a free [Telnyx](https://telnyx.com/) account

### Instructions

1. Configure and build [PJSIP](https://github.com/pjsip/pjproject) with the `-fPIC` flag.
2. Clone the repository.
```
git clone https://github.com/KawaiiFiveO/PhoneWave.git
cd PhoneWave
```
3. Create a virtual environment.
```
python -m venv sipenv
source sipenv/bin/activate
```
4. Install SWIG.
```
sudo apt-get install swig
```
5. In the `pjproject` directory, build and install PJSUA2 for Python. Make sure you are in the virtual environment when running the `install` command.
```
cd pjsip-apps/src/swig/python
make
python setup.py install
```
6. Back in the `PhoneWave` directory, copy the config file and edit it with your values.
```
cp config.example config.py
nano config.py
```
You can also change `audio/welcome.wav` to any message of your choice.
7. Install requirements.
```
pip install -r requirements.txt
```
8. Run the program.
```
python main.py
```
9. From your phone, call the phone number of the SIP client. You will hear `welcome.wav`.
10. Enter a time in seconds and press `#` to turn the plug on for that period of time.

### TODO

- Add safety checks/handle edge cases
- Method to run the program in the background or as a service
- Improve display aesthetics