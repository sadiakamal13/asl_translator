import cv2, mediapipe as mp, numpy as np, json, sys, time, math, base64
from collections import deque, Counter

mp_hands = mp.solutions.hands
mp_face  = mp.solutions.face_mesh

hands_model = mp_hands.Hands(static_image_mode=False, max_num_hands=2,
    min_detection_confidence=0.3, min_tracking_confidence=0.3)
face_model = mp_face.FaceMesh(static_image_mode=False, max_num_faces=1,
    refine_landmarks=True, min_detection_confidence=0.3, min_tracking_confidence=0.3)

history = deque(maxlen=5)

T4,I8,M12,R16,P20 = 4,8,12,16,20
T3,I6,M10,R14,P18 = 3,6,10,14,18
LB=[70,63,105,66,107]; RB=[300,293,334,296,336]
LE=[33,160,158,133,153,144]; RE=[362,385,387,263,373,380]
UL=[13,312,311,310,415,308]; LL=[14,317,402,318,324,78]
ML,MR,NT,LC,RC,CH = 61,291,1,234,454,152

def emit(d):
    sys.stdout.write(json.dumps(d)+"\n")
    sys.stdout.flush()

def classify(lm, label):
    t = (lm[T4].x < lm[T3].x) if label=="Right" else (lm[T4].x > lm[T3].x)
    i = lm[I8].y  < lm[I6].y
    m = lm[M12].y < lm[M10].y
    r = lm[R16].y < lm[R14].y
    p = lm[P20].y < lm[P18].y
    f=[int(t),int(i),int(m),int(r),int(p)]; c=sum(f)
    sp=abs(lm[I8].x-lm[M12].x)>0.05
    if f==[0,0,0,0,0]: return "FIST"
    if f==[1,1,1,1,1]: return "5"
    if f==[0,1,1,1,1]: return "B"
    if f==[0,1,0,0,0]: return "1"
    if f==[0,1,1,0,0]: return "V" if sp else "2"
    if f==[0,1,1,1,0]: return "3"
    if f==[0,1,1,1,1]: return "4"
    if f==[1,0,0,0,1]: return "ILY"
    if f==[1,0,0,0,0]: return "A"
    if f==[0,0,0,0,1]: return "I"
    if f==[1,1,0,0,0]: return "L"
    return f"SIGN{c}"

def face_analysis(flm):
    lm=flm.landmark; ex=[]; mo=[]
    try:
        lb=np.mean([lm[i].y for i in LB]); rb=np.mean([lm[i].y for i in RB])
        le=np.mean([lm[i].y for i in LE]); re=np.mean([lm[i].y for i in RE])
        if (le-lb)>0.030 and (re-rb)>0.030: ex.append("raised_eyebrows"); mo.append("yes/no_question")
        elif (le-lb)<0.022 and (re-rb)<0.022: ex.append("furrowed_brows"); mo.append("wh_question")
        ul=np.mean([lm[i].y for i in UL]); ll=np.mean([lm[i].y for i in LL])
        if ll-ul>0.020: ex.append("mouth_open")
        mw=abs(lm[MR].x-lm[ML].x); fw=abs(lm[LC].x-lm[RC].x)
        if fw>0 and mw/fw>0.40: ex.append("smile"); mo.append("positive_sentiment")
    except: pass
    return {"expressions":ex,"grammatical_modifiers":mo}

def smooth(g):
    history.append(g)
    return Counter(history).most_common(1)[0][0]

def run():
    cap=None
    for idx in [0,1,2]:
        try:
            c=cv2.VideoCapture(idx)
            if c.isOpened(): cap=c; break
            c.release()
        except: pass
    if cap is None:
        for idx in [0,1,2]:
            c=cv2.VideoCapture(idx)
            if c.isOpened(): cap=c; break
            c.release()
    if cap is None:
        emit({"type":"error","message":"No camera found"}); sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    emit({"type":"status","message":"Camera opened"})

    prev=None; seq=[]; last_t=time.time(); fn=0

    while True:
        ok,frame=cap.read()
        if not ok: time.sleep(0.03); continue
        fn+=1
        frame=cv2.flip(frame,1)
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        hr=hands_model.process(rgb)
        fr=face_model.process(rgb)

        hands_out=[]; face_out={"expressions":[],"grammatical_modifiers":[]}
        if hr.multi_hand_landmarks:
            for hlm,hi in zip(hr.multi_hand_landmarks,hr.multi_handedness):
                g=smooth(classify(hlm.landmark,hi.classification[0].label))
                hands_out.append({"hand":hi.classification[0].label,"gesture":g})
        if fr.multi_face_landmarks:
            face_out=face_analysis(fr.multi_face_landmarks[0])

        # Send frame image every 4th frame
        if fn%4==0:
            try:
                small=cv2.resize(frame,(320,240))
                _,buf=cv2.imencode(".jpg",small,[cv2.IMWRITE_JPEG_QUALITY,50])
                b64=base64.b64encode(buf.tobytes()).decode("ascii")
                emit({"type":"frame","hands":hands_out,"face":face_out,"image":b64})
            except:
                emit({"type":"frame","hands":hands_out,"face":face_out})
        elif fn%2==0:
            emit({"type":"frame","hands":hands_out,"face":face_out})

        cur=hands_out[0]["gesture"] if hands_out else None
        if cur and cur!=prev:
            seq.append({"sign":cur,"expressions":face_out["expressions"],
                        "modifiers":face_out["grammatical_modifiers"],"time":time.time()})
            last_t=time.time(); prev=cur
            emit({"type":"sign_added","sign":cur,"face":face_out,"sequence":seq})
        if seq and (time.time()-last_t)>2.0:
            emit({"type":"translate_request","sequence":seq})
            seq=[]; prev=None
        if not cur: prev=None

if __name__=="__main__":
    run()