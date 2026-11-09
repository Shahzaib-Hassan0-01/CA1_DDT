"""
book_room.py - books a room on an already-deployed HotelBooking contract,
sending the deposit (roomPrice) from a guest account.

Usage (Ganache running, from the repo folder):
    python scripts/book_room.py <contract_address> [guest_account_index]

guest_account_index defaults to 1 (the 2nd account; account 0 is the hotel).
"""
import json
import sys
from pathlib import Path

from web3 import Web3

GANACHE_URL = "http://127.0.0.1:8545"
CHECK_IN_DATE = 1893456000  # 1 Jan 2030 (Unix timestamp)

if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/book_room.py <contract_address> [guest_account_index]")

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise SystemExit(f"Cannot reach Ganache at {GANACHE_URL} - start it with: ganache")

abi = json.loads(Path(__file__).with_name("HotelBooking.json").read_text())["abi"]
address = Web3.to_checksum_address(sys.argv[1])
if w3.eth.get_code(address) in (b"", b"\x00"):
    raise SystemExit(f"No contract at {address} - was Ganache restarted? Redeploy in Remix.")

c = w3.eth.contract(address=address, abi=abi)
guest = w3.eth.accounts[int(sys.argv[2]) if len(sys.argv) > 2 else 1]
price = c.functions.roomPrice().call()


def eth(wei):
    return f"{w3.from_wei(wei, 'ether')} ETH"


print(f"Contract : {address}")
print(f"Hotel    : {c.functions.hotel().call()}")
print(f"Guest    : {guest}  (balance {eth(w3.eth.get_balance(guest))})")
print(f"Deposit  : {eth(price)}\n")

tx = c.functions.bookRoom(CHECK_IN_DATE).transact({"from": guest, "value": price})
receipt = w3.eth.wait_for_transaction_receipt(tx)
event = c.events.RoomBooked().process_receipt(receipt)[0]["args"]

print("bookRoom() transaction mined" if receipt.status == 1 else "bookRoom() FAILED")
print(f"  tx hash         : {Web3.to_hex(receipt.transactionHash)}")
print(f"  block           : {receipt.blockNumber}")
print(f"  gas used        : {receipt.gasUsed}")
print(f"  RoomBooked event: booking id = {event['id']}, deposit = {eth(event['deposit'])}")
print(f"\nGuest balance now   : {eth(w3.eth.get_balance(guest))}")
print(f"Contract balance now: {eth(c.functions.contractBalance().call())}  (deposit held in escrow)")
