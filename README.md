# DocOrchestrationScheduler

Schedule and automate DocOrchestrator pipeline runs at configurable times and intervals.

## Features

- **Flexible Scheduling**: Support for cron-style, daily, and interval-based schedules
- **YAML Configuration**: Easy-to-read and modify configuration files
- **Multiple Pipelines**: Schedule different pipelines with different cadences
- **Logging**: Comprehensive logging with configurable levels
- **Test Mode**: Run jobs immediately for testing
- **Auto-confirm**: Runs pipelines with `--yes` flag for unattended execution

## Installation

```bash
cd ~/Development/Scripts/DocOrchestrationScheduler
pip install -r requirements.txt
```

## Quick Start

1. Copy the example configuration:
```bash
cp schedules.example.yaml schedules.yaml
```

2. Edit `schedules.yaml` to configure your jobs

3. Test your configuration:
```bash
# List all configured jobs
python3 scheduler.py --config schedules.yaml --list

# Run a specific job once (for testing)
python3 scheduler.py --config schedules.yaml --run-once --job "Weekly Qwilo Blog"

# Run all enabled jobs once
python3 scheduler.py --config schedules.yaml --run-once
```

4. Start the scheduler daemon:
```bash
python3 scheduler.py --config schedules.yaml
```

## Configuration

### Basic Job Configuration

```yaml
jobs:
  - name: "Weekly Blog Pipeline"
    enabled: true
    pipeline_config: "qwilo_pipeline.yaml"  # Relative to DocOrchestrator directory
    timeout: 1800  # 30 minutes
    schedule:
      type: daily
      time: "09:00"
      timezone: America/Los_Angeles
```

### Schedule Types

#### 1. Cron Schedule
Most flexible option using cron-style expressions:

```yaml
schedule:
  type: cron
  day_of_week: mon-fri  # Monday through Friday
  hour: 9  # 9 AM
  minute: 0
  timezone: America/Los_Angeles
```

Options:
- `day_of_week`: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`, ranges (`mon-fri`), or lists (`sat,sun`)
- `hour`: 0-23 or comma-separated list (`9`, `14,18`)
- `minute`: 0-59
- `timezone`: Any pytz timezone

#### 2. Daily Schedule
Run once per day at a specific time:

```yaml
schedule:
  type: daily
  time: "14:30"  # 2:30 PM
  timezone: America/Los_Angeles
```

#### 3. Interval Schedule
Run at fixed intervals:

```yaml
schedule:
  type: interval
  hours: 6  # Every 6 hours
  minutes: 0
  timezone: America/Los_Angeles
```

### Logging Configuration

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  directory: ./logs
```

## Usage Examples

### Start Scheduler Daemon
```bash
python3 scheduler.py --config schedules.yaml
```

### List Configured Jobs
```bash
python3 scheduler.py --config schedules.yaml --list
```

### Test Run
```bash
# Run all enabled jobs once
python3 scheduler.py --config schedules.yaml --run-once

# Run specific job
python3 scheduler.py --config schedules.yaml --run-once --job "Weekly Qwilo Blog"
```

## Pipeline Configuration

Pipeline configs can be specified as:
- **Relative paths**: `qwilo_pipeline.yaml` (relative to DocOrchestrator directory)
- **Absolute paths**: `~/Development/Scripts/DocOrchestrator/my_pipeline.yaml`

All pipelines run with the `--yes` flag for unattended execution.

## Running as a Service

### macOS (launchd)

Create `~/Library/LaunchAgents/com.docorchestration.scheduler.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.docorchestration.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/Development/Scripts/DocOrchestrationScheduler/scheduler.py</string>
        <string>--config</string>
        <string>/Users/YOUR_USERNAME/Development/Scripts/DocOrchestrationScheduler/schedules.yaml</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Development/Scripts/DocOrchestrationScheduler/logs/scheduler_out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Development/Scripts/DocOrchestrationScheduler/logs/scheduler_err.log</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.docorchestration.scheduler.plist
```

### Linux (systemd)

Create `/etc/systemd/system/docorchestration-scheduler.service`:

```ini
[Unit]
Description=DocOrchestration Scheduler
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/Development/Scripts/DocOrchestrationScheduler
ExecStart=/usr/bin/python3 scheduler.py --config schedules.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable docorchestration-scheduler
sudo systemctl start docorchestration-scheduler
sudo systemctl status docorchestration-scheduler
```

## Logs

Logs are stored in the configured log directory (default: `./logs`):
- Daily log files: `scheduler_YYYYMMDD.log`
- Each job execution is logged with timestamp
- Includes job status (success/failure) and output

## Requirements

- Python 3.8+
- PyYAML
- APScheduler
- DocOrchestrator (installed at `~/Development/Scripts/DocOrchestrator`)

## License

MIT License - See LICENSE file for details
