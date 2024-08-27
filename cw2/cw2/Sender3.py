# Emir Ersanli S2221285
import socket
import sys
import math
import time
import select

# Initialize socket setup and file transfer parameters from command-line arguments
destination_IP = sys.argv[1]
destination_PORT = int(sys.argv[2])
file_name = sys.argv[3]
timeout = int(sys.argv[4])  # Timeout duration in milliseconds
window_size = int(sys.argv[5])

# Function to send a single packet
def send_packet(sequence_number, last_sequence_number, last_packet_size, data, socket_obj):
    """
    Prepares and sends a packet of data using the provided UDP socket.
    Adjusts packet size for the final packet and handles EOF flag.
    """
    EOF = 1 if sequence_number == last_sequence_number else 0
    packet_size = 1024 if EOF == 0 else last_packet_size
    start_index = sequence_number * 1024
    packet_data = data[start_index:start_index+packet_size]
    
    # Construct packet with header and payload
    packet_header = bytearray(sequence_number.to_bytes(2, 'big')) + bytearray([EOF])
    packet = packet_header + packet_data
    
    # Send the packet, using select for non-blocking sockets
    try:
        socket_obj.sendto(packet, (destination_IP, destination_PORT))
    except socket.error:
        select.select([], [socket_obj], [])

# Function to receive ACKs
def receive_ack(expected_sequence_number, socket_obj):
    """
    Waits for an ACK for the specified sequence number.
    Implements timeout and retransmission based on socket timeout.
    """
    while True:
        try:
            socket_obj.settimeout(timeout / 1000)  # Convert milliseconds to seconds
            ack_data, _ = socket_obj.recvfrom(2)
            ack_sequence_number = int.from_bytes(ack_data[:2], 'big')
            
            if expected_sequence_number < ack_sequence_number:
                return ack_sequence_number
        except socket.timeout:
            # On timeout, return the current expected sequence number to trigger retransmission
            return expected_sequence_number

# Setup UDP socket
socket_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_obj.setblocking(False)  # Set socket to non-blocking mode

# Read file data
with open(file_name, 'rb') as file:
    data = bytearray(file.read())

# Calculate transmission parameters
total_packets = math.ceil(len(data) / 1024)
last_packet_size = len(data) % 1024 if len(data) % 1024 != 0 else 1024

# Initialize control variables
base = -1
sequence_number = 0
file_sent = False
retransmissions = 0
start_time = time.perf_counter()

try:
    while not file_sent:
        # Send packets within the window
        while sequence_number - base <= window_size and sequence_number < total_packets:
            send_packet(sequence_number, total_packets - 1, last_packet_size, data, socket_obj)
            sequence_number += 1
        
        # Receive ACKs and handle timeouts
        try:
            new_base = receive_ack(base, socket_obj)
            if new_base == base:  # Timeout occurred, prepare for retransmission
                sequence_number = base + 1
                retransmissions += 1
            else:
                base = new_base
            
            if base >= total_packets - 1:  # Last packet acknowledged
                file_sent = True
        except socket.error as e:
            print(f"Socket error: {e}")
            break  # Exit the loop on socket error
except socket.error as exc:
    print(f"Caught socket.error: {exc}")

# Calculate and print transmission metrics
end_time = time.perf_counter()
transmission_time = end_time - start_time
data_kb = len(data) / 1024
transmission_rate = data_kb / transmission_time
print(f" {transmission_rate:.2f} ")

socket_obj.close()
