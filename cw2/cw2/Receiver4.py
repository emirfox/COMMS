#Emir Ersanli S2221285
import socket  # For network connections
import sys  # For command line arguments
import os  # For file operations

# Constants for managing data packets and control flow
DATA_PAYLOAD_SIZE = 1024  # Size of the data payload in each UDP packet
HEADER_LENGTH = 3  # Size of the header in each packet (2 bytes for sequence number + 1 byte for EOF flag)
ACK_PACKET_SIZE = 2  # Size of the acknowledgement packet
SYSTEM_BYTE_ORDER = 'big'  # Byte order for converting between bytes and integers
REPEATED_ACKS_FOR_LAST_PACKET = 5  # Number of times the ACK for the final packet will be sent

def handle_incoming_data(sock, target_filename, ctrl_window_size):
    """
    Receives data packets over UDP, acknowledges each packet, ensures packets are processed
    in sequence using a sliding window protocol, and writes the received data to a file.
    """
    window_start = 1  # Initial sequence number of the sliding window
    received_data_packets = {}  # Dictionary to store out-of-order packets
    file_end_received = False  # Flag to indicate the end of file transfer
    final_packet_seq = None  # Sequence number of the final packet

    # Continue receiving packets until the end of the file is marked and all packets within the window are processed
    while not file_end_received or any(seq >= window_start for seq in received_data_packets):
        packet, sender_addr = sock.recvfrom(DATA_PAYLOAD_SIZE + HEADER_LENGTH)  # Receive a packet
        sequence_number = int.from_bytes(packet[:2], SYSTEM_BYTE_ORDER)  # Extract sequence number
        eof_marker = packet[2]  # Extract EOF flag
        packet_data = packet[3:]  # Extract the data payload

        # Send an ACK for the received packet
        ack_response = sequence_number.to_bytes(2, SYSTEM_BYTE_ORDER)
        sock.sendto(ack_response, sender_addr)

        # Check if the packet is within the window and not already received
        if window_start <= sequence_number < window_start + ctrl_window_size and sequence_number not in received_data_packets:
            received_data_packets[sequence_number] = (packet_data, eof_marker)  # Store packet
            if eof_marker == 1:
                # If EOF marker is set, record the end of file and the final packet's sequence number
                file_end_received = True
                final_packet_seq = sequence_number

            # Write in-sequence packets to the file and advance the window as appropriate
            with open(target_filename, 'ab') as output_file:
                while window_start in received_data_packets:
                    data, is_eof = received_data_packets.pop(window_start)
                    output_file.write(data)  # Write data to file
                    if is_eof == 1:
                        # Break the loop if EOF marker is encountered
                        file_end_received = True
                        break
                    window_start += 1  # Advance the sliding window

    # After receiving the final packet, send repeated ACKs to ensure the sender knows transmission is complete
    if final_packet_seq is not None:
        for _ in range(REPEATED_ACKS_FOR_LAST_PACKET):
            ack_response = final_packet_seq.to_bytes(2, SYSTEM_BYTE_ORDER)
            sock.sendto(ack_response, sender_addr)

if __name__ == "__main__":
    # Check for correct command line arguments and exit if incorrect
    if len(sys.argv) != 4:
        sys.exit(1)

    # Extract command line arguments for port, output filename, and window size
    UDP_PORT, OUTPUT_FILENAME, WINDOW_SIZE = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])

    # Remove the output file if it already exists to start fresh
    if os.path.exists(OUTPUT_FILENAME):
        os.remove(OUTPUT_FILENAME)

    # Create a UDP socket and bind it to the specified port
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('0.0.0.0', UDP_PORT))

    try:
        # Handle incoming data until the transmission is complete
        handle_incoming_data(udp_socket, OUTPUT_FILENAME, WINDOW_SIZE)
    finally:
        # Ensure the socket is closed properly
        udp_socket.close()
