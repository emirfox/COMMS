# Emir Ersanli S2221285

from socket import socket, AF_INET, SOCK_DGRAM  # Import necessary components for UDP socket programming
import sys  # For accessing command-line arguments
import os  # For executing system commands

class Sender:
    def __init__(self, destination_host, destination_port, file_path):
        # Initialize the Sender with destination details and file path
        self.destination = (destination_host, int(destination_port))  # Destination address and port
        self.file_path = file_path  # File to send
        self.sock = socket(AF_INET, SOCK_DGRAM)  # Create a UDP socket
        self.packet_size = 1024  # Define the size of data in each packet

    def transmit_file(self):
        # Method to read the file and send it in packets
        with open(self.file_path, 'rb') as file:
            file_data = file.read()  # Read the entire file
            # Calculate total number of packets needed
            total_packets = len(file_data) // self.packet_size + (1 if len(file_data) % self.packet_size else 0)

            for i in range(total_packets):
                # For each packet, prepare and send it
                start = i * self.packet_size
                end = start + self.packet_size
                eof_flag = 1 if i == total_packets - 1 else 0  # Set EOF flag for the last packet
                # Prepare the packet header with sequence number and EOF flag
                header = i.to_bytes(2, byteorder='big') + eof_flag.to_bytes(1, byteorder='big')
                packet = header + file_data[start:end]  # Combine header with data slice
                self.sock.sendto(packet, self.destination)  # Send the packet
                os.system("sleep 0.01")  # Simulate propagation delay

        self.sock.close()  # Close the socket after sending all packets

if __name__ == '__main__':
    # Main entry point for the script
    if len(sys.argv) != 4:
        # Ensure correct command-line arguments are provided
        print("Usage: python3 Sender1.py <RemoteHost> <Port> <Filename>")
        sys.exit(1)  # Exit if arguments are incorrect
    sender = Sender(sys.argv[1], sys.argv[2], sys.argv[3])
    sender.transmit_file()  # Start file transmission





    
