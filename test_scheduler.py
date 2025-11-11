#!/usr/bin/env python3
"""
Test suite for DocOrchestrationScheduler
"""

import unittest
import tempfile
import yaml
from pathlib import Path
from scheduler import DocOrchestrationScheduler, JobConfig


class TestSchedulerConfig(unittest.TestCase):
    """Test configuration loading and parsing"""

    def setUp(self):
        """Create temporary config file for testing"""
        self.test_config = {
            'logging': {
                'level': 'INFO',
                'directory': './test_logs'
            },
            'jobs': [
                {
                    'name': 'Test Job 1',
                    'enabled': True,
                    'pipeline_config': 'test_pipeline.yaml',
                    'timeout': 1800,
                    'schedule': {
                        'type': 'daily',
                        'time': '09:00',
                        'timezone': 'America/Los_Angeles'
                    }
                },
                {
                    'name': 'Test Job 2',
                    'enabled': False,
                    'pipeline_config': 'test_pipeline2.yaml',
                    'timeout': 3600,
                    'schedule': {
                        'type': 'cron',
                        'day_of_week': 'mon',
                        'hour': 10,
                        'minute': 0,
                        'timezone': 'America/Los_Angeles'
                    }
                }
            ]
        }

        self.temp_config = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        )
        yaml.dump(self.test_config, self.temp_config)
        self.temp_config.close()

    def tearDown(self):
        """Clean up temporary files"""
        Path(self.temp_config.name).unlink(missing_ok=True)

    def test_config_loading(self):
        """Test configuration file loading"""
        try:
            scheduler = DocOrchestrationScheduler(self.temp_config.name)
            self.assertIsNotNone(scheduler.config)
            self.assertEqual(scheduler.config['logging']['level'], 'INFO')
            self.assertEqual(len(scheduler.config['jobs']), 2)
        except FileNotFoundError:
            # DocOrchestrator not found - skip test
            self.skipTest("DocOrchestrator not installed")

    def test_job_config_parsing(self):
        """Test parsing job configuration"""
        try:
            scheduler = DocOrchestrationScheduler(self.temp_config.name)
            jobs = scheduler.config['jobs']

            # Test first job
            job1 = jobs[0]
            self.assertEqual(job1['name'], 'Test Job 1')
            self.assertTrue(job1['enabled'])
            self.assertEqual(job1['schedule']['type'], 'daily')

            # Test second job
            job2 = jobs[1]
            self.assertEqual(job2['name'], 'Test Job 2')
            self.assertFalse(job2['enabled'])
            self.assertEqual(job2['schedule']['type'], 'cron')
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")

    def test_daily_schedule_parsing(self):
        """Test parsing daily schedule type"""
        try:
            scheduler = DocOrchestrationScheduler(self.temp_config.name)
            schedule = self.test_config['jobs'][0]['schedule']
            trigger = scheduler._parse_schedule(schedule)
            self.assertIsNotNone(trigger)
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")

    def test_cron_schedule_parsing(self):
        """Test parsing cron schedule type"""
        try:
            scheduler = DocOrchestrationScheduler(self.temp_config.name)
            schedule = self.test_config['jobs'][1]['schedule']
            trigger = scheduler._parse_schedule(schedule)
            self.assertIsNotNone(trigger)
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")


class TestJobConfig(unittest.TestCase):
    """Test JobConfig dataclass"""

    def test_job_config_creation(self):
        """Test creating JobConfig instance"""
        job = JobConfig(
            name='Test Job',
            pipeline_config='test.yaml',
            schedule={'type': 'daily', 'time': '09:00'},
            enabled=True,
            timeout=1800
        )

        self.assertEqual(job.name, 'Test Job')
        self.assertEqual(job.pipeline_config, 'test.yaml')
        self.assertTrue(job.enabled)
        self.assertEqual(job.timeout, 1800)

    def test_job_config_defaults(self):
        """Test JobConfig default values"""
        job = JobConfig(
            name='Test Job',
            pipeline_config='test.yaml',
            schedule={'type': 'daily'}
        )

        self.assertTrue(job.enabled)
        self.assertEqual(job.timeout, 3600)


class TestScheduleTypes(unittest.TestCase):
    """Test different schedule type configurations"""

    def setUp(self):
        """Create temporary config for schedule testing"""
        self.test_configs = {
            'daily': {
                'type': 'daily',
                'time': '14:30',
                'timezone': 'America/Los_Angeles'
            },
            'cron_simple': {
                'type': 'cron',
                'day_of_week': 'mon',
                'hour': 9,
                'minute': 0,
                'timezone': 'America/Los_Angeles'
            },
            'cron_complex': {
                'type': 'cron',
                'day_of_week': 'mon-fri',
                'hour': 14,
                'minute': 30,
                'timezone': 'America/Los_Angeles'
            },
            'interval': {
                'type': 'interval',
                'hours': 6,
                'minutes': 0,
                'timezone': 'America/Los_Angeles'
            }
        }

    def test_daily_schedule_type(self):
        """Test daily schedule type parsing"""
        # Create minimal config for scheduler
        config = {
            'logging': {'level': 'INFO', 'directory': './test_logs'},
            'jobs': [{
                'name': 'Daily Test',
                'pipeline_config': 'test.yaml',
                'schedule': self.test_configs['daily']
            }]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            scheduler = DocOrchestrationScheduler(config_path)
            trigger = scheduler._parse_schedule(self.test_configs['daily'])
            self.assertIsNotNone(trigger)
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_cron_schedule_type(self):
        """Test cron schedule type parsing"""
        config = {
            'logging': {'level': 'INFO', 'directory': './test_logs'},
            'jobs': [{
                'name': 'Cron Test',
                'pipeline_config': 'test.yaml',
                'schedule': self.test_configs['cron_simple']
            }]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            scheduler = DocOrchestrationScheduler(config_path)
            trigger = scheduler._parse_schedule(self.test_configs['cron_simple'])
            self.assertIsNotNone(trigger)
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_interval_schedule_type(self):
        """Test interval schedule type parsing"""
        config = {
            'logging': {'level': 'INFO', 'directory': './test_logs'},
            'jobs': [{
                'name': 'Interval Test',
                'pipeline_config': 'test.yaml',
                'schedule': self.test_configs['interval']
            }]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            scheduler = DocOrchestrationScheduler(config_path)
            trigger = scheduler._parse_schedule(self.test_configs['interval'])
            self.assertIsNotNone(trigger)
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestIncrementalProcessing(unittest.TestCase):
    """Test incremental state tracking"""

    def setUp(self):
        """Create temporary config with incremental job"""
        self.config = {
            'logging': {'level': 'INFO', 'directory': './test_logs'},
            'jobs': [{
                'name': 'Incremental Test Job',
                'pipeline_config': 'test_pipeline.yaml',
                'timeout': 1800,
                'incremental': True,
                'date_format': '%m%d%Y',
                'lookback_days': 1,
                'schedule': {
                    'type': 'daily',
                    'time': '09:00',
                    'timezone': 'America/Los_Angeles'
                }
            }]
        }

        self.temp_config = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        )
        yaml.dump(self.config, self.temp_config)
        self.temp_config.close()

    def tearDown(self):
        """Clean up temporary files"""
        Path(self.temp_config.name).unlink(missing_ok=True)
        state_file = Path(self.temp_config.name).parent / 'scheduler_state.json'
        state_file.unlink(missing_ok=True)

    def test_incremental_config_loading(self):
        """Test loading incremental job configuration"""
        try:
            scheduler = DocOrchestrationScheduler(self.temp_config.name)
            job_config = scheduler.config['jobs'][0]

            self.assertTrue(job_config.get('incremental', False))
            self.assertEqual(job_config.get('date_format'), '%m%d%Y')
            self.assertEqual(job_config.get('lookback_days'), 1)
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")

    def test_state_file_creation(self):
        """Test state file is created"""
        try:
            scheduler = DocOrchestrationScheduler(self.temp_config.name)
            # State file should exist after initialization
            self.assertEqual(scheduler.state, {})

            # Simulate state update
            scheduler.state['test_job'] = {
                'last_run': '2025-01-15T09:00:00',
                'status': 'success'
            }
            scheduler._save_state()

            # Verify file exists
            self.assertTrue(scheduler.state_file.exists())
        except FileNotFoundError:
            self.skipTest("DocOrchestrator not installed")

    def test_incremental_job_defaults(self):
        """Test JobConfig incremental defaults"""
        job = JobConfig(
            name='Test Job',
            pipeline_config='test.yaml',
            schedule={'type': 'daily'}
        )

        self.assertFalse(job.incremental)
        self.assertEqual(job.date_format, '%m%d%Y')
        self.assertEqual(job.lookback_days, 0)

    def test_incremental_job_with_values(self):
        """Test JobConfig with incremental values"""
        job = JobConfig(
            name='Test Job',
            pipeline_config='test.yaml',
            schedule={'type': 'daily'},
            incremental=True,
            date_format='%Y-%m-%d',
            lookback_days=2
        )

        self.assertTrue(job.incremental)
        self.assertEqual(job.date_format, '%Y-%m-%d')
        self.assertEqual(job.lookback_days, 2)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSchedulerConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestJobConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestScheduleTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalProcessing))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
