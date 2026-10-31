import cv2

def list_cameras(max_tested=10):
    available_cameras = []
    for i in range(max_tested):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # 尝试打开摄像头
        if cap.isOpened():  # 检查摄像头是否成功打开
            available_cameras.append(i)
            cap.release()  # 释放摄像头
        else:
            break  # 如果一个摄像头索引打不开，假设后面的都不可用
    return available_cameras

def capture_image(camera_index=0):
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print(f"Cannot open camera {camera_index}")
        return None

    ret, frame = cap.read()  # 读取一帧图像
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        return None
    cap.release()  # 释放摄像头
    return frame

# 列出所有摄像头
cameras = list_cameras()
print("Available cameras:", cameras)

# 如果有可用摄像头，从第一个摄像头获取截图
if cameras:
    frame = capture_image(cameras[0])
    if frame is not None:
        cv2.imshow('Capture', frame)
        cv2.waitKey(0)  # 等待按键
        cv2.destroyAllWindows()
