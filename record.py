import cv2
from datetime import datetime

def record():
    #cap = cv2.VideoCapture('http://192.168.1.107:8080/video')
    cap = cv2.VideoCapture(1)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(f'recordings/{datetime.now().strftime("%H-%M-%S")}.avi', fourcc,20.0,(640,480))

    while True:
        _, frame = cap.read()


        cv2.putText(frame, "A I S S | ", (20,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "O N", (100,20), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (0,0,255), 1)
        cv2.putText(frame, f'{datetime.now().strftime("%d %B %Y")}', (20,450), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.rectangle(frame, (290, 430), (380,460), (122, 63, 24), -1)

        cv2.putText(frame, f'{datetime.now().strftime("%H:%M:%S")}', (300,450), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)
        cv2.putText(frame, "Room 1", (20,470), cv2.FONT_HERSHEY_DUPLEX,
                        0.5, (255,255,255), 1)

        out.write(frame)
        

        cv2.imshow("Press Esc. to Stop", frame)

        if cv2.waitKey(1) == 27:
            cap.release()
            cv2.destroyAllWindows()
            break 
