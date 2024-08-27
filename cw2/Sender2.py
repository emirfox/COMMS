# Emir Ersanli S2221285
import socket
import sys
import math
import time

# Collect command-line arguments for network configuration and file details
destination_IP = sys.argv[1]
destination_PORT = int(sys.argv[2])
file_name = sys.argv[3]
timeout = int(sys.argv[4])  # Timeout duration for ACK waiting, in milliseconds

# Setup the UDP socket for data transmission
socket_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def read_file_to_bytearray(filepath):
    """
    Opens and reads the contents of the specified file,
    returning a bytearray of the file's contents.
    """
    with open(filepath, 'rb') as file:
        file_data = file.read()
    return bytearray(file_data)

# Reading the specified file into a bytearray for transmission
data = read_file_to_bytearray(file_name)

# Calculate the necessary transmission metrics
num_full_packets = math.floor(len(data) / 1024)
final_packet_size = len(data) % 1024

# Initialize transmission control variables
sequence_number = 0
num_retransmissions = 0
start_time = time.perf_counter()

# Main loop for packet preparation and transmission
for packet_index in range(num_full_packets + 1):
    # Determine if this packet is the last packet
    is_final_packet = 1 if packet_index == num_full_packets and final_packet_size != 0 else 0
    
    # Increment the sequence number for each packet
    sequence_number += 1
    
    # Construct the packet with its header and data
    packet_header = bytearray(sequence_number.to_bytes(2, 'big')) + bytearray([is_final_packet])
    packet_data = data[packet_index * 1024: (packet_index + 1) * 1024] if not is_final_packet else data[-final_packet_size:]
    packet = packet_header + packet_data
    
    # Transmit the packet
    socket_obj.sendto(packet, (destination_IP, destination_PORT))
    
    # Initialize ACK reception logic
    correct_ack_received = False
    while not correct_ack_received:
        try:
            socket_obj.settimeout(timeout / 1000)  # Convert milliseconds to seconds for the timeout
            ack_data, _ = socket_obj.recvfrom(2)
            ack_sequence_number = int.from_bytes(ack_data[:2], 'big')
            
            # Verify the ACK is for the current packet
            if ack_sequence_number == sequence_number:
                correct_ack_received = True
            else:
                # If ACK sequence number does not match, prepare for retransmission
                raise ValueError("Received incorrect ACK sequence number.")
        except (socket.timeout, ValueError):
            # Retransmit the packet if ACK was not received correctly
            socket_obj.sendto(packet, (destination_IP, destination_PORT))
            num_retransmissions += 1

# Mark the end of the transmission to calculate metrics
end_time = time.perf_counter()

# Calculate and report transmission metrics
transmission_duration = end_time - start_time
data_kb = len(data) / 1024  # Convert data size to kilobytes
transmission_rate = data_kb / transmission_duration  # KB per second

print(f" {num_retransmissions} {transmission_rate:.2f}")
#print(f"Data sent: {data_kb:.2f} KB")
#print(f"Transmission time: {transmission_duration:.2f} seconds")
#print(f" {transmission_rate:.2f}  ")

# Clean up by closing the socket
socket_obj.close()
