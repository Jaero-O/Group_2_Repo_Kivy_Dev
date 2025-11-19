"""Pytest plugin to auto-assign category markers based on filename heuristics.
This avoids manual bulk editing of existing test files.
"""
import pytest

def pytest_collection_modifyitems(config, items):
    for item in items:
        name = item.name.lower()
        path = str(item.fspath).lower()
        markers_to_add = []
        if 'integration' in path or 'integration' in name:
            markers_to_add.append('integration')
        if 'regression' in path or 'visual_regression' in name:
            markers_to_add.append('regression')
            if 'visual' in path or 'visual' in name:
                markers_to_add.append('visual')
        if 'performance' in path or 'benchmark' in name:
            markers_to_add.append('performance')
        if 'stress' in path:
            markers_to_add.append('stress')
        if 'contrast' in path or 'accessibility' in name:
            markers_to_add.append('accessibility')
        if 'kv_smoke' in name or 'screen' in name or 'lcd_app' in name:
            markers_to_add.append('ui')
        # Default functional for tests not categorized
        if not markers_to_add:
            markers_to_add.append('functional')
        for m in markers_to_add:
            item.add_marker(getattr(pytest.mark, m))
