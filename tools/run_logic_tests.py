#!/usr/bin/env python3
"""Run logic-focused test subset avoiding heavy Kivy UI initialization.

Usage:
  python tools/run_logic_tests.py

Adjust SAFE_TESTS list if new pure-logic tests are added.
"""
import subprocess, sys, os

SAFE_TESTS = [
    'tests/test_severity_calculator.py',
    'tests/test_ml_predictor.py',
    'tests/test_db_manager.py',
    'tests/test_database.py',
    'tests/test_db_migration.py',
]

def main():
    env = os.environ.copy()
    # Ensure headless flag so settings guards activate, but logic tests shouldn't touch UI.
    env.setdefault('HEADLESS_TEST','1')
    cmd = [sys.executable, '-m', 'pytest', '-q'] + SAFE_TESTS
    print('Running logic test subset...')
    print('Command:', ' '.join(cmd))
    proc = subprocess.run(cmd, env=env)
    sys.exit(proc.returncode)

if __name__ == '__main__':
    main()
