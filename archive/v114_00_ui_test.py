import tkinter as tk
import sys
import os
import time
import threading

# Ensure project modules are in path
sys.path.append(r"e:\Snow Runner New Tool")

def test_ui_launch():
    print("=" * 60)
    print("UI LAUNCH VERIFICATION (v114.00)")
    print("=" * 60)
    
    try:
        from snowrunner_editor import SnowRunnerEditor
        
        # We need to run this in a way that it doesn't block forever
        root = tk.Tk()
        app = SnowRunnerEditor(root)
        
        # Test if the new tab exists
        tabs = [app.notebook.tab(i, "text") for i in range(app.notebook.index("end"))]
        print(f"Detected Tabs: {tabs}")
        
        if "💰 Bank & Rank" in tabs:
            print("SUCCESS: 'Bank & Rank' tab found in UI.")
        else:
            print("FAILURE: 'Bank & Rank' tab NOT found in UI.")
            
        # Close after 1 second
        root.after(1000, root.destroy)
        root.mainloop()
        print("SUCCESS: UI launched and closed without fatal errors.")
        
    except Exception as e:
        print(f"CRITICAL UI FAIL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ui_launch()
