# Emir Ersanli S2221285
import socket
import sys
import threading
import time
import select

# Define constants
CHUNK_SIZE = 1024  # Size of data chunks to be sent
HEADER_LENGTH = 3  # Length of the header: 2 bytes for sequence number, 1 byte for EOF indicator
ACK_LENGTH = 2  # Length of the acknowledgement
BYTE_ORDERING = 'big'  # Byte order to be used

# Define a class for data packets
class DataPacket:
    """
    Encapsulates a data packet's attributes and functionality.
    """

    # Initialize the data packet with sequence number, content, and EOF indicator
    def __init__(self, seq_no, content, is_last):
        self.seq_no = seq_no
        self.content = content
        self.is_last = is_last

    # Assemble the data packet
    def assemble(self):
        seq_bytes = self.seq_no.to_bytes(2, byteorder=BYTE_ORDERING)
        eof_byte = b'\x01' if self.is_last else b'\x00'
        return seq_bytes + eof_byte + self.content  # Return the assembled packet

# Define a class for reliable UDP sender
class ReliableUDPSender:
    # Initialize the sender with target host and port, source file, retry timeout, and maximum window size
    def __init__(self, target_host, target_port, source_file, retry_timeout, max_window):
        self.target_host = target_host
        self.target_port = target_port
        self.source_file = source_file
        self.retry_timeout = retry_timeout / 1000.0  # Convert timeout to seconds
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a UDP socket
        self.max_window = max_window  # Maximum window size for transmission
        self.seq_base = 1  # Base sequence number
        self.seq_next = 1  # Next sequence number
        self.acknowledged = {}  # Dictionary to keep track of acknowledged packets
        self.mutex = threading.Lock()  # Mutex for synchronization
        self.finished = False  # Flag to indicate if transmission is finished
        self.outgoing = {}  # Dictionary to keep track of outgoing packets
        self.ack_listener = threading.Thread(target=self.listen_for_ack)  # Thread to listen for acknowledgements
        self.ack_listener.start()  # Start the acknowledgement listener thread
        self.timeouts = {}  # Dictionary to keep track of timeouts
        self.resends = 0  # Counter for resends

    # Transmit the file
    def transmit(self):
        total_bytes = 0  # Total bytes sent
        with open(self.source_file, 'rb') as f:  # Open the source file in binary mode
            start = time.time()  # Start time of transmission
            while not self.finished or self.outgoing:  # While transmission is not finished or there are outgoing packets
                self.mutex.acquire()  # Acquire the mutex
                while self.seq_next < self.seq_base + self.max_window and not self.finished:  # While the sequence number is within the window and transmission is not finished
                    block = f.read(CHUNK_SIZE)  # Read a block of data from the file
                    final_packet = len(block) < CHUNK_SIZE  # Check if this is the final packet
                    packet = DataPacket(self.seq_next, block, final_packet).assemble()  # Assemble the packet
                    self.outgoing[self.seq_next] = packet  # Add the packet to the outgoing dictionary
                    self.socket.sendto(packet, (self.target_host, self.target_port))  # Send the packet
                    total_bytes += len(block)  # Update the total bytes sent
                    if self.seq_next not in self.timeouts:  # If the sequence number is not in the timeouts dictionary
                        self.timeouts[self.seq_next] = time.time()  # Add it with the current time
                    self.seq_next += 1  # Increment the sequence number
                    if final_packet:  # If this is the final packet
                        self.finished = True  # Set the finished flag to True
                self.mutex.release()  # Release the mutex
                self.handle_timeouts()  # Handle timeouts
            end = time.time()  # End time of transmission
            duration = end - start  # Duration of transmission
            speed = total_bytes / duration / 1024  # Speed of transmission in KB/s
            print(f' {speed:.2f} ')  # Print the speed
            self.ack_listener.join()  # Wait for the acknowledgement listener thread to finish

    # Handle timeouts
    def handle_timeouts(self):
        now = time.time()  # Current time
        self.mutex.acquire()  # Acquire the mutex
        for seq, start_time in list(self.timeouts.items()):  # For each sequence number and start time in the timeouts dictionary
            if now - start_time > self.retry_timeout:  # If the difference is greater than the retry timeout
                if self.seq_base <= seq < self.seq_next:  # If the sequence number is within the window
                    self.resends += 1  # Increment the resends counter
                    self.socket.sendto(self.outgoing[seq], (self.target_host, self.target_port))  # Resend the packet
                    self.timeouts[seq] = now  # Update the start time in the timeouts dictionary
        self.mutex.release()  # Release the mutex

    # Listen for acknowledgements
    def listen_for_ack(self):
        while not self.finished or self.outgoing:  # While transmission is not finished or there are outgoing packets
            ready = select.select([self.socket], [], [], self.retry_timeout)  # Wait for the socket to be ready
            if ready[0]:  # If the socket is ready
                ack, _ = self.socket.recvfrom(ACK_LENGTH)  # Receive the acknowledgement
                ack_seq = int.from_bytes(ack, BYTE_ORDERING)  # Convert the acknowledgement to integer
                self.mutex.acquire()  # Acquire the mutex
                if self.seq_base <= ack_seq < self.seq_next:  # If the acknowledgement sequence number is within the window
                    self.acknowledged[ack_seq] = True  # Acknowledge the packet
                    while self.seq_base in self.acknowledged:  # While the base sequence number is in the acknowledged dictionary
                        del self.outgoing[self.seq_base]  # Remove the packet from the outgoing dictionary
                        del self.acknowledged[self.seq_base]  # Remove the acknowledgement from the acknowledged dictionary
                        if self.seq_base in self.timeouts:  # If the base sequence number is in the timeouts dictionary
                            del self.timeouts[self.seq_base]  # Remove it
                        self.seq_base += 1  # Increment the base sequence number
                self.mutex.release()  # Release the mutex

    # Finalize the transmission
    def finalize(self):
        self.finished = True  # Set the finished flag to True
        self.ack_listener.join()  # Wait for the acknowledgement listener thread to finish
        self.socket.close()  # Close the socket

# Main function
if __name__ == "__main__":
    if len(sys.argv) != 6:  # If the number of command line arguments is not 6
        print("Usage: script.py <TargetHost> <TargetPort> <SourceFile> <RetryTimeout(ms)> <MaxWindowSize>")  # Print the usage
        sys.exit()  # Exit the program

    # Parse the command line arguments
    host, port, file, timeout, window = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    udp_sender = ReliableUDPSender(host, port, file, timeout, window)  # Create a reliable UDP sender
    try:
        udp_sender.transmit()  # Start sending the file
    finally:
        udp_sender.finalize()  # Ensure proper closure


