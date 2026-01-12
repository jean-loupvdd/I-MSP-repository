import threading
from vimba import Vimba
from threading import Thread
import time
import queue

class CameraLive:
    def __init__(self):
        self.streaming = False
        self.latest_frame = None
        self.thread = None
        self.cam = None
        self.camera_found = False
        self.lock = threading.Lock()
        self.last_error = None  # alleen voor debug / status

    def start_live(self):
        """Start live camera stream (stil, geen fout-popups)."""
        if self.streaming:
            return
        self.streaming = True
        self.thread = Thread(target=self._live_thread, daemon=True)
        self.thread.start()

    def _live_thread(self):
        frame_queue = queue.Queue(maxsize=10)

        try:
            with Vimba.get_instance() as vimba:
                cams = vimba.get_all_cameras()
                if not cams:
                    raise RuntimeError("Geen camera gevonden!")

                with cams[0] as cam:
                    self.cam = cam
                    cam.get_feature_by_name("PixelFormat").set("Mono8")
                    cam.get_feature_by_name("Gain").set(0)
                    cam.get_feature_by_name("ExposureAuto").set("Continuous")
                    self.camera_found = True

                    def handler(camera, frame):
                        try:
                            if frame.get_status() != 0:
                                camera.queue_frame(frame)
                                return

                            img = frame.as_numpy_ndarray().copy()

                            try:
                                frame_queue.put_nowait(img)
                            except queue.Full:
                                frame_queue.get_nowait()
                                frame_queue.put_nowait(img)

                            camera.queue_frame(frame)

                        except Exception:
                            camera.queue_frame(frame)

                    cam.start_streaming(handler=handler, buffer_count=10)
                    self.streaming = True

                    while self.streaming:
                        if not frame_queue.empty():
                            frame = frame_queue.get_nowait()
                            with self.lock:
                                self.latest_frame = frame
                        else:
                            time.sleep(0.01)

        except Exception as e:
            self.last_error = str(e)
            self.camera_found = False

        finally:
            self.streaming = False
            self.cam = None
            self.camera_found = False

    def get_latest_frame(self):
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def stop_live(self):
        if not self.streaming:
            return

        self.streaming = False

        try:
            if self.cam is not None:
                self.cam.stop_streaming()
        except:
            pass

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

        self.cam = None
        self.camera_found = False
