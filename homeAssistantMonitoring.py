"""
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 * Link to my github: 'https://github.com/RaghaniSebastien/HomeAssistantVmMonitoring'
"""

import threading
import os
import subprocess
import requests
from pystray import Icon, MenuItem, Menu
from PIL import Image
from win10toast import ToastNotifier
import time
import logging

# Configuration
VM_NAME = "HomeAssistant"
URL = "http://192.168.1.**:****/"
INITIAL_DELAY = 60  # Initial delay to let VM boot up or restart
CHECK_INTERVAL = 30  # Interval to check the website
TIMEOUT = 5  # Timeout for the HTTP request
VBOXMANAGE_PATH = "C:\\Program Files\\Oracle\\VirtualBox\\VBoxManage.exe"  # Update this path
LOG_FILE = "homeAssistantMonitoring_logs.log"

# Global variables
verbose = False  # Verbose mode flag
toastNotification = False
logs = True

status = "unknown"
checking = True
status_lock = threading.Lock()
checking_lock = threading.Lock()
running_lock = threading.Lock()
running = True

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Create a ToastNotifier object for notifications
toast = ToastNotifier()

def launch_vm():
    """
    Launches or restarts the VM.
    """
    # Check if the VM is running
    vm_running = subprocess.run([VBOXMANAGE_PATH, "showvminfo", VM_NAME], capture_output=True, text=True)
    if "running (since" in vm_running.stdout:
        # If the VM is running, power it off first
        subprocess.run([VBOXMANAGE_PATH, "controlvm", VM_NAME, "poweroff"])
        if verbose:
            print("VM is running. Shutting it down.")

    # Start the VM
    subprocess.run([VBOXMANAGE_PATH, "startvm", VM_NAME, "--type", "headless"])
    if verbose:
        print("VM started.")

    # Notify that the VM is starting
    log_and_notify(f"{VM_NAME} Status", "The VM is starting")

def create_image(color):
    """
    Creates an image with the specified color.
    """
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color)
    return image

def log_and_notify(title, message):
    """
    Logs a message and displays a toast notification.
    """
    if logs:
        logging.info(f"{title}: {message}")
    if verbose:
        print(f"[Notification] {title}: {message}")
    if toastNotification :
        toast.show_toast(title, message, duration=5)

def check_website():
    """
    Checks the website status.
    """
    global status
    time.sleep(INITIAL_DELAY)  # Initial delay to let VM boot up
    while running:
        with status_lock:
            if checking:
                try:
                    if verbose:
                        print("Checking if the website is online...")
                    response = requests.get(URL, timeout=TIMEOUT)
                    if response.status_code == 200:
                        if status != "online":
                            status = "online"
                            log_and_notify(f"{VM_NAME} Status", "The VM is online")
                        if verbose:
                            print("VM is online.")
                    else:
                        raise Exception("Service unavailable")
                except Exception as e:
                    if status != "offline":
                        status = "offline"
                        log_and_notify(f"{VM_NAME} Status", "The VM is offline")

                    status = "restarting"
                    log_and_notify(f"{VM_NAME} Status", "Restarting VM")
                    subprocess.run([VBOXMANAGE_PATH, "controlvm", VM_NAME, "poweroff"])
                    time.sleep(5)
                    subprocess.run([VBOXMANAGE_PATH, "startvm", VM_NAME, "--type", "headless"])
                    time.sleep(INITIAL_DELAY)  # Initial delay to let VM restart
        time.sleep(CHECK_INTERVAL)

def update_icon(icon):
    """
    Updates the tray icon based on the VM status.
    """
    global status
    while running:
        with status_lock:
            if status == "online":
                icon.icon = create_image("green")
            elif status == "offline":
                icon.icon = create_image("red")
            elif status == "restarting":
                icon.icon = create_image("orange")
            icon.update_menu()
            time.sleep(1)

def pause_checking(icon, item):
    """
    Pauses the website checking.
    """
    global checking
    log_and_notify(f"{VM_NAME} Status", "Pausing script...")
    with checking_lock:
        checking = False
    icon.update_menu()

def resume_checking(icon, item):
    """
    Resumes the website checking.
    """
    global checking
    log_and_notify(f"{VM_NAME} Status", "Resuming script...")
    with checking_lock:
        checking = True
    icon.update_menu()

def stop_script(icon, item):
    """
    Stops the script.
    """
    global running
    log_and_notify(f"{VM_NAME} Status", "Stopping script...")
    with running_lock:
        running = False
    icon.stop()


def tray_icon():
    """
    Manages the tray icon.
    """
    if verbose:
        print("Creating tray icon...")  # Debugging statement
    icon = Icon("VM Monitor")
    icon.icon = create_image("black")
    icon.menu = Menu(
        MenuItem('Pause', pause_checking, enabled=lambda item: checking),
        MenuItem('Resume', resume_checking, enabled=lambda item: not checking),
        MenuItem('Stop', stop_script, enabled=lambda item: True)
    )

    # Start the icon update job
    icon_update_thread = threading.Thread(target=update_icon, args=(icon,))
    icon_update_thread.start()

    # Run the tray icon
    icon.run()

    if verbose:
        print("Tray icon created and running.")  # Debugging statement


def main():
    """
    Main function to start all jobs.
    """
    # Start the VM
    launch_vm()
    # Start the website checking job
    check_website_thread = threading.Thread(target=check_website)
    check_website_thread.start()
    # Start the tray icon job
    tray_icon()

if __name__ == "__main__":
    # Enable verbose mode if verbose flag is set
    if verbose:
        print("Verbose mode enabled.")
    main()
