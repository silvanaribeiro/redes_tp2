import socket
from socket import AF_INET, SOCK_DGRAM
import sys, getopt
import subprocess
import json
from pprint import pprint

def main(argv):
	opts = None
	args = None
	ADDR = None
	PERIOD = None
	STARTUP = None
	# Temos que pensar melhor nisso aqui. Cada roteador tem um routing table.
	routing_table = {}
	try:
		opts, args = getopt.getopt(argv, "")
	except getopt.GetoptError:
		print("router.py <ADDR> <PERIOD> [STARTUP]")
	
	ADDR = args[0]
	PERIOD = args[1]
	if len(args) == 3:
		STARTUP = args[2]

	print(ADDR, PERIOD, STARTUP)

# receives string 'add' or 'del'. Pelo que eu entendi a gente só vai usar isso pra inicializar os roteadores mesmo. Talvez nem precisasse estar no programa.	
def loopback(operation):
	 subprocess.call(['./tests/lo-adresses.sh',operation]) 
	 
def add_ve(ip, weight, routing_table):
	routing_table[ip] = weight
	return routing_table

def del_ve(ip, routing_table):
	return routing_table.pop(ip)
	
def read_file(file_name, routing_table):
    with open(file_name, "r") as f:
        lines = f.readlines()
        for line in lines:
            command = line.replace('\n', '')
            commands = command.split(" ")
            print(commands)
            if commands[0] != 'add':
                print("Inavlid command was read in startup file:", commands[0])
            if len(commands) != 3:
                print("Inavlid format was read in startup file:", commands)
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


		
if __name__ == "__main__":
	main(sys.argv[1:])
