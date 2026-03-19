import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from database import DatabaseManager

# Use a professional style for plots
plt.style.use('ggplot')

try:
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class AnalyticsModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#f8fafd") # Modern light background

        # Professional Style Configuration
        self.style = ttk.Style()
        self.style.configure("TNotebook", background="#f8fafd")
        self.style.configure("TNotebook.Tab", font=("Helvetica", 10, "bold"), padding=[10, 5])

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)

        # Tab 1: Attendance
        self.attendance_frame = tk.Frame(self.notebook, bg="#ffffff", bd=1, relief="flat")
        self.notebook.add(self.attendance_frame, text=" 📊 Attendance Forecast ")

        # Tab 2: Contributions
        self.contrib_frame = tk.Frame(self.notebook, bg="#ffffff", bd=1, relief="flat")
        self.notebook.add(self.contrib_frame, text=" 💰 Financial Analytics ")

        self.setup_attendance_tab()
        self.setup_contrib_tab()

    def create_control_bar(self, parent, command):
        """Helper to create a consistent toolbar for both tabs."""
        bar = tk.Frame(parent, bg="#ffffff", pady=10)
        bar.pack(fill="x", padx=10)

        # Container for the date filters
        filter_frame = tk.Frame(bar, bg="#ffffff")
        filter_frame.pack(side="left")

        tk.Label(filter_frame, text="Date Range:", bg="#ffffff", font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        
        date_from = DateEntry(filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        date_from.pack(side="left", padx=5)
        date_from.set_date(datetime.now() - timedelta(days=180))

        tk.Label(filter_frame, text="to", bg="#ffffff").pack(side="left")

        date_to = DateEntry(filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        date_to.pack(side="left", padx=5)
        date_to.set_date(datetime.now())

        btn = tk.Button(bar, text="Generate Analytics", bg="#1a73e8", fg="white", relief="flat", 
                        font=("Helvetica", 10, "bold"), padx=15, pady=5, cursor="hand2", command=command)
        btn.pack(side="right", padx=10)

        return date_from, date_to

    # ---------- Attendance Forecast ----------
    def setup_attendance_tab(self):
        self.att_from, self.att_to = self.create_control_bar(self.attendance_frame, self.forecast_attendance)
        
        self.att_chart_frame = tk.Frame(self.attendance_frame, bg="#ffffff")
        self.att_chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.show_placeholder(self.att_chart_frame, "Attendance")

    def show_placeholder(self, frame, label):
        for w in frame.winfo_children(): w.destroy()
        msg = f"Ready to analyze {label} trends.\nAdjust date range and click 'Generate Analytics'."
        tk.Label(frame, text=msg, bg="#ffffff", font=("Helvetica", 11), fg="#5f6368").pack(expand=True)

    def forecast_attendance(self):
        try:
            db = DatabaseManager()
            start = self.att_from.get_date()
            end = self.att_to.get_date()

            if start >= end:
                messagebox.showerror("Error", "Start date must be before end date.")
                return

            data = db.fetch_all("""
                SELECT date, COUNT(*) FROM attendance 
                WHERE date BETWEEN ? AND ? AND present=1 
                GROUP BY date ORDER BY date
            """, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))

            if len(data) < 3:
                messagebox.showinfo("Data Needed", "Need at least 3 days of historical attendance for a trend forecast.")
                return

            for w in self.att_chart_frame.winfo_children(): w.destroy()

            dates = [datetime.strptime(r[0], "%Y-%m-%d") for r in data]
            counts = [r[1] for r in data]

            # Regression Analysis
            x_ord = np.array([d.toordinal() for d in dates]).reshape(-1, 1)
            y_vals = np.array(counts)

            future_dates = [dates[-1] + timedelta(days=i) for i in range(1, 31)]
            future_x = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)

            if HAS_SKLEARN:
                model = LinearRegression().fit(x_ord, y_vals)
                future_y = model.predict(future_x)
            else:
                # Fallback manual calculation
                m, b = np.polyfit(x_ord.flatten(), y_vals, 1)
                future_y = m * future_x.flatten() + b

            # Clean Forecast: No negative attendance
            future_y = [max(0, val) for val in future_y]

            # Visuals
            fig = Figure(figsize=(9, 5), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(dates, counts, color='#1a73e8', linewidth=2, marker='o', markersize=4, label='Historical')
            ax.plot(future_dates, future_y, color='#d93025', linestyle='--', linewidth=2, label='Forecast')
            
            ax.set_title("Attendance Trend & 30-Day Forecast", fontsize=12, pad=15, fontweight='bold')
            ax.legend(frameon=True, facecolor='white')
            ax.tick_params(axis='x', rotation=35, labelsize=9)
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.att_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror("Forecast Error", f"An error occurred: {str(e)}")

    # ---------- Contribution Forecast ----------
    def setup_contrib_tab(self):
        self.contrib_from, self.contrib_to = self.create_control_bar(self.contrib_frame, self.forecast_contributions)
        
        self.contrib_chart_frame = tk.Frame(self.contrib_frame, bg="#ffffff")
        self.contrib_chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.show_placeholder(self.contrib_chart_frame, "Financial")

    def forecast_contributions(self):
        try:
            db = DatabaseManager()
            start = self.contrib_from.get_date().strftime("%Y-%m-%d")
            end = self.contrib_to.get_date().strftime("%Y-%m-%d")

            query = """
                SELECT strftime('%Y-%m', date) as month, SUM(amount) 
                FROM financial_records 
                WHERE date BETWEEN ? AND ?
                GROUP BY month 
                ORDER BY month
            """
            data = db.fetch_all(query, (start, end))

            # Clear previous chart area
            for widget in self.contrib_chart_frame.winfo_children():
                widget.destroy()

            if not data:
                # No data at all
                msg = f"No financial records found between {start} and {end}."
                label = tk.Label(self.contrib_chart_frame, text=msg, bg="#ffffff",
                                 font=("Helvetica", 11), fg="#5f6368")
                label.pack(expand=True)
                return

            months = [r[0] for r in data]
            amounts = [float(r[1]) for r in data]

            # Create figure
            fig = Figure(figsize=(9, 5), dpi=100, facecolor='#ffffff')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#f8fafd')

            # Plot historical bars
            ax.bar(months, amounts, color='#34a853', alpha=0.8, label='Historical')

            # If enough data for forecast (≥3 months)
            if len(data) >= 3:
                x = np.arange(len(amounts)).reshape(-1, 1)
                y = np.array(amounts)

                if HAS_SKLEARN:
                    model = LinearRegression().fit(x, y)
                    future_x = np.arange(len(amounts), len(amounts) + 6).reshape(-1, 1)
                    future_y = model.predict(future_x)
                else:
                    m, b = np.polyfit(x.flatten(), y, 1)
                    future_x = np.arange(len(amounts), len(amounts) + 6)
                    future_y = m * future_x + b

                # Ensure no negative projections
                future_y = np.maximum(future_y, 0)

                # Generate future month labels (manual month increment)
                def add_months(date_str, months):
                    year, month = map(int, date_str.split('-'))
                    month += months
                    year += (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    return f"{year:04d}-{month:02d}"

                last_month = months[-1]
                future_months = [add_months(last_month, i) for i in range(1, 7)]

                # Plot forecast bars
                ax.bar(future_months, future_y, color='#fbbc04', alpha=0.7, label='Projected')
                ax.set_title("Financial Projection (6-Month Forecast)", fontsize=12, fontweight='bold')
            else:
                # Not enough data for forecast
                ax.set_title("Historical Contributions (Insufficient Data for Forecast)", fontsize=12, fontweight='bold')
                ax.text(0.5, 0.95, "Need at least 3 months of data for a forecast",
                        transform=ax.transAxes, ha='center', color='#d93025', fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

            # Improve layout
            ax.legend()
            ax.tick_params(axis='x', rotation=45, labelsize=9)
            ax.set_ylabel('Amount (GH₵)', fontsize=10)   # Changed to Ghana Cedis
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            fig.tight_layout()

            # Create canvas and pack
            canvas = FigureCanvasTkAgg(fig, master=self.contrib_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except Exception as e:
            # Show error directly in the frame
            for widget in self.contrib_chart_frame.winfo_children():
                widget.destroy()
            error_msg = f"An error occurred:\n{str(e)}"
            label = tk.Label(self.contrib_chart_frame, text=error_msg, bg="#ffffff",
                             font=("Helvetica", 10), fg="#d93025", justify="center")
            label.pack(expand=True)
            # Also print to console for debugging
            import traceback
            traceback.print_exc()