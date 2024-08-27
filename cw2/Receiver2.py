#Emir Ersanli S2221285
import socket
import sys

# Function to create and bind a socket
def create_bound_socket(ip, port):
    """Create a UDP socket and bind it to the specified IP and port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    return sock

# Function to write the received data to a file
def write_to_file(filename, data):
    """Write the received bytearray data to a file."""
    with open(filename, 'wb') as file:
        file.write(data)

# Specify localhost and port from command line arguments
local_IP = "127.0.0.1"
local_PORT = int(sys.argv[1])   
# Specify output filename from command line arguments
output_filename = sys.argv[2] 

# Create and bind the socket to localhost and the specified port
socket_obj = create_bound_socket(local_IP, local_PORT)

# Initialize a bytearray to store the received data
received_data = bytearray()

# Initialize variables to track sequence numbers for duplicate packet checking
current_sequence_number = 0
previous_sequence_number = 0
end_of_file = False

# Main loop to receive data packets
while not end_of_file:
    # Receive a data packet from the sender
    data, addr = socket_obj.recvfrom(1027) # Buffer size includes packet header
    
    # If the data packet is empty, skip this iteration
    if data is None:
        continue
    
    # Extract the sequence number from the beginning of the packet
    current_sequence_number = int.from_bytes(data[:2], 'big')
    
    # Check if the received packet is the next in the sequence
    if current_sequence_number == (previous_sequence_number + 1):
        # Update the sequence number and append the packet data to the received_data bytearray
        previous_sequence_number = current_sequence_number
        received_data.extend(data[3:])
        
        # Construct the ACK packet and send it back to the sender
        packet = bytearray(previous_sequence_number.to_bytes(2, byteorder='big'))
        socket_obj.sendto(packet, addr)
    else:
        # If the packet is a duplicate, re-send the ACK for the last correctly received packet
        packet = bytearray(previous_sequence_number.to_bytes(2, byteorder='big'))
        socket_obj.sendto(packet, addr)
    
    # Check if the packet is marked as the last packet (EOF)
    if data[2] == 1:
        # Construct a packet to acknowledge the reception of the last packet and send it
        end_sequence_number = 0
        packet = bytearray(end_sequence_number.to_bytes(2, byteorder='big'))
        socket_obj.sendto(packet, addr)
        # Set the flag to exit the loop since the last packet has been received
        end_of_file = True

# Once all packets are received, write the data to the specified output file
write_to_file(output_filename, received_data)

# Close the socket after transmission is complete
socket_obj.close()

