from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import in_proto
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet.ether_types import ETH_TYPE_IP

class L4State14(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L4State14, self).__init__(*args, **kwargs)
        self.ht = set()

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        acts = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, psr.OFPMatch(), acts)

    def add_flow(self, dp, prio, match, acts, buffer_id=None):
        ofp, psr = (dp.ofproto, dp.ofproto_parser)
        bid = buffer_id if buffer_id is not None else ofp.OFP_NO_BUFFER
        ins = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, acts)]
        mod = psr.OFPFlowMod(datapath=dp, buffer_id=bid, priority=prio,
                                match=match, instructions=ins)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        in_port, pkt = (msg.match['in_port'], packet.Packet(msg.data))
        dp = msg.datapath
        ofp, psr, did = (dp.ofproto, dp.ofproto_parser, format(dp.id, '016d'))
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Initialize an empty list for actions
        action_set = []

        # Extract destination and source from ethernet packet
        destination, source = (eth.dst, eth.src)

        # Extract tcp and ipv4 protocols from packet
        tcp_protocol_extract = pkt.get_protocol(tcp.tcp)
        ipv4_protocol_extract = pkt.get_protocol(ipv4.ipv4)
        # Check if packet is tcp/ipv4
        is_tcp_ipv4 = (tcp_protocol_extract is not None) and (ipv4_protocol_extract is not None)

        # If the packet is not tcp, it is allowed to pass
        if not is_tcp_ipv4:
            # Set actions according to the input port
            output_port = 1 if in_port == 2 else 2
            action_set = [psr.OFPActionOutput(output_port)]
        else:
            # Check for invalid tcp flags
            invalid_tcp_flags = tcp_protocol_extract.has_flags(tcp.TCP_SYN, tcp.TCP_FIN) or tcp_protocol_extract.has_flags(tcp.TCP_SYN, tcp.TCP_RST) or tcp_protocol_extract.bits == 0
            # If tcp flags are invalid
            if invalid_tcp_flags:
                # Define action
                action_set = [psr.OFPActionOutput(ofp.OFPPC_NO_FWD)]
            else:
                # Define match for protocol
                protocol_match = psr.OFPMatch(in_port=in_port, ip_proto=ipv4_protocol_extract.proto, ipv4_src=ipv4_protocol_extract.src, ipv4_dst=ipv4_protocol_extract.dst, tcp_src=tcp_protocol_extract.src_port, tcp_dst=tcp_protocol_extract.dst_port)

                # Define frame tuple
                frame_tuple = (ipv4_protocol_extract.src, ipv4_protocol_extract.dst, tcp_protocol_extract.src_port, tcp_protocol_extract.dst_port) if in_port == 1 else (ipv4_protocol_extract.dst, ipv4_protocol_extract.src, tcp_protocol_extract.dst_port, tcp_protocol_extract.src_port)

                # If input port is 2
                if in_port == 2:
                    # If frame tuple not in hash table
                    if frame_tuple not in self.ht:
                        action_set = [psr.OFPActionOutput(ofp.OFPPC_NO_FWD)]
                    else:
                        output_port = 1
                        action_set = [psr.OFPActionOutput(output_port)]
                        self.add_flow(dp, 1, protocol_match, action_set, msg.buffer_id)

                        # Check buffer
                        if msg.buffer_id != ofp.OFP_NO_BUFFER:
                            return
                else:
                    # If tcp packet, add flow to switch
                    output_port = 2
                    action_set = [psr.OFPActionOutput(output_port)]
                    self.add_flow(dp, 1, protocol_match, action_set, msg.buffer_id)

                    # Add frame tuple to hash table
                    self.ht.add(frame_tuple)

                    # Check buffer
                    if msg.buffer_id != ofp.OFP_NO_BUFFER:
                        return

        # Forward the packet
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                               in_port=in_port, actions=action_set, data=data)
        dp.send_msg(out)
