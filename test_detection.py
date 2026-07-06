import cv2
import mediapipe as mp
import numpy as np

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.3, min_tracking_confidence=0.3)

cap = cv2.VideoCapture(0)
print("Camera opened:", cap.isOpened())

for i in range(150):
    ret, frame = cap.read()
    if not ret:
        print(f"Frame {i}: could not read")
        continue

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    brightness = int(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:,:,2]))

    if results.multi_hand_landmarks:
        print(f"Frame {i}: *** HAND DETECTED! *** Brightness={brightness}")
    else:
        if i % 15 == 0:
            print(f"Frame {i}: no hand detected. Brightness={brightness}")

cap.release()
print("Done - if no HAND DETECTED printed, see tips below")
print("Tips: improve lighting, hold hand closer, use plain background")
