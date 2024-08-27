# Emir Ersanli S2221285

from socket import *  # Imports necessary functions and constants for socket programming
import sys  # For accessing command-line arguments

class Receiver:
    def __init__(self, port, file_to_save):
        # Initialize the Receiver with a port and a file name to save received data
        self.UDP_PORT = int(port)  # Convert port number to integer
        self.file_to_save = file_to_save  # File path to save received data
        self.receiver_socket = socket(AF_INET, SOCK_DGRAM)  # Create a UDP socket
        self.receiver_socket.bind(('', self.UDP_PORT))  # Bind socket to the given port on all interfaces
        self.data_received = bytearray()  # Initialize a bytearray to accumulate received data

    def receive(self):
        while True:
            # Continuously receive packets of size 1027 bytes
            packet, _ = self.receiver_socket.recvfrom(1027)
            sequence_number = packet[:2]  # The first 2 bytes represent the sequence number
            EOF = packet[2]  # The third byte is the EOF flag
            data = packet[3:]  # The rest of the packet is the actual data
            self.data_received.extend(data)  # Append data to the accumulator
            if EOF == 1:  # If EOF flag is set, break the loop
                break
        # Write the accumulated data to a file
        with open(self.file_to_save, 'wb') as file:
            file.write(self.data_received)
        self.receiver_socket.close()  # Close the socket

if __name__ == '__main__':
    # Ensure that two arguments are passed (port number and file to save)
    if len(sys.argv) != 3:
        print("Usage: python3 Receiver1.py <Port> <Filename>")
        sys.exit(1)
    receiver = Receiver(sys.argv[1], sys.argv[2])
    receiver.receive()  # Start receiving data



    
