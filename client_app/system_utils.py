import os
import subprocess
import socket
import platform
import psutil
import time
from datetime import datetime

def get_system_info():
    """Collects system info for the ticket"""
    try:
        boot_time_timestamp = psutil.boot_time()
        bt = datetime.fromtimestamp(boot_time_timestamp)
        
        info = {
            "Username": os.getlogin(),
            "Computer Name": platform.node(),
            "OS": f"{platform.system()} {platform.release()}",
            "IP Address": socket.gethostbyname(socket.gethostname()),
            "Last Boot": bt.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        info = {"Error": str(e)}
    return info

def run_fix(action_type):
    """Executes the specific fix script"""
    log = []
    
    if action_type == "flush_dns":
        try:
            # Silently run command
            subprocess.run(["ipconfig", "/flushdns"], shell=True, check=True)
            log.append("✅ Executed: ipconfig /flushdns")
            log.append("✅ DNS Resolver Cache Flushed.")
        except Exception as e:
            log.append(f"❌ Failed: {str(e)}")

    elif action_type == "restart_explorer":
        try:
            subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], shell=True)
            subprocess.Popen(["explorer.exe"], shell=True)
            log.append("✅ Restarted Windows Explorer")
        except Exception as e:
            log.append(f"❌ Failed: {str(e)}")
            
    # Add more scripts here
    
    return "\n".join(log)

def calculate_priority(urgency, impact):
    """Logic based on your Priority Matrix"""
    # 1=High, 2=Medium, 3=Low
    matrix = {
        (1, 1): "Urgent", (2, 1): "High", (3, 1): "Medium",
        (1, 2): "High",   (2, 2): "Medium", (3, 2): "Low",
        (1, 3): "Medium", (2, 3): "Low",    (3, 3): "Low"
    }
    return matrix.get((urgency, impact), "Medium")