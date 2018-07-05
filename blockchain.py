from time import time, sleep
import json
import hashlib
from flask import Flask, jsonify, request
from uuid import uuid4
from textwrap import dedent
from urllib.parse import urlparse
import requests

class Blockchain(object):
	def __init__(self):
		self.current_transactions = []

		self.chain = []

		self.new_block(previous_hash=1, nonce=100, hash_value="0000")

		self.nodes = set()
		self.nodes_address = set()
		# self.nodes_name = set()

	def new_block(self, hash_value, nonce, previous_hash):
		block = {
			'index': len(self.chain) + 1,
			'timestamp': time(),
			'transactions': self.current_transactions,
			'nonce': nonce,
			'hash': hash_value,
			# 'previous_hash': previous_hash or self.hash(self.chain[-1]),
			'previous_hash': previous_hash,
		}

		self.current_transactions = []

		self.chain.append(block)
	
		return block

	
	def new_transaction(self, sender, recipient, MTC_amount):
		self.current_transactions.append({
			'sender': sender,
			'recipient': recipient,
			'MTC_amount': MTC_amount,
			})
	
		return self.last_block['index'] + 1

	@property
	def last_block(self):
		return self.chain[-1]

	@staticmethod
	def hash(block):
		block_string = json.dumps(block, sort_keys=True).encode()
		
		return hashlib.sha256(block_string).hexdigest()

	
	def proof_of_work(self, previous_hash, hashtree):
		nonce = 0
		while self.valid_proof(previous_hash, hashtree, nonce) is False:
			nonce += 1

		return nonce
	
	@staticmethod
	def valid_proof(previous_hash, hashtree, nonce):
		guess = f'{previous_hash}{hashtree}{nonce}'.encode()
		guess_hash = hashlib.sha256(guess).hexdigest()

		return guess_hash[:4] == "0000"

	def get_hashtree(self):
		n = 0
		length = len(self.chain)
		hashes = []
		for n in range(length - 1):
			guess = f'{self.chain[n]}{self.chain[n + 1]}'.encode()
			guess_hash = hashlib.sha256(guess).hexdigest()
			# print(guess_hash)
			hashes.append(guess_hash)

		m = 0
		length = len(hashes)
		guess = ""
		for n in range(length - 1):
			guess += hashes[m]

		guess = guess.encode()
		hashtree = hashlib.sha256(guess).hexdigest()
		# print(hashtree)
		return hashtree


	def register_node(self,node):
		# parsed_url = urlparse(address)
		# self.nodes.add(parsed_url.netloc)
		self.nodes.add(node)
		self.register_node_address(node.identifire)
		# self.register_node_name(node.name)

	def register_node_address(self, address):
		self.nodes_address.add(address)

	# def register_node_name(self, name):
	# 	self.nodes_name.add(name)

	def valid_chain(self, chain):
		last_block = chain[0]
		current_index = 1

		while current_index < len(chain):
			block = chain[current_index]
			print(f'{last_block}')
			print(f'{block}')
			print("\n--------------\n")

			if block['previous_hash'] != self.hash(last_block):
				return False

			if not self.valid_proof(last_block['proof'], block['proof']):
				return False

			last_block = block
			current_index += 1

		return True

	def resolve_conflicts(self):
		# neighbours = self.nodes_name
		neighbours = self.nodes_address
		new_chain = None
		max_length = len(self.chain)

		for node in neighbours:
			response = requests.get(f'http://{node}/chain')

			if response.status_code == 200:
				length = response.json()['length']
				chain = response.json()['chain']

				if length > max_length and self.valid_chain(chain):
					max_length = length
					new_chain = chain

		if new_chain:
			self.chain = new_chain
			return True

		return False




app = Flask(__name__)

# node_identifire = str(uuid4()).replace('-', '')

class Node(object):
	def __init__(self):
		# self.identifire = str(uuid4()).replace('-', '')
		# self.name = "localhost:5000"
		self.identifire = "127.17.0.1:32770"
		self.balance = 0

		blockchain.register_node(self)

		# ノードを登録する
		# よくわからないけどこれをやるとおかしくなる
		# payload = {'nodes': '0.0.0.0:5000'}
		# response = requests.post('http://0.0.0.0:5001/nodes/register', json=payload )
		# print(response.text)

	# MTCを受け取る
	def receive_MTC(self, MTC_amount):
		self.balance += MTC_amount

	def mining(self):
		# response = requests.get('http://172.17.0.1:32771/nodes/resolve')
		# print(response.text)

		# response = requests.get('http://172.17.0.1:32771/mine')
		response = requests.get('http://192.168.100.101:5000/mine')
		print(response.text)

blockchain = Blockchain()

node = Node()

interval = 1
while True:
	node.mining()
	sleep(interval)

@app.route('/mine', methods=['GET'])
def mine():
	last_block = blockchain.last_block
	previous_hash = last_block['hash']

	hashtree = blockchain.get_hashtree()

	nonce = blockchain.proof_of_work(previous_hash, hashtree)

	guess = f'{previous_hash}{hashtree}{nonce}'.encode()
	hash_value = hashlib.sha256(guess).hexdigest()

	blockchain.new_transaction(
		sender="0",
		recipient=node.identifire,
		MTC_amount=1,
	)

	node.receive_MTC(1)

	block = blockchain.new_block(hash_value, nonce, previous_hash)

	responce = {
		'message': '新しいブロックを採掘しました',
		'index': block['index'],
		'transactions': block['transactions'],
		'nonce': block['nonce'],
		'hash': block['hash'],
		'previous_hash': block['previous_hash'],
		'hashtree': hashtree,
	}

	return jsonify(responce), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
	values = request.get_json()

	required = ['recipient', 'MTC_amount']
	if not all(k in values for k in required):
		return 'Missing values', 400

	MTC_amount = values['MTC_amount']
	recipient = values['recipient']
	if MTC_amount > node.balance:
		return 'Error: Insufficient funds', 400
	node.balance -= MTC_amount

	payload = {'MTC_amount' : MTC_amount}
	r = requests.post(f'http://{recipient}/send', json=payload)

	# for i in blockchain.nodes_address:
	# 	if (str(values['recipient']) in i):
	index = blockchain.new_transaction(node.identifire, values['recipient'], values['MTC_amount'])

	response = {'message': f'トランザクションはブロック{index}に追加されました',}
	return jsonify(response), 201
		# else:
		# 	return 'Error: does not exist node', 400

@app.route('/chain', methods=['GET'])
def full_chain():
	responce = {
		'chain': blockchain.chain,
		'length': len(blockchain.chain),
	}
	return jsonify(responce), 200

# ノードを追加するときに使う
class Additional_Node(object):
	def __init__(self,identifire):
		self.identifire = identifire
		self.balance = 0

		blockchain.register_node(self)

	# MTCを受け取る
	def receive_MTC(self, MTC_amount):
		self.balance += MTC_amount

@app.route('/nodes/register', methods=['POST'])
def register_node():
	values = request.get_json()
	nodes = values.get('nodes')

	additional_node_identifire = str(nodes)

	if nodes is None:
		return "Error: 有効ではないノードのリストです", 400

	add_node = Additional_Node(additional_node_identifire)

	response = {
		'message': '新しいノードが追加されました',
		'total_nodes': list(blockchain.nodes_address),
	}
	return jsonify(response), 201

# 参加ノードの一覧を得る
@app.route('/nodes/list', methods=['GET'])
def list_node():
	response = {
		'参加ノード一覧': list(blockchain.nodes_address),
	}
	return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
	replaced = blockchain.resolve_conflicts()

	if replaced:
		response = {
			'message': 'チェーンが置き換えられました',
			'new_chain': blockchain.chain,
		}
	else:
		response = {
			'message': 'チェーンが確認されました',
			'chain': blockchain.chain,
		}

	return jsonify(response), 200

# 所有MTC量を調べる
@app.route('/nodes/check', methods=['GET'])
def check_balance():
	response = {
		'balance': node.balance
	}
	return jsonify(response), 200

# MTCを送る。直接呼び出さない
@app.route('/send', methods=['POST'])
def send():
	values = request.get_json()
	MTC_amount = values['MTC_amount']
	if MTC_amount is None:
		return "Error: MTC量を指定してください", 400

	node.balance += MTC_amount

	response = {'message': f'入金を確認しました{MTC_amount}'}
	return jsonify(response), 201

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000)