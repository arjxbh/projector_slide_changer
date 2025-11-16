#!/usr/bin/env python3
"""
Unit tests for actuator_control.py
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import sys
import threading
import time

# Mock RPi.GPIO before importing actuator_control
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

# Now import the module under test
import actuator_control


class TestGPIOFunctions(unittest.TestCase):
    """Test GPIO control functions"""
    
    def setUp(self):
        """Reset GPIO state before each test"""
        actuator_control.gpio_initialized = False
        actuator_control.GPIO.reset_mock()
    
    @patch('actuator_control.GPIO')
    def test_setup_gpio(self, mock_gpio):
        """Test GPIO initialization"""
        actuator_control.setup_gpio()
        
        # Verify GPIO was configured correctly
        mock_gpio.setmode.assert_called_once_with(actuator_control.GPIO.BCM)
        mock_gpio.setwarnings.assert_called_once_with(False)
        self.assertEqual(mock_gpio.setup.call_count, 2)
        mock_gpio.setup.assert_any_call(actuator_control.RELAY_CHANNEL_1, actuator_control.GPIO.OUT)
        mock_gpio.setup.assert_any_call(actuator_control.RELAY_CHANNEL_2, actuator_control.GPIO.OUT)
        
        # Verify initial state (stop state)
        self.assertEqual(mock_gpio.output.call_count, 2)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_1, actuator_control.RELAY_ON)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_2, actuator_control.RELAY_OFF)
        
        # Verify it's marked as initialized
        self.assertTrue(actuator_control.gpio_initialized)
    
    @patch('actuator_control.GPIO')
    def test_setup_gpio_idempotent(self, mock_gpio):
        """Test that setup_gpio can be called multiple times safely"""
        actuator_control.setup_gpio()
        actuator_control.setup_gpio()
        
        # Should only initialize once
        self.assertEqual(mock_gpio.setmode.call_count, 1)
    
    @patch('actuator_control.GPIO')
    def test_stop_actuator(self, mock_gpio):
        """Test stopping the actuator"""
        actuator_control.stop_actuator()
        
        # Verify GPIO pins set to different states (stop)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_1, actuator_control.RELAY_ON)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_2, actuator_control.RELAY_OFF)
    
    @patch('actuator_control.time.sleep')
    @patch('actuator_control.GPIO')
    @patch('actuator_control.stop_actuator')
    def test_extend_actuator(self, mock_stop, mock_gpio, mock_sleep):
        """Test extending the actuator"""
        duration = 2.0
        actuator_control.extend_actuator(duration)
        
        # Verify both GPIO pins set to ON (extend)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_1, actuator_control.RELAY_ON)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_2, actuator_control.RELAY_ON)
        
        # Verify sleep was called with the duration
        mock_sleep.assert_any_call(duration)
        
        # Verify stop was called after extension
        mock_stop.assert_called_once()
    
    @patch('actuator_control.time.sleep')
    @patch('actuator_control.GPIO')
    @patch('actuator_control.stop_actuator')
    def test_retract_actuator(self, mock_stop, mock_gpio, mock_sleep):
        """Test retracting the actuator"""
        duration = 2.0
        actuator_control.retract_actuator(duration)
        
        # Verify both GPIO pins set to OFF (retract)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_1, actuator_control.RELAY_OFF)
        mock_gpio.output.assert_any_call(actuator_control.RELAY_CHANNEL_2, actuator_control.RELAY_OFF)
        
        # Verify sleep was called with the duration
        mock_sleep.assert_any_call(duration)
        
        # Verify stop was called after retraction
        mock_stop.assert_called_once()


class TestCycleFunctions(unittest.TestCase):
    """Test cycle execution functions"""
    
    def setUp(self):
        """Reset state before each test"""
        actuator_control.running = False
        actuator_control.cycle_wait_time = 10.0
    
    @patch('actuator_control.time.sleep')
    @patch('actuator_control.retract_actuator')
    @patch('actuator_control.extend_actuator')
    def test_run_cycle(self, mock_extend, mock_retract, mock_sleep):
        """Test running a complete cycle"""
        actuator_control.run_cycle()
        
        # Verify extend was called
        mock_extend.assert_called_once_with(actuator_control.CYCLE_EXTEND_TIME)
        
        # Verify stop delay
        mock_sleep.assert_any_call(actuator_control.STOP_DELAY)
        
        # Verify retract was called
        mock_retract.assert_called_once_with(actuator_control.CYCLE_RETRACT_TIME)
        
        # Verify cycle wait time was used
        mock_sleep.assert_any_call(10.0)


class TestAPIRoutes(unittest.TestCase):
    """Test Flask API endpoints"""
    
    def setUp(self):
        """Reset state and create test client before each test"""
        actuator_control.running = False
        actuator_control.cycle_wait_time = 10.0
        actuator_control.cycle_thread = None
        self.app = actuator_control.app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
    
    def tearDown(self):
        """Clean up after each test"""
        actuator_control.running = False
        if actuator_control.cycle_thread and actuator_control.cycle_thread.is_alive():
            actuator_control.running = False
            actuator_control.cycle_thread.join(timeout=1.0)
    
    def test_get_status_stopped(self):
        """Test getting status when stopped"""
        actuator_control.running = False
        actuator_control.cycle_wait_time = 15.0
        
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['running'])
        self.assertEqual(data['cycle_wait_time'], 15.0)
    
    def test_get_status_running(self):
        """Test getting status when running"""
        actuator_control.running = True
        actuator_control.cycle_wait_time = 20.0
        
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['running'])
        self.assertEqual(data['cycle_wait_time'], 20.0)
    
    @patch('actuator_control.threading.Thread')
    def test_start_cycling_success(self, mock_thread):
        """Test starting the actuator successfully"""
        actuator_control.running = False
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        response = self.client.post('/api/start')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('started', data['message'].lower())
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Verify running flag was set
        self.assertTrue(actuator_control.running)
    
    def test_start_cycling_already_running(self):
        """Test starting when already running"""
        actuator_control.running = True
        
        response = self.client.post('/api/start')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('already', data['message'].lower())
    
    @patch('actuator_control.stop_actuator')
    def test_stop_cycling_success(self, mock_stop):
        """Test stopping the actuator successfully"""
        actuator_control.running = True
        
        response = self.client.post('/api/stop')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('stopped', data['message'].lower())
        
        # Verify stop_actuator was called
        mock_stop.assert_called_once()
        
        # Verify running flag was cleared
        self.assertFalse(actuator_control.running)
    
    def test_stop_cycling_not_running(self):
        """Test stopping when not running"""
        actuator_control.running = False
        
        response = self.client.post('/api/stop')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('not running', data['message'].lower())
    
    def test_update_cycle_wait_time_success(self):
        """Test updating cycle wait time successfully"""
        new_time = 15.5
        
        response = self.client.post(
            '/api/cycle_wait_time',
            data=json.dumps({'time': new_time}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['cycle_wait_time'], new_time)
        self.assertEqual(actuator_control.cycle_wait_time, new_time)
    
    def test_update_cycle_wait_time_missing_parameter(self):
        """Test updating cycle wait time without time parameter"""
        response = self.client.post(
            '/api/cycle_wait_time',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('missing', data['message'].lower())
    
    def test_update_cycle_wait_time_negative(self):
        """Test updating cycle wait time with negative value"""
        response = self.client.post(
            '/api/cycle_wait_time',
            data=json.dumps({'time': -5}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('non-negative', data['message'].lower())
    
    def test_update_cycle_wait_time_invalid_type(self):
        """Test updating cycle wait time with invalid type"""
        response = self.client.post(
            '/api/cycle_wait_time',
            data=json.dumps({'time': 'not a number'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('invalid', data['message'].lower())


class TestActuatorControlLoop(unittest.TestCase):
    """Test the actuator control loop"""
    
    def setUp(self):
        """Reset state before each test"""
        actuator_control.running = False
        actuator_control.cycle_wait_time = 0.1  # Short wait for testing
    
    @patch('actuator_control.time.sleep')
    @patch('actuator_control.run_cycle')
    @patch('actuator_control.retract_actuator')
    @patch('actuator_control.setup_gpio')
    def test_actuator_control_loop_initial_retract(self, mock_setup, mock_retract, mock_run_cycle, mock_sleep):
        """Test that control loop performs initial retraction"""
        actuator_control.running = True
        
        # Run the loop briefly
        actuator_control.actuator_control_loop()
        
        # Verify initial retraction
        mock_retract.assert_called_once_with(actuator_control.INITIAL_RETRACT_TIME)
    
    @patch('actuator_control.time.sleep')
    @patch('actuator_control.run_cycle')
    @patch('actuator_control.retract_actuator')
    @patch('actuator_control.setup_gpio')
    def test_actuator_control_loop_runs_cycles(self, mock_setup, mock_retract, mock_run_cycle, mock_sleep):
        """Test that control loop runs cycles when running"""
        actuator_control.running = True
        
        # Make run_cycle set running to False after first call to prevent infinite loop
        def stop_after_one():
            actuator_control.running = False
        
        mock_run_cycle.side_effect = stop_after_one
        
        # Run the loop
        actuator_control.actuator_control_loop()
        
        # Verify cycle was run
        mock_run_cycle.assert_called()
    
    @patch('actuator_control.stop_actuator')
    @patch('actuator_control.GPIO')
    def test_actuator_control_loop_error_handling(self, mock_gpio, mock_stop):
        """Test error handling in control loop"""
        actuator_control.running = True
        
        # Make setup_gpio raise an exception
        mock_gpio.setmode.side_effect = Exception("GPIO error")
        
        # Run the loop - should handle error gracefully
        actuator_control.actuator_control_loop()
        
        # Verify stop was called
        mock_stop.assert_called()
        
        # Verify running was set to False
        self.assertFalse(actuator_control.running)


if __name__ == '__main__':
    unittest.main()

