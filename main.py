#!/usr/bin/env python3
"""
System Monitor Server
Real-time system statistics dashboard server
Cross-platform support for Windows and Linux
"""

import json
import time
import threading
import logging
import socket
import platform
from datetime import datetime
from pathlib import Path

import psutil
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

try:
    import pynvml
    NVIDIA_AVAILABLE = True
except ImportError:
    NVIDIA_AVAILABLE = False
    print("Warning - NVIDIA GPU monitoring not available. Install pynvml for GPU stats.")

# Configure logging without colons
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H-%M-%S'
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.running = True
        self.update_interval = 1000  # milliseconds
        self.session_start = time.time()
        self.max_gpu_temp = 0
        self.network_baseline = self._get_network_stats()
        self.gpu_name = "GPU Not Available"  # Default value
        self.is_linux = platform.system().lower() == 'linux'
        self.connected_clients = {}  # Track connected clients
        
        # Get hostname and IP addresses
        self.hostname = socket.gethostname()
        self.ip_addresses = self._get_ip_addresses()
        
        if NVIDIA_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                # Fix: Handle both string and bytes return types
                gpu_name_raw = pynvml.nvmlDeviceGetName(self.gpu_handle)
                if isinstance(gpu_name_raw, bytes):
                    self.gpu_name = gpu_name_raw.decode('utf-8')
                else:
                    self.gpu_name = str(gpu_name_raw)
                logger.info(f"GPU monitoring initialized for {self.gpu_name}")
            except Exception as e:
                logger.error(f"GPU initialization failed {str(e)}")
                self.gpu_name = "GPU Error"  # Set fallback name
        
        logger.info(f"System monitor initialized successfully on {platform.system()}")
    
    def add_client(self, client_id, client_ip):
        """Add a connected client"""
        self.connected_clients[client_id] = {
            'ip': client_ip,
            'connected_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        logger.info(f"Client connected: {client_ip} (ID: {client_id})")
    
    def remove_client(self, client_id):
        """Remove a disconnected client"""
        if client_id in self.connected_clients:
            client_ip = self.connected_clients[client_id]['ip']
            del self.connected_clients[client_id]
            logger.info(f"Client disconnected: {client_ip} (ID: {client_id})")
    
    def update_client_activity(self, client_id):
        """Update client's last seen timestamp"""
        if client_id in self.connected_clients:
            self.connected_clients[client_id]['last_seen'] = datetime.now().isoformat()
    
    def get_connected_clients(self):
        """Get list of connected clients"""
        return dict(self.connected_clients)
    
    def _get_ip_addresses(self):
        """Get all IP addresses excluding those starting with 169 and localhost"""
        ip_addresses = []
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:  # AF_INET (IPv4)
                        ip = addr.address
                        if not ip.startswith('169.') and ip != '127.0.0.1':
                            ip_addresses.append(ip)
        except Exception as e:
            logger.error(f"IP address retrieval error {str(e)}")
        return ip_addresses
    
    def _get_network_stats(self):
        """Get network I/O statistics"""
        try:
            return psutil.net_io_counters()
        except Exception as e:
            logger.error(f"Network stats error {str(e)}")
            return None
    
    def get_cpu_stats(self):
        """Get CPU statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_freq = psutil.cpu_freq()
            
            if cpu_freq:
                current_freq = cpu_freq.current / 1000  # Convert to GHz
                max_freq = cpu_freq.max / 1000 if cpu_freq.max else 5.0
            else:
                # Fallback for systems without frequency info
                current_freq = 0
                max_freq = 5.0
            
            return {
                'usage': round(cpu_percent, 1),
                'frequency': round(current_freq, 1),
                'max_frequency': round(max_freq, 1)
            }
        except Exception as e:
            logger.error(f"CPU stats error {str(e)}")
            return {'usage': 0, 'frequency': 0, 'max_frequency': 5.0}
    
    def get_memory_stats(self):
        """Get memory statistics"""
        try:
            memory = psutil.virtual_memory()
            return {
                'usage_percent': round(memory.percent, 1),
                'used_gb': round(memory.used / (1024**3), 1),
                'total_gb': round(memory.total / (1024**3), 1)
            }
        except Exception as e:
            logger.error(f"Memory stats error {str(e)}")
            return {'usage_percent': 0, 'used_gb': 0, 'total_gb': 0}
    
    def get_gpu_stats(self):
        """Get GPU statistics"""
        if not NVIDIA_AVAILABLE:
            return {
                'name': 'GPU Not Available',
                'temperature': 0, 'max_temp': 0, 'fan_speed': 0, 'fan_percent': 0,
                'power_draw': 0, 'max_power': 0, 'usage': 0,
                'memory_usage': 0, 'memory_used': 0, 'memory_total': 0,
                'driver_version': 'N/A', 'cuda_version': 'N/A'
            }
        
        try:
            # Check if GPU handle exists (initialization was successful)
            if not hasattr(self, 'gpu_handle'):
                return {
                    'name': self.gpu_name,
                    'temperature': 0, 'max_temp': 0, 'fan_speed': 0, 'fan_percent': 0,
                    'power_draw': 0, 'max_power': 0, 'usage': 0,
                    'memory_usage': 0, 'memory_used': 0, 'memory_total': 0,
                    'driver_version': 'Error', 'cuda_version': 'Error'
                }
            
            temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            self.max_gpu_temp = max(self.max_gpu_temp, temp)
            
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(self.gpu_handle)
            except:
                fan_speed = 0
            
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(self.gpu_handle) / 1000  # Convert to watts
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(self.gpu_handle)[1] / 1000
            except:
                power_draw, power_limit = 0, 320
            
            try:
                utilization = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                gpu_usage = utilization.gpu
            except:
                gpu_usage = 0

            try:
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                memory_used = memory_info.used / (1024**3)  # Convert to GB
                memory_total = memory_info.total / (1024**3)
            except:
                memory_used, memory_total = 0, 16
            
            # Calculate memory usage percentage from actual memory used
            memory_usage = (memory_used / memory_total) * 100 if memory_total > 0 else 0
            
            try:
                driver_version_raw = pynvml.nvmlSystemGetDriverVersion()
                if isinstance(driver_version_raw, bytes):
                    driver_version = driver_version_raw.decode('utf-8')
                else:
                    driver_version = str(driver_version_raw)
                
                cuda_version = pynvml.nvmlSystemGetCudaDriverVersion_v2()
                cuda_version = f"{cuda_version // 1000}.{(cuda_version % 1000) // 10}"
            except:
                driver_version, cuda_version = 'Unknown', 'Unknown'
            
            return {
                'name': self.gpu_name,
                'temperature': temp,
                'max_temp': self.max_gpu_temp,
                'fan_speed': int(fan_speed * 22),  # Approximate RPM
                'fan_percent': fan_speed,
                'power_draw': round(power_draw, 0),
                'max_power': round(power_limit, 0),
                'usage': gpu_usage,
                'memory_usage': round(memory_usage, 1),
                'memory_used': round(memory_used, 1),
                'memory_total': round(memory_total, 0),
                'driver_version': driver_version,
                'cuda_version': cuda_version
            }
        except Exception as e:
            logger.error(f"GPU stats error {str(e)}")
            return {
                'name': self.gpu_name,
                'temperature': 0, 'max_temp': 0, 'fan_speed': 0, 'fan_percent': 0,
                'power_draw': 0, 'max_power': 0, 'usage': 0,
                'memory_usage': 0, 'memory_used': 0, 'memory_total': 0,
                'driver_version': 'Error', 'cuda_version': 'Error'
            }
    
    def get_disk_stats(self):
        """Get disk statistics - cross-platform"""
        disks = {}
        try:
            for partition in psutil.disk_partitions():
                # Skip special filesystems on Linux
                if self.is_linux:
                    # Skip virtual/special filesystems
                    skip_types = ['tmpfs', 'devtmpfs', 'sysfs', 'proc', 'squashfs', 'overlay']
                    if partition.fstype in skip_types:
                        continue
                    # Skip if mountpoint starts with /sys, /proc, /dev, /run
                    skip_mounts = ['/sys', '/proc', '/dev', '/run', '/snap']
                    if any(partition.mountpoint.startswith(skip) for skip in skip_mounts):
                        continue
                else:
                    # Windows - skip CD-ROM drives
                    if 'cdrom' in partition.opts or partition.fstype == '':
                        continue
                
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    if self.is_linux:
                        # Linux: Use mountpoint as identifier
                        disk_name = partition.mountpoint.replace('/', '_').strip('_')
                        if not disk_name:
                            disk_name = 'root'
                        display_name = partition.mountpoint
                    else:
                        # Windows: Use drive letter
                        disk_name = partition.device.replace(':', '').replace('\\', '').lower()
                        display_name = partition.device.split('\\')[-1] if '\\' in partition.device else 'Local Disk'
                    
                    disks[disk_name] = {
                        'used': round(usage.used / (1024**3), 1),
                        'total': round(usage.total / (1024**3), 1),
                        'label': display_name,
                        'fstype': partition.fstype
                    }
                except (PermissionError, OSError) as e:
                    # Skip inaccessible drives
                    continue
        except Exception as e:
            logger.error(f"Disk stats error {str(e)}")
        
        return disks
    
    def get_network_stats(self):
        """Get network statistics"""
        try:
            current_stats = psutil.net_io_counters()
            if not current_stats or not self.network_baseline:
                return {'usage': 0, 'upload_speed': 0, 'download_speed': 0, 'total_sent': 0, 'total_received': 0}
            
            # Calculate speeds (bytes per second to Mbps)
            time_diff = 1.0  # 1 second interval
            upload_speed = ((current_stats.bytes_sent - self.network_baseline.bytes_sent) / time_diff) * 8 / 1024 / 1024
            download_speed = ((current_stats.bytes_recv - self.network_baseline.bytes_recv) / time_diff) * 8 / 1024 / 1024
            
            # Update baseline
            self.network_baseline = current_stats
            
            # Calculate totals since session start
            total_sent = current_stats.bytes_sent / (1024**3)
            total_received = current_stats.bytes_recv / (1024**3)
            
            # Calculate usage percentage (assuming 100 Mbps connection)
            max_speed = 100
            usage = max(upload_speed, download_speed) / max_speed * 100
            
            return {
                'usage': round(min(usage, 100), 1),
                'upload_speed': round(max(upload_speed, 0), 1),
                'download_speed': round(max(download_speed, 0), 1),
                'total_sent': round(total_sent, 2),
                'total_received': round(total_received, 2)
            }
        except Exception as e:
            logger.error(f"Network stats error {str(e)}")
            return {'usage': 0, 'upload_speed': 0, 'download_speed': 0, 'total_sent': 0, 'total_received': 0}

    def get_all_stats(self):
        """Get all system statistics"""
        return {
            'cpu': self.get_cpu_stats(),
            'memory': self.get_memory_stats(),
            'gpu': self.get_gpu_stats(),
            'disks': self.get_disk_stats(),
            'network': self.get_network_stats(),
            'hostname': self.hostname,
            'ip_addresses': self.ip_addresses,
            'connected_clients': self.get_connected_clients(),
            'platform': platform.system(),
            'timestamp': datetime.now().isoformat()
        }

# Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'system_monitor_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

monitor = SystemMonitor()

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Monitor Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            padding: 20px;
            color: white;
        }

        .monitor-container {
            width: 100%;
            position: relative;
        }

        .settings-button {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .settings-button:hover {
            background: #3a3a3a;
            transform: rotate(90deg);
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
        }

        .modal-content {
            background-color: #2a2a2a;
            margin: 15% auto;
            padding: 30px;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            width: 400px;
            max-width: 90%;
            color: white;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .modal-title {
            font-size: 20px;
            font-weight: 600;
        }

        .close {
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            line-height: 1;
        }

        .close:hover {
            color: white;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #d1d5db;
        }

        .form-input {
            width: 100%;
            padding: 10px 12px;
            background: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            color: white;
            font-size: 14px;
        }

        .form-input:focus {
            outline: none;
            border-color: #3b82f6;
        }

        .form-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .btn-primary {
            background: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background: #2563eb;
        }

        .btn-secondary {
            background: #6b7280;
            color: white;
        }

        .btn-secondary:hover {
            background: #4b5563;
        }

        /* Updated grid system for equal width/height blocks */
        .system-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .gpu-section {
            width: 100%;
            margin-top: 30px;
        }

        .section-title {
            color: white;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }

        .gpu-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .gpu-panel-wide {
            grid-column: span 2;
        }

        .disk-section {
            width: 100%;
            margin-top: 30px;
        }

        .disk-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .disk-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .drive-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }

        .drive-letter {
            font-size: 24px;
            font-weight: 700;
            color: white;
        }

        .drive-label {
            font-size: 14px;
            color: #9ca3af;
            font-weight: 400;
        }

        .disk-usage-text {
            font-size: 12px;
            color: #d1d5db;
            line-height: 1.3;
        }

        .network-section {
            width: 100%;
            margin-top: 30px;
        }

        .network-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .network-speeds {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .speed-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }

        .speed-label {
            color: #9ca3af;
            font-weight: 500;
        }

        .speed-value {
            color: white;
            font-weight: 600;
        }

        /* Connected Clients Section */
        .clients-section {
            width: 100%;
            margin-top: 30px;
        }

        .clients-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .client-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .client-ip {
            font-size: 18px;
            font-weight: 600;
            color: white;
            margin-bottom: 4px;
        }

        .client-details {
            font-size: 12px;
            color: #9ca3af;
            line-height: 1.3;
        }

        /* Updated stat panel for consistent sizing */
        .stat-panel {
            position: relative;
            background: #2a2a2a;
            border-radius: 12px;
            padding: 16px 20px;
            overflow: hidden;
            border: 1px solid #3a3a3a;
            height: 120px; /* Fixed height for all panels */
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        /* Special styling for specifications panel */
        .stat-panel.gpu-panel-wide {
            height: 120px; /* Same height as other panels */
        }

        .fill-bar {
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            background: linear-gradient(90deg, #1e3a8a, #3b82f6);
            border-radius: 12px;
            transition: width 0.8s ease-in-out;
            opacity: 0.3;
        }

        .fill-bar-green-red {
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            border-radius: 12px;
            transition: width 0.8s ease-in-out;
            opacity: 0.3;
        }

        .stat-content {
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100%;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: white;
            margin-bottom: 4px;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }

        .stat-label {
            font-size: 12px;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }

        .frequency-split {
            font-size: 20px;
        }

        .frequency-max {
            color: #6b7280;
            font-weight: 400;
        }

        /* Special adjustments for network speeds and session totals */
        .network-speeds .stat-value {
            font-size: 18px;
            margin-bottom: 8px;
        }

        /* Responsive design */
        @media (max-width: 768px) {
            .system-container, .gpu-container, .disk-container, .network-container, .clients-container {
                grid-template-columns: 1fr;
            }
            
            .gpu-panel-wide {
                grid-column: span 1;
            }

            .modal-content {
                margin: 10% auto;
                width: 350px;
            }
        }

        @media (min-width: 769px) and (max-width: 1200px) {
            .system-container, .gpu-container, .disk-container, .network-container, .clients-container {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (min-width: 1201px) and (max-width: 1600px) {
            .system-container, .gpu-container, .disk-container, .network-container, .clients-container {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        @media (min-width: 1601px) {
            .system-container, .gpu-container, .disk-container, .network-container, .clients-container {
                grid-template-columns: repeat(4, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="settings-button" onclick="openModal()">⚙️</div>

    <div id="settingsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Settings</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="form-group">
                <label class="form-label" for="refreshRate">Refresh Rate (milliseconds)</label>
                <input type="number" id="refreshRate" class="form-input" value="1000" min="100" max="10000" step="100">
            </div>
            <div class="form-buttons">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="saveSettings()">Save</button>
            </div>
        </div>
    </div>

    <div class="monitor-container">
        <div class="section-title">System</div>
        <div class="system-container">
            <div class="stat-panel" id="cpu-usage">
                <div class="fill-bar-green-red" id="cpu-fill"></div>
                <div class="stat-content">
                    <div class="stat-value" id="cpu-value">0%</div>
                    <div class="stat-label">CPU Usage</div>
                </div>
            </div>

            <div class="stat-panel" id="cpu-freq">
                <div class="fill-bar" id="freq-fill"></div>
                <div class="stat-content">
                    <div class="stat-value frequency-split" id="freq-value">
                        0<span class="frequency-max">/0</span>GHz
                    </div>
                    <div class="stat-label">CPU Frequency</div>
                </div>
            </div>

            <div class="stat-panel" id="memory-usage">
                <div class="fill-bar" id="memory-fill"></div>
                <div class="stat-content">
                    <div class="stat-value" id="memory-value">0%</div>
                    <div class="stat-label">Memory Usage</div>
                </div>
            </div>

            <div class="stat-panel" id="memory-used">
                <div class="fill-bar" id="memory-used-fill"></div>
                <div class="stat-content">
                    <div class="stat-value frequency-split" id="memory-used-value">
                        0<span class="frequency-max">/0</span>GB
                    </div>
                    <div class="stat-label">Memory Used</div>
                </div>
            </div>
        </div>
    </div>

    <div class="gpu-section">
        <div class="section-title" id="gpu-title">GPU</div>
        <div class="gpu-container">
            <div class="stat-panel" id="gpu-temp">
                <div class="fill-bar-green-red" id="gpu-temp-fill"></div>
                <div class="stat-content">
                    <div class="stat-value frequency-split" id="gpu-temp-value">
                        0<span class="frequency-max">/0</span>°C
                    </div>
                    <div class="stat-label">Temperature</div>
                </div>
            </div>

            <div class="stat-panel" id="gpu-fans">
                <div class="fill-bar" id="gpu-fans-fill"></div>
                <div class="stat-content">
                    <div class="stat-value frequency-split" id="gpu-fans-value">
                        0<span class="frequency-max"> (0%)</span>
                    </div>
                    <div class="stat-label">Fan Speed RPM</div>
                </div>
            </div>

            <div class="stat-panel" id="gpu-power">
                <div class="fill-bar-green-red" id="gpu-power-fill"></div>
                <div class="stat-content">
                    <div class="stat-value frequency-split" id="gpu-power-value">
                        0<span class="frequency-max">/0</span>W
                    </div>
                    <div class="stat-label">Power Draw</div>
                </div>
            </div>

            <div class="stat-panel" id="gpu-usage">
                <div class="fill-bar-green-red" id="gpu-usage-fill"></div>
                <div class="stat-content">
                    <div class="stat-value" id="gpu-usage-value">0%</div>
                    <div class="stat-label">GPU Usage</div>
                </div>
            </div>

            <div class="stat-panel" id="gpu-mem-usage">
                <div class="fill-bar-green-red" id="gpu-mem-usage-fill"></div>
                <div class="stat-content">
                    <div class="stat-value" id="gpu-mem-usage-value">0%</div>
                    <div class="stat-label">Memory Usage</div>
                </div>
            </div>

            <div class="stat-panel" id="gpu-mem-used">
                <div class="fill-bar" id="gpu-mem-used-fill"></div>
                <div class="stat-content">
                    <div class="stat-value frequency-split" id="gpu-mem-used-value">
                        0<span class="frequency-max">/0</span>GB
                    </div>
                    <div class="stat-label">Memory Used</div>
                </div>
            </div>

            <div class="stat-panel gpu-panel-wide" id="gpu-specs">
                <div class="fill-bar" style="width: 0%; opacity: 0.1;"></div>
                <div class="stat-content">
                    <div class="stat-value" style="font-size: 16px; line-height: 1.4;" id="gpu-specs-value">
                        PCIe 4.0 x16 | Driver N/A | CUDA N/A
                    </div>
                    <div class="stat-label">Specifications</div>
                </div>
            </div>
        </div>
    </div>

    <div class="disk-section">
        <div class="section-title">Disks</div>
        <div class="disk-container" id="disk-container">
            <!-- Disks will be populated dynamically -->
        </div>
    </div>

    <div class="network-section">
        <div class="section-title" id="network-title">Network</div>
        <div class="network-container">
            <div class="stat-panel" id="network-usage">
                <div class="fill-bar" id="network-usage-fill"></div>
                <div class="stat-content">
                    <div class="stat-value" id="network-usage-value">0%</div>
                    <div class="stat-label">Network Usage</div>
                </div>
            </div>

            <div class="stat-panel" id="network-speeds">
                <div class="fill-bar" id="network-speeds-fill"></div>
                <div class="stat-content">
                    <div class="stat-value" style="font-size: 18px; margin-bottom: 8px;">Current Speeds</div>
                    <div class="network-speeds">
                        <div class="speed-row">
                            <span class="speed-label">↑ Upload</span>
                            <span class="speed-value" id="upload-speed">0 Mbps</span>
                        </div>
                        <div class="speed-row">
                            <span class="speed-label">↓ Download</span>
                            <span class="speed-value" id="download-speed">0 Mbps</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="stat-panel" id="network-totals">
                <div class="fill-bar" style="width: 0%; opacity: 0.1;"></div>
                <div class="stat-content">
                    <div class="stat-value" style="font-size: 18px; margin-bottom: 8px;">Session Totals</div>
                    <div class="network-speeds">
                        <div class="speed-row">
                            <span class="speed-label">↑ Sent</span>
                            <span class="speed-value" id="total-sent">0 GB</span>
                        </div>
                        <div class="speed-row">
                            <span class="speed-label">↓ Received</span>
                            <span class="speed-value" id="total-received">0 GB</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="clients-section">
        <div class="section-title">Connected Clients</div>
        <div class="clients-container" id="clients-container">
            <!-- Connected clients will be populated dynamically -->
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        let diskPanels = {};
        let clientPanels = {};
        let updateInterval = 1000; // Default 1000ms

        function openModal() {
            document.getElementById('settingsModal').style.display = 'block';
            document.getElementById('refreshRate').value = updateInterval;
        }

        function closeModal() {
            document.getElementById('settingsModal').style.display = 'none';
        }

        function saveSettings() {
            const newInterval = parseInt(document.getElementById('refreshRate').value);
            if (newInterval >= 100 && newInterval <= 10000) {
                updateInterval = newInterval;
                // Emit the new interval to the server
                socket.emit('update_interval', {interval: updateInterval});
                closeModal();
            } else {
                alert('Please enter a value between 100 and 10000 milliseconds.');
            }
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('settingsModal');
            if (event.target === modal) {
                closeModal();
            }
        }

        function getGreenRedGradient(percentage) {
            // Green for low values (0%), red for high values (100%)
            const normalizedPercentage = Math.max(0, Math.min(100, percentage)) / 100;
            
            // Calculate RGB values: green (0,255,0) to red (255,0,0)
            const red = Math.round(255 * normalizedPercentage);
            const green = Math.round(255 * (1 - normalizedPercentage));
            
            // Create gradient from current color to slightly more intense version
            const startColor = `rgb(${red}, ${green}, 0)`;
            const endColor = `rgb(${Math.min(255, red + 50)}, ${Math.min(255, green + 50)}, 0)`;
            
            return `linear-gradient(90deg, ${startColor}, ${endColor})`;
        }

        function updateNetworkTitle(hostname, ipAddresses) {
            const networkTitle = document.getElementById('network-title');
            const ipList = ipAddresses.join(' ');
            networkTitle.textContent = `Network - ${hostname} - ${ipList}`;
        }

        function updateSystemStats(data) {
            const cpu = data.cpu;
            const memory = data.memory;
            
            // CPU Updates
            document.getElementById('cpu-value').textContent = `${cpu.usage}%`;
            const cpuFill = document.getElementById('cpu-fill');
            cpuFill.style.width = `${cpu.usage}%`;
            cpuFill.style.background = getGreenRedGradient(cpu.usage);
            
            const freqElement = document.getElementById('freq-value');
            freqElement.innerHTML = `${cpu.frequency}<span class="frequency-max">/${cpu.max_frequency}</span>GHz`;
            const freqPercentage = (cpu.frequency / cpu.max_frequency) * 100;
            document.getElementById('freq-fill').style.width = `${freqPercentage}%`;
            
            // Memory Updates
            document.getElementById('memory-value').textContent = `${memory.usage_percent}%`;
            document.getElementById('memory-fill').style.width = `${memory.usage_percent}%`;
            
            const memUsedElement = document.getElementById('memory-used-value');
            memUsedElement.innerHTML = `${memory.used_gb}<span class="frequency-max">/${memory.total_gb}</span>GB`;
            const memUsedPercentage = (memory.used_gb / memory.total_gb) * 100;
            document.getElementById('memory-used-fill').style.width = `${memUsedPercentage}%`;
        }

        function updateGPUStats(data) {
            const gpu = data.gpu;
            
            // Update GPU title
            document.getElementById('gpu-title').textContent = gpu.name;
            
            // Temperature (green at low temps, red at high temps)
            const tempElement = document.getElementById('gpu-temp-value');
            tempElement.innerHTML = `${gpu.temperature}<span class="frequency-max">/${gpu.max_temp}</span>°C`;
            const tempPercentage = (gpu.temperature / 90) * 100; // Assume 90°C as max safe temp
            const tempFill = document.getElementById('gpu-temp-fill');
            tempFill.style.width = `${tempPercentage}%`;
            tempFill.style.background = getGreenRedGradient(tempPercentage);
            
            // Fans (keep blue gradient)
            const fansElement = document.getElementById('gpu-fans-value');
            fansElement.innerHTML = `${gpu.fan_speed}<span class="frequency-max"> (${gpu.fan_percent}%)</span>`;
            document.getElementById('gpu-fans-fill').style.width = `${gpu.fan_percent}%`;
            
            // Power (green at low power, red at high power)
            const powerElement = document.getElementById('gpu-power-value');
            powerElement.innerHTML = `${gpu.power_draw}<span class="frequency-max">/${gpu.max_power}</span>W`;
            const powerPercentage = (gpu.power_draw / gpu.max_power) * 100;
            const powerFill = document.getElementById('gpu-power-fill');
            powerFill.style.width = `${powerPercentage}%`;
            powerFill.style.background = getGreenRedGradient(powerPercentage);
            
            // GPU Usage (green at low usage, red at high usage)
            document.getElementById('gpu-usage-value').textContent = `${gpu.usage}%`;
            const gpuUsageFill = document.getElementById('gpu-usage-fill');
            gpuUsageFill.style.width = `${gpu.usage}%`;
            gpuUsageFill.style.background = getGreenRedGradient(gpu.usage);
            
            // GPU Memory Usage (green at low usage, red at high usage)
            document.getElementById('gpu-mem-usage-value').textContent = `${gpu.memory_usage}%`;
            const gpuMemUsageFill = document.getElementById('gpu-mem-usage-fill');
            gpuMemUsageFill.style.width = `${gpu.memory_usage}%`;
            gpuMemUsageFill.style.background = getGreenRedGradient(gpu.memory_usage);
            
            // GPU Memory Used (keep blue gradient)
            const gpuMemElement = document.getElementById('gpu-mem-used-value');
            gpuMemElement.innerHTML = `${gpu.memory_used}<span class="frequency-max">/${gpu.memory_total}</span>GB`;
            const gpuMemPercentage = (gpu.memory_used / gpu.memory_total) * 100;
            document.getElementById('gpu-mem-used-fill').style.width = `${gpuMemPercentage}%`;
            
            // Specifications
            document.getElementById('gpu-specs-value').textContent = 
                `PCIe 4.0 x16 | Driver ${gpu.driver_version} | CUDA ${gpu.cuda_version}`;
        }

        function updateDiskStats(data) {
            const disks = data.disks;
            const container = document.getElementById('disk-container');
            
            Object.keys(disks).forEach(drive => {
                const disk = disks[drive];
                const percentage = (disk.used / disk.total) * 100;
                const free = disk.total - disk.used;
                
                if (!diskPanels[drive]) {
                    // Create new disk panel
                    const panel = document.createElement('div');
                    panel.className = 'stat-panel';
                    panel.id = `disk-${drive}`;
                    panel.innerHTML = `
                        <div class="fill-bar" id="disk-${drive}-fill"></div>
                        <div class="stat-content">
                            <div class="drive-header">
                                <span class="drive-letter">${disk.label}</span>
                                <span class="stat-value disk-usage-text" id="disk-${drive}-percent">${percentage.toFixed(1)}%</span>
                            </div>
                        
                            <div class="disk-usage-text" id="disk-${drive}-usage">
                                ${disk.used.toFixed(1)} GB used / ${free.toFixed(1)} GB free
                            </div>
                        </div>
                    `;

                    container.appendChild(panel);
                    diskPanels[drive] = panel;
                }
                
                // Update existing panel
                document.getElementById(`disk-${drive}-percent`).textContent = `${percentage.toFixed(1)}%`;
                document.getElementById(`disk-${drive}-usage`).textContent = 
                    `${disk.used.toFixed(1)} GB used / ${free.toFixed(1)} GB free`;
                document.getElementById(`disk-${drive}-fill`).style.width = `${percentage}%`;
            });
        }

        function updateNetworkStats(data) {
            const network = data.network;
            
            document.getElementById('network-usage-value').textContent = `${network.usage}%`;
            document.getElementById('network-usage-fill').style.width = `${network.usage}%`;
            
            document.getElementById('upload-speed').textContent = `${network.upload_speed} Mbps`;
            document.getElementById('download-speed').textContent = `${network.download_speed} Mbps`;
            
            const speedsPercentage = Math.max(network.upload_speed / 50 * 100, network.download_speed / 100 * 100);
            document.getElementById('network-speeds-fill').style.width = `${Math.min(speedsPercentage, 100)}%`;
            
            document.getElementById('total-sent').textContent = `${network.total_sent} GB`;
            document.getElementById('total-received').textContent = `${network.total_received} GB`;
        }

        function updateConnectedClients(data) {
            const clients = data.connected_clients;
            const container = document.getElementById('clients-container');
            
            // Remove clients that are no longer connected
            Object.keys(clientPanels).forEach(clientId => {
                if (!clients[clientId]) {
                    const panel = clientPanels[clientId];
                    if (panel && panel.parentNode) {
                        panel.parentNode.removeChild(panel);
                    }
                    delete clientPanels[clientId];
                }
            });
            
            // Add or update existing clients
            Object.keys(clients).forEach(clientId => {
                const client = clients[clientId];
                const connectedTime = new Date(client.connected_at).toLocaleTimeString();
                
                if (!clientPanels[clientId]) {
                    // Create new client panel
                    const panel = document.createElement('div');
                    panel.className = 'stat-panel';
                    panel.id = `client-${clientId}`;
                    panel.innerHTML = `
                        <div class="fill-bar" style="width: 100%; background: linear-gradient(90deg, #059669, #10b981);"></div>
                        <div class="stat-content">
                            <div class="client-ip" id="client-${clientId}-ip">${client.ip}</div>
                            <div class="client-details" id="client-${clientId}-details">
                                Connected: ${connectedTime}
                            </div>
                        </div>
                    `;

                    container.appendChild(panel);
                    clientPanels[clientId] = panel;
                } else {
                    // Update existing panel
                    document.getElementById(`client-${clientId}-ip`).textContent = client.ip;
                    document.getElementById(`client-${clientId}-details`).textContent = 
                        `Connected: ${connectedTime}`;
                }
            });
        }

        socket.on('system_stats', function(data) {
            updateNetworkTitle(data.hostname, data.ip_addresses);
            updateSystemStats(data);
            updateGPUStats(data);
            updateDiskStats(data);
            updateNetworkStats(data);
            updateConnectedClients(data);
        });

        socket.on('connect', function() {
            console.log('Connected to system monitor server');
        });

        socket.on('disconnect', function() {
            console.log('Disconnected from system monitor server');
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    """API endpoint for system statistics"""
    return jsonify(monitor.get_all_stats())

# Background task using Flask-SocketIO's background task system
def background_stats_updater():
    """Background task to emit stats via WebSocket"""
    while monitor.running:
        try:
            stats = monitor.get_all_stats()
            socketio.emit('system_stats', stats)
            socketio.sleep(monitor.update_interval / 1000.0)
        except Exception as e:
            logger.error(f"Stats update error {str(e)}")
            socketio.sleep(1)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
    client_id = request.sid
    
    monitor.add_client(client_id, client_ip)
    logger.info(f"Client connected: {client_ip} (ID: {client_id})")
    
    # Send initial stats immediately
    emit('system_stats', monitor.get_all_stats())

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    monitor.remove_client(client_id)
    logger.info(f"Client disconnected (ID: {client_id})")

@socketio.on('update_interval')
def handle_update_interval(data):
    """Handle refresh rate update from client"""
    client_id = request.sid
    monitor.update_client_activity(client_id)
    
    new_interval = data.get('interval', 1000)
    if 100 <= new_interval <= 10000:
        monitor.update_interval = new_interval
        logger.info(f"Update interval changed to {new_interval}ms")
        emit('interval_updated', {'interval': new_interval})

if __name__ == '__main__':
    logger.info("Starting System Monitor Server on port 9876")
    
    # Start background stats updater using Flask-SocketIO's background task system
    socketio.start_background_task(background_stats_updater)
    
    try:
        socketio.run(app, host='0.0.0.0', port=9876, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        monitor.running = False
    except Exception as e:
        logger.error(f"Server error {str(e)}")
    finally:
        logger.info("System Monitor Server stopped")
