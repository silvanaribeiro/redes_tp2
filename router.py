import socket
from socket import AF_INET, SOCK_DGRAM
import sys, getopt, os
import subprocess
import json
from pprint import pprint
from collections import namedtuple
import threading
from threading import Timer
import time
import random as ra

from sys import exit

routing_table = list()
RouteRow = namedtuple('RouteRow', 'destination nextHop cost ttl')
count_route_rows = 0
PORT = 55151
PERIOD = None
origin = None
def main(argv):
	opts = None
	args = None
	STARTUP = None
	ADDR = None
	PERIOD = None


	# teste = RouteRow('A','C',2)
	# print (teste)

	try:
		opts,args=getopt.getopt(argv,'a:u:s:',[ 'addr=', 'update-period=', 'startup-commands=' ])
	except getopt.GetoptError:
		print("router.py <ADDR> <PERIOD> [STARTUP]")

	print(opts, args)
	if opts:
		for opt, arg in opts:
			if opt in ('-a', '--addr'):
				ADDR = arg
			elif opt in ('-u', '--update-period'):
				PERIOD = arg
			elif opt in ('-s', '--startup-commands'):
				STARTUP = arg
	elif len(args) >= 2:
		ADDR = args[0]
		PERIOD = args[1]
		if len(args) == 3:
			STARTUP = args[2]

	if ADDR is None or PERIOD is None:
		print("Error on startup. Use either: ")
		print("router.py <ADDR> <PERIOD> [STARTUP]")
		print("Or:")
		print("router.py --addr <ADDR> --update-period <PERIOD> --startup-commands [STARTUP]")
	else:
		if STARTUP:
			read_file(STARTUP)

		print("OPTS", ADDR, PERIOD, STARTUP)

		t1 = threading.Thread(target=start_listening, args=(ADDR, PORT))
		t1.setDaemon(True)
		t1.start()
		send_message(ADDR, PORT, encode_message("data", "1.1.1.1", "127.0.1.1", [1,2,3]))

		t2=threading.Thread(target=listen_to_cdm, args = (ADDR,))
		t2.setDaemon(True)
		t2.start()

		origin = ADDR
		update_routes_periodically(PERIOD)
		# remove_old_routes()

def listen_to_cdm(ADDR):
	comando = None
	while True:
		comando = input('')
		comando = comando.replace('\n', '')
		comando = comando.split(" ")
		if comando[0] == 'add' and len(comando) == 3:
			add_ve(comando[1], comando[2], routing_table)
			print ('Enlace adicionado')
			print (routing_table)
		elif comando[0] == 'del' and len(comando) == 2:
			del_ve(comando[1], routing_table)
			print ('Enlace removido')
			print (routing_table)
		elif comando[0] == 'trace' and len(comando) == 2:
			print (get_next_hop(comando[1]))
			send_trace(ADDR, comando[1])
			print ('Trace enviado')
		elif comando[0] == 'quit':
			os._exit(1)

def send_trace(ADDR, destination):
	json_msg = encode_message("trace", ADDR, destination, "")
	ip = get_next_hop(destination)
	if ip is not None:
		send_message(ip, PORT, json_msg)

def add_ve(ip, weight, routing_table):
	route_row = RouteRow (ip, ip, weight, time.time())
	routing_table.append(route_row)
	return routing_table

def del_ve(ip, routing_table):
    for route in routing_table:
        if ip == route.destination:
            routing_table.remove(route)
    return routing_table

def get_next_hop(destination):
	for i in range (0,len(routing_table)):
		if routing_table[i].destination == destination:
			return routing_table[i].nextHop
	return None

def get_neighbors(routing_table):
	neighbors = []
	for router in routing_table:
		if router not in neighbors:
			neighbors.append(router.nextHop)

	return neighbors

def merge_route(new_route, routing_table, cost_hop):
	index = -1
	for i in range(0,routing_table.count()):
		if routing_table[i].destination == new_route.destination:
			if (new_route.cost < routing_table[i].cost) or (new_route.nextHop == routing_table[i].nextHop): #metrica mudou
				index = i
				break

	if index == -1: # nova rota
		new_route.cost += cost_hop
		routing_table.append(new_route)
	else:
		routing_table[index] = new_route
		routing_table[index].cost += cost_hop


def read_file(file_name):
    with open(file_name, "r") as f:
        lines = f.readlines()
        for line in lines:
            command = line.replace('\n', '')
            commands = command.split(" ")
            print(commands)
            if commands[0] != 'add':
                print("Invalid command was read in startup file:", commands[0])
            if len(commands) != 3:
                print("Invalid format was read in startup file:", commands)
            else:
                add_ve(commands[1], commands[2], routing_table)

def encode_message(type, source, destination, last_info):
	if type is 'data':
		return json.dumps({'type': type, 'source': source, 'destination': destination, 'payload': last_info})
	elif type is 'update': # tem que arrumar o distances. Eh outro json --> OK
		table = json.dumps(last_info)
		return json.dumps({'type': type, 'source': source, 'destination': destination, 'distances': table})
	elif type is 'trace':
		return json.dumps({'type': type, 'source': source, 'destination': destination, 'hops': last_info})


def decode_message(IP, message):
	data = json.loads(message)
	# Prints if it's the destination of the data type message
	if data["type"] == 'data' and data["destination"] == IP:
		pprint(data)
	return data


def send_message(HOST, PORT, message):
	udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	dest = (HOST, int(PORT))
	print (dest)
	print (message)
	udp.sendto(message.encode('utf-8'), dest)
	print ("Mensagem enviada")
	udp.close()

def start_listening(IP, PORT):
	udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	orig = (IP, int(PORT))
	udp.bind(orig)
	while True:
		message, client = udp.recvfrom(1024)
		decode_message(IP, message)
	udp.close()

def remove_old_routes():
    threading.Timer(PERIOD, remove_old_routes).start()
    for route in routing_table:
        if time.time() > route.ttl + 4*PERIOD :
            routing_table.remove(route)

def update_routes_periodically(PERIOD):
	print ("PERIOD:", PERIOD)
	threading.Timer(int(PERIOD), update).start()


def update():
	print ("---------Sending updates------------")
	routers = get_neighbors(routing_table)
	for router in routers:
		json_msg = encode_message("update", origin, router, routing_table)
		# send_message(router, PORT, json_msg)
		# send_message(router, PORT, encode_message("data", "1.1.1.1", "127.0.1.1", [1,2,3]))
		send_message("127.0.1.2", PORT, encode_message("data", "1.1.1.1", "127.0.1.1", [1,2,3]))

# receives list with tied routes like ['1.1.1.1', '1.1.1.2', '1.1.1.3'] and returns the chosen one
def load_balance(tied_routes):
    a = 1
    b = len(tied_routes)+1
    chosen = ra.uniform(a,b)
    chosen = int(chosen)
    return tied_routes[chosen-1]

if __name__ == "__main__":
	main(sys.argv[1:])
