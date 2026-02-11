"""
Motor Controller for MangoFy Scanning System
Handles stepper motor control for linear rail positioning during leaf scanning.

Hardware Configuration (from scanning code.pdf):
- Stepper Motor: NEMA 17 (200 steps/revolution, 1.8° per step)
- Driver: A4988 or DRV8825
- GPIO Pins:
  * STEP: GPIO 12 (hardware PWM-capable)
  * DIR: GPIO 5
  * ENABLE: GPIO 6
  * IR_SENSOR: GPIO 26 (limit switch/home sensor)
  * LED_LIGHT: GPIO 13 (illumination control)
- Linear travel per revolution: ~94.2mm (Module 1.5, 20-tooth pinion)
- Total travel distance: 200mm (for 4 frames)
"""
import time
import os
from typing import Optional, Callable

# Try to import GPIO libraries (only available on Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("RPi.GPIO not available - running in simulation mode")


class MotorController:
    """
    Controls stepper motor via GPIO for linear rail scanning system.
    
    Hardware Configuration (from HARDWARE_SPECIFICATIONS.md):
    - Stepper Motor: NEMA 17 (200 steps/revolution, 1.8° per step)
    - Driver: A4988 or DRV8825
    - Linear travel per revolution: ~94.2mm (Module 1.5, 20-tooth pinion)
    - Total travel distance: 200mm (for 4 frames)
    
    Scanning Process:
    1. Home motor to initial position (limit switch)
    2. Move to first frame position (0mm)
    3. Capture frame, move to next position (+50mm steps for 4 frames)
    4. Return to home after scan complete
    """
    
    def __init__(self, 
                 step_pin: int = 12,  # Hardware PWM-capable pin (PDF spec)
                 dir_pin: int = 5,    # PDF spec
                 enable_pin: int = 6,  # PDF spec
                 limit_switch_pin: int = 26,  # IR sensor (PDF spec)
                 light_pin: int = 13,  # LED control (PDF spec)
                 steps_per_revolution: int = 200,
                 linear_travel_per_rev: float = 94.2,  # mm
                 use_gpio: bool = True):
        """
        Initialize motor controller.
        
        Args:
            step_pin: GPIO pin for STEP signal
            dir_pin: GPIO pin for DIR signal  
            enable_pin: GPIO pin for ENABLE signal
            limit_switch_pin: GPIO pin for home limit switch
            steps_per_revolution: Stepper motor steps (200 for 1.8° motors)
            linear_travel_per_rev: Linear distance per full rotation (mm)
            use_gpio: Whether to use actual GPIO (False for testing/simulation)
        """
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.enable_pin = enable_pin
        self.limit_switch_pin = limit_switch_pin
        self.light_pin = light_pin
        self.steps_per_rev = steps_per_revolution
        self.mm_per_rev = linear_travel_per_rev
        self.steps_per_mm = steps_per_revolution / linear_travel_per_rev
        
        self.current_position = 0.0  # Current position in mm
        self.is_homed = False
        self.is_enabled = False
        
        # GPIO setup
        self.use_gpio = use_gpio and HAS_GPIO
        if self.use_gpio:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.step_pin, GPIO.OUT)
            GPIO.setup(self.dir_pin, GPIO.OUT)
            GPIO.setup(self.enable_pin, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(self.light_pin, GPIO.OUT, initial=GPIO.HIGH)  # LED off initially
            GPIO.setup(self.limit_switch_pin, GPIO.IN)
            
            # Start with motor disabled and LED off
            GPIO.output(self.enable_pin, GPIO.HIGH)
            GPIO.output(self.light_pin, GPIO.HIGH)
            self.is_enabled = False
        else:
            print("Motor controller initialized in SIMULATION mode")
    
    def enable_motor(self):
        """Enable stepper motor driver."""
        if self.use_gpio:
            GPIO.output(self.enable_pin, GPIO.LOW)  # Active LOW
        self.is_enabled = True
    
    def disable_motor(self):
        """Disable stepper motor driver (reduces power consumption and heat)."""
        if self.use_gpio:
            GPIO.output(self.enable_pin, GPIO.HIGH)
        self.is_enabled = False
    
    def led_on(self):
        """Turn on LED lighting for image capture."""
        if self.use_gpio:
            GPIO.output(self.light_pin, GPIO.LOW)  # Active LOW
    
    def led_off(self):
        """Turn off LED lighting."""
        if self.use_gpio:
            GPIO.output(self.light_pin, GPIO.HIGH)  # Active LOW
    
    def is_at_home(self) -> bool:
        """Check if limit switch is triggered (at home position)."""
        if self.use_gpio:
            return GPIO.input(self.limit_switch_pin) == GPIO.LOW  # Active LOW switch
        return False  # Simulation mode
    
    def home_motor(self, callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """
        Home the motor by moving backward until limit switch is triggered.
        
        Args:
            callback: Optional progress callback(status_message, progress_pct)
        
        Returns:
            True if homing successful, False otherwise
        """
        if callback:
            callback("Homing motor...", 0.0)
        
        if not self.use_gpio:
            # Simulation mode
            time.sleep(1.5)
            self.current_position = 0.0
            self.is_homed = True
            if callback:
                callback("Motor homed (simulation)", 100.0)
            return True
        
        self.enable_motor()
        
        # Set direction to backward (toward home)
        GPIO.output(self.dir_pin, GPIO.LOW)
        
        # Move backward slowly until limit switch triggers
        max_steps = int(220 * self.steps_per_mm)  # 220mm max travel (safety)
        steps_taken = 0
        
        while not self.is_at_home() and steps_taken < max_steps:
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(0.001)  # 1ms pulse width
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(0.001)  # 1ms delay between steps (slow homing)
            steps_taken += 1
            
            if callback and steps_taken % 50 == 0:
                progress = (steps_taken / max_steps) * 100
                callback(f"Homing... {steps_taken} steps", progress)
        
        if self.is_at_home():
            self.current_position = 0.0
            self.is_homed = True
            if callback:
                callback("Motor homed successfully", 100.0)
            return True
        else:
            if callback:
                callback("Homing failed - limit switch not found", 0.0)
            self.disable_motor()
            return False
    
    def move_to_position(self, target_mm: float, speed_delay: float = 0.0005,
                        callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """
        Move motor to absolute position (in mm from home).
        
        Args:
            target_mm: Target position in millimeters from home
            speed_delay: Delay between steps (seconds) - controls speed
            callback: Optional progress callback(status_message, progress_pct)
        
        Returns:
            True if move successful, False otherwise
        """
        if not self.is_homed:
            if callback:
                callback("Motor not homed - cannot move", 0.0)
            return False
        
        if target_mm < 0 or target_mm > 200:
            if callback:
                callback(f"Invalid position {target_mm}mm (range 0-200mm)", 0.0)
            return False
        
        distance = target_mm - self.current_position
        if abs(distance) < 0.1:  # Already at position
            if callback:
                callback(f"Already at {target_mm:.1f}mm", 100.0)
            return True
        
        if not self.use_gpio:
            # Simulation mode
            time.sleep(abs(distance) * 0.02)  # Simulate movement time
            self.current_position = target_mm
            if callback:
                callback(f"Moved to {target_mm:.1f}mm (simulation)", 100.0)
            return True
        
        self.enable_motor()
        
        # Calculate steps needed
        steps = int(abs(distance) * self.steps_per_mm)
        
        # Set direction
        if distance > 0:
            GPIO.output(self.dir_pin, GPIO.HIGH)  # Forward
        else:
            GPIO.output(self.dir_pin, GPIO.LOW)   # Backward
        
        # Execute steps
        for step in range(steps):
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(speed_delay)
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(speed_delay)
            
            if callback and step % 50 == 0:
                progress = (step / steps) * 100
                callback(f"Moving to {target_mm:.1f}mm", progress)
        
        self.current_position = target_mm
        if callback:
            callback(f"Reached {target_mm:.1f}mm", 100.0)
        return True
    
    def scan_sequence(self, num_frames: int = 4, 
                     callback: Optional[Callable[[str, int, float], None]] = None) -> list:
        """
        Execute full scanning sequence - move to each frame position.
        
        Args:
            num_frames: Number of frames to capture (default 4)
            callback: Optional callback(status_message, frame_index, progress_pct)
        
        Returns:
            List of positions (mm) for each frame
        """
        if not self.is_homed:
            if callback:
                callback("Must home motor before scanning", 0, 0.0)
            return []
        
        # Calculate frame positions (evenly spaced across 150mm)
        total_scan_distance = 150.0  # mm (leave margin on 200mm rail)
        frame_spacing = total_scan_distance / (num_frames - 1) if num_frames > 1 else 0
        
        positions = [i * frame_spacing for i in range(num_frames)]
        
        for idx, pos in enumerate(positions):
            if callback:
                callback(f"Moving to frame {idx + 1} position", idx + 1, 
                        (idx / num_frames) * 100)
            
            success = self.move_to_position(pos)
            if not success:
                if callback:
                    callback(f"Failed to reach frame {idx + 1} position", idx + 1, 0.0)
                return positions[:idx]  # Return partial list
            
            # Small delay for vibration to settle
            time.sleep(0.2)
        
        if callback:
            callback("Scan sequence complete", num_frames, 100.0)
        
        return positions
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        self.disable_motor()
        if self.use_gpio:
            GPIO.output(self.light_pin, GPIO.HIGH)  # Turn off LED
            GPIO.cleanup([self.step_pin, self.dir_pin, self.enable_pin, self.light_pin, self.limit_switch_pin])
    
    def __del__(self):
        """Destructor - ensure cleanup."""
        self.cleanup()
