# Version 1.70
# 12/19/2023
# Visual Regression Software
# Developed by Tyler MacLean
# Email: tyler.maclean@xplore.ca
# Property of Xplore inc


import pyautogui
from PIL import Image
from io import BytesIO
import numpy as np
import PySimpleGUI as sg
from pathlib import Path
from selenium import webdriver
import os
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from difflib import SequenceMatcher
import difflib
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

a = r'Actual/'
b = "Base/"

sg.theme("DarkBlue")

# Define the layout for the tab content
run_tab_layout = [
    [sg.Text('Select a test file'), sg.InputText(key='-file1-'), sg.FileBrowse()],
    [sg.Button("Base"), sg.ProgressBar(100, orientation='h', size=(20, 20), key='-base-progress-')],
    [sg.Button("Actual"), sg.ProgressBar(100, orientation='h', size=(20, 20), key='-actual-progress-')],
    [sg.Button("Compare")],
]

view_tab_layout = [
    [sg.Text('Complete a run and Compare Images to display Charts')],
    [sg.Canvas(key='-canvas-')],  # Canvas for pie chart
]
column1 = [[sg.Column(view_tab_layout, scrollable=True, vertical_scroll_only=True, size=(400,300))],]
# Create the tab layout
tab_layout = [
    [sg.Tab('Run', run_tab_layout), sg.Tab('View', column1)],
]

layout = [
    [sg.TabGroup(tab_layout)],
]

window = sg.Window('Visual Regression', layout, icon=r'T.ico')
driver = webdriver.Chrome()

def update_progress_bar(key, value):
    window[key].update_bar(value)

def create_pie_chart(percentage_diff, title):
    # Create a pie chart
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.pie([percentage_diff, 100 - percentage_diff], labels=[" ", "Similarity"], autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures the pie chart is circular

    # Save the pie chart as an image
    pie_chart_path = 'pie_chart.png'
    plt.title(title)
    plt.savefig(pie_chart_path, bbox_inches='tight')
    plt.close()

    # Display the pie chart on the canvas in the "View" tab
    canvas_elem = window['-canvas-']
    canvas = FigureCanvasTkAgg(fig, master=canvas_elem.Widget)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=1)

    return pie_chart_path


def ss(url, driver: webdriver.Chrome, path: str = '/tmp/screenshot.png'):
    print("Starting chrome full page screenshot workaround ...")
    driver.get(url)
    time.sleep(10)
    file = path
    with open('html/'+path+'HTMLoutput.txt', 'a') as f:
        try:
             f.write(driver.page_source)
        except:
            print("there was an error")


    total_width = driver.execute_script("return document.body.offsetWidth")
    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
    viewport_width = driver.execute_script("return document.body.clientWidth")
    viewport_height = driver.execute_script("return window.innerHeight")
    print("Total: ({0}, {1}), Viewport: ({2},{3})".format(total_width, total_height, viewport_width, viewport_height))
    rectangles = []

    i = 0
    while i < total_height:
        ii = 0
        top_height = i + viewport_height

        if top_height > total_height:
            top_height = total_height

        while ii < total_width:
            top_width = ii + viewport_width

            if top_width > total_width:
                top_width = total_width

            print("Appending rectangle ({0},{1},{2},{3})".format(ii, i, top_width, top_height))
            rectangles.append((ii, i, top_width, top_height))

            ii = ii + viewport_width

        i = i + viewport_height

    stitched_image = Image.new('RGB', (total_width, total_height))
    previous = None
    part = 0

    for rectangle in rectangles:
        if not previous is None:
            driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            print("Scrolled To ({0},{1})".format(rectangle[0], rectangle[1]))
            time.sleep(0.2)

        file_name = "part_{0}.png".format(part)
        print("Capturing {0} ...".format(file_name))

        driver.get_screenshot_as_file(file_name)
        screenshot = Image.open(file_name)

        if rectangle[1] + viewport_height > total_height:
            offset = (rectangle[0], total_height - viewport_height)
        else:
            offset = (rectangle[0], rectangle[1])

        print("Adding to stitched image with offset ({0}, {1})".format(offset[0], offset[1]))
        stitched_image.paste(screenshot, offset)

        del screenshot
        os.remove(file_name)
        part = part + 1
        previous = rectangle

    stitched_image.save(file)
    print("Finishing chrome full page screenshot workaround...")
    return True


def compare_images(image1_path, image2_path, output_path):
    # Open the images
    image1 = Image.open(image1_path)
    image2 = Image.open(image2_path)

    # Ensure both images have the same dimensions
    if image1.size > image2.size:
        new_image = Image.new('RGB', image1.size, 'green')
        new_image.paste(image2, (0, 0))
        image2 = new_image

    if image1.size < image2.size:
        new_image = Image.new('RGB', image2.size, 'green')
        new_image.paste(image1, (0, 0))
        image1 = new_image

    # Convert images to numpy arrays for pixel-wise comparison
    np_image1 = np.array(image1)
    np_image2 = np.array(image2)

    # Calculate pixel-wise absolute difference
    diff = np.abs(np_image1 - np_image2)

    # Create a mask where differences are present
    diff_mask = np.sum(diff, axis=2) > 0

    # Create an all-red image
    red_image = np.zeros_like(np_image1)
    try:
        red_image[diff_mask] = [255, 0, 0]  # Set differing pixels to red
    except:
        red_image[diff_mask] = [255, 0, 0, 255]

    # Calculate the percentage difference
    total_pixels = np.prod(image1.size)
    diff_pixels = np.sum(diff_mask)
    percentage_difference = (diff_pixels / total_pixels) * 100

    # Save the resulting image
    result_image = Image.fromarray(red_image)
    new_img = Image.blend(image1, result_image, 0.5)
    new_img.save(output_path)

    return percentage_difference

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    elif event == "Base":
        filename = values['-file1-']
        while True:
            if not Path(filename).is_file():
                if filename == '':
                    sg.popup_ok('Select a file to go !')
                else:
                    sg.popup_ok('File not exist !')
                filename = sg.popup_get_file("", no_window=True)
                if filename == '':
                    break
                window['-file1-'].update(filename)
            else:
                lines = []
                with open(filename, 'r') as file:
                    n = 1
                    for line in file:
                        # Remove leading and trailing whitespace (e.g., newline characters)
                        cleaned_line = line.strip()

                        # Append the cleaned line to the list
                        lines.append(cleaned_line)

                    total_lines = len(lines)
                    for i, line in enumerate(lines, start=1):
                        ss(line, driver=driver, path=(b+"image " + str(n) + ".png"))
                        n = n + 1
                        update_progress_bar('-base-progress-', (i / total_lines) * 100)

                break
    elif event == "Actual":
        filename = values['-file1-']
        while True:
            if not Path(filename).is_file():
                if filename == '':
                    sg.popup_ok('Select a file to go !')
                else:
                    sg.popup_ok('File not exist !')
                filename = sg.popup_get_file("", no_window=True)
                if filename == '':
                    break
                window['-file1-'].update(filename)
            else:
                lines = []
                with open(filename, 'r') as file:
                    n = 1
                    for line in file:
                        # Remove leading and trailing whitespace (e.g., newline characters)
                        cleaned_line = line.strip()

                        # Append the cleaned line to the list
                        lines.append(cleaned_line)

                    total_lines = len(lines)
                    for i, line in enumerate(lines, start=1):
                        ss(line, driver=driver, path=(a+"image " + str(n) + ".png"))
                        n = n + 1
                        update_progress_bar('-actual-progress-', (i / total_lines) * 100)

                break
    elif event == "Compare":
        # Ensure the folder path exists
        if not os.path.exists(b):
            print(f"Folder not found: {b}")
        elif not os.path.exists(a):
            print(f"Folder not found: {a}")
        else:
            # List all files in the folder
            files = os.listdir(b)

            # Iterate through each file in the folder
            n = 1
            for file_name in files:
                # Create the full file path by joining the folder path and file name
                full_file_pathb = os.path.join(b, file_name)
                full_file_patha = os.path.join(a, file_name)
                try:
                    first_file_lines = Path('html/Actual/image ' + str(n) + '.pngHTMLoutput.txt').read_text().splitlines()
                    second_file_lines = Path('html/Base/image ' + str(n) + '.pngHTMLoutput.txt').read_text().splitlines()
                    html_diff = difflib.HtmlDiff().make_file(first_file_lines, second_file_lines)
                    m = SequenceMatcher(None, first_file_lines, second_file_lines)

                    print("Difference in HTML " + str(n) + f": {(1-m.ratio())*100:.2f}%")
                    Path('html/Diff/diff' + str(n) + '.html').write_text(html_diff)

                except:
                    print("there was an uncaught error with the HTML compare")

                # Check if the item is a file (not a subdirectory)
                if os.path.isfile(full_file_pathb) and os.path.isfile(full_file_patha):
                    percentage_diff = compare_images(full_file_pathb, full_file_patha, "Diff/Image " + str(n) + ".png")
                    print("Difference in Image " + str(n) + f": {percentage_diff:.2f}%")

                    # Create and display a pie chart for the percentage difference
                    pie_chart_path = create_pie_chart(percentage_diff, "Difference in Image " + str(n))
                    n = n + 1

window.close()
