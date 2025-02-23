# MTA Subway Times Display

## Hardware 
- Raspberry Pi Zero 2 W
- Adafruit RGB Matrix Bonnet
- Adafruit 64x32 RGB LED Matrix
- 5V 4A Power Supply
- MicroSD Card

## Software
- RaspbianPI OS
- Python 3.9

## Setup
### 1. Install Raspbian
1. Download the latest Raspbian image from the official website: https://www.raspberrypi.org/downloads/raspbian/
2. Write the image to the SD card using Etcher: https://etcher.io/
3. Insert the SD card into the Raspberry Pi and boot it up.
4. Follow the on-screen instructions to set up the system.
5. Update the system by running the following commands:
```bash
sudo apt-get update
sudo apt-get upgrade
```
6. Reboot the system to apply the changes.
```bash
sudo reboot
```

### Install Python
1. Check if Python is already installed by running the following command:
```bash
python --version
```
2. If Python is not installed, install it by running the following command:
```bash
sudo apt-get install python3
```
3. Check if Python is installed correctly by running the following command:
```bash
python --version
```

### Install Git
1. Check if Git is already installed by running the following command:
```bash
git --version
```
2. If Git is not installed, install it by running the following command:
```bash
sudo apt-get install git
```
3. Check if Git is installed correctly by running the following command:
```bash
git --version
```

### Clone the Repository
1. Clone the repository to your Raspberry Pi by running the following command:
```bash
git clone
```
2. Navigate to the repository directory by running the following command:
```bash
cd
```
3. Install the required Python packages by running the following command:
```bash
pip install -r requirements.txt
```

### Update and Configure Bonnet
1. Update the Bonnet by running the following command:
```bash
curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh >rgb-matrix.sh
sudo bash rgb-matrix.sh
```


### Run the Program
1. SSH into the Raspberry Pi by running the following command:
```bash
ssh pi@raspberrypi.local
```
2. Run the program by running the following command:
```bash
cd "repos/pi-subway-times"
sudo python "pizero/src/main.py"
```
2. The program will start running and display the output on the screen.
3. Press `Ctrl + C` to stop the program.