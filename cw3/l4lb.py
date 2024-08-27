from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet.tcp import TCP_SYN, TCP_FIN, TCP_RST, TCP_ACK
from ryu.lib.packet.ether_types import ETH_TYPE_IP, ETH_TYPE_ARP

class L4Lb(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L4Lb, self).__init__(*args, **kwargs)
        self.ht = {}  # {(<sip><vip><sport><dport>): out_port, ...}
        self.vip = '10.0.0.10'
        self.dips = ('10.0.0.2', '10.0.0.3')
        self.dmacs = ('00:00:00:00:00:02', '00:00:00:00:00:03')
        # write your code here, if needed
        self.loadBalancerCounter = 0
        self.controllerMacAddress = '00:00:00:00:00:01'
        self.controllerIpAddress = '10.0.0.1'
        #

    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        return out

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        actions = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, psr.OFPMatch(), actions)

    def add_flow(self, dp, priority, match, actions, buffer_id=None):
        ofproto, parser = (dp.ofproto, dp.ofproto_parser)
        bufferId = buffer_id if buffer_id is not None else ofproto.OFP_NO_BUFFER
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flow_mod = parser.OFPFlowMod(datapath=dp, buffer_id=bufferId, priority=priority,
                                     match=match, instructions=instructions)
        dp.send_msg(flow_mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        in_port, pkt = (msg.match['in_port'], packet.Packet(msg.data))
        dp = msg.datapath
        ofproto, parser, dpId = (dp.ofproto, dp.ofproto_parser, format(dp.id, '016d'))
        eth = pkt.get_protocols(ethernet.ethernet)[0]
                # Extract the headers from the packet
        ipv4Headers = pkt.get_protocols(ipv4.ipv4)
        tcpHeaders = pkt.get_protocols(tcp.tcp)
        arpHeaders = pkt.get_protocols(arp.arp)

        # Check if the packet is a TCP/IP packet or an ARP packet
        tcpIpPacket = (len(tcpHeaders) != 0) and (len(ipv4Headers) != 0)
        arpPacket = (len(arpHeaders) != 0)

        # If it's a TCP/IP packet
        if tcpIpPacket:
            # Create a unique identifier for the packet
            packetIdentifier = (ipv4Headers[0].src, ipv4Headers[0].dst, tcpHeaders[0].src_port, tcpHeaders[0].dst_port)

            # If the packet is not from the controller
            if in_port != 1:
                outputPort = 1
                actions = [parser.OFPActionSetField(ipv4_src=self.vip),
                           parser.OFPActionOutput(outputPort)]
            else:
                # Load balancing logic
                self.loadBalancerCounter += 1
                outputPort = 2 if self.loadBalancerCounter % 2 == 1 else 3
                actions = [parser.OFPActionSetField(eth_dst=self.dmacs[outputPort - 2]),
                           parser.OFPActionSetField(ipv4_dst=self.dips[outputPort - 2]),
                           parser.OFPActionOutput(outputPort)]

            # Store the output port for this packet identifier
            self.ht.setdefault(packetIdentifier, outputPort)

            # Create match criteria for the flow
            matchCriteria = parser.OFPMatch(in_port=in_port, eth_type=ETH_TYPE_IP, ip_proto=in_proto.IPPROTO_TCP, ipv4_src=ipv4Headers[0].src, ipv4_dst=ipv4Headers[0].dst, tcp_src=tcpHeaders[0].src_port, tcp_dst=tcpHeaders[0].dst_port)

            # Add the flow to the switch
            self.add_flow(dp, 1, matchCriteria, actions, msg.buffer_id)

            # If the packet is buffered, no need to send it again
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                return
        # If it's an ARP packet
        elif arpPacket:
            # Extract the ARP request details
            arpRequest = arpHeaders[0]
            if in_port == 1:
                # Load balancing logic for ARP requests
                self.loadBalancerCounter +=1
                if self.loadBalancerCounter % 2 == 1:
                    # Create an ARP reply packet
                    arpReplyPacket = packet.Packet()
                    ethernetHeader = ethernet.ethernet(arpHeaders[0].src_mac, self.dmacs[0], ETH_TYPE_ARP)
                    arpReply = arp.arp_ip(arp.ARP_REPLY, src_mac=self.dmacs[0], src_ip=self.vip, dst_mac=arpHeaders[0].src_mac, dst_ip=arpHeaders[0].src_ip)
                    arpReplyPacket.add_protocol(ethernetHeader)
                    arpReplyPacket.add_protocol(arpReply)
                    out = self._send_packet(dp, in_port, arpReplyPacket)
                    dp.send_msg(out)
                else:
                    # Create an ARP reply packet
                    arpReplyPacket = packet.Packet()
                    ethernetHeader = ethernet.ethernet(arpHeaders[0].src_mac, self.dmacs[1], ETH_TYPE_ARP)
                    arpReply = arp.arp_ip(arp.ARP_REPLY, src_mac=self.dmacs[1], src_ip=self.vip, dst_mac=arpHeaders[0].src_mac, dst_ip=arpHeaders[0].src_ip)
                    arpReplyPacket.add_protocol(ethernetHeader)
                    arpReplyPacket.add_protocol(arpReply)
                    out = self._send_packet(dp, in_port, arpReplyPacket)
                    dp.send_msg(out)
            else:
                # Create an ARP reply packet
                arpReplyPacket = packet.Packet()
                ethernetPacket = ethernet.ethernet(dst=arpRequest.src_mac, src=self.controllerMacAddress, ethertype=ETH_TYPE_ARP)
                arpReply = arp.arp(hwtype=1, proto=0x0800, hlen=6, plen=4, opcode=arp.ARP_REPLY,
                                   src_mac=self.controllerMacAddress, src_ip=self.controllerIpAddress,
                                   dst_mac=arpRequest.src_mac, dst_ip=arpRequest.src_ip)
                arpReplyPacket.add_protocol(ethernetPacket)
                arpReplyPacket.add_protocol(arpReply)
                out = self._send_packet(dp, in_port, arpReplyPacket)
                dp.send_msg(out)
        else:
            # If the packet is neither TCP/IP nor ARP, drop it
            actions = [parser.OFPActionOutput(ofproto.OFPPC_NO_FWD)]
            data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
            out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
            dp.send_msg(out)

    '''
         hash logic didn't work
            elif arp_pkt:
            # Extract the ARP request details
            arp_request = arph[0]
    
            # Check if the ARP request is querying the virtual IP
            if arp_request.dst_ip == self.vip and in_port == 1:
                # Determine the destination MAC address based on the requested IP
                selected_index = hash(arp_request.src_ip) % len(self.dmacs)
                selected_dmac = self.dmacs[selected_index]
                
                # Create an ARP reply with the virtual IP's MAC address responding to the client
                arp_reply_pkt = packet.Packet()
                ethernet_header = ethernet.ethernet(dst=arp_request.src_mac, src=selected_dmac, ethertype=ETH_TYPE_ARP)
                arp_reply = arp.arp(opcode=arp.ARP_REPLY, src_mac=selected_dmac, src_ip=self.vip,
                                    dst_mac=arp_request.src_mac, dst_ip=arp_request.src_ip)
                
                arp_reply_pkt.add_protocol(ethernet_header)
                arp_reply_pkt.add_protocol(arp_reply)
                
                # Send the ARP reply back to the requester
                out = self._send_packet(dp, in_port, arp_reply_pkt)
                dp.send_msg(out)
    
    
    '''








        