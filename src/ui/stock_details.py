from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPicture, QPainter, QColor
import pyqtgraph as pg

class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # data must be a list of tuples (t, open, close, min, max)
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)

        w = (self.data[1][0] - self.data[0][0]) / 3. if len(self.data) > 1 else 86400 * 0.3

        for (t, open, close, min, max) in self.data:
            is_bullish = close >= open
            color = QColor('#2ecc71') if is_bullish else QColor('#e74c3c')

            p.setPen(pg.mkPen(color))
            p.setBrush(pg.mkBrush(color))

            # Draw wick
            p.drawLine(pg.Point(t, min), pg.Point(t, max))

            # Draw body
            if open == close:
                p.drawLine(pg.Point(t - w, open), pg.Point(t + w, close))
            else:
                p.drawRect(QRectF(t - w, open, w * 2, close - open))

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class StockDetailsWidget(QWidget):
    """
    A comprehensive dashboard for an individual stock.
    Features an Overview (Trade Setup, Scanner Reasons), Interactive Chart,
    Technical Indicators, and Historical Data.
    """
    def __init__(self, symbol, data_dict, close_callback):
        super().__init__()
        self.symbol = symbol
        self.data = data_dict
        self.close_callback = close_callback

        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # 1. Header Section
        self.build_header()

        # 2. Main Tabs
        self.tabs = QTabWidget()

        self.tab_overview = QWidget()
        self.build_overview_tab(self.tab_overview)
        self.tabs.addTab(self.tab_overview, "Overview")

        self.tab_chart = QWidget()
        self.build_chart_tab(self.tab_chart)
        self.tabs.addTab(self.tab_chart, "Interactive Chart")

        self.tab_technicals = QWidget()
        self.build_technicals_tab(self.tab_technicals)
        self.tabs.addTab(self.tab_technicals, "Technicals")

        self.tab_history = QWidget()
        self.build_history_tab(self.tab_history)
        self.tabs.addTab(self.tab_history, "Historical Data")

        self.layout.addWidget(self.tabs)

    def build_header(self):
        header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        name_label = QLabel(f"{self.symbol} - {self.data['company_name']}")
        name_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #3498db;")

        latest = self.data['df'].iloc[-1]
        price_label = QLabel(f"LTP: ₹{latest['close']:.2f}")
        price_label.setStyleSheet("font-size: 18px; color: #ecf0f1;")

        title_box.addWidget(name_label)
        title_box.addWidget(price_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Score & Close Button
        score_label = QLabel(f"Scanner Score: {self.data['score']}/100")
        score_color = "#27ae60" if self.data['score'] >= 75 else ("#f39c12" if self.data['score'] >= 50 else "#c0392b")
        score_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {score_color}; padding: 10px;")
        header_layout.addWidget(score_label)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #c0392b; max-width: 80px;")
        close_btn.clicked.connect(self.close_callback)
        header_layout.addWidget(close_btn)

        self.layout.addLayout(header_layout)

    def build_overview_tab(self, parent):
        layout = QHBoxLayout(parent)

        # Left Side: Scanner Reasons
        reasons_group = QGroupBox("Why did this stock qualify?")
        reasons_layout = QVBoxLayout()
        if not self.data['reasons']:
            reasons_layout.addWidget(QLabel("No specific scanner criteria met."))
        else:
            for reason in self.data['reasons']:
                lbl = QLabel(reason)
                lbl.setStyleSheet("font-size: 14px; color: #2ecc71; padding: 5px;")
                reasons_layout.addWidget(lbl)
        reasons_layout.addStretch()
        reasons_group.setLayout(reasons_layout)
        layout.addWidget(reasons_group, stretch=1)

        # Right Side: Trade Setup
        setup_group = QGroupBox("Swing Trade Setup (ATR Based)")
        setup_layout = QGridLayout()
        setup_layout.setSpacing(15)

        setup = self.data['setup']

        fields = [
            ("Entry Price:", f"₹{setup['entry']}"),
            ("Stop Loss:", f"₹{setup['stop_loss']} (-{setup['risk']}₹)"),
            ("Target 1 (1:2):", f"₹{setup['target_1']}"),
            ("Target 2 (1:3):", f"₹{setup['target_2']}")
        ]

        for row, (label, val) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold; color: #bdc3c7; font-size: 14px;")
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("font-weight: bold; color: #ecf0f1; font-size: 16px;")
            setup_layout.addWidget(lbl, row, 0)
            setup_layout.addWidget(v_lbl, row, 1)

        setup_group.setLayout(setup_layout)
        layout.addWidget(setup_group, stretch=1)

    def build_chart_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Configure pyqtgraph styling
        pg.setConfigOption('background', '#121212')
        pg.setConfigOption('foreground', '#ecf0f1')

        # Main plot layout
        win = pg.GraphicsLayoutWidget()
        layout.addWidget(win)

        # Price Plot
        p1 = win.addPlot(row=0, col=0)
        p1.showGrid(x=True, y=True, alpha=0.3)
        p1.setLabel('left', 'Price (₹)')

        # Volume Plot (beneath price)
        p2 = win.addPlot(row=1, col=0)
        p2.setMaximumHeight(150)
        p2.showGrid(x=True, y=True, alpha=0.3)
        p2.setLabel('left', 'Volume')
        p2.setXLink(p1) # Link X-axis panning/zooming

        # Adjust layout ratios
        win.ci.layout.setRowStretchFactor(0, 3)
        win.ci.layout.setRowStretchFactor(1, 1)

        # Plot Data
        df = self.data['full_df'] # Use full 250 days for charting

        # Prepare x-axis timestamps (pyqtgraph uses float timestamps)
        x_timestamps = [dt.timestamp() for dt in df.index]

        # 1. Candlesticks (True scalable graphics object)
        candle_data = []
        for i, (date, row) in enumerate(df.iterrows()):
            t = x_timestamps[i]
            candle_data.append((t, row['open'], row['close'], row['low'], row['high']))

            # Draw volume bars using simple plot lines (since width matters less for vol)
            is_bullish = row['close'] >= row['open']
            v_color = pg.mkColor('#2ecc71') if is_bullish else pg.mkColor('#e74c3c')
            p2.plot([t, t], [0, row['volume']], pen=pg.mkPen(v_color, width=4))

        item = CandlestickItem(candle_data)
        p1.addItem(item)

        # 2. EMAs
        if 'EMA_20' in df.columns:
            p1.plot(x_timestamps, df['EMA_20'].values, pen=pg.mkPen('#3498db', width=2), name="EMA 20")
        if 'EMA_50' in df.columns:
            p1.plot(x_timestamps, df['EMA_50'].values, pen=pg.mkPen('#f1c40f', width=2), name="EMA 50")
        if 'EMA_200' in df.columns:
            p1.plot(x_timestamps, df['EMA_200'].values, pen=pg.mkPen('#e67e22', width=2.5), name="EMA 200")

        # 3. Setup Lines (Entry, Target, Stop Loss)
        setup = self.data['setup']
        p1.addLine(y=setup['entry'], pen=pg.mkPen('#ecf0f1', width=1, style=Qt.PenStyle.DashLine))
        p1.addLine(y=setup['stop_loss'], pen=pg.mkPen('#c0392b', width=1, style=Qt.PenStyle.DashLine))
        p1.addLine(y=setup['target_1'], pen=pg.mkPen('#2ecc71', width=1, style=Qt.PenStyle.DashLine))

        # Format X-axis to show dates instead of float timestamps
        class DateAxis(pg.AxisItem):
            def tickStrings(self, values, scale, spacing):
                import datetime
                return [datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d') for value in values]

        p1.setAxisItems({'bottom': DateAxis(orientation='bottom')})
        p2.setAxisItems({'bottom': DateAxis(orientation='bottom')})

    def build_technicals_tab(self, parent):
        layout = QGridLayout(parent)
        latest = self.data['df'].iloc[-1]

        metrics = [
            ("RSI (14)", latest.get('RSI_14', 0)),
            ("Relative Volume", f"{latest.get('RVOL', 0)}x"),
            ("Delivery %", f"{latest.get('delivery_percent', 0)}%"),
            ("EMA 20", latest.get('EMA_20', 0)),
            ("EMA 50", latest.get('EMA_50', 0)),
            ("EMA 200", latest.get('EMA_200', 0)),
        ]

        row, col = 0, 0
        for name, value in metrics:
            box = QGroupBox(name)
            box_layout = QVBoxLayout()
            val_label = QLabel(str(value))
            val_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1c40f;")
            val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(val_label)
            box.setLayout(box_layout)

            layout.addWidget(box, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def build_history_tab(self, parent):
        layout = QVBoxLayout(parent)

        hist_table = QTableWidget()
        hist_table.setColumnCount(8)
        hist_table.setHorizontalHeaderLabels([
            "Date", "Close", "Volume", "Deliv %", "EMA 20", "EMA 50", "RSI", "RVOL"
        ])
        hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hist_table.setAlternatingRowColors(True)
        hist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hist_table.setShowGrid(False)

        df = self.data['df']
        hist_table.setRowCount(0) # Clear existing just in case

        for i, (date, row_data) in enumerate(df.iterrows()):
            date_str = date.strftime("%Y-%m-%d")
            hist_table.insertRow(i)
            hist_table.setItem(i, 0, QTableWidgetItem(date_str))
            hist_table.setItem(i, 1, QTableWidgetItem(str(row_data['close'])))
            hist_table.setItem(i, 2, QTableWidgetItem(str(int(row_data['volume']))))
            hist_table.setItem(i, 3, QTableWidgetItem(f"{row_data.get('delivery_percent', 0)}%"))
            hist_table.setItem(i, 4, QTableWidgetItem(str(row_data.get('EMA_20', 0))))
            hist_table.setItem(i, 5, QTableWidgetItem(str(row_data.get('EMA_50', 0))))
            hist_table.setItem(i, 6, QTableWidgetItem(str(row_data.get('RSI_14', 0))))
            hist_table.setItem(i, 7, QTableWidgetItem(str(row_data.get('RVOL', 0))))

        layout.addWidget(hist_table)
