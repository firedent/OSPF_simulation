# coding=utf-8
import threading
import socket
import pathlib
import time
import json
import argparse
import queue

MAX_CONSECUTIVE_LOST_TIME = 3
UPDATE_INTERVAL = 1
node_data = {
    5000: 'A',
    5001: 'B',
    5002: 'C',
    5003: 'D',
    5004: 'E',
    5005: 'F'
}


class NodesKnown(dict):
    # 其他节点是否更新
    timestamp = 0


def get_ts():
    return time.strftime('%H:%M:%S', time.localtime(time.time()))


def read_config(filename):
    file_path = pathlib.Path(filename)
    with open(file_path) as f:
        file_contains = f.readlines()
    nodes = NodesKnown()
    try:
        # neighbour_number = int(file_contains[0].strip())
        for line in file_contains[1:]:
            line_e = line.strip().split()
            if len(line_e) != 3:
                continue
            nodes[line_e[0]] = [float(line_e[1]), int(line_e[2]), True]
    except (ValueError,):
        print("config wrong")
        exit()
    nodes.timestamp = time.time()
    return nodes


# target = (source_ID, source_port)
def sending(target, message):
    socket_instance.sendto(
        bytes(
            message,
            encoding='ascii'
        ),
        ('127.0.0.1', target[1])
    )


def listening_thread():
    i = 0
    while True:
        data, address = socket_instance.recvfrom(1024)
        data_list = json.loads(data.decode('ascii'))

        if data_list[1] == 1:
            if data_list[0] not in NEIGHBOURS.keys():
                print(f'[!!! ERROR !!!] Receive a broadcast not belong of neighbours')
            i += 1
        if i == 10:
            print(f'[INFO] receive LST x 10')
            i = 0

        receive_queue.put((data_list, address[1]))
    pass


def dijkstra_thread():
    pass


def broadcast_thread():
    # default_message_for_broadcast = [
    #     'C',
    #     1|2|3|4,
    #     123456754,
    #     {
    #         'A' : 4.5,
    #         'B' : 5,
    #         ...
    #     }
    # ]

    # NEIGHBOURS = {
    #   'B' : (6.5, 5001, True),
    #   'F' : (2.2, 5005, False),
    #   ...
    # }
    list_for_broadcast = default_message_for_broadcast
    neighbour = list_for_broadcast[3]
    last_update = list_for_broadcast[2]
    while True:
        try:
            NEIGHBOURS_lock.acquire(True, 0.5)
            if last_update < NEIGHBOURS.timestamp:
                neighbour = dict(
                    [(n[0], n[1]) for n in NEIGHBOURS.items() if n[1][2]]
                )
                list_for_broadcast = [ID, 1, NEIGHBOURS.timestamp, neighbour]
        finally:
            NEIGHBOURS_lock.release()
        # neighbour = {
        #     'B' : 6.5,
        #     'F' : 2.2,
        #     ...
        # }
        for n in neighbour.items():
            # send = (
            #     [source_id, type, timestamp, data],
            #     (source_id, source_port)
            # )
            send = (list_for_broadcast, (n[0], NEIGHBOURS[n[0]][1]))
            send_queue.put(send)
            # broadcast_queue.put((list_for_broadcast, nbh[1]))
        if len(neighbour) == 0:
            print(f'[Broadcast] 0')
        time.sleep(1)


def sending_thread():
    broadcast_thread_instance = threading.Thread(target=broadcast_thread)
    broadcast_thread_instance.start()
    i = 0
    while True:

        # while broadcast_queue.empty() is False:
        #     send_queue.put(broadcast_queue.get())
        #
        # Deadlock if without get_nowait()
        # This part of code with get_nowait() would also raise
        # the CPU load because there is no blocking
        #
        # try:
        #     send = send_queue.get_nowait()
        # except queue.Empty:
        #     continue


        # send = (
        #     [source_id, type, timestamp, data],
        #     (source_id, source_port)
        # )

        send = send_queue.get()
        data_list, target = send

        packet_type = data_list[1]
        data = json.dumps(data_list, separators=(',', ':'))
        if packet_type == 2:
            # 创建一个计时器
            check_ack_thread = threading.Thread(target=check_ack, args=send)
            sending(target, message=data)
            print(f'[Forward] To {target[0]}:{target[1]} {data}')
            # 触发计时器，发送完数据5s后运行check()
            check_ack_thread.start()
        else:
            if packet_type == 1:
                # print(f'[Broadcast] {node_data[target]}:{target} {data}')
                i += 1
            if i == 10:
                print(f'[Broadcast] {data} x 10')
                i = 0
            sending(target, message=data)


# send = (
#     [source_id, type, timestamp, data],
#     (source_id, source_port)
# )
def check_ack(*send):
    time.sleep(3)
    target = send[1]
    router_name, router_port = target
    with nodes_ack_lock:
        success = nodes_ack.get(router_name, False)
        # print(f'ACK DATABASE {nodes_ack} in check_ack')
    try:
        nodes_ack_lock.acquire()
        # print(f'nodes_ack[{router_name}] is {success} in check_ack after used')
        if nodes_ack.get(router_name, False):
            # print(f'ACK DATABASE {nodes_ack} in check_ack')
            return
    finally:
        nodes_ack[router_name] = False
        nodes_ack_lock.release()

    try:
        nodes_known_lock.acquire()
        if router_name not in nodes_known[ID]:
            print(f'[Fail] To {router_name}:{router_port} has been removed from neighbour')
            return
    finally:
        nodes_known_lock.release()

    print(f'[Fail] To {router_name}:{router_port} {send[0]}, try again')
    send_queue.put(send)


def check_alive():
    # nodes_heartbeat = {
    #     'A' : 1,
    #     'B' : 2,
    #     .....
    # }

    # nodes_known = {
    #     'B' : {
    #         'F' : 2.2,
    #     },
    #     'F' : {
    #         'B' : 2.2,
    #         'A' : 4,
    #         ...
    #     },
    #     ...
    # }

    while True:
        lost_node = []
        with nodes_heartbeat_lock, nodes_known_lock:
            for n in nodes_known[ID].keys():
                if nodes_heartbeat.setdefault(n, MAX_CONSECUTIVE_LOST_TIME) >= MAX_CONSECUTIVE_LOST_TIME:
                    lost_node.append(n)
                else:
                    nodes_heartbeat[n] += 1

        if len(lost_node) != 0:
            print(f'[LOST] {lost_node}')
            with nodes_known_lock:
                for n in lost_node:
                    print(f'[DELETE] nodes_known[{ID}][{n}]: {nodes_known[ID][n]}')
                    # print(f'{nodes_known[ID].pop(n)}')
                    del nodes_known[ID][n]
                    print(f'[DELETE] OK')
                nodes_known.neighbour_timestamp = time.time()

        time.sleep(UPDATE_INTERVAL)


def main_thread():
    while True:
        receive = receive_queue.get()
        receive_data_list, packet_receive_from_port = receive[0], receive[1]
        packet_source_router, packet_type, packet_timestamp = \
            receive_data_list[0], receive_data_list[1], receive_data_list[2]

        if packet_type not in {1, 2, 3, 4}:
            print(f'I don\'t know what\'s the meaning of packet!!!!')
            continue

        if packet_type == 4:
            pass

        if packet_type == 3:
            print(f'[ACK] From {node_data[packet_receive_from_port]}: {packet_receive_from_port}')
            with nodes_ack_lock:
                nodes_ack[packet_source_router] = True
                # print(f'SET nodes_ack[{packet_source_router}] to True')
                # print(f'ACK DATABASE {nodes_ack}')
            continue

        # 如果是转发报文 reply ACK
        if packet_type == 2:
            print(f'[RECEIVE] Forwarded packet from {node_data[packet_receive_from_port]}:{packet_receive_from_port} '
                  f'{receive_data_list}')

            # ？？？？
            # send_queue.put(([ID, 3, receive_data_list[2]], packet_receive_from_port))
            print(f'[SEND] ACK to {node_data[packet_receive_from_port]}:{packet_receive_from_port} ')
            send_queue.put(([ID, 3, packet_timestamp], (receive_data_list[0], packet_receive_from_port)))

        # 心跳包
        with nodes_heartbeat_lock:
            nodes_heartbeat[packet_source_router] = 0
            print(f'[RETENTION] nodes_heartbeat[{packet_source_router}] == 0')

        node_cost = receive_data_list[3]
        # print(f'[RECEIVE] Broadcast packet from {node_data[packet_receive_from_port]}:{packet_receive_from_port} '
        #       f'{receive_data_list}')
        receive_data_list[1] = 2
        last_update_time = packet_update_time.get(packet_source_router, 0)
        # print(f'recorded timestamp {packet_source_router} to self: {last_update_time}')
        # print(f'packet timestamp {packet_source_router} to self: {packet_timestamp}')

        if last_update_time < packet_timestamp:

            with nodes_known_lock:
                nodes_known[packet_source_router] = node_cost
                nodes_known.timestamp = int(time.time())
                print(f'[UPDATE] Know {nodes_known}')

            packet_update_time[packet_source_router] = packet_timestamp

            print(f'[INFO] {nodes_known.timestamp}: {nodes_known}')

        for i in NEIGHBOURS.items():

            target_router = i[0]
            # 不转发给信件原作者
            if target_router == packet_source_router:
                continue

            target_router_info = i[1]
            target_router_info_port = target_router_info[1]
            # 不转发给来信放
            if target_router_info_port == packet_receive_from_port:
                continue

            # 如果接收的时间戳是旧的或者是相等的，和每一个都比较一下
            if last_update_time >= packet_timestamp:
                # print(f'last_update_time >= packet_timestamp')
                last_update_time_s_to_t = packet_update_time.get((packet_source_router, target_router), 0)
                # print(f'recorded timestamp {packet_source_router} to {target_router}: {last_update_time_s_to_t}')
                if last_update_time_s_to_t >= packet_timestamp:
                    # print(f'ast_update_time_s_to_t >= packet_timestamp')
                    continue

            packet_update_time[(packet_source_router, target_router)] = packet_timestamp
            print(f'[UPDATE] Forward packet from {packet_source_router} to {target_router}, '
                  f'old: {last_update_time}, new: {packet_timestamp}')

            print(f'[Forward] To {target_router}:{target_router_info_port} {receive_data_list}')
            send_queue.put((receive_data_list, (target_router, target_router_info_port)))


        # print(get_ts() + ': '
        #       f'receive data from {receive_data_list[0][0]}, type {receive_data_list[0][1]}, '
        #       f'timestamp {receive_data_list[0][2]}: {receive_data_list[0][3]}')


ap = argparse.ArgumentParser(description='Assignment of COMP9331\n author: Shichao ZHANG (z5178127)')
ap.add_argument('id', metavar='ID')
ap.add_argument('port', metavar='PORT')
ap.add_argument('config', metavar='CONFIG')
args = ap.parse_args()


PORT = args.port
try:
    PORT = int(PORT)
    if PORT < 0 or PORT > 65535:
        raise ValueError
except (ValueError, TypeError):
    print('PORT is incorrect')

ID = args.id
CONFIG = args.config

socket_instance = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
socket_instance.bind(('0.0.0.0', PORT))

# NEIGHBOURS = {
#   'B' : (6.5, 5001, True),
#   'F' : (2.2, 5005, False),
#   ...
# }

# nodes_known = {
#     'B' : {
#         'F' : 2.2,
#     },
#     'F' : {
#         'B' : 2.2,
#         'A' : 4,
#         ...
#     },
#     ...
# }

NEIGHBOURS = read_config(CONFIG)
NEIGHBOURS_lock = threading.Lock()

nodes_known = NodesKnown()
nodes_known_lock = threading.Lock()
nodes_known[ID] = dict([(n[0], n[1][0]) for n in NEIGHBOURS.items()])
nodes_known.neighbour_timestamp = int(time.time())
default_message_for_broadcast = [ID, 1, NEIGHBOURS.timestamp, nodes_known[ID]]

# +-------------------------------------------+
# | SOURCE ID | TYPE | TIMESTAMP | STATE DATA |
# +-------------------------------------------+
# TYPE:
#   1: 自身广播包，无序被确认
#   2: 转发别人的广播包，需要被确认，因为只广播一次
#   3: 确认包

# message_for_broadcast = json.dumps([ID, 1, int(time.time()), NEIGHBOURS])
# message_for_broadcast = json.dumps([ID, 1, int(time.time()), nodes_known[ID]])

packet_update_time = dict()

nodes_ack = dict()
nodes_ack_lock = threading.Lock()

nodes_heartbeat = dict()
nodes_heartbeat_lock = threading.Lock()

receive_queue = queue.Queue()
send_queue = queue.Queue()
broadcast_queue = queue.Queue()

print(f'[INFO] ROuter: {ID}')
print(f'[INFO] Config: {NEIGHBOURS}')
# print(f'[INFO] {nodes_known.neighbour_timestamp}: {nodes_known}')


t1 = threading.Thread(target=sending_thread)
t2 = threading.Thread(target=listening_thread)
t3 = threading.Thread(target=main_thread)
t4 = threading.Thread(target=check_alive)

t1.start()
t2.start()
t3.start()
t4.start()
