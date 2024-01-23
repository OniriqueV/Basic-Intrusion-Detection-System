import cv2
from cvzone.PoseModule import PoseDetector
from fbchat import Client
from fbchat.models import *
import requests
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import fbchat
import logging

class MyClient(Client):
    def onMessage(self, mid, author_id, message_object, thread_id, thread_type, **kwargs):
        # Xử lý tin nhắn đến
        self.markAsDelivered(thread_id, mid)  # Đánh dấu tin nhắn đã được giao đến server
        self.markAsRead(thread_id)  # Đánh dấu tina nhắn đã được đọc

def capture_and_save_image():
    cap = cv2.VideoCapture(0)  # Khởi tạo webcam
    
    # Chờ vài giây hoặc vài frame để ổn định hình ảnh từ webcam
    time.sleep(2)  # Chờ 2 giây
    
    ret, frame = cap.read()  # Chụp một frame từ webcam
    cap.release()  # Đóng webcam sau khi chụp ảnh
    if ret:
        image_filename = "captured_image.jpg"
        cv2.imwrite(image_filename, frame)  # Lưu ảnh
        print("Captured image saved.")
        return image_filename  # Trả về tên file ảnh đã chụp
    else:
        print("Failed to capture image.")
        return None

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org')
        public_ip = response.text
        return public_ip
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_geolocation(ip_address):
    try:
        response = requests.get(f'https://ipinfo.io/{ip_address}/json')
        geolocation_data = response.json()
        return geolocation_data
    except Exception as e:
        print(f"Error: {e}")
        return None

# Đọc ảnh mẫu
reference_image = cv2.imread("your_image.jpg")

# Khởi tạo PoseDetector từ thư viện cvzone
detector = PoseDetector()

# Khởi tạo webcam
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

# Ngưỡng độ tương đồng để xác định sự giống nhau giữa hình ảnh từ webcam và ảnh mẫu
threshold = 0.8

# Số frame tối đa để xử lý
max_frames = 100

# Biến đếm số frame đã xử lý
frame_count = 0

#Chụp ảnh và lưu lại
image_filename = capture_and_save_image()

# Tạo đối tượng MyClient để gửi tin nhắn và ảnh
client = MyClient("tên đăng nhập", "mật khẩu")

# Kiểm tra xem ảnh đã được chụp thành công hay không
if image_filename:
    # Gửi ảnh qua Messenger
    client.sendLocalImage(
        image_path=image_filename,
        thread_id="ví dụ id:100012973474754", #tìm id người nhận : vào trang https://lookup-id.com/ nhập url trang cá nhân fb người nhận
        thread_type=ThreadType.USER
    )
else:
    print("Failed to capture and send image.")


# Danh sách chứa các Similarity Score
similarity_scores = []

while frame_count < max_frames:
    # Đọc frame từ webcam
    success, img = cap.read()
    
    # Tìm kiếm vị trí và pose trong frame
    img = detector.findPose(img)
    imlist, bbox = detector.findPosition(img)

    if len(imlist) > 0:
        print("Human Detect")

        # Chuyển đổi hình ảnh từ webcam thành grayscale để so sánh
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Chuyển đổi ảnh mẫu thành grayscale để so sánh
        gray_reference = cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY)

        # Tính toán độ tương đồng giữa hai hình ảnh
        similarity_score = cv2.matchTemplate(gray_img, gray_reference, cv2.TM_CCOEFF_NORMED)[0][0]

        # Thêm similarity_score vào danh sách
        similarity_scores.append(similarity_score)

        frame_count += 1

    cv2.imshow("Output", img)
    q = cv2.waitKey(1)
    if q == ord('q'):
        break

# Tính trung bình Similarity Score
average_similarity = sum(similarity_scores) / len(similarity_scores)

# Hiển thị kết quả
if average_similarity > threshold:
    print(f"Trung bình Similarity Score: {average_similarity}")
    print("Chào mừng bạn trở lại!")
else:
    print(f"Trung bình Similarity Score: {average_similarity}")
    print("Có người lạ xâm nhập!")

# Đóng webcam và cửa sổ hiển thị video
cap.release()
cv2.destroyAllWindows()

# Lấy địa chỉ IP công cộng và thông tin vị trí nếu có
public_ip = get_public_ip()
geolocation_data = get_geolocation(public_ip)

# Xử lý thông báo dựa trên Similarity Score
if average_similarity > threshold:
    client.send(Message(text="Chào mừng bạn trở lại !"), thread_id="id_who_take_mes", thread_type=ThreadType.USER)
else:
    # Chuyển đổi dữ liệu vị trí thành định dạng JSON
    geolocation_json = json.dumps(geolocation_data, indent=4)
    # Gửi thông báo với thông tin vị trí qua Messenger
    try:
        client.send(Message(text="Có người lạ xâm nhập!\n"+"Địa chỉ IP công cộng của bạn là: "+public_ip+"\nThông tin vị trí: "+geolocation_json), thread_id="100012973474754", thread_type=ThreadType.USER)
        print("Gửi tin nhắn thành công")
    except fbchat._exception.FBchatUserError as e:
        print(f"Error: {e}")

# Khởi tạo đối tượng xử lý sự kiện để theo dõi sự thay đổi trong thư mục
class CustomHandler(FileSystemEventHandler):
    def __init__(self, messenger_client):
        super().__init__()
        self.messenger_client = messenger_client

    def on_modified(self, event):
        if event.is_directory:
            # Xử lý sự kiện thay đổi thư mục
            message = f'Thư mục (file) {event.src_path} vừa bị truy cập.'
            print(message)
            # Gửi thông báo đến Messenger
            self.messenger_client.send(fbchat.models.Message(text=message), thread_id="100012973474754", thread_type=fbchat.models.ThreadType.USER)

if __name__ == "__main__":
    # Thiết lập logging và đường dẫn thư mục để theo dõi
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = 'D:\\' # đường dẫn thư mục muốn theo dõi , ví dụ :  D:\\Python or D:\\ or C:\\User\\Appdata
    
    # Khởi tạo đối tượng MessengerClient
    client = Client('ten đăng nhập', 'mật khẩu')
    
    # Khởi tạo đối tượng xử lý sự kiện để theo dõi sự thay đổi trong thư mục
    custom_handler = CustomHandler(client)
    
    # Khởi tạo và bắt đầu observer để theo dõi sự kiện thay đổi trong thư mục
    observer = Observer()
    observer.schedule(custom_handler, path, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
    # Đăng xuất khỏi tài khoản Messenger
    client.logout()
