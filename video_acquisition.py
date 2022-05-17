# importing libraries
import socket
import pickle
import struct
import json
import cv2
import numpy as np
import zmq


def main():
    json_data = json.load(open('rcrop_parameters.json'))

    alpha = json_data["alpha"]
    ox = json_data["ox"]
    oy = json_data["oy"]
    h = json_data["height"]
    w = json_data["width"]

    # Server socket
    # create an INET, STREAMing socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # host_name = socket.gethostname()
    # host_ip = socket.gethostbyname(host_name)

    host_ip = '0.0.0.0'

    print('HOST IP:', host_ip)

    port = 10050
    socket_address = (host_ip, port)

    print('Socket created')
    # bind the socket to the host.
    # The values passed to bind() depend on the address family of the socket
    server_socket.bind(socket_address)
    print('Socket bind complete')
    # listen() enables a server to accept() connections
    # listen() has a backlog parameter.
    # It specifies the number of unaccepted connections that the system will allow before refusing new connections.
    server_socket.listen(5)
    print('Socket now listening')

    while True:
        client_socket, addr = server_socket.accept()
        print('Connection from:', addr)
        if client_socket:
            vid = cv2.VideoCapture(0)
            # set new dimensionns to cam object (not cap)
            while(vid.isOpened()):
                img, frame = vid.read()

                a = pickle.dumps(frame)

                message = struct.pack("Q", len(a))+a

                try:
                    client_socket.sendall(message)
                except:
                    break

                rect = ((ox*frame.shape[1], oy*frame.shape[0]),
                        (w*frame.shape[1], h*frame.shape[0]), 360-alpha)

                box = cv2.boxPoints(rect)
                box = np.int0(box)

                cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)

                left_index, top_index = np.argmin(box, axis=0)
                right_index, bottom_index = np.argmax(box, axis=0)

                frame = cv2.circle(frame, box[top_index],
                                   radius=0, color=(0, 0, 255), thickness=15)
                frame = cv2.circle(frame, box[bottom_index], radius=0,
                                   color=(0, 255, 0), thickness=15)
                frame = cv2.circle(frame, box[right_index], radius=0,
                                   color=(255, 0, 255), thickness=15)
                frame = cv2.circle(frame, box[left_index], radius=0,
                                   color=(255, 0, 0), thickness=15)

                cv2.imshow('Sending...', frame)

                key = cv2.waitKey(10)
                if key == 27:
                    client_socket.close()


def main_zmq():
    # get configuration data
    json_data = json.load(open('rcrop_parameters.json'))

    alpha = json_data["alpha"]
    ox = json_data["ox"]
    oy = json_data["oy"]
    h = json_data["height"]
    w = json_data["width"]

    # create a zmq context that can create sockets
    context = zmq.Context()
    # create a socket of type PUB
    footage_socket = context.socket(zmq.PUB)
    # connect the socket to the localhost on port 10050
    host_ip = 'localhost'
    port = 10050
    footage_socket.connect('tcp://' + str(host_ip) + ":" + str(port))

    # create the camera object
    camera = cv2.VideoCapture(0)

    while True:
        try:
            # grab the current frame
            (_, frame) = camera.read()
            # encode the image to jpg
            _, buffer = cv2.imencode('.jpg', frame)
            # serialize the jpg to pickle obj
            buffer = pickle.dumps(buffer)

            # send the encoded pickled object on socket
            try:
                footage_socket.send_pyobj(buffer)
            except:
                break

            cv2.imshow("Sending...", frame)

        except KeyboardInterrupt:
            footage_socket.close()
            camera.release()
            cv2.destroyAllWindows()
            break


if __name__ == "__main__":
    # main()
    main_zmq()
