# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox
from monocromator import Monocromator
from lightsource_tech import list_monocromators
from time import sleep
from demo_GUI import DemoMonochromator
from Camera_live import CameraLive
from PIL import Image, ImageTk
from sweep import wavelength_sweep
import numpy as np
import shutil  
import os
import threading
os.environ["TK_USE_INPUT_METHODS"] = "0"  # voorkomt Tk/Spyder-interferentie


class MSP_GUI:

#---------------------------------------------------------
# INITIALISATIE CONTROLS GUI
#---------------------------------------------------------
    def set_controls_state(self, state):
        """Schakel alle bedieningselementen in of uit"""
        widgets = [self.toggle_button, self.button_up, self.button_down,
                  self.entry_wl, self.button_sweep,  self.update_button, self.Bit_mode_12, self.Bit_mode_16]
        for widget in widgets:
            widget.config(state=state)
            
    def _show_error(self, title, message):
        """Toont een messagebox voor fouten"""
        messagebox.showerror(title, message)

    def _camera_error(self, message):
        """Wordt vanuit CameraLive-thread aangeroepen."""
        # Via after ervoor zorgen dat het in de Tkinter mainloop draait:
        self.root.after(0, lambda: self._show_error("Camera fout", message))   
        
#---------------------------------------------------------
# LAYOUT SETTINGS GUI
#---------------------------------------------------------

    def __init__(self):
        """
         -Bouwt alle GUI-frames en widgets
         -detecteert de monochromator (demo indien nodig)
         -initialiseert de camera 
         -koppelt events/callbacks en start de hoofd-eventloop
        """
        
        # basis Tk-root en algemene applicatie-instellingen  
        self.root = tk.Tk()
        self.root.title("MSP GUI")
        self.root.geometry("825x500")
        self.root.minsize(800, 650)
        self.slider_min = 250
        self.slider_max = 700
        self.step_size = 20
        self.bg_colour =  "lightblue"

        # stateflags (shutter, running, demo_mode)
        self.shutter_open = False
        self.running = True  # Houd bij of GUI actief is
        self.demo_mode = False  # Demo mode flag
        self.sweep_running = False

        
        # bovenste balk aanmaken (shutter, demo status en status label)
        top_frame = tk.Frame(self.root, bg=self.bg_colour)
        top_frame.pack(side="top", fill="x", pady=(10,0))
        
        # demoMonochromator check
        self.m = list_monocromators()
        if not self.m:
            # Start demo mode
            messagebox.showwarning("Demo Mode", "Geen monochromator gevonden.\nDe GUI draait nu in DEMO-MODUS.")
            self.mono = DemoMonochromator()
            self.demo_label = tk.Label(top_frame, text="⚠️ DEMO MODUS ACTIEF", fg="red", font=("Arial", 10, "bold"), bg=self.bg_colour)
            self.demo_label.pack(padx=10)
            self.demo_mode = True
        else:
            self.mono = self.m[0]
            self.demo_mode = False

        # status label voor start-up en shutter positie
        self.status_label = tk.Label(top_frame, text="Initialisatie bezig...", font=("Arial", 12), bg= self.bg_colour)
        self.status_label.pack( padx=10, pady=5)
        
        # shutter knop
        self.toggle_button = tk.Button(
            top_frame,
            text="Open Shutter",
            font=("Arial", 12),
            bg="#444",
            fg="white",
            command=self.toggle_shutter,
            state="disabled"
            )
        self.toggle_button.pack(pady=12)  # Zorgt dat hij boven en gecentreerd staat
        
        # houdt shutter positie bij voor labels
        if getattr(self.mono, 'shutter_open', False):
            self.toggle_button.config(text="Sluit Shutter", bg="red")
        else:
            self.toggle_button.config(text="Open Shutter", bg="#444")

        # camera beeld frame (middle_frame)
        middle_frame = tk.Frame(self.root, bg= self.bg_colour)
        middle_frame.pack(fill = "both", expand=True)
        
        # slider + controls links
        left_frame = tk.Frame(middle_frame, bg= self.bg_colour)
        left_frame.pack(side="left", padx= 0, pady=10, anchor="n")
        
        # top frame voor scheiding slider en knoppen
        left_top_frame = tk.Frame(left_frame, bg= self.bg_colour)
        left_top_frame.pack(side = "top", padx=(5, 0), pady=10, anchor="n")
        
        # golflengte invoeren
        self.wl_Label = tk.Label(left_top_frame, text="\u03BB (nm):", font=('Arial', 11), bg= self.bg_colour)
        self.wl_Label.pack(side = "top", pady=(10, 0), padx = (0,0))
        self.current_wl = tk.IntVar(value=500)
        self.entry_wl = tk.Entry(left_top_frame, textvariable=self.current_wl, font=('Arial', 11), width=15)
        self.entry_wl.pack(fill="x", padx = (0,0))
        self.entry_wl.bind("<Return>", lambda event: self.update_from_entry()) #Enter voor veranderen

        #Omhoog / omlaag knop 
        self.button_up = tk.Button(left_top_frame, text="▲", command=lambda: self.change_step(1), state="disabled")
        self.button_up.pack(side = "top", fill="y", pady=(10, 0), padx = (0,0))
        self.button_down = tk.Button(left_top_frame, text="▼", command=lambda: self.change_step(-1), state="disabled")
        self.button_down.pack(side = "top", fill="y", padx = (0,0))
        
        # update knop om de golflengte echt te veranderen
        self.update_button = tk.Button(left_top_frame, text="Update", font=('Arial', 11), command=self.update_from_entry, state="disabled")
        self.update_button.pack(pady=(10, 0), padx = (0,0))
        
        # slider positie en canvas aanmaken
        self.slider_canvas = tk.Canvas(left_frame, width=80, bg= self.bg_colour, bd=0, highlightthickness=0)
        self.slider_canvas.pack(fill="y", expand=True)
        self.slider_canvas.bind("<Configure>", self.redraw_slider)
        self.slider_canvas.bind("<Button-1>", self.slider_click)
        
        # camera midden
        self.camera_frame = tk.Frame(middle_frame, bg= self.bg_colour)
        self.camera_frame.pack(side="left", fill="both", expand=True, padx=10, pady=(10,40))
        self.camera_frame.pack_propagate(False)
        self._square_update_pending = False
        self.camera_frame.bind("<Configure>", self._schedule_square_update)

        # interne frame voor de image
        self.camera_image_label = tk.Label(self.camera_frame,bg="black")
        self.camera_image_label.pack(fill="both", expand=True)

        # status label onderaan
        self.camera_status_label = tk.Label(self.camera_image_label, text="📷 Camera initialiseren...", bg="#222", fg="white", font=("Arial", 9), bd = 2, highlightthickness = 0)
        self.camera_status_label.pack(fill="both", side="bottom")

        # rechts: sweep controls
        right_frame = tk.Frame(middle_frame, bg= self.bg_colour)
        right_frame.pack(side="right", fill="y", padx=0, pady=0, anchor="n")

        # start sweep knop
        self.button_sweep = tk.Button(right_frame, text="Start sweep",  font=('Arial', 11), command=self.start_sweep, state="disabled")
        self.button_sweep.pack(fill="x", pady=(10, 0), padx=(20,20))

        # golflengte min / max / step size positie en entry
        self.start_wl_label = tk.Label(right_frame, text="Wavelength min (nm):", font=('Arial', 11), bg= self.bg_colour)
        self.start_wl_label.pack(pady=(40, 0), padx=(0,0))
        self.start_wl_entry = tk.Entry(right_frame)
        self.start_wl_entry.pack(fill="x", pady=(0, 10), padx=(20,20))
        
        self.end_wl_label = tk.Label(right_frame, text="Wavelength max (nm):", font=('Arial', 11), bg= self.bg_colour)
        self.end_wl_label.pack()
        self.end_wl_entry = tk.Entry(right_frame)
        self.end_wl_entry.pack(fill="x", pady=(0, 10), padx=(20,20))
        
        self.step_label = tk.Label(right_frame, text="Step size (nm):", font=('Arial', 11), bg= self.bg_colour)
        self.step_label.pack()
        self.step_entry = tk.Entry(right_frame)
        self.step_entry.pack(fill="x", pady=(0, 10), padx=(20,20))
        
        # camera resolutie knop
        self.bit_mode_label = tk.Label(right_frame, text="Camera resolutie:", font=('Arial', 11), bg= self.bg_colour)
        self.bit_mode_label.pack(pady=(20,0))
        self.bit_mode_var = tk.StringVar(value="12bit")
        self.Bit_mode_12 = tk.Radiobutton(right_frame,text="12-bit",variable=self.bit_mode_var,value="12bit", state="disabled")
        self.Bit_mode_12.pack(pady=(0,0))
        self.Bit_mode_16 = tk.Radiobutton(right_frame,text="16-bit",variable=self.bit_mode_var,value="16bit", state="disabled")
        self.Bit_mode_16.pack()

         
        self.root.after(200, self.update_camera_feed) #periodieke update camera feed
        self.cam_live = CameraLive()  # live camera aan

        # Start de automatische camera-reconnect loop
        #self.root.after(5000, self._attempt_camera_reconnect)
        
        self.root.after(200, self.startup_sequence) # start-up sequence starten
        self.root.protocol("WM_DELETE_WINDOW", self.on_close) # sluit window
        self.root.mainloop() #start eventloop
        
#---------------------------------------------------------
# START / STOP SEQUENCE
#---------------------------------------------------------
    def startup_sequence(self):
        """Verbeterde startup met camera integratie"""
    
        def init_device():
            try:
                # Update status
                self.root.after(0, lambda: self.status_label.config(text="🔵 Verbinden met apparatuur..."))

                # Start camera EERST
                self.root.after(0, lambda: self.status_label.config(text="🔵 Initialiseren camera..."))
                self.cam_live.start_live()
                
                # Monochromator initialisatie
                if self.demo_mode:
                    self.root.after(0, lambda: self.status_label.config(text="🟡 DEMO MODUS - Klaar"))
                else:
                    self.root.after(0, lambda: self.status_label.config(text="🟡 Verbinden monochromator..."))
                    self.m = list_monocromators()
                    if not self.m:
                        raise Exception("Geen monochromator gevonden!")
                
                    self.mono = self.m[0]
                    if not self.mono.open():
                        raise Exception("Kon monochromator niet openen!")
                
                     # Korte initialisatie
                    self.mono.readConfig()
                    self.mono.readAddress('variables')
                    self.mono.sync()  # Negeer eventuele fouten
                    self.mono.reset()
                    sleep(8.5)
                    self.mono.set_wavelength(500)

                # FINALE STATUS - Activeer controls
                self.root.after(0, self.finalize_startup)
            
            except Exception as exc:
                error_msg = f"Opstart fout: {str(exc)}"
                self.root.after(0, lambda: self.status_label.config(text="❌ Opstart mislukt"))
                self.root.after(0, lambda: messagebox.showerror("Opstart Fout", error_msg))

        threading.Thread(target=init_device, daemon=True).start()

    def finalize_startup(self):
        """Finaliseer startup en activeer alles"""
        self.set_controls_state("normal")
        self.status_label.config(text="🟢 Systeem klaar!")  

    def on_close(self):
        """Netjes afsluiten van alles"""
   
        self.running = False
    
        try:
            # Sluit monochromator
            if hasattr(self, "mono") and not self.demo_mode:
                if hasattr(self, 'shutter_open') and self.shutter_open:
                    self.mono.shutterPos("close")
                    sleep(0.1)
            
                if hasattr(self.mono, 'close'):
                    self.mono.close()
                    sleep(0.1)
            
            
            # Stop camera EERST
            if hasattr(self, "cam_live"):
                self.cam_live.stop_live()
                sleep(0.1)
        
        except Exception as e:
            self._show_error("Afsluitfout", f"Fout bij afsluiten: {e}")
    
        finally:
            try:
                self.root.destroy()
               
            except:
                pass
                
#---------------------------------------------------------
# SETTING WAVELENGTH FUNCTIONS
#---------------------------------------------------------   
    def redraw_slider(self, event=None):
        self.slider_canvas.delete("all")
        width = self.slider_canvas.winfo_width()
        height = self.slider_canvas.winfo_height()

        margin = int(height * 0.1)
        slider_height = height - 2 * margin
        top_y = margin
        bottom_y = margin + slider_height

        # Sla deze variabelen tijdelijk op
        self._slider_draw_params = (margin, slider_height, top_y, bottom_y)  # Je kunt eventueel ook als dict doen

        # Sliderbalk
        self.slider_canvas.create_rectangle(10, top_y, 30, bottom_y, fill="lightgray", outline="black")

        # Grote streepjes
        for wl in range(self.slider_min, self.slider_max + 1, 20):
            y = bottom_y - ((wl - self.slider_min) / (self.slider_max - self.slider_min) * slider_height)
            self.slider_canvas.create_line(30, y, 20, y, fill="black")
            self.slider_canvas.create_text(35, y, text=str(wl), anchor='w', font=('Arial', 9))

        # Kleine streepjes
        for wl in range(self.slider_min, self.slider_max + 1, 5):
            y = bottom_y - ((wl - self.slider_min) / (self.slider_max - self.slider_min) * slider_height)
            self.slider_canvas.create_line(30, y, 25, y, fill="black")
    
        # Herteken direct de marker na het tekenen van de slider
        self.update_slider_marker()

    def update_slider_marker(self):
        """Verplaatst rode markering naar juiste positie"""
        # Gebruik de actuele tekenparameters
        if not hasattr(self, '_slider_draw_params'):
            return  # Niks tekenen als slider nog niet gerenderd is

        margin, slider_height, top_y, bottom_y = self._slider_draw_params
        wl = self.current_wl.get()
        wl = max(self.slider_min, min(self.slider_max, wl))
        y = bottom_y - ((wl - self.slider_min) / (self.slider_max - self.slider_min) * slider_height)
        self.slider_canvas.delete("marker")
        self.slider_canvas.create_line(10, y, 30, y, fill="red", width=2, tags="marker")

    def slider_click(self, event):
        """Klik op slider → update huidige golflengte"""
        if not hasattr(self, '_slider_draw_params'):
            return
        margin, slider_height, top_y, bottom_y = self._slider_draw_params
        y = event.y - margin
        if y < 0 or y > slider_height:
            return
        wl = self.slider_max - ((y / slider_height) * (self.slider_max - self.slider_min))
        wl = int(round(wl))
        self.current_wl.set(wl)
        self.update_slider_marker()

    def update_from_entry(self):
        """Als gebruiker handmatig golflengte invoert"""
        try:
            wl = int(self.entry_wl.get())
            if self.slider_min <= wl <= self.slider_max:
                wl = int(wl)
                self.current_wl.set(wl)
                self.update_slider_marker()
                
                if not self.mono.set_wavelength(wl):          
                   return  # stop de functie hier
                
                
            else:
                messagebox.showerror("Fout", f"Waarde moet tussen {self.slider_min} en {self.slider_max} liggen.")
        except ValueError:
            messagebox.showerror("Fout", "Voer een geldig getal in!")

    def change_step(self, direction):
        """Verander golflengte in stappen van 20 met fysieke knoppen"""
        wl = self.current_wl.get() + direction * self.step_size
        wl = max(self.slider_min, min(self.slider_max, wl))
        self.current_wl.set(wl)
        self.update_slider_marker()
        
#---------------------------------------------------------
# CAMERA FEED
#---------------------------------------------------------      

    def update_camera_feed(self):
        if not self.running:
            return

        frame = self.cam_live.get_latest_frame()
        
        # 1) Camera niet verbonden / niet gevonden
        if (self.cam_live is None) or (not self.cam_live.camera_found):
            self.camera_image_label.config(image="")
            self.camera_status_label.config(
                text="❌ Camera niet verbonden",
                fg="red",
                bg="#222"
                )

        # 2) Camera gevonden maar (nog) geen streaming of nog geen frame
        elif not self.cam_live.streaming:
            # theoretisch zeldzaam, maar houden we simpel bij "niet verbonden"
            self.camera_image_label.config(image="")
            self.camera_status_label.config(
                text="❌ Camera geeft geen data",
                fg="red",
            bg="#222"
            )

        elif frame is None:
            # Hier weten we: camera_found == True en streaming == True
            self.camera_image_label.config(image="")
            self.camera_status_label.config(
                text="⏳ Wachten op frame...",
                fg="white",
                bg="#222"
                )

        # 3) Camera verbonden en frame beschikbaar → tonen
        else:
            if frame.ndim == 3:
                frame = frame[:, :, 0] if frame.shape[2] == 1 else np.mean(frame, axis=2).astype("uint8")

            frame_width = self.camera_frame.winfo_width()
            frame_height = self.camera_frame.winfo_height()
            side = min(frame_width, frame_height)
            
            img = Image.fromarray(frame)
            img = img.resize((side, side), Image.Resampling.LANCZOS)
            
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_image_label.imgtk = imgtk
            self.camera_image_label.config(image=imgtk)
            
            self.camera_status_label.config(
                text="🟢 Live feed actief (Mono8)",
                fg="#7CFC00",
                bg="#222"
                )

        # periodieke update
        if self.running:
            self.root.after(400, self.update_camera_feed)

  
    
    def update_camera_frame_size(self, event=None):
        if hasattr(self, "_resize_job"):
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(100, self._apply_square_size)
        
    def _attempt_camera_reconnect(self):
        """Probeer om de X seconden stil de camera opnieuw te verbinden."""
        if not self.running:
            return
        
        if self.sweep_running:
            self.root.after(1000, self._attempt_camera_reconnect)
            return

        # Als er geen camera actief is → probeer opnieuw te starten
        if not self.cam_live.streaming:
            self.cam_live.start_live()

        # Altijd opnieuw plannen
        self.root.after(1000, self._attempt_camera_reconnect)  # elke 5 sec

    def _schedule_square_update(self, event=None):
        """Throttle de resize-events zodat de GUI niet traag wordt."""
        if not getattr(self, "_square_update_pending", False):
            self._square_update_pending = True
            self.root.after(120, self._apply_square_size)

    def _apply_square_size(self):
        self._square_update_pending = False
        
        w = self.camera_frame.winfo_width()
        h = self.camera_frame.winfo_height()
        if w <= 1 or h <= 1:
            return

        side = min(w, h)
        self.camera_frame.config(width=side, height=side)
 
#---------------------------------------------------------
# SWEEP
#---------------------------------------------------------              
    def start_sweep(self):
        try:
            start_wl = float(self.start_wl_entry.get())
            end_wl = float(self.end_wl_entry.get())
            step = float(self.step_entry.get())
            bit_mode = self.bit_mode_var.get()
            
            # Controleer of de waarden binnen het bereik liggen
            if not (self.slider_min <= start_wl <= self.slider_max):
                messagebox.showerror(
                    "Fout",
                    f"Startgolflengte ({start_wl} nm) ligt buiten bereik "
                    f"({self.slider_min}–{self.slider_max} nm)."
                    )
                return

            if not (self.slider_min <= end_wl <= self.slider_max):
                messagebox.showerror(
                    "Fout",
                    f"Eindgolflengte ({end_wl} nm) ligt buiten bereik "
                    f"({self.slider_min}–{self.slider_max} nm)."
                    )
                return

            if start_wl >= end_wl:
                messagebox.showerror(
                    "Fout",
                    "De startgolflengte moet kleiner zijn dan de eindgolflengte."
                    )
                return

            if step <= 0:
                messagebox.showerror("Fout", "De stapgrootte moet groter dan 0 zijn.")
                return
            self.sweep_running = True
            # Start sweep in een nieuwe thread zodat GUI niet bevriest
            threading.Thread(target=self._sweep_thread, args=(start_wl, end_wl, step, bit_mode), daemon=True).start()


        except ValueError:
            messagebox.showerror("Fout", "Voer geldige numerieke waarden in!")

    def _sweep_thread(self, start_wl, end_wl, step_wl, bit_mode):
        try:
            # --- GUI blokkeren ---
            self.set_controls_state("disabled")
            self.status_label.config(text=f"🔵 Sweep bezig: {start_wl}-{end_wl} nm")

            # --- Stop live feed ---
            self.cam_live.stop_live()

            sleep(2)
            def update_gui_wl(wl):
                # Veilig in de hoofdthread uitvoeren
                self.root.after(0, lambda: self._update_wavelength_gui(wl))

            # --- Start sweep (Camera wordt intern geopend door CameraCapture) ---
            output_dir = "captures"
            wavelength_sweep(
                mono=self.mono,
                start_wl=start_wl,
                end_wl=end_wl,
                step_wl=step_wl,
                output_dir=output_dir,
                delay_after_move=0.2,
                bit_mode=bit_mode,
                on_step=update_gui_wl
                )

            self.status_label.config(text="🟢 Sweep voltooid")
            
            self.root.after(0, lambda: self._ask_to_save_dataset(output_dir))


        except Exception as e:
            self._show_error("Sweep fout", f"Fout tijdens sweep: {e}")
            self.status_label.config(text="❌ Sweep mislukt")

        finally:
            # --- GUI terug actief ---
            self.set_controls_state("normal")
            self.sweep_running = False
            # --- Herstart live feed ---
            self.cam_live.start_live()

    def _update_wavelength_gui(self, wl):
        """Update de GUI tijdens sweep met huidige golflengte."""
        self.current_wl.set(int(wl))
        self.update_slider_marker()
        self.entry_wl.delete(0, "end")
        self.entry_wl.insert(0, int(wl))
        self.status_label.config(text=f"🔵 Sweep bezig bij {wl:.1f} nm")

#---------------------------------------------------------
# SHUTTER / DATA SAVING
#---------------------------------------------------------  
    def toggle_shutter(self):

        try: 
            if not self.shutter_open:  # GUI bool
                success = self.mono.shutterPos("open")
            else:
                success = self.mono.shutterPos("close")

            if success:
                self.shutter_open = not self.shutter_open  # update GUI state
                if self.shutter_open:
                    self.status_label.config(text="Shutter: OPEN", fg="green")
                    self.toggle_button.config(text="Sluit Shutter", bg="red")
                else:
                    self.status_label.config(text="Shutter: GESLOTEN", fg="black")
                    self.toggle_button.config(text="Open Shutter", bg="#444")
            else:
                messagebox.showerror("Fout", "Kon shutter niet schakelen!")

        except Exception as e:
            messagebox.showerror("Fout", f"Shutter error:\n{e}")

    def _ask_to_save_dataset(self, source_dir):
        """
        Vraagt de gebruiker of de samengestelde TIFF ("alles_in_een_sweep.tiff")
        opgeslagen moet worden op een andere locatie.
        """
        antwoord = messagebox.askyesno("Dataset opslaan", "Wil je de dataset opslaan?")
        if not antwoord:
            return

        # Pad naar de gecombineerde TIFF
        source_file = os.path.join(source_dir, "alles_in_een_sweep.tiff")
        if not os.path.exists(source_file):
            messagebox.showerror("Fout", f"Het bestand '{source_file}' bestaat niet.")
            return

        # Laat gebruiker een opslaglocatie kiezen
        target_path = filedialog.asksaveasfilename(
            title="Sla de dataset op als",
            defaultextension=".tiff",
            filetypes=[("TIFF-bestanden", "*.tiff"), ("Alle bestanden", "*.*")],
            initialfile=".tiff"
            )
        if not target_path:
            messagebox.showinfo("Geannuleerd", "Opslaan geannuleerd.")
            return

        # Kopieer alleen het TIFF-bestand
        try:
            shutil.copy2(source_file, target_path)
            messagebox.showinfo("Succes", f"Dataset succesvol opgeslagen als:\n{target_path}")
        except Exception as e:

            messagebox.showerror("Fout", f"Kon dataset niet opslaan:\n{e}")
