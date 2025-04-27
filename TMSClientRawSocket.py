import threading
import time
import socket
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Server settings
serverIP = '127.0.0.1'
serverPort = 12000
client_socket = None

# GUI setup
root = ttk.Window(themename="flatly")
root.title("TMS Client - Student View")
root.geometry("500x600")
root.minsize(500, 600)
root.configure(bg="#1E3A8A")
style = ttk.Style()
style.configure("Custom.TFrame", background="#1E3A8A")
style.configure("Custom.TLabelframe", background="#1E3A8A", foreground="#FFFFFF")
style.configure("Custom.TLabelframe.Label", background="#1E3A8A", foreground="#FFFFFF", font=("Helvetica", 12, "bold"))
style.configure("Custom.TLabel", background="#1E3A8A", foreground="#FFFFFF", font=("Helvetica", 10))
style.configure("Custom.TButton", background="#2196F3", foreground="#FFFFFF", font=("Helvetica", 10))
style.configure("Status.TLabel", font=("Helvetica", 10))

main_frame = ttk.Frame(root, style="Custom.TFrame")
main_frame.pack(fill="both", expand=True, padx=10, pady=10)

canvas = tk.Canvas(main_frame, bg="#1E3A8A", highlightthickness=0)
scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas, style="Custom.TFrame")
scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def on_resize(event):
    canvas_width = event.width
    canvas.itemconfig(canvas.create_window((0, 0), window=scrollable_frame, anchor="nw"), width=canvas_width)

canvas.bind("<Configure>", on_resize)

def on_mouse_wheel(event):
    if event.delta:
        canvas.yview_scroll(-1 * (event.delta // 120), "units")
    elif event.num == 4:
        canvas.yview_scroll(-1, "units")
    elif event.num == 5:
        canvas.yview_scroll(1, "units")
canvas.bind_all("<MouseWheel>", on_mouse_wheel)
canvas.bind_all("<Button-4>", on_mouse_wheel)
canvas.bind_all("<Button-5>", on_mouse_wheel)

heading_label = ttk.Label(scrollable_frame, text="TMS Client - Student View", style="Custom.TLabel", font=("Helvetica", 16, "bold"))
heading_label.pack(pady=(0, 10), fill="x")

conn_frame = ttk.LabelFrame(scrollable_frame, text="Connect to Server", style="Custom.TLabelframe")
conn_frame.pack(fill="x", pady=(0, 5))

ttk.Label(conn_frame, text="Student ID (3-10 alphanumeric):", style="Custom.TLabel").pack(pady=2, padx=5, anchor="w")
id_entry = ttk.Entry(conn_frame, font=("Helvetica", 10))
id_entry.pack(pady=2, padx=5, fill="x")

ttk.Label(conn_frame, text="Name (not used):", style="Custom.TLabel").pack(pady=2, padx=5, anchor="w")
name_entry = ttk.Entry(conn_frame, font=("Helvetica", 10))
name_entry.pack(pady=2, padx=5, fill="x")

connect_button = ttk.Button(conn_frame, text="Connect", command=lambda: connect_to_server(), style="Custom.TButton")
connect_button.pack(pady=5)

connected_as_label = ttk.Label(scrollable_frame, text="", style="Custom.TLabel")
connected_as_label.pack(pady=(0, 5), fill="x")

status_frame = ttk.LabelFrame(scrollable_frame, text="Session Status", style="Custom.TLabelframe")
status_frame.pack(fill="x", pady=(0, 5))

conn_status_label = ttk.Label(status_frame, text="Connection: Disconnected", style="Status.TLabel", foreground="red")
conn_status_label.pack(anchor="w", padx=5)

time_status_label = ttk.Label(status_frame, text="Time Remaining: N/A", style="Custom.TLabel")
time_status_label.pack(anchor="w", padx=5)

participants_label = ttk.Label(status_frame, text="Participants: N/A", style="Custom.TLabel")
participants_label.pack(anchor="w", padx=5)

msg_frame = ttk.LabelFrame(scrollable_frame, text="Messages", style="Custom.TLabelframe")
msg_frame.pack(fill="both", expand=True, pady=(0, 5))

msg_text = scrolledtext.ScrolledText(msg_frame, height=12, bg="#FFFFFF", fg="#000000", font=("Helvetica", 10))
msg_text.pack(fill="both", expand=True, pady=5, padx=5)
msg_text.config(state='disabled')

sys_frame = ttk.LabelFrame(scrollable_frame, text="System Messages", style="Custom.TLabelframe")
sys_frame.pack(fill="both", expand=True, pady=(0, 5))

sys_text = scrolledtext.ScrolledText(sys_frame, height=3, bg="#FFFFFF", fg="#000000", font=("Helvetica", 10))
sys_text.pack(fill="both", expand=True, pady=5, padx=5)
sys_text.config(state='disabled')

input_frame = ttk.LabelFrame(scrollable_frame, text="Send Message", style="Custom.TLabelframe")
input_frame.pack(fill="x", pady=(0, 5))

ttk.Label(input_frame, text="Message (max 200 chars, press Enter to send):", style="Custom.TLabel").pack(pady=2, padx=5, anchor="w")
message_entry = ttk.Entry(input_frame, font=("Helvetica", 10))
message_entry.pack(pady=2, padx=5, fill="x")
message_entry.insert(0, "Type your message here...")
message_entry.bind("<FocusIn>", lambda event: message_entry.delete(0, tk.END) if message_entry.get() == "Type your message here..." else None)
message_entry.bind("<FocusOut>", lambda event: message_entry.insert(0, "Type your message here...") if not message_entry.get() else None)
message_entry.bind("<Return>", lambda event: send_message())

button_frame = ttk.Frame(input_frame, style="Custom.TFrame")
button_frame.pack(fill="x", pady=5, padx=5)
send_button = ttk.Button(button_frame, text="Send", command=lambda: send_message(), state='disabled', style="Custom.TButton")
send_button.pack(side="left", padx=2)
exit_button = ttk.Button(button_frame, text="Exit", command=lambda: exit_session(), state='disabled', style="Custom.TButton")
exit_button.pack(side="left", padx=2)

# Connection state
connected = False
student_id = ""

def log_system(text):
    sys_text.config(state='normal')
    sys_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
    sys_text.see(tk.END)
    sys_text.config(state='disabled')
    with open("tms_client.log", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] System: {text}\n")

def create_message_widget(text, is_self=False):
    msg_container = ttk.Frame(msg_text, style="Custom.TFrame")
    msg_container.grid_columnconfigure(0, weight=1)
    timestamp = datetime.now().strftime('%H:%M:%S')
    timestamp_label = ttk.Label(msg_container, text=timestamp, font=("Helvetica", 8), foreground="gray", background="#FFFFFF")
    timestamp_label.pack(anchor="e" if is_self else "w")
    msg_bubble = tk.Frame(msg_container, borderwidth=1, relief="raised")
    msg_bubble.pack(anchor="e" if is_self else "w", padx=5, pady=2, fill="x")
    if is_self:
        msg_bubble.configure(bg="#2196F3")
        text_color = "white"
    else:
        msg_bubble.configure(bg="#E0E0E0")
        text_color = "black"
    msg_label = tk.Label(
        msg_bubble,
        text=text,
        font=("Helvetica", 10),
        fg=text_color,
        bg="#2196F3" if is_self else "#E0E0E0",
        wraplength=300,
        justify="right" if is_self else "left",
        padx=10,
        pady=5
    )
    msg_label.pack(anchor="e" if is_self else "w")
    return msg_container

def log_message(text, is_self=False):
    msg_widget = create_message_widget(text, is_self)
    msg_text.config(state='normal')
    msg_text.insert(tk.END, "\n")
    msg_text.window_create(tk.END, window=msg_widget)
    msg_text.insert(tk.END, "\n")
    msg_text.see(tk.END)
    msg_text.config(state='disabled')
    with open("tms_client.log", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Message ({'self' if is_self else 'other'}): {text}\n")

def update_ui_status(connected, time_remaining=None, participants=None):
    if connected:
        conn_status_label.config(text="Connection: Connected", foreground="green")
        connected_as_label.config(text=f"Connected as: {student_id}")
        connect_button.config(state='disabled')
        send_button.config(state='normal')
        exit_button.config(state='normal')
    else:
        conn_status_label.config(text="Connection: Disconnected", foreground="red")
        connected_as_label.config(text="")
        connect_button.config(state='normal')
        send_button.config(state='disabled')
        exit_button.config(state='disabled')
    if time_remaining is not None:
        time_status_label.config(text=f"Time Remaining: {time_remaining} minutes")
    if participants is not None:
        participants_label.config(text=f"Participants: {participants}")

def receive_messages():
    global connected
    while connected:
        try:
            data = client_socket.recv(1024).decode(errors='ignore').strip()
            if not data:
                log_system("Connection closed by server")
                connected = False
                update_ui_status(connected=False)
                break
            log_system(f"Received: {data}")
            parts = data.split(" ", 2)
            if parts[0] == "Welcome," and len(parts) > 1:
                update_ui_status(connected=True)
            elif parts[0] == "TIME" and len(parts) > 1:
                time_remaining = int(parts[1])
                update_ui_status(connected=True, time_remaining=time_remaining)
            elif parts[0] == "PARTICIPANTS" and len(parts) > 1:
                participants = int(parts[1])
                update_ui_status(connected=True, participants=participants)
            elif parts[0] == "BROADCAST" and len(parts) > 2:
                sender_id, text = parts[1], parts[2]
                log_message(f"{sender_id}: {text}", is_self=(sender_id == student_id))
            elif parts[0] == "ERROR" and len(parts) > 1:
                log_system(f"Error: {parts[1]}")
                messagebox.showerror("Error", parts[1])
                connected = False
                update_ui_status(connected=False)
                break
            elif data.startswith("Your session has expired"):
                log_system("Session expired, disconnecting")
                connected = False
                update_ui_status(connected=False)
                break
        except Exception as e:
            log_system(f"Error receiving message: {e}")
            connected = False
            update_ui_status(connected=False)
            break

def connect_to_server():
    global connected, student_id, client_socket
    student_id = id_entry.get().strip()
    if not student_id or len(student_id) < 3 or len(student_id) > 10 or not student_id.isalnum():
        messagebox.showerror("Error", "Invalid ID (3-10 alphanumeric)")
        return
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((serverIP, serverPort))
        connected = True
        log_system("Connected to server")
        client_socket.sendall(f"CHECKIN {student_id}".encode())
        threading.Thread(target=receive_messages, daemon=True).start()
    except Exception as e:
        log_system(f"Failed to connect: {e}")
        messagebox.showerror("Error", f"Failed to connect to server: {e}")
        connected = False
        update_ui_status(connected=False)

def send_message():
    if not connected:
        messagebox.showerror("Error", "Not connected to server")
        return
    message = message_entry.get().strip()
    if not message or message == "Type your message here...":
        messagebox.showerror("Error", "Message empty")
        return
    if len(message) > 200:
        messagebox.showerror("Error", "Message too long (max 200 chars)")
        return
    try:
        client_socket.sendall(f"MSG {message}".encode())
        log_message(f"{student_id}: {message}", is_self=True)
        log_system(f"Sent message: {message}")
        message_entry.delete(0, tk.END)
        message_entry.insert(0, "Type your message here...")
    except Exception as e:
        log_system(f"Error sending message: {e}")
        connected = False
        update_ui_status(connected=False)

def exit_session():
    global connected
    if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit?"):
        if connected:
            try:
                client_socket.sendall("MSG exit".encode())
                client_socket.close()
            except:
                pass
        connected = False
        update_ui_status(connected=False)
        log_system("Session exited")

root.mainloop()