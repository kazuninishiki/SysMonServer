<<<<<<< HEAD
# SysMonServer
System Monitor Server
=======
# System Monitor Dashboard

A real-time system monitoring dashboard with elegant gradient visualizations for CPU, GPU, Memory, Disk, and Network statistics.

![System Monitor Dashboard](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.7+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Real-Time Monitoring
- **System Stats**: CPU usage, frequency, memory usage and allocation
- **GPU Monitoring**: Temperature, fan speed, power draw, utilization, memory usage
- **Disk Information**: Usage percentages and free space for all drives
- **Network Activity**: Current speeds, usage percentage, and session totals

### Visual Design
- **Gradient Fill Bars**: Dynamic background fills showing real-time utilization
- **Responsive Layout**: Auto-adjusting grid system for all screen sizes
- **Dark Theme**: Professional dark interface with blue accent colors
- **Smooth Animations**: 800ms transitions for seamless visual updates

### Technical Features
- **WebSocket Updates**: Real-time data streaming every second (configurable)
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **GPU Support**: NVIDIA GPU monitoring with NVML integration
- **API Endpoint**: REST API available at `/api/stats`
- **Error Handling**: Robust error handling with detailed logging

## Installation

### Prerequisites
- Python 3.7 or higher
- NVIDIA GPU drivers (for GPU monitoring)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/system-monitor-dashboard.git
   cd system-monitor-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   python main.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:9876`

### Alternative Installation Methods

**Using Virtual Environment (Recommended)**
```bash
python -m venv system-monitor
# Windows
system-monitor\Scripts\activate
# Linux/macOS
source system-monitor/bin/activate
pip install -r requirements.txt
python main.py
```

**Using Conda**
```bash
conda create -n system-monitor python=3.9
conda activate system-monitor
pip install -r requirements.txt
python main.py
```

## Configuration

### Update Interval
Modify the update interval in `main.py`:
```python
self.update_interval = 1000  # milliseconds (1 second)
```

### Port Configuration
Change the server port:
```python
socketio.run(app, host='0.0.0.0', port=9876)  # Change 9876 to desired port
```

### Network Speed Assumptions
The network usage percentage is calculated based on assumed maximum speeds. Modify in `get_network_stats()`:
```python
max_speed = 100  # Mbps - adjust to your connection speed
```

## API Documentation

### REST API
Get current system statistics:
```
GET http://localhost:9876/api/stats
```

**Response Format:**
```json
{
  "cpu": {
    "usage": 45.2,
    "frequency": 3.8,
    "max_frequency": 4.2
  },
  "memory": {
    "usage_percent": 67.3,
    "used_gb": 10.8,
    "total_gb": 16.0
  },
  "gpu": {
    "name": "NVIDIA GeForce RTX 4080",
    "temperature": 68,
    "usage": 85,
    "memory_usage": 72
  },
  "disks": {
    "c": {
      "used": 245.7,
      "total": 500.0,
      "label": "Windows"
    }
  },
  "network": {
    "usage": 15.3,
    "upload_speed": 12.4,
    "download_speed": 89.2,
    "total_sent": 2.47,
    "total_received": 18.93
  }
}
```

### WebSocket Events
Connect to WebSocket for real-time updates:
```javascript
const socket = io('http://localhost:9876');
socket.on('system_stats', function(data) {
    // Handle real-time data
});
```

## Troubleshooting

### Common Issues

**GPU Monitoring Not Working**
```bash
# Install NVIDIA drivers and NVML
pip install pynvml
# Ensure NVIDIA drivers are installed and GPU is detected
nvidia-smi
```

**Permission Errors (Linux/macOS)**
```bash
# Run with appropriate permissions for system monitoring
sudo python main.py
```

**Port Already in Use**
```bash
# Check what's using port 9876
netstat -an | grep 9876
# Kill the process or change port in main.py
```

**Missing Dependencies**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

### Performance Optimization

**Reduce Update Frequency**
For lower-end systems, increase the update interval:
```python
self.update_interval = 2000  # 2 seconds instead of 1
```

**Disable GPU Monitoring**
If you don't have an NVIDIA GPU:
```python
NVIDIA_AVAILABLE = False  # Set to False at the top of main.py
```

## Development

### Project Structure
```
system-monitor-dashboard/
├── main.py              # Main server application
├── requirements.txt     # Python dependencies
├── README.md           # Project documentation
└── LICENSE            # MIT license
```

### Adding Custom Metrics
Extend the `SystemMonitor` class to add new metrics:
```python
def get_custom_stats(self):
    # Add your custom monitoring logic
    return {"custom_metric": value}

def get_all_stats(self):
    stats = {
        # ... existing stats
        'custom': self.get_custom_stats()
    }
    return stats
```

### Modifying the UI
The HTML template is embedded in `main.py`. For extensive UI changes, consider moving to separate template files:
```python
from flask import render_template
# Move HTML to templates/index.html
return render_template('index.html')
```

## System Requirements

### Minimum Requirements
- **CPU**: Any modern processor
- **RAM**: 100MB available memory
- **Python**: 3.7+
- **OS**: Windows 10+, Linux (Ubuntu 18.04+), macOS 10.14+

### Recommended Requirements
- **CPU**: Multi-core processor for better monitoring accuracy
- **RAM**: 200MB available memory
- **GPU**: NVIDIA GPU with recent drivers (for GPU monitoring)
- **Network**: Stable network connection for accurate network monitoring

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add logging for error conditions
- Test on multiple platforms
- Update documentation for new features
- Ensure backward compatibility

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **psutil**: Cross-platform process and system monitoring
- **Flask-SocketIO**: Real-time WebSocket communication
- **pynvml**: NVIDIA GPU monitoring library
- **Flask**: Lightweight web framework

## Roadmap

### Planned Features
- [ ] Historical data graphs
- [ ] Email/SMS alerts for threshold breaches
- [ ] Multi-system monitoring
- [ ] Docker containerization
- [ ] Database logging
- [ ] Custom dashboard themes
- [ ] Mobile app companion

### Version History
- **v1.0.0**: Initial release with basic monitoring
- **v1.1.0**: Added GPU monitoring support
- **v1.2.0**: Enhanced UI with gradient animations
- **v1.3.0**: Network monitoring and WebSocket updates

## Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Built with ❤️ for system monitoring enthusiasts**
>>>>>>> 2d73b1d (Initial commit: System Monitor Dashboard)
