import socket
from socket import AF_INET, SOCK_DGRAM
import sys, getopt
import subprocess
import json
from pprint import pprint
from collections import namedtuple
import threading
from threading import Timer
import time

routing_table = list()
RouteRow = namedtuple('RouteRow', 'destination nextHop cost ttl')
count_route_rows = 0
PORT = 55151
PERIOD = None

def main(argv):
	opts = None
	args = None
	ADDR = None
	STARTUP = None

	# teste = RouteRow('A','C',2)
	# print (teste)

	try:
		opts,args=getopt.getopt(argv,'a:u:s:',[ 'addr=', 'update-period=', 'startup-commands=' ])
	except getopt.GetoptError:
		print("router.py <ADDR> <PERIOD> [STARTUP]")

	# print (opts)
	for opt, arg in opts:
		if opt  in ('-a', '--addr'):
			ADDR = arg
		elif opt in ('-u', '--update-period'):
			PERIOD = arg
		elif opt in ('-s', '--startup-commands'):
			STARTUP = arg

	if STARTUP:
		read_file(STARTUP)

	print("OPTS", ADDR, PERIOD, STARTUP)

	t1 = threading.Thread(target=start_listening, args=(ADDR, PORT))
	t1.start()
	send_message(ADDR, PORT, encode_message("update", "1.1.1.1", "1.1.1.2", [1,2,3]))

	t=threading.Thread(target=listen_to_cdm, args = (ADDR,))
	t.start()

	update_routes()

def listen_to_cdm(ADDR):
	comando = None
	while comando is not 'quit':
		comando = input('')
		print (comando)
		comando = comando.replace('\n', '')
		comando = comando.split(" ")
		if comando[0] == 'add' and len(comando) == 3:
			add_ve(comando[1], comando[2], routing_table)
			print ('Enlace adicionado')
			print (routing_table)
		elif comando[0] == 'del' and len(comando) == 2:
			del_ve(comando[1], routing_table)
			print ('Enlace removido')
		elif comando[0] == 'trace' and len(comando) == 2:
			print (get_next_hop(comando[1]))
			send_trace(ADDR, comando[1])
			print ('Trace enviado')

def send_trace(ADDR, destination):

	json_msg = encode_message("trace", ADDR, destination, "")
	ip = get_next_hop(destination)
	if ip is not None:
		send_message(ip, PORT, json_msg)

# receives string 'add' or 'del'. Pelo que eu entendi a gente só vai usar isso pra inicializar os roteadores mesmo. Talvez nem precisasse estar no programa.
def loopback(operation):
	 subprocess.call(['./tests/lo-adresses.sh',operation])

def add_ve(ip, weight, routing_table):
	route_row = RouteRow (ip,ip,weight, 0)
	routing_table.append(route_row)
	return routing_table

def del_ve(ip, routing_table):
	return routing_table.pop(ip)

def get_next_hop(destination):
	for i in range (0,len(routing_table)):
		if routing_table[i].destination == destination:
			return routing_table[i].nextHop

	return None
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


def read_file(file_name, routing_table):
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
	elif type is 'update': # tem que arrumar o distances. Eh outro json.
		return json.dumps({'type': type, 'source': source, 'destination': destination, 'distances': last_info})
	elif type is 'trace':
		return json.dumps({'type': type, 'source': source, 'destination': destination, 'hops': last_info})

def decode_message(message):
	data = json.loads(message)
	# Prints if it's data type message
	if data["type"] is 'data':
		pprint(data)
	return data


def send_message(HOST, PORT, message):
	print ("HOST:", HOST)
	udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	dest = (HOST, int(PORT))
	print (dest)
	udp.sendto(message.encode('utf-8'), dest)
	udp.close()

def start_listening(IP, PORT):
	print("Entrou na start_listening")
	udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	orig = (IP, int(PORT))
	udp.bind(orig)
	while True:
		message, client = udp.recvfrom(1024)
		print ("MENSAGEM RECEBIDA", decode_message(message), client)
	udp.close()

def update_routes():
    threading.Timer(PERIOD, update_routes).start()
    for route in routing_table:
        if time.time() > route.ttl + 4*PERIOD :
            routing_table.remove(route)


if __name__ == "__main__":
	main(sys.argv[1:])
