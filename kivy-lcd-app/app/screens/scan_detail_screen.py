"""Scan Detail Screen - Display full details of a single scan record."""
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
import os


class ScanDetailScreen(Screen):
    """Display detailed information about a single scan record.
    
    Shows:
    - Full-size captured image
    - Disease name, confidence score, severity percentage
    - Leaf metrics (total area, lesion area, lesion coverage)
    - Associated tree name
    - Scan timestamp
    - User notes
    - Delete record button
    """
    
    # Display properties
    scan_id = NumericProperty(0)
    image_path = StringProperty("")
    disease_name = StringProperty("Unknown")
    confidence_score = NumericProperty(0.0)
    severity_percentage = NumericProperty(0.0)
    severity_name = StringProperty("Unknown")
    tree_name = StringProperty("Unknown")
    scan_timestamp = StringProperty("N/A")
    formatted_timestamp = StringProperty("N/A")
    notes = StringProperty("")
    
    # Leaf metrics (calculated from severity data)
    total_leaf_area = NumericProperty(0.0)
    lesion_area = NumericProperty(0.0)
    lesion_coverage = NumericProperty(0.0)
    
    # Confidence badge properties
    confidence_badge_text = StringProperty("")
    confidence_badge_color = StringProperty("")
    
    # UI state
    delete_enabled = BooleanProperty(True)
    
    def on_pre_enter(self, *args):
        """Load scan details when screen is entered."""
        self._load_scan_details()
    
    def _load_scan_details(self):
        """Load full scan record details from database."""
        from app.core.db import get_scan_detail
        
        # Get scan_id from app state (set by previous screen)
        app = App.get_running_app()
        scan_id = getattr(app, 'current_scan_id', 0)
        
        if not scan_id:
            self.disease_name = "Error: No scan selected"
            return
        
        self.scan_id = scan_id
        
        # Fetch full details
        scan_data = get_scan_detail(scan_id)
        
        if not scan_data:
            self.disease_name = "Error: Scan not found"
            return
        
        # Populate display properties
        self.image_path = scan_data.get("image_path", "")
        self.disease_name = scan_data.get("disease_name", "Unknown")
        self.confidence_score = scan_data.get("confidence_score", 0.0)
        self.severity_percentage = scan_data.get("severity_percentage", 0.0)
        self.severity_name = scan_data.get("severity_name", "Unknown")
        self.tree_name = scan_data.get("tree_name", "Unknown")
        self.scan_timestamp = scan_data.get("scan_timestamp", "N/A")
        self.notes = scan_data.get("notes", "") or ""
        
        # Format timestamp
        self._format_timestamp()
        
        # Update confidence badge
        self._update_confidence_badge(self.confidence_score)
        
        # Calculate leaf metrics from severity percentage
        # Assuming standard image size or using actual pixel data if available
        self._calculate_leaf_metrics()
    
    def _format_timestamp(self):
        """Format scan timestamp for display."""
        try:
            from datetime import datetime
            dt = datetime.strptime(self.scan_timestamp, "%Y-%m-%d %H:%M:%S")
            self.formatted_timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            self.formatted_timestamp = self.scan_timestamp
    
    def _calculate_leaf_metrics(self):
        """Calculate leaf area metrics from severity percentage.
        
        Note: This is a simplified calculation. In a full implementation,
        these values would be stored in the database during analysis.
        """
        # Placeholder calculation (assume standard leaf size)
        # In production, these should be stored during image analysis
        standard_leaf_area = 100000.0  # pixels² (example)
        
        self.total_leaf_area = standard_leaf_area
        self.lesion_coverage = self.severity_percentage
        self.lesion_area = (self.severity_percentage / 100.0) * standard_leaf_area
    
    def _update_confidence_badge(self, confidence):
        '''Update confidence badge text and color based on confidence value.'''
        if confidence < 0.60:
            self.confidence_badge_text = "⚠ Low Confidence"
            self.confidence_badge_color = "#DD2D1D"  # Red
        elif confidence < 0.85:
            self.confidence_badge_text = "Moderate Confidence"
            self.confidence_badge_color = "#CFBF2C"  # Yellow
        else:
            self.confidence_badge_text = "High Confidence"
            self.confidence_badge_color = "#26A421"  # Green
    
    def confirm_delete(self):
        """Show confirmation dialog before deleting scan record."""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        message = Label(
            text=f"Are you sure you want to delete this scan?\n\n"
                 f"Tree: {self.tree_name}\n"
                 f"Disease: {self.disease_name}\n"
                 f"Date: {self.formatted_timestamp}\n\n"
                 f"This action cannot be undone.",
            halign='center',
            valign='middle'
        )
        content.add_widget(message)
        
        buttons = BoxLayout(size_hint_y=0.3, spacing=10)
        
        popup = Popup(
            title="Confirm Delete",
            content=content,
            size_hint=(0.8, 0.5),
            auto_dismiss=False
        )
        
        def on_cancel(instance):
            popup.dismiss()
        
        def on_confirm(instance):
            popup.dismiss()
            self.delete_scan()
        
        btn_cancel = Button(text="Cancel", on_press=on_cancel)
        btn_delete = Button(
            text="Delete",
            background_color=(0.8, 0.2, 0.2, 1.0),
            on_press=on_confirm
        )
        
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_delete)
        content.add_widget(buttons)
        
        popup.open()
    
    def delete_scan(self):
        """Delete the current scan record from database."""
        from app.core.db import delete_scan_record
        
        if not self.scan_id:
            self._show_error("No scan ID to delete")
            return
        
        try:
            success = delete_scan_record(self.scan_id)
            
            if success:
                self._show_success("Scan deleted successfully")
                # Navigate back after short delay
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self.go_back(), 1.5)
            else:
                self._show_error("Failed to delete scan")
        except Exception as e:
            self._show_error(f"Delete error: {str(e)}")
    
    def _show_success(self, message: str):
        """Show success message popup."""
        popup = Popup(
            title="Success",
            content=Label(text=message),
            size_hint=(0.6, 0.3)
        )
        popup.open()
    
    def _show_error(self, message: str):
        """Show error message popup."""
        popup = Popup(
            title="Error",
            content=Label(text=message),
            size_hint=(0.6, 0.3)
        )
        popup.open()
    
    def export_data(self):
        """Export this scan's data to JSON file."""
        from app.core.db import export_scan_to_json
        
        if not self.scan_id:
            self._show_error("No scan to export")
            return
        
        try:
            output_path = export_scan_to_json(self.scan_id)
            
            if output_path:
                self._show_success(f"Scan exported to:\n{output_path}")
            else:
                self._show_error("Export failed")
        except Exception as e:
            self._show_error(f"Export error: {str(e)}")
    
    def go_back(self):
        """Navigate back to previous screen."""
        app = App.get_running_app()
        
        # Determine which screen to return to
        previous = getattr(app, 'last_screen', 'records')
        
        if previous == 'scan_list':
            self.manager.current = 'scan_list'
        else:
            self.manager.current = 'records'
