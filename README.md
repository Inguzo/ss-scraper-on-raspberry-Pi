# ss-scraper-on-raspberry-Pi
ss.com scraper for cars with specific filter criteria on Raspberry Pi

Setting Up Your BMW Scraper on a Raspberry Pi
A Raspberry Pi is an excellent choice for running your scraper 24/7 with minimal power consumption. Here's a complete guide to set it up:
What You'll Need

A Raspberry Pi (any model will work, even an older one)
SD card with Raspberry Pi OS installed
Power supply for your Pi
Internet connection (Wi-Fi or Ethernet)
Optional: SSH access for remote management

Step 1: Basic Raspberry Pi Setup

Install Raspberry Pi OS on your SD card using the Raspberry Pi Imager tool
Insert the SD card and power on your Raspberry Pi
Complete the initial setup (set username, password, connect to Wi-Fi)
Make sure your Pi has internet access

Step 2: Update Your System
Connect to your Pi (either directly or via SSH) and run:
bashCopysudo apt update
sudo apt upgrade -y
Step 3: Install Required Packages
bashCopysudo apt install -y python3-pip git
pip3 install requests beautifulsoup4
Step 4: Create a Directory for Your Script
bashCopymkdir -p ~/bmw_scraper
cd ~/bmw_scraper
Step 5: Transfer Your Script to the Raspberry Pi
Option A: Create the files directly on the Pi:

Use nano to create your script:
bashCopynano bmw_scraper.py

Paste your script content, then press Ctrl+O to save and Ctrl+X to exit
Create the JSON file:
bashCopyecho "{}" > seen_ads.json


Option B: Transfer from your computer:
If your Pi is on the same network as your computer:
bashCopy# From your computer (replace PI_IP_ADDRESS with your Pi's IP)
scp bmw_scraper.py pi@PI_IP_ADDRESS:~/bmw_scraper/
scp seen_ads.json pi@PI_IP_ADDRESS:~/bmw_scraper/
Step 6: Update Email Settings
Edit your script to include your actual email credentials:
bashCopynano bmw_scraper.py
Find and update these lines:
pythonCopyself.sender_email = "your_email@gmail.com"  # CHANGE THIS
self.sender_password = "your_app_password"  # CHANGE THIS 
self.receiver_email = "your_email@gmail.com"  # CHANGE THIS
Step 7: Test Run Your Script
bashCopycd ~/bmw_scraper
python3 bmw_scraper.py --check-once
Make sure it runs without errors.
Step 8: Setup Automatic Startup
Create a systemd service to run your script automatically and restart it if it crashes:
bashCopysudo nano /etc/systemd/system/bmw-scraper.service
Paste the following (replace "pi" with your username if different):
Copy[Unit]
Description=BMW SS.com Scraper
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/bmw_scraper
ExecStart=/usr/bin/python3 /home/pi/bmw_scraper/bmw_scraper.py
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
Save and exit (Ctrl+O, then Ctrl+X)
Step 9: Enable and Start the Service
bashCopysudo systemctl enable bmw-scraper.service
sudo systemctl start bmw-scraper.service
Step 10: Monitor the Service
Check if it's running:
bashCopysudo systemctl status bmw-scraper.service
View the logs:
bashCopyjournalctl -u bmw-scraper.service -f
Maintenance Tips

Checking script status:
bashCopysudo systemctl status bmw-scraper.service

Restarting the script:
bashCopysudo systemctl restart bmw-scraper.service

Stopping the script:
bashCopysudo systemctl stop bmw-scraper.service

Viewing most recent logs:
bashCopyjournalctl -u bmw-scraper.service -n 50

Setting up remote access to your Pi for easier management:
bashCopysudo raspi-config
# Go to Interface Options → SSH → Enable


Your BMW scraper should now run continuously on your Raspberry Pi, checking for new listings at the specified interval and sending you email notifications when new cars matching your criteria are found.
