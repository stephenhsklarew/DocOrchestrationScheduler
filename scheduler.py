#!/usr/bin/env python3
"""
DocOrchestrationScheduler
Schedules and runs DocOrchestrator pipelines at configurable times.
"""

import os
import sys
import yaml
import json
import subprocess
import logging
import argparse
import tempfile
from pathlib import Path
from datetime import datetime, time as dt_time, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


@dataclass
class JobConfig:
    """Configuration for a scheduled job"""
    name: str
    pipeline_config: str
    schedule: Dict
    enabled: bool = True
    timeout: int = 3600  # 1 hour default
    incremental: bool = False  # Enable incremental processing
    date_format: str = "%m%d%Y"  # Date format for start_date parameter
    lookback_days: int = 0  # Days to look back from last run (for overlap)


class DocOrchestrationScheduler:
    """Scheduler for DocOrchestrator pipelines"""

    def __init__(self, config_path: str):
        """Initialize scheduler with config file"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.scheduler = BlockingScheduler()
        self.scripts_dir = Path.home() / 'Development' / 'Scripts'
        self.orchestrator_path = self.scripts_dir / 'DocOrchestrator' / 'orchestrator.py'

        # State file for tracking incremental runs
        self.state_file = self.config_path.parent / 'scheduler_state.json'
        self.state = self._load_state()

        # Setup logging
        self._setup_logging()

        # Validate DocOrchestrator exists
        if not self.orchestrator_path.exists():
            raise FileNotFoundError(f"DocOrchestrator not found at {self.orchestrator_path}")

        self.logger.info(f"Scheduler initialized with config: {config_path}")
        if self.state:
            self.logger.info(f"Loaded state for {len(self.state)} job(s)")

    def _load_config(self) -> Dict:
        """Load scheduler configuration from YAML"""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def _load_state(self) -> Dict:
        """Load scheduler state from JSON file"""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            # If state file is corrupt, start fresh
            return {}

    def _save_state(self):
        """Save scheduler state to JSON file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_dir = Path(log_config.get('directory', './logs')).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('DocOrchestrationScheduler')
        self.logger.setLevel(log_level)
        self.logger.handlers.clear()

        # File handler
        log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def _parse_schedule(self, schedule: Dict) -> tuple:
        """Parse schedule configuration into APScheduler trigger"""
        schedule_type = schedule.get('type', 'cron')

        if schedule_type == 'cron':
            # Cron expression
            return CronTrigger(
                day_of_week=schedule.get('day_of_week', '*'),
                hour=schedule.get('hour', '*'),
                minute=schedule.get('minute', '0'),
                timezone=schedule.get('timezone', 'America/Los_Angeles')
            )
        elif schedule_type == 'interval':
            # Interval-based (every N hours/minutes)
            return IntervalTrigger(
                hours=schedule.get('hours', 0),
                minutes=schedule.get('minutes', 0),
                timezone=schedule.get('timezone', 'America/Los_Angeles')
            )
        elif schedule_type == 'daily':
            # Daily at specific time
            hour, minute = map(int, schedule.get('time', '09:00').split(':'))
            return CronTrigger(
                hour=hour,
                minute=minute,
                timezone=schedule.get('timezone', 'America/Los_Angeles')
            )
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    def run_job(self, job: JobConfig):
        """Execute a DocOrchestrator job"""
        self.logger.info(f"Starting job: {job.name}")
        self.logger.info(f"Pipeline config: {job.pipeline_config}")

        # Build command
        pipeline_config_path = Path(job.pipeline_config).expanduser()
        if not pipeline_config_path.is_absolute():
            # Relative to DocOrchestrator directory
            pipeline_config_path = self.orchestrator_path.parent / job.pipeline_config

        if not pipeline_config_path.exists():
            self.logger.error(f"Pipeline config not found: {pipeline_config_path}")
            return

        # Handle incremental processing
        actual_config_path = pipeline_config_path
        temp_config_file = None

        if job.incremental:
            self.logger.info(f"Incremental mode enabled for job '{job.name}'")

            # Get last run date from state
            last_run = self.state.get(job.name, {}).get('last_run')

            if last_run:
                # Parse last run date
                try:
                    last_run_date = datetime.fromisoformat(last_run)
                    # Calculate start_date: last_run + 1 day - lookback_days
                    start_date = last_run_date + timedelta(days=1) - timedelta(days=job.lookback_days)
                    start_date_str = start_date.strftime(job.date_format)

                    self.logger.info(f"Last run: {last_run_date.strftime('%Y-%m-%d')}")
                    self.logger.info(f"Start date for this run: {start_date.strftime('%Y-%m-%d')} (formatted as {start_date_str})")

                    # Load and modify pipeline config
                    with open(pipeline_config_path, 'r') as f:
                        pipeline_config = yaml.safe_load(f)

                    # Inject start_date parameter
                    if 'parameters' not in pipeline_config:
                        pipeline_config['parameters'] = {}
                    pipeline_config['parameters']['start_date'] = start_date_str

                    # Write to temporary config file
                    temp_config_file = tempfile.NamedTemporaryFile(
                        mode='w',
                        suffix='.yaml',
                        delete=False,
                        dir=pipeline_config_path.parent
                    )
                    yaml.dump(pipeline_config, temp_config_file)
                    temp_config_file.close()
                    actual_config_path = Path(temp_config_file.name)

                    self.logger.info(f"Created temporary config with start_date parameter: {actual_config_path}")

                except Exception as e:
                    self.logger.warning(f"Failed to process incremental date: {e}. Running without start_date.")
            else:
                self.logger.info(f"No previous run found for '{job.name}'. Running full job.")

        cmd = [
            'python3',
            str(self.orchestrator_path),
            '--config', str(actual_config_path),
            '--yes'  # Auto-confirm all prompts
        ]

        self.logger.info(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=job.timeout
            )

            if result.returncode == 0:
                self.logger.info(f"Job '{job.name}' completed successfully")
                self.logger.debug(f"Output: {result.stdout[-500:]}")  # Last 500 chars

                # Update state for incremental jobs
                if job.incremental:
                    self.state[job.name] = {
                        'last_run': datetime.now().isoformat(),
                        'status': 'success'
                    }
                    self._save_state()
                    self.logger.info(f"Updated state for '{job.name}'")
            else:
                self.logger.error(f"Job '{job.name}' failed with code {result.returncode}")
                self.logger.error(f"Error: {result.stderr[-500:]}")

                # Update state with failure
                if job.incremental:
                    if job.name not in self.state:
                        self.state[job.name] = {}
                    self.state[job.name]['status'] = 'failed'
                    self.state[job.name]['last_attempt'] = datetime.now().isoformat()
                    self._save_state()

        except subprocess.TimeoutExpired:
            self.logger.error(f"Job '{job.name}' timed out after {job.timeout} seconds")

            if job.incremental:
                if job.name not in self.state:
                    self.state[job.name] = {}
                self.state[job.name]['status'] = 'timeout'
                self.state[job.name]['last_attempt'] = datetime.now().isoformat()
                self._save_state()

        except Exception as e:
            self.logger.error(f"Job '{job.name}' failed with exception: {e}")

            if job.incremental:
                if job.name not in self.state:
                    self.state[job.name] = {}
                self.state[job.name]['status'] = 'error'
                self.state[job.name]['last_attempt'] = datetime.now().isoformat()
                self._save_state()
        finally:
            # Clean up temporary config file
            if temp_config_file and actual_config_path.exists():
                try:
                    actual_config_path.unlink()
                    self.logger.debug(f"Cleaned up temporary config: {actual_config_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary config: {e}")

    def add_jobs(self):
        """Add all configured jobs to the scheduler"""
        jobs = self.config.get('jobs', [])

        if not jobs:
            self.logger.warning("No jobs configured")
            return

        for job_config in jobs:
            if not job_config.get('enabled', True):
                self.logger.info(f"Skipping disabled job: {job_config.get('name')}")
                continue

            job = JobConfig(
                name=job_config['name'],
                pipeline_config=job_config['pipeline_config'],
                schedule=job_config['schedule'],
                enabled=job_config.get('enabled', True),
                timeout=job_config.get('timeout', 3600),
                incremental=job_config.get('incremental', False),
                date_format=job_config.get('date_format', '%m%d%Y'),
                lookback_days=job_config.get('lookback_days', 0)
            )

            try:
                trigger = self._parse_schedule(job.schedule)
                self.scheduler.add_job(
                    self.run_job,
                    trigger=trigger,
                    args=[job],
                    id=job.name,
                    name=job.name,
                    replace_existing=True
                )
                self.logger.info(f"Added job: {job.name}")
                self.logger.info(f"  Schedule: {job.schedule}")
            except Exception as e:
                self.logger.error(f"Failed to add job '{job.name}': {e}")

    def start(self):
        """Start the scheduler"""
        self.logger.info("="*60)
        self.logger.info("DocOrchestrationScheduler Starting")
        self.logger.info("="*60)

        # Add jobs
        self.add_jobs()

        # Print scheduled jobs
        jobs = self.scheduler.get_jobs()
        if jobs:
            self.logger.info(f"\nScheduled {len(jobs)} job(s):")
            for job in jobs:
                self.logger.info(f"  • {job.name}")
                self.logger.info(f"    Next run: {job.next_run_time}")
        else:
            self.logger.warning("No jobs scheduled. Exiting.")
            return

        # Start scheduler
        try:
            self.logger.info("\nScheduler started. Press Ctrl+C to stop.")
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("\nScheduler stopped by user")

    def run_once(self, job_name: Optional[str] = None):
        """Run jobs once immediately (for testing)"""
        self.logger.info("Running jobs once (test mode)")

        jobs_config = self.config.get('jobs', [])

        for job_config in jobs_config:
            if not job_config.get('enabled', True):
                continue

            if job_name and job_config['name'] != job_name:
                continue

            job = JobConfig(
                name=job_config['name'],
                pipeline_config=job_config['pipeline_config'],
                schedule=job_config['schedule'],
                enabled=job_config.get('enabled', True),
                timeout=job_config.get('timeout', 3600),
                incremental=job_config.get('incremental', False),
                date_format=job_config.get('date_format', '%m%d%Y'),
                lookback_days=job_config.get('lookback_days', 0)
            )

            self.run_job(job)

    def list_jobs(self):
        """List all configured jobs"""
        jobs = self.config.get('jobs', [])

        print("\n" + "="*60)
        print("CONFIGURED JOBS")
        print("="*60)

        if not jobs:
            print("No jobs configured")
            return

        for job in jobs:
            status = "✓ Enabled" if job.get('enabled', True) else "✗ Disabled"
            print(f"\n{job['name']} ({status})")
            print(f"  Pipeline: {job['pipeline_config']}")
            print(f"  Schedule: {job['schedule']}")
            print(f"  Timeout: {job.get('timeout', 3600)}s")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DocOrchestrationScheduler - Schedule DocOrchestrator pipeline runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start scheduler daemon (runs continuously)
  python3 scheduler.py --config schedules.yaml

  # List configured jobs
  python3 scheduler.py --config schedules.yaml --list

  # Run all jobs once (for testing)
  python3 scheduler.py --config schedules.yaml --run-once

  # Run specific job once
  python3 scheduler.py --config schedules.yaml --run-once --job "Weekly Qwilo Blog"
        """
    )

    parser.add_argument(
        '-c', '--config',
        required=True,
        help='Path to scheduler configuration YAML file'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all configured jobs and exit'
    )

    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run all jobs once immediately (for testing)'
    )

    parser.add_argument(
        '--job',
        help='Specific job name to run with --run-once'
    )

    args = parser.parse_args()

    try:
        scheduler = DocOrchestrationScheduler(args.config)

        if args.list:
            scheduler.list_jobs()
        elif args.run_once:
            scheduler.run_once(job_name=args.job)
        else:
            scheduler.start()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
