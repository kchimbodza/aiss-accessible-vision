#!/usr/bin/python3

from tkinter import *
import tkinter as tk
import os

import tkinter.font as font
from PIL import Image, ImageTk
from multiprocessing import Process
from tkinter import filedialog

####______Intruder Detection Code______####

import numpy as np
import cv2
import time
import datetime
from collections import deque


def intruder():
    global foog
    #time.sleep(15)
    # Set Window normal so we can resize it
    #cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
    # Note the starting time
    start_time = time.time()

    # Initialize these variables for calculating FPS
    fps = 0 
    frame_counter = 0

    # Read the video stream from the camera
    cap = cv2.VideoCapture('http://192.168.1.104:8080/video')
    #cap1 = cv2.VideoCapture(1)
    # Get width and height of the frame
    width = int(cap.get(352))
    height = int(cap.get(288))

    


    ###################################################################

    # Read and store the credentials information in a dictionary
    from twilio.rest import Client
    with open('credentials.txt', 'r') as myfile:
      data = myfile.read()

    info_dict = eval(data)
    # Your Account SID from twilio.com/console
    account_sid = info_dict['account_sid']

    # Your Auth Token from twilio.com/console
    auth_token  = info_dict['auth_token']

    # Set client and send the message
    client = Client(account_sid, auth_token)
    #message = client.messages.create( to =info_dict['your_num'], from_ = info_dict['trial_num'], body= "What's Up Man")



    #########################################################################

    kernel=None
    # Initialize the background Subtractor
    foog = cv2.createBackgroundSubtractorMOG2( detectShadows = True, varThreshold = 50, history = 2800)


    def is_person_present(frame, thresh=1100):
        
        global foog
        
        # Apply background subtraction
        fgmask = foog.apply(frame)

        # Get rid of the shadows
        ret, fgmask = cv2.threshold(fgmask, 250, 255, cv2.THRESH_BINARY)

        # Apply some morphological operations to make sure you have a good mask
        fgmask = cv2.dilate(fgmask,kernel,iterations = 4)

        # Detect contours in the frame
        contours, hierarchy = cv2.findContours(fgmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
         
        # Check if there was a contour and the area is somewhat higher than some threshold so we know its a person and not noise
        if contours and cv2.contourArea(max(contours, key = cv2.contourArea)) > thresh:
                
                # Get the max contour
                cnt = max(contours, key = cv2.contourArea)

                # Draw a bounding box around the person and label it as person detected
                x,y,w,h = cv2.boundingRect(cnt)
                cv2.rectangle(frame,(x ,y),(x+w,y+h),(255,255,86),2)
                cv2.putText(frame,'Activity Detected',(x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,86), 1, cv2.LINE_AA)
                
                return True, frame
            
            
        # Otherwise report there was no one present
        else:
            return False, frame


    def send_message(body, info_dict):

        # Your Account SID from twilio.com/console
        account_sid = info_dict['account_sid']

        # Your Auth Token from twilio.com/console
        auth_token  = info_dict['auth_token']


        client = Client(account_sid, auth_token)

        message = client.messages.create( to = info_dict['your_num'], from_ = info_dict['trial_num'], body= body)



        ################################################################################


    # Status is True when person is present and False when the person is not present.
    status = False

    # After the person disapears from view, wait atleast 7 seconds before making the status False
    patience = 7

    # We don't consider an initial detection unless its detected 15 times, this gets rid of false positives
    detection_thresh = 15

    # Initial time for calculating if patience time is up
    initial_time = None

    # We are creating a deque object of length detection_thresh and will store individual detection statuses here
    de = deque([False] * detection_thresh, maxlen=detection_thresh)

    # Initialize these variables for calculating FPS
    fps = 0 
    frame_counter = 0
    start_time = time.time()


    while(True):
        
        ret, frame = cap.read()
        if not ret:
            break 
                
        # This function will return a boolean variable telling if someone was present or not, it will also draw boxes if it 
        # finds someone
        detected, annotated_image = is_person_present(frame)  
        
        # Register the current detection status on our deque object
        de.appendleft(detected)
         
        # If we have consectutively detected a person 15 times then we are sure that soemone is present    
        # We also make this is the first time that this person has been detected so we only initialize the videowriter once
        if sum(de) == detection_thresh and not status:                       
                status = True
                entry_time = datetime.datetime.now().strftime("IDS_Cam1_%a-%-I-%M-%S-%p_%d-%b-%Y")
                out = cv2.VideoWriter('intrusions/{}.mp4'.format(entry_time), cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (352, 288))

        # If status is True but the person is not in the current frame
        if status and not detected:
            
            # Restart the patience timer only if the person has not been detected for a few frames so we are sure it was'nt a 
            # False positive
            if sum(de) > (detection_thresh/2): 
                
                if initial_time is None:
                    initial_time = time.time()
                
            elif initial_time is not None:        
                
                # If the patience has run out and the person is still not detected then set the status to False
                # Also save the video by releasing the video writer and send a text message.
                if  time.time() - initial_time >= patience:
                    status = False
                    exit_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")
                    out.release()
                    initial_time = None
                
                    body = "Alert: Activity detected in the room on {} and ended on {}".format(entry_time, exit_time)
                    send_message(body, info_dict)
        
        # If significant amount of detections (more than half of detection_thresh) has occured then we reset the Initial Time.
        elif status and sum(de) > (detection_thresh/2):
            initial_time = None
        
        # Get the current time in the required format
        current_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")

        # Display the FPS


        
        #cv2.putText(annotated_image, 'FPS: {:.2f}'.format(fps), (300, 265), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255),1)
        
        # Display Time

        cv2.rectangle(frame, (190, 430), (520,460), (122, 63, 24), -1)
        cv2.putText(annotated_image, current_time, (20, 265), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255),1)    
        
        # Display the Room Status

        cv2.putText(frame, "A I S S | ", (20,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "O N", (100,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (0,0,255), 1)

        cv2.putText(annotated_image, 'Room Activity: {}'.format(str(status)), (150, 20), cv2.FONT_HERSHEY_DUPLEX, 0.5, 
                    (255, 255, 86),1)

        # Show the patience Value
        if initial_time is None:
            text = 'Patience: {}'.format(patience)
        else: 
            text = 'Patience: {:.2f}'.format(max(0, patience - (time.time() - initial_time)))
            
        cv2.putText(annotated_image, text, (20, 250), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255) , 1)   

        # If status is true save the frame
        if status:
            out.write(annotated_image)
     
        # Show the Frame
        cv2.imshow('Intrusion Detection',frame)
        
        # Calculate the Average FPS
        frame_counter += 1
        fps = (frame_counter / (time.time() - start_time))
        
        
        # Exit if q is pressed.
        if cv2.waitKey(1) == 27:
            break

    # Release Capture and destroy windows
    cap.release()
    cv2.destroyAllWindows()

def intruder2():
    global foog
    #time.sleep(15)
    # Set Window normal so we can resize it
    #cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
    # Note the starting time
    start_time = time.time()

    # Initialize these variables for calculating FPS
    fps = 0 
    frame_counter = 0

    # Read the video stream from the camera
    cap = cv2.VideoCapture('http://192.168.1.112:8080/video')
    #cap1 = cv2.VideoCapture(1)
    # Get width and height of the frame
    width = int(cap.get(352))
    height = int(cap.get(288))

    


    ###################################################################

    # Read and store the credentials information in a dictionary
    from twilio.rest import Client
    with open('credentials.txt', 'r') as myfile:
      data = myfile.read()

    info_dict = eval(data)
    # Your Account SID from twilio.com/console
    account_sid = info_dict['account_sid']

    # Your Auth Token from twilio.com/console
    auth_token  = info_dict['auth_token']

    # Set client and send the message
    client = Client(account_sid, auth_token)
    #message = client.messages.create( to =info_dict['your_num'], from_ = info_dict['trial_num'], body= "What's Up Man")



    #########################################################################

    kernel=None
    # Initialize the background Subtractor
    foog = cv2.createBackgroundSubtractorMOG2( detectShadows = True, varThreshold = 50, history = 2800)


    def is_person_present(frame, thresh=1100):
        
        global foog
        
        # Apply background subtraction
        fgmask = foog.apply(frame)

        # Get rid of the shadows
        ret, fgmask = cv2.threshold(fgmask, 250, 255, cv2.THRESH_BINARY)

        # Apply some morphological operations to make sure you have a good mask
        fgmask = cv2.dilate(fgmask,kernel,iterations = 4)

        # Detect contours in the frame
        contours, hierarchy = cv2.findContours(fgmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
         
        # Check if there was a contour and the area is somewhat higher than some threshold so we know its a person and not noise
        if contours and cv2.contourArea(max(contours, key = cv2.contourArea)) > thresh:
                
                # Get the max contour
                cnt = max(contours, key = cv2.contourArea)

                # Draw a bounding box around the person and label it as person detected
                x,y,w,h = cv2.boundingRect(cnt)
                cv2.rectangle(frame,(x ,y),(x+w,y+h),(255,255,86),2)
                cv2.putText(frame,'Activity Detected',(x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,86), 1, cv2.LINE_AA)
                
                return True, frame
            
            
        # Otherwise report there was no one present
        else:
            return False, frame


    def send_message(body, info_dict):

        # Your Account SID from twilio.com/console
        account_sid = info_dict['account_sid']

        # Your Auth Token from twilio.com/console
        auth_token  = info_dict['auth_token']


        client = Client(account_sid, auth_token)

        message = client.messages.create( to = info_dict['your_num'], from_ = info_dict['trial_num'], body= body)



        ################################################################################


    # Status is True when person is present and False when the person is not present.
    status = False

    # After the person disapears from view, wait atleast 7 seconds before making the status False
    patience = 7

    # We don't consider an initial detection unless its detected 15 times, this gets rid of false positives
    detection_thresh = 15

    # Initial time for calculating if patience time is up
    initial_time = None

    # We are creating a deque object of length detection_thresh and will store individual detection statuses here
    de = deque([False] * detection_thresh, maxlen=detection_thresh)

    # Initialize these variables for calculating FPS
    fps = 0 
    frame_counter = 0
    start_time = time.time()


    while(True):
        
        ret, frame = cap.read()
        if not ret:
            break 
                
        # This function will return a boolean variable telling if someone was present or not, it will also draw boxes if it 
        # finds someone
        detected, annotated_image = is_person_present(frame)  
        
        # Register the current detection status on our deque object
        de.appendleft(detected)
         
        # If we have consectutively detected a person 15 times then we are sure that soemone is present    
        # We also make this is the first time that this person has been detected so we only initialize the videowriter once
        if sum(de) == detection_thresh and not status:                       
                status = True
                entry_time = datetime.datetime.now().strftime("IDS_Cam2_%a-%-I-%M-%S-%p_%d-%b-%Y")
                out = cv2.VideoWriter('intrusions/{}.mp4'.format(entry_time), cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (352, 288))

        # If status is True but the person is not in the current frame
        if status and not detected:
            
            # Restart the patience timer only if the person has not been detected for a few frames so we are sure it was'nt a 
            # False positive
            if sum(de) > (detection_thresh/2): 
                
                if initial_time is None:
                    initial_time = time.time()
                
            elif initial_time is not None:        
                
                # If the patience has run out and the person is still not detected then set the status to False
                # Also save the video by releasing the video writer and send a text message.
                if  time.time() - initial_time >= patience:
                    status = False
                    exit_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")
                    out.release()
                    initial_time = None
                
                    body = "Alert: Activity detected in the room on {} and ended on {}".format(entry_time, exit_time)
                    send_message(body, info_dict)
        
        # If significant amount of detections (more than half of detection_thresh) has occured then we reset the Initial Time.
        elif status and sum(de) > (detection_thresh/2):
            initial_time = None
        
        # Get the current time in the required format
        current_time = datetime.datetime.now().strftime("%A, %I:%M:%S %p %d %B %Y")

        # Display the FPS


        
        #cv2.putText(annotated_image, 'FPS: {:.2f}'.format(fps), (550, 450), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255),1)
        
        # Display Time

        cv2.rectangle(frame, (190, 430), (520,460), (122, 63, 24), -1)
        cv2.putText(annotated_image, current_time, (20, 265), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255),1)    
        
        # Display the Room Status

        cv2.putText(frame, "A I S S | ", (20,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "O N", (100,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (0,0,255), 1)

        cv2.putText(annotated_image, 'Room Activity: {}'.format(str(status)), (150, 20), cv2.FONT_HERSHEY_DUPLEX, 0.5, 
                    (255, 255, 86),1)

        # Show the patience Value
        if initial_time is None:
            text = 'Patience: {}'.format(patience)
        else: 
            text = 'Patience: {:.2f}'.format(max(0, patience - (time.time() - initial_time)))
            
        cv2.putText(annotated_image, text, (20, 250), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255) , 1)   

        # If status is true save the frame
        if status:
            out.write(annotated_image)
     
        # Show the Frame
        cv2.imshow('Intrusion Detection',frame)
        
        # Calculate the Average FPS
        frame_counter += 1
        fps = (frame_counter / (time.time() - start_time))
        
        
        # Exit if Esc is pressed.
        if cv2.waitKey(1) == 27:
            break

    # Release Capture and destroy windows
    cap.release()
    cv2.destroyAllWindows()

### Open folders #####

def footage():
    #opens specific folder with live footage
    cmd = 'nemo //home/kc/Desktop/AISS1.4/footage'
    os.system(cmd)
    
def intrusions():
    cmd = 'nemo //home/kc/Desktop/AISS1.4/intrusions'
    os.system(cmd)


###### Live Recording Code ##################


def record():
    from datetime import datetime
    #cap = cv2.VideoCapture('http://192.168.1.107:8080/video')
    cap = cv2.VideoCapture(0)

    def make_288p():
        cap.set(3,352)
        cap.set(4,288)
    make_288p()

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(f'footage/{datetime.now().strftime("LS.Cam1_%a-%-I-%M-%S-%p_%d-%b-%Y")}.mp4', fourcc,20.0,(352,288))

    while True:
        _, frame = cap.read()


        cv2.putText(frame, "A I S S | ", (20,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "O N", (100,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (0,0,255), 1)
        cv2.putText(frame, f'{datetime.now().strftime("%d %B %Y")}', (20,265), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.rectangle(frame, (170, 250), (255,270), (122, 63, 24), -1)

        cv2.putText(frame, f'{datetime.now().strftime("%H:%M:%S")}', (175,265), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "Room 1", (20,280), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)

        out.write(frame)
        

        cv2.imshow("Press Esc. to Stop", frame)

        if cv2.waitKey(1) == 27:
            cap.release()
            cv2.destroyAllWindows()
            break 

def record2():
    from datetime import datetime
    cap = cv2.VideoCapture('http://192.168.1.102:8123/video')
    #cap = cv2.VideoCapture(0)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(f'footage/{datetime.now().strftime("LS.Cam2_%a-%-I-%M-%S-%p_%d-%b-%Y")}.mp4', fourcc,20.0,(352,288))

    while True:
        _, frame = cap.read()


        cv2.putText(frame, "A I S S | ", (20,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "O N", (100,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (0,0,255), 1)
        cv2.putText(frame, f'{datetime.now().strftime("%d %B %Y")}', (20,265), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.rectangle(frame, (170, 250), (255,270), (122, 63, 24), -1)

        cv2.putText(frame, f'{datetime.now().strftime("%H:%M:%S")}', (175,265), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "Room 2", (20,280), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)

        out.write(frame)
        

        cv2.imshow("Press Esc. to Stop", frame)

        if cv2.waitKey(1) == 27:
            cap.release()
            cv2.destroyAllWindows()
            break             


if __name__ == '__main__':
    
    def p1():
        p1= Process(target = record)
        p1.start()
    def p2():
        p2= Process(target = record2)
        p2.start()
    def p3():
        p3= Process(target = intruder)
        p3.start()
    def p4():
        p4= Process(target = intruder2)
        p4.start()
        

###################### Main Menu Window ############################################


IMAGE_PATH = 'bkg2.jpg'
WIDTH, HEIGHT = 720, 360

window = tk.Tk()
window.title("AI SURVEILLANCE SYSTEM (AISS)")
window.iconphoto(False, tk.PhotoImage(file='taskbaricon.png'))
window.geometry('720x360')
#window.geometry('{}x{}'.format(WIDTH, HEIGHT))


img = ImageTk.PhotoImage(Image.open(IMAGE_PATH).resize((WIDTH, HEIGHT), Image.ANTIALIAS))
lbl = tk.Label(window, image=img)
lbl.img = img  # Keep a reference in case this code put is in a function.
lbl.place(relx=0.5, rely=0.5, anchor='center')

def on_enter (e):
    btn1['background']='#ffffff'
    btn1['foreground']='#2e3192'

def on_leave(e):
    btn1['background']='#2e3192'
    btn1['foreground']='#FFFFFF'

def on_enter (e):
    btn2['background']='#ffffff'
    btn2['foreground']='#2e3192'

def on_leave(e):
    btn2['background']='#2e3192'
    btn2['foreground']='#FFFFFF'

def on_enter (e):
    btn3['background']='#ffffff'
    btn3['foreground']='#2e3192'

def on_leave(e):
    btn3['background']='#2e3192'
    btn3['foreground']='#FFFFFF'

def on_enter (e):
    btn4['background']='#ffffff'
    btn4['foreground']='#2e3192'

def on_leave(e):
    btn4['background']='#2e3192'
    btn4['foreground']='#FFFFFF'

def on_enter (e):
    btn5['background']='#ffffff'
    btn5['foreground']='#2e3192'

def on_leave(e):
    btn5['background']='#2e3192'
    btn5['foreground']='#FF0000'


def on_enter (e):
    btn6['background']='#ffffff'
    btn6['foreground']='#2e3192'

def on_leave(e):
    btn6['background']='#2e3192'
    btn6['foreground']='#FF0000'

myFont = font.Font(size=16)
lblFont = font.Font(size=12)

btn1=Button(window, text="Cam 1",width=4,height=1,fg='#ffffff',border=0,bg='#2e3192',activeforeground="#2e3192",activebackground="#ffffff",command=p1)
btn1['font'] = myFont
btn1.bind("<Enter>", on_enter)
btn1.bind("<Leave>", on_leave)
btn1.place(x=250,y=76)

btn2=Button(window, text="Cam 1",width=4,height=1,fg='#ffffff',border=0,bg='#2e3192',activeforeground="#2e3192",activebackground="#ffffff",command=p3)
btn2['font'] = myFont
btn2.bind("<Enter>", on_enter)
btn2.bind("<Leave>", on_leave)
btn2.place(x=250,y=161)

btn3=Button(window, text="Cam 2",width=4,height=1,fg='#ffffff',border=0,bg='#2e3192',activeforeground="#2e3192",activebackground="#ffffff",command=p2)
btn3['font'] = myFont
btn3.bind("<Enter>", on_enter)
btn3.bind("<Leave>", on_leave)
btn3.place(x=350,y=76)

btn4=Button(window, text="Cam 2",width=4,height=1,fg='#ffffff',border=0,bg='#2e3192',activeforeground="#2e3192",activebackground="#ffffff",command =p4)
btn4['font'] = myFont
btn4.bind("<Enter>", on_enter)
btn4.bind("<Leave>", on_leave)
btn4.place(x=350,y=161)

btn5=Button(window, text="EXIT",width=4,height=1,fg='#ffffff',border=0,bg='#2e3192',activeforeground="#ffffff",activebackground="#ff0000",command=window.quit)
btn5['font'] = myFont
btn5.bind("<Enter>", on_enter)
btn5.bind("<Leave>", on_leave)
btn5.place(x=320,y=315)

btn6=Button(window,width=28,height=2,fg='#ffffff',border=0,bg='#2e3192',activeforeground="#ffffff",activebackground="#ff0000",command=window.quit)
btn6['font'] = myFont

## Buttons to open folders

btn7=Button(window, text="Footage",width=11,height=1,fg='#ffffff',border=0,bg='#3DDC84',activeforeground="#3DDC84",activebackground="#ffffff",command =footage)
btn7['font'] = myFont
btn7.bind("<Enter>", on_enter)
btn7.bind("<Leave>", on_leave)
btn7.place(x=250,y=245)

btn8=Button(window, text="Intrusions",width=11,height=1,fg='#ffffff',border=0,bg='#3DDC84',activeforeground="#3DDC84",activebackground="#ffffff",command =intrusions)
btn8['font'] = myFont
btn8.bind("<Enter>", on_enter)
btn8.bind("<Leave>", on_leave)
btn8.place(x=473,y=245)

#window.pack()
window.mainloop()
