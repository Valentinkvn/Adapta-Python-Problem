import socket
import pickle
import struct
import json
import cv2
import numpy as np


def crop_video(image, w, h, border_points, image_tilt):
    '''
        Crop the image considering the following parameters:
        - w: the width of the crop taken from the json file
        - h: the height of the crop taken from the json file
        - border_points: a dictionary which contains the position 
                        of the four corners of the crop
        - image_tilt: which says if the image is tilted "left" or "right"

        The function returns the cropped image
    '''

    # define the source points for the perspective transform
    src_pts = np.array([border_points["bottom_point"],
                        border_points["left_point"],
                        border_points["top_point"],
                        border_points["right_point"]]).astype("float32")

    dst_pts = None

    # define the order of the warping destination points according to the image tilt
    if image_tilt == "left":
        dst_pts = np.array([[0, h*image.shape[0]],
                            [0, 0],
                            [w*image.shape[1], 0],
                            [w*image.shape[1], h*image.shape[0]]], dtype="float32")

    elif image_tilt == "right":
        dst_pts = np.array([[w*image.shape[1], h*image.shape[0]],
                            [0, h*image.shape[0]],
                            [0, 0],
                            [w*image.shape[1], 0]], dtype="float32")

    # compute the perspective transform matrix
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # directly warp the rotated rectangle to get the straightened rectangle
    warped = cv2.warpPerspective(
        image, M, (int(w*image.shape[1]), int(h*image.shape[0])))

    return warped


def find_border_points(json_obj, image_shape, image_tilt):
    '''
        Find the cropping points inside the boundaries of the image.
        The function takes the following parameters:
        - json_obj: the json file containing the crop configuration
        - image_shape: the size of the image
        - image_tilt: which says if the image is tilted "left" or "right"

        The function returns a dictionary with the following keys:
        - ["left_point"]
        - ["top_point"]
        - ["right_point"] 
        - ["bottom_point"]
    '''

    # find the box object using the boxPoints openCV's function
    rect = ((json_obj["ox"]*image_shape[1], json_obj["oy"]*image_shape[0]),
            (json_obj["width"]*image_shape[1], json_obj["height"]*image_shape[0]), 360-json_obj["alpha"])

    box = cv2.boxPoints(rect)
    box = np.int0(box)

    # find the corners of the crop
    left_index, top_index = np.argmin(box, axis=0)
    right_index, bottom_index = np.argmax(box, axis=0)

    # check if the crop is out of bounds of the image in any direction
    if box[top_index][1] < 0:
        # check whether the crop outbound the top of the image
        print("A iesit in sus")
        # correct the outbounded point and its neighbour
        changing_ratio = box[top_index][1] / image_shape[0]
        box[top_index][1] = 0
        if image_tilt == "left":
            box[right_index][1] += abs(changing_ratio) * image_shape[0]
        if image_tilt == "right":
            box[left_index][1] += abs(changing_ratio) * image_shape[0]

    if box[bottom_index][1] > image_shape[0]:
        # check whether the crop outbound the bottom of the image
        print("A iesit in jos")
        # correct the outbounded point and its neighbour
        changing_ratio = box[bottom_index][1] / image_shape[0] - 1
        box[bottom_index][1] = image_shape[0]
        if image_tilt == "right":
            box[left_index][1] -= abs(changing_ratio) * image_shape[0]
        if image_tilt == "left":
            box[right_index][1] -= abs(changing_ratio) * image_shape[0]

    if box[left_index][0] < 0:
        # check whether the crop outbound the left side of the image
        print("A iesit in stanga")
        # correct the outbounded point and its neighbour
        changing_ratio = box[left_index][0] / image_shape[1]
        box[left_index][0] = 0
        if image_tilt == "left":
            box[top_index][0] += abs(changing_ratio) * image_shape[1]
        if image_tilt == "right":
            box[bottom_index][0] += abs(changing_ratio) * image_shape[1]

    if box[right_index][0] > image_shape[1]:
        # check whether the crop outbound the right side of the image
        print("A iesit in dreapta")
        # correct the outbounded point and its neighbour
        changing_ratio = box[right_index][0]/image_shape[1] - 1
        box[right_index][0] = image_shape[1]
        if image_tilt == "right":
            box[bottom_index][0] -= abs(changing_ratio) * image_shape[1]
        if image_tilt == "left":
            box[top_index][0] -= abs(changing_ratio) * image_shape[1]

    border_points = dict()

    border_points["left_point"] = box[left_index]
    border_points["top_point"] = box[top_index]
    border_points["right_point"] = box[right_index]
    border_points["bottom_point"] = box[bottom_index]

    return border_points


def find_image_tilt(json_obj, image_shape):
    '''
        Find the cropping points inside the boundaries of the image.
        The function takes the following parameters:
        - json_obj: the json file containing the crop configuration
        - image_shape: the size of the image

        The function returns whether the image is tilted "left" or "right"
    '''
    rect = ((json_obj["ox"]*image_shape[1], json_obj["oy"]*image_shape[0]),
            (json_obj["width"]*image_shape[1], json_obj["height"]*image_shape[0]), 360-json_obj["alpha"])

    box = cv2.boxPoints(rect)
    box = np.int0(box)

    left_index, _ = np.argmin(box, axis=0)

    if left_index == 1 or left_index == 3:
        return "left"
    elif left_index == 2 or left_index == 0:
        return "right"


def main():
    img_shape = []
    img_tilt = ""
    initialization_passed = False
    border_points = dict()

    json_data = json.load(open('rcrop_parameters.json'))

    # Client socket
    # create an INET, STREAMing socket :
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Standard loopback interface address (localhost)
    host_ip = '192.168.136.1'
    port = 10050  # Port to listen on (non-privileged ports are > 1023)

    # now connect to the web server on the specified port number
    client_socket.connect((host_ip, port))
    # 'b' or 'B'produces an instance of the bytes type instead of the str type
    # used in handling binary data from network connections
    data = b""
    # Q: unsigned long long integer(8 bytes)
    payload_size = struct.calcsize("Q")

    while True:
        while len(data) < payload_size:
            packet = client_socket.recv(4*1024)
            if not packet:
                break
            data += packet

        packed_msg_size = data[:payload_size]

        data = data[payload_size:]

        msg_size = struct.unpack("Q", packed_msg_size)[0]

        while len(data) < msg_size:
            data += client_socket.recv(4*1024)

        frame_data = data[:msg_size]
        data = data[msg_size:]
        # unpack the frame
        frame = pickle.loads(frame_data)

        # in the initialization phase the image dimensions are stored,
        # the tilt of the image and the crop is corrected if it is outbounded
        if initialization_passed == False:
            img_shape = frame.shape
            img_tilt = find_image_tilt(json_data, img_shape)
            border_points = find_border_points(json_data, img_shape, img_tilt)
            initialization_passed = True

        # crop the image according to the border_point and the image tilt
        image = crop_video(frame, json_data["width"],
                           json_data["height"], border_points, img_tilt)

        cv2.imshow("Receiving...", image)
        key = cv2.waitKey(10)
        if key == 27:
            break

    client_socket.close()


if __name__ == "__main__":
    main()
