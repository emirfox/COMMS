# Emir Ersanli S2221285
import socket
import sys 
import os
import math

# specify localhost
local_IP = "127.0.0.1"
# specify port
local_port = int(sys.argv[1])
# specify filename to be created
file_name = sys.argv[2] 
# start a socket
data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Use this socket for specified port number
data_socket.bind((local_IP, local_port))
# create a bytearray
file_data = bytearray()
# create variables to check duplicate packets
packet_seq_num = 0
next_seq_num = 0
while True:
    # set buffer size to 1027 and get data from it
    data, addr = data_socket.recvfrom(1027) 
    # if seqNum is nextSeqnum it means we received the next in order packet
    packet_seq_num = int.from_bytes(data[:2],'big')
    if packet_seq_num == next_seq_num:
        # increase sequence number and add to bytearray image
        file_data.extend(data[3:])
        next_seq_num += 1
    if next_seq_num == 0 :
        var = 0
    else :
        var = next_seq_num - 1
    ack_packet = bytearray(var.to_bytes(2, byteorder='big'))
    # send acknowledgement
    data_socket.sendto(ack_packet, addr)
    # be in the loop until we receive the packet in order
    while next_seq_num != packet_seq_num + 1:
       # set buffer size to 1027 and get data from it
       data, addr = data_socket.recvfrom(1027) 
       # get sequence number of packet
       packet_seq_num = int.from_bytes(data[:2],'big')
       # if seqNum is nextSeqnum it means we received the next in order packet
       if packet_seq_num == next_seq_num:
           # extend to the file
           file_data.extend(data[3:])
           next_seq_num += 1
        # assign var as nextSeqnum -1 so that we can send ack to the sender for received packet
       if next_seq_num == 0 :
            var = 0
       else :
            var = next_seq_num - 1
       ack_packet = bytearray(var.to_bytes(2, byteorder='big'))
       # send acknowledgement
       data_socket.sendto(ack_packet, addr)
    # if it is last packet, break out of loop
    if(data[2] == 1):
        # send another packet indicating that receiver has the last packet in case the last ACK is lost
        ack_packet = bytearray(packet_seq_num.to_bytes(2, byteorder='big'))
        data_socket.sendto(ack_packet, addr)
        break
# write file   
with open(file_name, 'wb') as file:
    file.write(file_data)

data_socket.close()