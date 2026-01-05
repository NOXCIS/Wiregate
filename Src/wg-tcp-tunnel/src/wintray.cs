// wg-tcp-tunnel - wintray.cs
// SPDX-FileCopyrightText: 2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.IsolatedStorage;
using System.Reflection;
using System.Windows.Forms;

namespace TrayApp {

public class LogsForm : Form {
	private readonly TextBox logsTextBox;
	private string logsBuffer = "";

	public LogsForm() {
		Text = "WireGuard TCP Tunnel Logs";
		Size = new Size(800, 400);
		StartPosition = FormStartPosition.CenterScreen;
		FormClosing += OnFormClosing;

		logsTextBox = new TextBox { Dock = DockStyle.Fill, Multiline = true, ReadOnly = true,
			                        Font = new Font(FontFamily.GenericMonospace, 10),
			                        ScrollBars = ScrollBars.Both };

		Controls.Add(logsTextBox);
	}

	protected void OnFormClosing(object sender, FormClosingEventArgs e) {
		if (e.CloseReason == CloseReason.UserClosing) {
			e.Cancel = true;
			Hide();
		}
	}

	public void AppendLog(string text) {
		if (string.IsNullOrEmpty(text))
			return;
		if (logsTextBox.InvokeRequired) {
			logsTextBox.Invoke(new Action(() => AppendLog(text)));
		} else {
			if (Visible) {
				logsTextBox.AppendText(text + Environment.NewLine);
				logsTextBox.ScrollToCaret();
			}
			logsBuffer += text + Environment.NewLine;
		}
	}

	protected override void OnVisibleChanged(EventArgs e) {
		base.OnVisibleChanged(e);
		if (Visible) {
			logsTextBox.Text = logsBuffer;
			logsTextBox.SelectionStart = logsTextBox.Text.Length;
			logsTextBox.ScrollToCaret();
		}
	}
}

public partial class MainForm : Form {
	private enum Mode { TCP, UDP }

	private readonly NotifyIcon trayIcon = new NotifyIcon();
	private readonly ContextMenuStrip trayMenu = new ContextMenuStrip();
	private bool isActive = false;

	private ComboBox modeComboBox;
	private TextBox sourceTextBox;
	private TextBox destinationTextBox;
	private Button buttonOK;
	private Button buttonCancel;

	private Mode mode = Mode.TCP;
	private string source = "0.0.0.0:51820";
	private string destination = "127.0.0.1:51820";
	private Process tcpTunnelProcess;
	private LogsForm logsForm;

	public MainForm() {
		LoadSettings();
		// Initialize form components
		InitializeComponent();
		// Load tray icon from embedded resource
		using (var iconStream =
		           Assembly.GetExecutingAssembly().GetManifestResourceStream("src.wintray.ico")) {
			trayIcon.Icon = new Icon(iconStream);
		}
		// Setup tray icon menu
		trayMenu.Items.Add("", null, OnActivateDeactivate);
		trayMenu.Items.Add(new ToolStripSeparator());
		trayMenu.Items.Add("Settings...", null, OnSettings);
		trayMenu.Items.Add("Logs...", null, OnLogs);
		trayMenu.Items.Add(new ToolStripSeparator());
		trayMenu.Items.Add("About...", null, OnAbout);
		trayMenu.Items.Add("Exit", null, OnExit);
		trayIcon.ContextMenuStrip = trayMenu;
		trayIcon.MouseClick += OnTrayIconMouseClick;
		trayIcon.Visible = true;
		// Update tray icon state
		UpdateTrayIcon();
		// Initialize logs receiver
		logsForm = new LogsForm();
	}

	protected override void OnLoad(EventArgs e) {
		HideWindow(); // Hide the form on startup
		base.OnLoad(e);
	}

	protected override void OnFormClosing(FormClosingEventArgs e) {
		HideWindow(); // Hide the form instead of closing the application
		e.Cancel = true;
		base.OnFormClosing(e);
	}

	protected override void Dispose(bool disposing) {
		if (disposing) {
			trayIcon.Dispose();
		}
		base.Dispose(disposing);
	}

	private void InitializeComponent() {
		modeComboBox = new ComboBox();
		sourceTextBox = new TextBox();
		destinationTextBox = new TextBox();
		buttonOK = new Button();
		buttonCancel = new Button();

		modeComboBox.Items.AddRange(new string[] { "TCP", "UDP" });
		modeComboBox.DropDownStyle = ComboBoxStyle.DropDownList;

		var panel = new FlowLayoutPanel { FlowDirection = FlowDirection.LeftToRight,
			                              Dock = DockStyle.Fill };

		panel.Controls.Add(new Label { Text = "Mode", Dock = DockStyle.Bottom });
		panel.Controls.Add(modeComboBox);
		panel.SetFlowBreak(modeComboBox, true);

		panel.Controls.Add(new Label { Text = "Source IP:PORT", Dock = DockStyle.Bottom });
		panel.Controls.Add(sourceTextBox);
		panel.SetFlowBreak(sourceTextBox, true);

		panel.Controls.Add(new Label { Text = "Destination IP:PORT", Dock = DockStyle.Bottom });
		panel.Controls.Add(destinationTextBox);
		panel.SetFlowBreak(destinationTextBox, true);

		buttonOK.Text = "OK";
		buttonOK.DialogResult = DialogResult.OK;
		buttonOK.Click += OnButtonOK;

		buttonCancel.Text = "Cancel";
		buttonCancel.DialogResult = DialogResult.Cancel;
		buttonCancel.Click += OnButtonCancel;

		var buttonPanel = new FlowLayoutPanel { FlowDirection = FlowDirection.RightToLeft,
			                                    Dock = DockStyle.Bottom };
		buttonPanel.Controls.Add(buttonCancel);
		buttonPanel.Controls.Add(buttonOK);

		panel.Controls.Add(buttonPanel);

		Controls.Add(panel);

		Text = "WireGuard TCP Tunnel";
		FormBorderStyle = FormBorderStyle.FixedDialog;
		StartPosition = FormStartPosition.CenterParent;
		AcceptButton = buttonOK;
		CancelButton = buttonCancel;
		// AutoSize = true;
		// AutoSizeMode = AutoSizeMode.GrowAndShrink;
	}

	private void ShowWindow() {
		// Sync form with current settings
		modeComboBox.SelectedItem = mode.ToString();
		sourceTextBox.Text = source;
		destinationTextBox.Text = destination;
		// Show the form and bring it to the front
		Visible = true;
		ShowInTaskbar = true;
		Activate();
	}

	private void HideWindow() {
		Visible = false;
		ShowInTaskbar = false;
	}

	private void OnTrayIconMouseClick(object sender, MouseEventArgs e) {
		if (e.Button == MouseButtons.Left) {
			ShowWindow();
		}
	}

	private void OnButtonOK(object sender, EventArgs e) {
		mode = (Mode)Enum.Parse(typeof(Mode), modeComboBox.SelectedItem.ToString());
		source = sourceTextBox.Text;
		destination = destinationTextBox.Text;
		SaveSettings();
		HideWindow();
	}

	private void OnButtonCancel(object sender, EventArgs e) { HideWindow(); }

	private void OnActivateDeactivate(object sender, EventArgs e) {
		isActive = !isActive;
		UpdateTrayIcon();

		if (isActive) {
			var processStartInfo = new ProcessStartInfo {
				FileName = "wg-tcp-tunnel",
				Arguments = mode == Mode.TCP ? $"-v --src-tcp={source} --dst-udp={destination}"
				                             : $"-v --src-udp={source} --dst-tcp={destination}",
				RedirectStandardOutput = true,
				RedirectStandardError = true,
				UseShellExecute = false,
				CreateNoWindow = true,
			};
			try {
				tcpTunnelProcess = Process.Start(processStartInfo);
				tcpTunnelProcess.OutputDataReceived += (s, args) => {
					if (args.Data != null)
						logsForm.AppendLog(args.Data);
				};
				tcpTunnelProcess.ErrorDataReceived += (s, args) => {
					if (args.Data != null)
						logsForm.AppendLog(args.Data);
				};
				tcpTunnelProcess.BeginOutputReadLine();
				tcpTunnelProcess.BeginErrorReadLine();
			} catch (Exception ex) {
				MessageBox.Show($"Failed to start wg-tcp-tunnel: {ex.Message}", "Error",
				                MessageBoxButtons.OK, MessageBoxIcon.Error);
				isActive = false;
				UpdateTrayIcon();
			}
		} else {
			TerminateProcess();
		}
	}

	private void OnSettings(object sender, EventArgs e) { ShowWindow(); }

	private void OnLogs(object sender, EventArgs e) {
		logsForm.Show();
		logsForm.BringToFront();
	}

	private void OnAbout(object sender, EventArgs e) {
		MessageBox.Show("WireGuard TCP Tunnel\n\nVersion 1.1.0", "About");
	}

	private void OnExit(object sender, EventArgs e) {
		// Make sure to terminate the tunnel process before exiting.
		TerminateProcess();
		Application.ExitThread();
	}

	private void UpdateTrayIcon() {
		trayIcon.Text = "WireGuard TCP Tunnel: " + (isActive ? "Active" : "Inactive");
		trayIcon.ContextMenuStrip.Items[0].Text = isActive ? "Deactivate" : "Activate";
	}

	private void TerminateProcess() {
		if (tcpTunnelProcess != null && !tcpTunnelProcess.HasExited) {
			tcpTunnelProcess.Kill();
			tcpTunnelProcess = null;
		}
	}

	private void SaveSettings() {
		using (var storage = IsolatedStorageFile.GetUserStoreForAssembly()) {
			try {
				using (var stream = new IsolatedStorageFileStream("settings.ini", FileMode.Create,
				                                                  storage)) {
					using (var writer = new StreamWriter(stream)) {
						writer.WriteLine("[Settings]");
						writer.WriteLine("Mode=" + mode.ToString());
						writer.WriteLine("Source=" + source);
						writer.WriteLine("Destination=" + destination);
					}
				}
			} catch (Exception) {
			}
		}
	}

	private void LoadSettings() {
		using (var storage = IsolatedStorageFile.GetUserStoreForAssembly()) {
			try {
				using (var stream =
				           new IsolatedStorageFileStream("settings.ini", FileMode.Open, storage)) {
					using (var reader = new StreamReader(stream)) {
						string line;
						while ((line = reader.ReadLine()) != null) {
							if (line.StartsWith("Mode="))
								mode = (Mode)Enum.Parse(typeof(Mode),
								                        line.Substring("Mode=".Length));
							else if (line.StartsWith("Source="))
								source = line.Substring("Source=".Length);
							else if (line.StartsWith("Destination="))
								destination = line.Substring("Destination=".Length);
						}
					}
				}
			} catch (FileNotFoundException) {
			}
		}
	}
}

static class Program {
	[STAThread]
	static void Main() {
		Application.EnableVisualStyles();
		Application.SetCompatibleTextRenderingDefault(false);
		Application.Run(new MainForm());
	}
}

}
