import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import os
import shutil
from datetime import datetime

import botbuster
import botsorter

# Global Variables
platform_selected = "None"
fh = None
filepath_var = ""
filepath_netmapper_var = ""
loading_var = ""
success_run_var = ""
folder_to_run = ""

def reset_variables():
    global platform_selected, filepath_var, loading_var, success_run_var, fh, folder_to_run

    fh = None 
    platform_selected = None
    # filepath_var = ""
    # loading_var = ""
    # success_run_var = ""
    folder_to_run = ""
    
    try:
        set_loading_label("")
        set_success_run_label("")
    except:
        pass

def create_log_file():
    global fh
    log_filename = ""
    now = datetime.now()
    log_filename = now.strftime("platform_log_%Y%m%d_%H%M%S.txt")

    logs_directory = "logs"
    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)
    log_filepath = os.path.join(logs_directory, log_filename)
    
    try:
        fh = open(log_filepath, "a")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create log file: {str(e)}")
        return False

def create_temp_folder():
    global folder_to_run

    temp_directory = "temp"
    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_datetime_directory = os.path.join(temp_directory, current_datetime)
    if not os.path.exists(temp_datetime_directory):
        os.makedirs(temp_datetime_directory)

    folder_to_run = temp_datetime_directory

def close_log_file():
    global fh
    if fh:
        fh.close()

def to_log(text):
    if fh:
        fh.write(text)
        print(text)

## This function will pass uploaded file to BotBuster modules for analysis
def deal_with_uploaded_file(filepath):
    global filepath_var, folder_to_run

    create_temp_folder()

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        num_lines = len(lines)

        if num_lines > 50000:
            num_files = num_lines // 50000 + 1
            split_size = num_lines // num_files

            for i in range(num_files):
                start_idx = i * split_size
                end_idx = min((i + 1) * split_size, num_lines)
                split_file = f"{filepath}_{i+1}.txt"

                with open(os.path.join(folder_to_run, split_file), 'w', encoding='utf-8') as f:
                    f.writelines(lines[start_idx:end_idx])

                to_log(f"File split: {split_file} (lines {start_idx + 1}-{end_idx})")
        else:
            new_filepath = os.path.join(folder_to_run, os.path.basename(filepath))
            shutil.copy(filepath, new_filepath)
            to_log(f"File moved to temporary folder: {new_filepath}")
            to_log(f"File uploaded: {filepath}")

        filepath_var.set(filepath)

    except Exception as e:
        to_log(f"Failed to read JSON file: {str(e)}")
        filepath_var.set(f"Error, Failed to read JSON file: {str(e)}")

def deal_with_uploaded_netmapper_file(filepath):
    global filepath_netmapper_var, folder_to_run

    create_temp_folder()

    try:
        new_filepath = os.path.join(folder_to_run, os.path.basename(filepath))
        shutil.copy(filepath, new_filepath)
        to_log(f"File moved to temporary folder: {new_filepath}")
        to_log(f"File uploaded: {filepath}")

        filepath_netmapper_var.set(filepath)

    except Exception as e:
        to_log(f"Failed to read JSON file: {str(e)}")
        filepath_var.set(f"Error, Failed to read JSON file: {str(e)}")

def set_loading_label(message):
    global loading_var
    #root.after(2000, loading_var.set(message))
    loading_var.set(message)
    to_log(f'Current status: {message}\n')

def set_success_run_label(message):
    global success_run_var

    msg_orig = success_run_var.get()
    message_full = msg_orig + message
    success_run_var.set(message_full)
    to_log(f'Successfully Ran: {message}\n')

def upload_file():
    filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if filepath:
        deal_with_uploaded_file(filepath)
        filepath_var.set(filepath)

def upload_netmapper_file():
    filepath = filedialog.askopenfilename(filetypes=[("TSV files", "*.tsv")])
    if filepath:
        deal_with_uploaded_file(filepath)
        filepath_netmapper_var.set(filepath)

def show_about_popup():
    about_text = """
    BotBuster Universe analyzes social media bots for the following platforms: Twitter (X), Instagram, Reddit, Telegram
    BotBuster Universe has three main functions:
    (1) BotBuster: Identify if social media user is bot or human
    (2) BotSorter: Identify what type of bot it is
    (3) BotBias: Identify the biases that are inherent in the message

    The key papers for BotBuster Universe are:
    - Ng, L. H. X., & Carley, K. M. (2023). BotBuster: Multi-Platform Bot Detection Using a Mixture of Experts. Proceedings of the International AAAI Conference on Web and Social Media, 17(1), 686-697. https://doi.org/10.1609/icwsm.v17i1.22179

    For detailed explanation about the implementation and the analysis performed with the BotBuster Universe, please refer to https://quarbby.github.io/research/botbuster_universe.html.
    """
    messagebox.showinfo("About", about_text)

def run_botbuster(platform_selected):
    global folder_to_run

    try:
        if platform_selected == 'twitter_v1':
            run_success = botbuster.run_botbuster_twitter_v1(folder_to_run)
        elif platform_selected == 'twitter_v2':
            run_success = botbuster.run_botbuster_twitter_v2(folder_to_run)
        elif platform_selected == 'reddit':
            run_success = botbuster.run_botbuster_reddit(folder_to_run)
        elif platform_selected == 'instagram':
            run_success = botbuster.run_botbuster_instagram(folder_to_run)
        elif platform_selected == 'telegram':
            run_success = botbuster.run_botbuster_telegram(folder_to_run)

        return run_success
    
    except Exception as e:
        print(e)
        return 0
    
def run_botsorter(platform_selected):
    global folder_to_run

    try:
        if platform_selected == 'twitter_v1':
            run_success = botsorter.run_botsorter_twitter_v1(folder_to_run)
        elif platform_selected == 'twitter_v2':
            run_success = botsorter.run_botsorter_twitter_v2(folder_to_run)
        elif platform_selected == 'reddit':
            run_success = botsorter.run_botsorter_reddit(folder_to_run)
        elif platform_selected == 'instagram':
            run_success = botsorter.run_botsorter_instagram(folder_to_run)
        elif platform_selected == 'telegram':
            run_success = botsorter.run_botsorter_telegram(folder_to_run)

        return run_success
    
    except Exception as e:
        print('Exception ', e)
        return 0

def analyze_bots_btn_click():
    global platform_selected, filepath_var, filepath_netmapper_var

    platform_selected = platform_var.get()
    fp = filepath_var.get()
    #fp_netmapper = filepath_netmapper_var.get()     # this can be blank, then dont run botbias

    to_log(f"Selected Platform: {platform_selected}\n")
    to_log(f"filepath_var {fp}\n")

    if platform_selected == "None" and fp == "":
        analyze_bots_btn.config(bg="#98FB98")
        root.lift()
        messagebox.showwarning("BotBusting Failed!", "Please upload a file and select a platform.")
        return
    elif platform_selected != "None" and fp == "":
        analyze_bots_btn.config(bg="#98FB98")
        root.lift()
        messagebox.showwarning("BotBusting Failed!", "Please upload a file.")
        return
    elif platform_selected == "None" and fp != "":
        analyze_bots_btn.config(bg="#98FB98")
        root.lift()
        messagebox.showwarning("BotBusting Failed!", "Please select a platform.")
        return
    else:
        analyze_bots_btn.config(bg="#FFD5D5")

        set_loading_label('loading botbuster models...')
        model_reading = botbuster.read_models()
        if model_reading == 1:
            set_loading_label('botbuster models loaded')
        elif model_reading == 0:
            set_loading_label('error reading botbuster models')
            return
        
        set_loading_label('running botbuster...')
        botbuster_run = run_botbuster(platform_selected)

        if botbuster_run == 1:
            set_loading_label('BotBuster ran successfully. Check for files in temp/ folder')
            set_success_run_label(' BotBuster ')
        elif botbuster_run == 0:
            set_loading_label('Error running Botbuster :(')
        
        # run botsorter
        set_loading_label('loading botsorter models...')
        model_reading = botsorter.read_models()
        if model_reading == 1:
            set_loading_label('botsorter models loaded')
        elif model_reading == 0:
            set_loading_label('error reading botsorter models')
            return

        set_loading_label('running botsorter...')
        botsorter_run = run_botsorter(platform_selected)

        if botsorter_run == 1:
            set_loading_label('BotSorter ran successfully. Check for files in temp/ folder')
            set_success_run_label(' BotSorter BotBias')
        elif botbuster_run == 0:
            set_loading_label('Error running BotSorter BotBias:(')

        # Once done with botbuster, reset variables, set button to green
        analyze_bots_btn.config(bg="#98FB98")
        reset_variables()

def on_closing():
    global root

    if fh:
        fh.close()
    if botbuster.out_fh:
        botbuster.out_fh.close()

    root.destroy()  # Destroy the Tkinter window

if __name__ == "__main__":
    # Create the main application window
    create_log_file()
    
    root = tk.Tk()
    root.title("BotBuster Universe")
    root.geometry("1000x650")

    reset_variables()

    # Help Menu
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    about_menu = tk.Menu(menubar, tearoff=0)
    about_menu.add_command(label="About", command=show_about_popup)
    menubar.add_cascade(label="Help", menu=about_menu)

    # Row 1: Welcome message
    welcome_label = tk.Label(root, text="Welcome to BotBuster Universe", font=("Bebas Neue", 40))
    welcome_label.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")
    welcome_label_2 = tk.Label(root, wraplength=800, text="(1) BotBuster: Detecting Bots, (2) BotSorter: Identifying Bot Types, (3) BotBias: Identifying Use of Human Biases in Messages", font=("Bebas Neue", 16))
    welcome_label_2.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

    # Row 2: File Upload Button and Platform Selection
    upload_button = tk.Button(root, text="1. Upload JSON File of Posts", command=upload_file, font=("Arial", 16))
    upload_button.grid(row=2, column=0, padx=10, pady=10)
    filepath_var = tk.StringVar()
    upload_label = tk.Label(root, textvariable=filepath_var, font=("Arial", 14))
    upload_label.grid(row=3, column=0, padx=10, pady=10)

    platform_label = tk.Label(root, text="2. Select Platform", font=("Arial", 16))
    platform_label.grid(row=2, column=1, padx=10, pady=10, sticky="w")

    platform_var = tk.StringVar()
    rd_radio = tk.Radiobutton(root, text="Reddit", variable=platform_var, value="reddit", font=("Arial", 16))
    rd_radio.grid(row=3, column=1, sticky="w")
    tw_radio = tk.Radiobutton(root, text="Twitter V1 (X)", variable=platform_var, value="twitter_v1", font=("Arial", 16))
    tw_radio.grid(row=4, column=1, sticky="w")
    tw2_radio = tk.Radiobutton(root, text="Twitter V2 (X)", variable=platform_var, value="twitter_v2", font=("Arial", 16))
    tw2_radio.grid(row=5, column=1, sticky="w")
    ig_radio = tk.Radiobutton(root, text="Instagram", variable=platform_var, value="instagram", font=("Arial", 16))
    ig_radio.grid(row=6, column=1, sticky="w")
    tg_radio = tk.Radiobutton(root, text="Telegram", variable=platform_var, value="telegram", font=("Arial", 16))
    tg_radio.grid(row=7, column=1, sticky="w")
    platform_var.set(None)

    # Row 2.1 NetMapper Upload File
    # upload_netmapper_button = tk.Button(root, text="1b. Upload NetMapper File", command=upload_netmapper_file, font=("Arial", 16))
    # upload_netmapper_button.grid(row=4, column=0, padx=10, pady=10)
    # filepath_netmapper_var = tk.StringVar()
    # upload_netmapper_label = tk.Label(root, textvariable=filepath_netmapper_var, font=("Arial", 14))
    # upload_netmapper_label.grid(row=5, column=0, padx=10, pady=10)

    # Row 3: Analyze bots button
    analyze_bots_btn = tk.Button(root, text="4. Analyze Bots!", command=analyze_bots_btn_click, width=30, font=("Bebas Neue", 24), bg="#98FB98")
    analyze_bots_btn.grid(row=8, column=0, columnspan=2, pady=10)

    # Row 4: Loading Dialogs
    loading_var = tk.StringVar()
    loading_label = tk.Label(root, textvariable=loading_var, font=("Arial", 14))
    loading_label.grid(row=9, column=0, padx=10, pady=10)

    # Row 5: Successful Run
    success_run_var = tk.StringVar()
    success_run_var.set('Successfully ran: ')
    succsss_run_label = tk.Label(root, textvariable=success_run_var, font=("Arial", 14))
    succsss_run_label.grid(row=10, column=0, padx=10, pady=10)

    root.mainloop()
