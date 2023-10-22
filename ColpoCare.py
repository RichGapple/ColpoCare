import os
import cv2
import tkinter as tk
from datetime import datetime
from tkinter import Toplevel
from PIL import Image, ImageTk
import threading
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image as ReportLabImage, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Spacer
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
import base64
import tkinter.messagebox as messagebox

os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
def create_patient_folder():
    patient_name = entry_patient_name.get()
    patient_id = entry_patient_id.get()
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    patient_folder = os.path.join(".", "Patient_{}_{}".format(patient_name, patient_id))

    # Check if the patient folder with the same name already exists
    if not os.path.exists(patient_folder):
        os.makedirs(patient_folder)
        # Save patient details in a text file
        patient_details_file = os.path.join(patient_folder, "patient_details.txt")
        with open(patient_details_file, 'w') as f:
            f.write("Patient Name: {}\n".format(patient_name))
            f.write("Patient Age: {}\n".format(entry_patient_age.get()))
            f.write("Patient ID: {}\n".format(entry_patient_id.get()))
            f.write("Hospital Number: {}\n".format(entry_hospital_number.get()))
            f.write("Doctor Performing Colposcopy: {}\n".format(entry_doctor_name.get()))

    return patient_folder


captured_indications = set()

def capture_image(indication):
    global current_frame
    global captured_indications
    captured_indications.add(indication)
    if current_frame is not None:
        patient_folder = create_patient_folder()
        subfolder = os.path.join(patient_folder, indication)
        os.makedirs(subfolder, exist_ok=True)

        # Create a new folder for each set of images inside the subfolder
        set_folder = os.path.join(subfolder, f"Set_{datetime.now().strftime('%H-%M-%S')}")
        os.makedirs(set_folder)

        # Save the captured image
        image_name = os.path.join(set_folder, f"{indication}_{datetime.now().strftime('%H-%M-%S')}.png")
        cv2.imwrite(image_name, current_frame)
        print(f"Image captured and saved: {image_name}")

def convert_bgr_to_rgb(img):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)
    return ImageTk.PhotoImage(image=img_pil)

def view_images():
    view_screen = Toplevel(root)
    view_screen.title("View Patient Images")

    patient_folders = [folder for folder in os.listdir(".") if folder.startswith("Patient_")]

    listbox = tk.Listbox(view_screen)
    listbox.pack()

    for folder in patient_folders:
        listbox.insert(tk.END, folder)

    def browse_directory(directory):
        image_paths = []

        def add_image_paths(folder_path):
            for entry in os.scandir(folder_path):
                if entry.is_dir():
                    add_image_paths(entry.path)
                elif entry.name.endswith(".png"):
                    image_paths.append(entry.path)

        add_image_paths(directory)

        def show_image(index):
            nonlocal current_image_window

            if current_image_window is not None:
                current_image_window.destroy()

            img_path = image_paths[index]
            img = cv2.imread(img_path)
            img = convert_bgr_to_rgb(img)

            image_viewer_screen = Toplevel(view_screen)
            image_viewer_screen.title(f"Image Path: {img_path}")

            image_label = tk.Label(image_viewer_screen)
            image_label.config(image=img)
            image_label.image = img  # Keep a reference to the image to avoid garbage collection
            image_label.pack()

            current_image_window = image_viewer_screen

            if index > 0:
                btn_prev = tk.Button(image_viewer_screen, text="Previous", command=lambda: show_image(index-1))
                btn_prev.pack(side=tk.LEFT)

            if index < len(image_paths) - 1:
                btn_next = tk.Button(image_viewer_screen, text="Next", command=lambda: show_image(index+1))
                btn_next.pack(side=tk.RIGHT)
        
        
        if image_paths:
            show_image(0)

    def show_images():
        selected_indices = listbox.curselection()
        if not selected_indices:
            return

        selected_index = selected_indices[0]
        selected_folder = listbox.get(selected_index)
        patient_folder = os.path.join(".", selected_folder)

        browse_directory(patient_folder)

    current_image_window = None

    view_button = tk.Button(view_screen, text="View Images", command=show_images)
    view_button.pack()

    btn_back = tk.Button(view_screen, text="Back", command=view_screen.destroy)
    btn_back.pack()


def show_camera_feed():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return

    cv2.namedWindow("Camera Feed")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image.")
            break

        cv2.imshow("Camera Feed", frame)

        # Store the current frame in the global variable
        global current_frame
        current_frame = frame

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit the camera feed
            break

    cap.release()
    cv2.destroyAllWindows()

def run_camera_thread():
    show_camera_feed()

def start_camera():
    # Create a separate thread for the camera feed
    camera_thread = threading.Thread(target=run_camera_thread)
    camera_thread.start()

    # Start the main GUI loop
    #root.mainloop()

def start_video_recording():
    global recording
    recording = True

    # Create a VideoCapture object to capture video from the default camera (usually the webcam).
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Try CAP_DSHOW or other backends

    # Define the codec and create a VideoWriter object to save the video.
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # You can change the codec as needed.
    
    patient_folder = create_patient_folder()
    video_file = os.path.join(patient_folder, "patient_video.avi")
    
    out = cv2.VideoWriter(video_file, fourcc, 20.0, (640, 480))  # Output file name, codec, fps, and frame size.

    start_time = datetime.now()

    while recording:
        ret, frame = cap.read()
        if not ret:
            break

        out.write(frame)

        cv2.imshow('Recording', frame)

        # Record for 16 seconds
        if (datetime.now() - start_time).total_seconds() >= 6:
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the VideoCapture and VideoWriter objects
    cap.release()
    out.release()

    cv2.destroyAllWindows()

    messagebox.showinfo("Recording Completed", "Video recording completed and saved.")
    start_camera()
    
# Function to stop video recording
def stop_video_recording():
    global recording
    recording = False

current_frame = None

    
    
root = tk.Tk()
root.title("Colposcopy Application")
root.geometry("600x750")  # Increase the window size


def add_title(root):
    # Create a title frame to hold the title label
    title_frame = tk.Frame(root)
    title_frame.pack(pady=10)

    # Add the title label with bold font
    title_label = tk.Label(title_frame, text="Colposcopy Patient Record Management System", font=("Helvetica", 16, "bold"))
    title_label.pack()

def add_signature(root):
    # Create a signature frame to hold the signature label
    signature_frame = tk.Frame(root)
    signature_frame.pack(side=tk.BOTTOM, padx=20, pady=10, anchor=tk.SE)

    # Add the signature label
    signature_label = tk.Label(signature_frame, text="By ~ R Vishal Prasad", font=("Helvetica", 10))
    signature_label.pack()


def show_screen1():
    if not entry_patient_name.get() or not entry_patient_age.get() or not entry_patient_id.get() or \
            not entry_hospital_number.get() or not entry_doctor_name.get():
        error_label.config(text="Error: Fill out all patient details.", fg="red", font=("Helvetica", 16, "bold"))
        return

    error_label.config(text="", fg="black", font=("Helvetica", 22))
    screen1.pack_forget()
    screen2.pack()
    
    camera_thread = threading.Thread(target=run_camera_thread)
    camera_thread.start()

     # Add the form
    add_form()
    
    # Add title and signature only on Screen 1
    #add_title(root)
    #add_signature(root)
    
    # Add the "Generate Report" button
    #btn_generate_report = tk.Button(screen2, text="Generate Report", font=("Helvetica", 14, "bold"), command=generate_report)
    #btn_generate_report.pack(pady=10)


entry_margin_surface = None
entry_vessel = None
entry_lesion_size = None
entry_acetic_acid = None
entry_lugol_iodine = None
entry_total_score = None
entry_biopsy_taken = None
entry_histopathology_report = None

def generate_report():
    global entry_margin_surface, entry_vessel, entry_lesion_size, entry_acetic_acid, entry_lugol_iodine
    global entry_total_score, entry_biopsy_taken, entry_histopathology_report
    global captured_indications
    # Check if all images have been captured for each indication
    missing_indications = set(indications) - captured_indications
    if missing_indications:
        missing_indications_str = "\n".join(missing_indications)
        messagebox.showerror("Error", f"Images are missing for the following indications:\n{missing_indications_str}")
        return

    
    # Get patient details
    patient_name = entry_patient_name.get()
    patient_age = entry_patient_age.get()
    patient_id = entry_patient_id.get()
    hospital_number = entry_hospital_number.get()
    doctor_name = entry_doctor_name.get()
    
    # Check if all form fields have been filled
    if not entry_margin_surface.get() or not entry_vessel.get() or not entry_lesion_size.get() or \
       not entry_acetic_acid.get() or not entry_lugol_iodine.get() or not entry_total_score.get() or \
       not entry_biopsy_taken.get() or not entry_histopathology_report.get():
        messagebox.showerror("Error", "Fill out all form fields.")
        return
    
    # Get form details
    margin_surface = entry_margin_surface.get()
    vessel = entry_vessel.get()
    lesion_size = entry_lesion_size.get()
    acetic_acid = entry_acetic_acid.get()
    lugol_iodine = entry_lugol_iodine.get()
    total_score = entry_total_score.get()
    biopsy_taken = entry_biopsy_taken.get()
    histopathology_report = entry_histopathology_report.get()

    patient_folder = create_patient_folder()
    
    # Create a new PDF file
    pdf_file = os.path.join(patient_folder, f"Patient_Report.pdf")
    doc = SimpleDocTemplate(pdf_file, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    elements = []




    # Load logo images
    logo1_path = "logo1.png"
    logo2_path = "logo2.png"
    logo1 = ReportLabImage(logo1_path, width=50, height=50)
    logo2 = ReportLabImage(logo2_path, width=50, height=50)

    # Create a table to hold the logos
    logos_table = Table([[logo1, logo2]], colWidths=[doc.width / 2, doc.width / 2])
    logos_table.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                     ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Align the right logo to the right
                                     ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                     ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    elements.append(logos_table)

    # Patient details
    patient_details = [
        f"<b>Patient Name:</b> {patient_name}",
        f"<b>Patient Age:</b> {patient_age}",
        f"<b>Patient ID:</b> {patient_id}",
        f"<b>Hospital Number:</b> {hospital_number}",
        f"<b>Doctor Performing Colposcopy:</b> {doctor_name}",
    ]

    # Create a list of Paragraphs for patient details with bigger and bolder text
    styles = getSampleStyleSheet()
    patient_details_paragraphs = [Paragraph(detail, ParagraphStyle('Normal', fontSize=14, spaceAfter=10, fontName='Helvetica-Bold')) for detail in patient_details]
    elements.extend(patient_details_paragraphs)

    # Add Spacer to create some vertical spacing between patient details and form data
    spacer = Spacer(1, 20)
    elements.append(spacer)

    # Form details
    form_data = [
        "<b>Form Data:</b>",
        f"<b>1. Margin and Surface:</b> {entry_margin_surface.get()}",
        f"<b>2. Vessel:</b> {entry_vessel.get()}",
        f"<b>3. Lesion size:</b> {entry_lesion_size.get()}",
        f"<b>4. Acetic acid:</b> {entry_acetic_acid.get()}",
        f"<b>5. Lugol iodine:</b> {entry_lugol_iodine.get()}",
        f"<b>6. Total score:</b> {entry_total_score.get()}",
        f"<b>7. Biopsy taken:</b> {entry_biopsy_taken.get()}",
        f"<b>8. Histopathology report:</b> {entry_histopathology_report.get()}",
    ]

    # Create a list of Paragraphs for form data with bigger and bolder text
    form_data_paragraphs = [Paragraph(detail, ParagraphStyle('Normal', fontSize=12, spaceAfter=10, fontName='Helvetica-Bold')) for detail in form_data]
    elements.extend(form_data_paragraphs)

    # Add Spacer to create some vertical spacing between form data and images
    spacer = Spacer(1, 20)
    elements.append(spacer)

    # Add images to the report
    patient_folder = create_patient_folder()
    for indication in indications:
        subfolder = os.path.join(patient_folder, indication)
        for root, _, files in os.walk(subfolder):
            for file in files:
                if file.endswith(".png"):
                    image_path = os.path.join(root, file)
                    img = ReportLabImage(image_path, width=500, height=500)
                    elements.append(img)

    # Build the report with the elements
    doc.build(elements)

    print(f"Report generated: {pdf_file}")
    captured_indications = set()

def add_logos_to_screen2():
    add_logos(screen2)

def add_logos(root):
    # Load logo images using PIL
    logo1 = Image.open("logo1.png")
    logo2 = Image.open("logo2.png")

    # Resize the logos if needed (adjust the size as per your requirement)
    logo1 = logo1.resize((50, 50))
    logo2 = logo2.resize((50, 50))

    # Convert the logos to Tkinter PhotoImage format
    logo1_tk = ImageTk.PhotoImage(logo1)
    logo2_tk = ImageTk.PhotoImage(logo2)

    # Create a frame for logos and pack it at the top of the root window
    logo_frame = tk.Frame(root)
    logo_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

    # Create labels to display the logos on the top left and top right within the logo_frame
    logo1_label = tk.Label(logo_frame, image=logo1_tk)
    logo1_label.image = logo1_tk  # Keep a reference to the image to avoid garbage collection
    logo1_label.pack(side=tk.LEFT)

    logo2_label = tk.Label(logo_frame, image=logo2_tk)
    logo2_label.image = logo2_tk  # Keep a reference to the image to avoid garbage collection
    logo2_label.pack(side=tk.RIGHT)



def add_form():
    global entry_margin_surface, entry_vessel, entry_lesion_size, entry_acetic_acid, entry_lugol_iodine
    global entry_total_score, entry_biopsy_taken, entry_histopathology_report

    form_frame = tk.Frame(screen2)
    form_frame.pack(pady=20)

    # Create a canvas to contain the form
    form_canvas = tk.Canvas(form_frame, highlightthickness=0)
    form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create another frame inside the canvas to hold the form elements
    form_inner_frame = tk.Frame(form_canvas)
    form_canvas.create_window((0, 0), window=form_inner_frame, anchor=tk.NW)

    # Form fields
    label_margin_surface = tk.Label(form_inner_frame, text="1. Margin and Surface:")
    label_margin_surface.grid(row=0, column=0, sticky="w")
    entry_margin_surface = tk.Entry(form_inner_frame)
    entry_margin_surface.grid(row=0, column=1, sticky="ew")

    label_vessel = tk.Label(form_inner_frame, text="2. Vessel:")
    label_vessel.grid(row=1, column=0, sticky="w")
    entry_vessel = tk.Entry(form_inner_frame)
    entry_vessel.grid(row=1, column=1, sticky="ew")

    label_lesion_size = tk.Label(form_inner_frame, text="3. Lesion size:")
    label_lesion_size.grid(row=2, column=0, sticky="w")
    entry_lesion_size = tk.Entry(form_inner_frame)
    entry_lesion_size.grid(row=2, column=1, sticky="ew")

    label_acetic_acid = tk.Label(form_inner_frame, text="4. Acetic acid:")
    label_acetic_acid.grid(row=3, column=0, sticky="w")
    entry_acetic_acid = tk.Entry(form_inner_frame)
    entry_acetic_acid.grid(row=3, column=1, sticky="ew")

    label_lugol_iodine = tk.Label(form_inner_frame, text="5. Lugol iodine:")
    label_lugol_iodine.grid(row=4, column=0, sticky="w")
    entry_lugol_iodine = tk.Entry(form_inner_frame)
    entry_lugol_iodine.grid(row=4, column=1, sticky="ew")

    label_total_score = tk.Label(form_inner_frame, text="6. Total score:")
    label_total_score.grid(row=5, column=0, sticky="w")
    entry_total_score = tk.Entry(form_inner_frame)
    entry_total_score.grid(row=5, column=1, sticky="ew")

    label_biopsy_taken = tk.Label(form_inner_frame, text="7. Biopsy taken:")
    label_biopsy_taken.grid(row=6, column=0, sticky="w")
    entry_biopsy_taken = tk.Entry(form_inner_frame)
    entry_biopsy_taken.grid(row=6, column=1, sticky="ew")

    label_histopathology_report = tk.Label(form_inner_frame, text="8. Histopathology report:")
    label_histopathology_report.grid(row=7, column=0, sticky="w")
    entry_histopathology_report = tk.Entry(form_inner_frame)
    entry_histopathology_report.grid(row=7, column=1, sticky="ew")


    def save_form_data():
        patient_name = entry_patient_name.get()
        patient_id = entry_patient_id.get()
        patient_folder = os.path.join(".", "Patient_{}_{}".format(patient_name, patient_id))

        # Check if the patient folder with the same name exists
        if not os.path.exists(patient_folder):
            print(f"Error: Patient folder not found for {patient_name}, {patient_id}")
            return

        # Save the form data in the patient text file
        patient_details_file = os.path.join(patient_folder, "patient_details.txt")
        with open(patient_details_file, 'a') as f:
            f.write("\n\nForm Data:\n")
            f.write("1. Margin and Surface: {}\n".format(entry_margin_surface.get()))
            f.write("2. Vessel: {}\n".format(entry_vessel.get()))
            f.write("3. Lesion size: {}\n".format(entry_lesion_size.get()))
            f.write("4. Acetic acid: {}\n".format(entry_acetic_acid.get()))
            f.write("5. Lugol iodine: {}\n".format(entry_lugol_iodine.get()))
            f.write("6. Total score: {}\n".format(entry_total_score.get()))
            f.write("7. Biopsy taken: {}\n".format(entry_biopsy_taken.get()))
            f.write("8. Histopathology report: {}\n".format(entry_histopathology_report.get()))

        print("Form data saved.")

    # Add a "Save" button to save the form data
    btn_save = tk.Button(form_frame, text="Save", command=save_form_data)
    btn_save.pack()
    
    



# Screen 1: Patient details
screen1 = tk.Frame(root)
screen1.pack()

# Add title and signature to screen 1
add_title(screen1)
add_signature(screen1)

label_patient_name = tk.Label(screen1, text="Patient Name:")
label_patient_name.pack()
entry_patient_name = tk.Entry(screen1)
entry_patient_name.pack()

label_patient_age = tk.Label(screen1, text="Patient Age:")
label_patient_age.pack()
entry_patient_age = tk.Entry(screen1)
entry_patient_age.pack()

label_patient_id = tk.Label(screen1, text="Patient ID:")
label_patient_id.pack()
entry_patient_id = tk.Entry(screen1)
entry_patient_id.pack()

label_hospital_number = tk.Label(screen1, text="Hospital Number:")
label_hospital_number.pack()
entry_hospital_number = tk.Entry(screen1)
entry_hospital_number.pack()

label_doctor_name = tk.Label(screen1, text="Doctor Performing Colposcopy:")
label_doctor_name.pack()
entry_doctor_name = tk.Entry(screen1)
entry_doctor_name.pack()

btn_next = tk.Button(screen1, text="Next", command=show_screen1)
btn_next.pack()

# Error Label to display error messages
error_label = tk.Label(screen1, text="", fg="red")
error_label.pack()

# Screen 2: Colposcopic Images
screen2 = tk.Frame(root)

# Define the image capture buttons and their actions
indications = [
    "Without magnification white light (Normal saline)",
    "With magnification white light (Normal Saline)",
    "Green filter",
    "Acetic acid",
    "Lugol's Iodine"
]

def add_spacing(parent_frame, spacing):
    frame = tk.Frame(parent_frame)
    frame.pack(pady=spacing)
    return frame

# Create a frame for the indication buttons and the "Back" button
buttons_frame = tk.Frame(screen2)
buttons_frame.pack(pady=10)

# Create a frame for the indication buttons
indications_frame = tk.Frame(buttons_frame)
indications_frame.grid(row=0, column=0, padx=20, pady=5)

# Create a list to keep track of the buttons
indication_buttons = []

for index, indication in enumerate(indications):
    btn_capture = tk.Button(indications_frame, text=indication, font=("Helvetica", 14, "bold"),
                            command=lambda ind=indication: capture_image(ind))
    btn_capture.pack(fill=tk.X, pady=2)
    indication_buttons.append(btn_capture)

# Create the "Back" button
btn_back = tk.Button(buttons_frame, text="Back", font=("Helvetica", 14, "bold"),
                     command=lambda: screen2.pack_forget() or screen1.pack())
btn_back.grid(row=0, column=1, sticky='ne', padx=20, pady=10)

btn_view_images = tk.Button(screen2, text="View Patient Images", font=("Helvetica", 14, "bold"), command=view_images)
btn_view_images.pack(pady=10)
# Create a button to start video recording
btn_start_recording = tk.Button(screen2, text="Start Video Recording", font=("Helvetica", 14, "bold"), command=start_video_recording)
btn_start_recording.pack(pady=10)

# Create a button to stop video recording
btn_stop_recording = tk.Button(screen2, text="Stop Video Recording", font=("Helvetica", 14, "bold"), command=stop_video_recording)
btn_stop_recording.pack(pady=10)
btn_stop_recording.configure(state=tk.DISABLED)  # Initially disable the stop button

# Add the "Generate Report" button
btn_generate_report = tk.Button(screen2, text="Generate Report", font=("Helvetica", 14, "bold"), command=generate_report)
btn_generate_report.pack(pady=10)


#btn_back = tk.Button(screen2, text="Back", font=("Helvetica", 14, "bold"),
#                     command=lambda: screen2.pack_forget() or screen1.pack())
#btn_back.pack()

add_logos(root)


#start_camera() # Start the camera feed

#add_title()
#add_signature()

root.mainloop()