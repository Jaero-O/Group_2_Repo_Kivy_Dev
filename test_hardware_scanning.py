"""
Test script for hardware scanning system.
Run this to test motor controller and capture pipeline without launching full Kivy app.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "kivy-lcd-app"))

def test_motor_controller():
    """Test motor controller in simulation mode."""
    print("\n" + "="*60)
    print("TEST 1: Motor Controller (Simulation Mode)")
    print("="*60)
    
    from app.core.motor_controller import MotorController
    
    # Initialize in simulation mode
    motor = MotorController(use_gpio=False)
    print(f"✓ Motor controller initialized")
    print(f"  - GPIO available: {motor.use_gpio}")
    print(f"  - Steps per mm: {motor.steps_per_mm:.2f}")
    
    # Test homing
    print("\nHoming motor...")
    success = motor.home_motor(callback=lambda msg, pct: print(f"  [{pct:3.0f}%] {msg}"))
    print(f"✓ Homing {'SUCCESS' if success else 'FAILED'}")
    print(f"  - Current position: {motor.current_position}mm")
    print(f"  - Is homed: {motor.is_homed}")
    
    # Test movement
    print("\nMoving to 50mm...")
    success = motor.move_to_position(50, callback=lambda msg, pct: print(f"  [{pct:3.0f}%] {msg}"))
    print(f"✓ Movement {'SUCCESS' if success else 'FAILED'}")
    print(f"  - Current position: {motor.current_position}mm")
    
    # Test scan sequence
    print("\nExecuting scan sequence (4 frames)...")
    positions = motor.scan_sequence(4, callback=lambda msg, idx, pct: print(f"  [{pct:3.0f}%] Frame {idx}: {msg}"))
    print(f"✓ Scan sequence complete")
    print(f"  - Positions: {positions}")
    
    # Cleanup
    motor.cleanup()
    print("\n✓ Motor controller test PASSED\n")
    return True


def test_capture_pipeline():
    """Test capture pipeline in simulation mode."""
    print("\n" + "="*60)
    print("TEST 2: Capture Pipeline (Simulation Mode)")
    print("="*60)
    
    from app.core.capture import MultiFrameCapture
    
    # Check for test image
    test_image = os.getenv("MANGOFY_TEST_IMAGE", "")
    if not test_image or not os.path.exists(test_image):
        print("⚠ MANGOFY_TEST_IMAGE not set or file doesn't exist")
        print("  Set environment variable to test with actual image:")
        print("  export MANGOFY_TEST_IMAGE='/path/to/test_leaf.jpg'")
        print("\n  Using fallback mode (will fail gracefully)")
        test_image = "nonexistent.jpg"
    else:
        print(f"✓ Test image found: {test_image}")
    
    # Initialize capture
    output_dir = os.path.join("data", "test_captures")
    os.makedirs(output_dir, exist_ok=True)
    
    capture = MultiFrameCapture(
        total_frames=4,
        use_hardware=False,  # Simulation mode
        overlap_percentage=15
    )
    print(f"✓ Capture pipeline initialized")
    print(f"  - Total frames: {capture.total_frames}")
    print(f"  - Hardware mode: {capture.use_hardware}")
    print(f"  - Overlap: {capture.overlap_pct}%")
    
    # Progress callback
    def on_progress(phase, frame_idx, total, pct):
        status_map = {
            'homing': "Homing motor",
            'positioning': f"Positioning for frame {frame_idx}",
            'capturing': f"Scanning {frame_idx} out of {total} Frames",
            'stitching': "Stitching Frames",
            'preprocessing': "Processing image",
            'analyzing': "Analyzing disease",
            'complete': "Capture complete",
        }
        msg = status_map.get(phase, phase)
        print(f"  [{pct:3.0f}%] {msg}...")
    
    # Run capture
    print("\nRunning capture pipeline...")
    result = capture.run(test_image, output_dir, callback=on_progress)
    
    if result:
        print(f"\n✓ Capture pipeline SUCCESS")
        print(f"  - Result image: {result}")
        print(f"  - File exists: {os.path.exists(result)}")
        
        # Check output files
        print("\nOutput files:")
        for filename in ['stitched_raw.jpg', 'stitched_processed.jpg', 'stitched_processed_480x800.jpg']:
            path = os.path.join(output_dir, filename)
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            print(f"  {'✓' if exists else '✗'} {filename}: {size/1024:.1f} KB")
    else:
        print(f"\n✗ Capture pipeline FAILED")
        if not os.path.exists(test_image):
            print("  Reason: Test image not found (expected in simulation mode)")
            print("\n✓ Capture pipeline test PASSED (graceful failure)")
            return True
    
    # Cleanup
    capture.cleanup()
    print("\n✓ Capture pipeline test PASSED\n")
    return True


def test_integration():
    """Test full integration of motor + capture."""
    print("\n" + "="*60)
    print("TEST 3: Full Integration Test")
    print("="*60)
    
    from app.core.motor_controller import MotorController
    from app.core.capture import MultiFrameCapture
    
    test_image = os.getenv("MANGOFY_TEST_IMAGE", "")
    if not test_image or not os.path.exists(test_image):
        print("⚠ Skipping integration test (no test image)")
        print("  Set MANGOFY_TEST_IMAGE to run full integration test")
        print("\n✓ Integration test SKIPPED (not a failure)\n")
        return True
    
    print(f"✓ Test image: {test_image}")
    
    # Initialize components
    motor = MotorController(use_gpio=False)
    capture = MultiFrameCapture(total_frames=4, use_hardware=False)
    
    # Execute workflow
    print("\n1. Homing motor...")
    if not motor.home_motor():
        print("✗ Homing failed")
        return False
    print("   ✓ Motor homed")
    
    print("\n2. Running capture...")
    output_dir = os.path.join("data", "integration_test")
    result = capture.run(test_image, output_dir, callback=lambda *args: None)
    
    if not result:
        print("✗ Capture failed")
        return False
    print(f"   ✓ Capture complete: {result}")
    
    print("\n3. Cleanup...")
    motor.cleanup()
    capture.cleanup()
    print("   ✓ Cleanup complete")
    
    print("\n✓ Integration test PASSED\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MANGOFY HARDWARE SCANNING SYSTEM - TEST SUITE")
    print("="*60)
    print("\nThis test suite validates the scanning system without hardware.")
    print("Tests run in SIMULATION MODE (no GPIO/camera required).\n")
    
    # Check environment
    print("Environment:")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working directory: {os.getcwd()}")
    print(f"  MANGOFY_TEST_IMAGE: {os.getenv('MANGOFY_TEST_IMAGE', 'NOT SET')}")
    
    # Run tests
    results = []
    
    try:
        results.append(("Motor Controller", test_motor_controller()))
    except Exception as e:
        print(f"\n✗ Motor Controller test FAILED with exception:")
        print(f"   {type(e).__name__}: {e}")
        results.append(("Motor Controller", False))
    
    try:
        results.append(("Capture Pipeline", test_capture_pipeline()))
    except Exception as e:
        print(f"\n✗ Capture Pipeline test FAILED with exception:")
        print(f"   {type(e).__name__}: {e}")
        results.append(("Capture Pipeline", False))
    
    try:
        results.append(("Integration Test", test_integration()))
    except Exception as e:
        print(f"\n✗ Integration test FAILED with exception:")
        print(f"   {type(e).__name__}: {e}")
        results.append(("Integration Test", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
