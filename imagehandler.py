import copy
import cv2
from scipy import ndimage
from PIL import Image
import io
import numpy as np


class ImageHandler:
    def __init__(self, battlebots=None):
        self.battlebots = battlebots
        self.battlebots.imagedata = None
        self.current_map = None
        self.map_img = None
        self.battlebots.impossible_positions = None

    def update_map_image(self):
        self.current_map = self.battlebots.map
        self.battlebots.mapfile = 'images/maps/' + self.battlebots.map + '.png'
        self.map_img = cv2.imread(self.battlebots.mapfile)

    def run(self):
        while not self.battlebots.stopthreads:
            if not self.battlebots.map:
                self.battlebots.mapfile = 'images/noconnection.png'
                map_img = cv2.imread(self.battlebots.mapfile)
                self.battlebots.imagedata = self.provide_image_data(map_img)
            else:
                if self.battlebots.received_update:
                    if self.current_map != self.battlebots.map or not self.current_map:
                        self.update_map_image()

                    # Create a copy of the map data
                    map_img = copy.deepcopy(self.map_img)

                    # Add markers
                    map_img_with_markers = self.place_markers(img=map_img)

                    # Make sure we use the full gui
                    final_image = cv2.resize(map_img_with_markers, (1000, 1000), interpolation=cv2.INTER_CUBIC)

                    # save the final image for the gui
                    self.battlebots.imagedata = self.provide_image_data(final_image)

                self.battlebots.received_update = False

    def provide_image_data(self, imgarray):
        """Generate image data using PIL
        """
        img = Image.fromarray(imgarray)

        bio = io.BytesIO()
        img.save(bio, format="PNG")
        del img

        return bio.getvalue()

    def place_markers(self, img):
        """Place markers on the Map
        """
        for o in self.battlebots.clients:
            # Tank Marker

            # Recolor marker
            color = o['color']
            image = 'images/tank.png'

            # Open marker image
            player_marker_plain = Image.open(image)
            player_marker_plain = player_marker_plain.convert('RGBA')

            # change its color
            data = np.array(player_marker_plain)
            red, green, blue, alpha = data.T
            white_areas = (red == 255) & (blue == 255) & (green == 255)
            data[..., :-1][white_areas.T] = color
            colored_marker = Image.fromarray(data)

            # Rotate the marker according to object rotation
            rotated_player_marker = ndimage.rotate(colored_marker, o['pos_angle'])

            img = self.merge_image(img, rotated_player_marker, o['pos_x'], o['pos_y'])

            # Radar Dish
            radar_image = 'images/radar.png'

            # Open marker image
            radar_marker_plain = Image.open(radar_image)

            # Rotate the radar marker according to object rotation
            rotated_radar_marker = ndimage.rotate(radar_marker_plain, o['radar_angle'])

            img = self.merge_image(img, rotated_radar_marker, o['pos_x'], o['pos_y'])

        return img

    def merge_image(self, back, front, x, y):
        # convert to rgba
        if back.shape[2] == 3:
            back = cv2.cvtColor(back, cv2.COLOR_BGR2BGRA)
        if front.shape[2] == 3:
            front = cv2.cvtColor(front, cv2.COLOR_BGR2BGRA)

        # crop the overlay from both images
        bh, bw = back.shape[:2]
        fh, fw = front.shape[:2]
        x1, x2 = max(x, 0), min(x + fw, bw)
        y1, y2 = max(y, 0), min(y + fh, bh)
        front_cropped = front[y1 - y:y2 - y, x1 - x:x2 - x]
        back_cropped = back[y1:y2, x1:x2]

        alpha_front = front_cropped[:, :, 3:4] / 255
        alpha_back = back_cropped[:, :, 3:4] / 255

        # replace an area in result with overlay
        result = back.copy()
        result[y1:y2, x1:x2, :3] = alpha_front * front_cropped[:, :, :3] + (1 - alpha_front) * back_cropped[:, :, :3]
        result[y1:y2, x1:x2, 3:4] = (alpha_front + alpha_back) / (1 + alpha_front * alpha_back) * 255

        return result