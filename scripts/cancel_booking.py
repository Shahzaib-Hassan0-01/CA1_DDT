"""
cancel_booking.py - the guest cancels a booking and is refunded automatically.

Usage (Ganache running, from the repo folder):
    python scripts/cancel_booking.py <contract_address> <booking_id>
"""
import json
import sys
from pathlib import Path

from web3 import Web3

GANACHE_URL = "http://127.0.0.1:8545"
STATUS = ["Booked", "Confirmed", "CheckedIn", "Cancelled"]

if len(sys.argv) < 3:
    raise SystemExit("Usage: python scripts/cancel_booking.py <contract_address> <booking_id>")

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise SystemExit(f"Cannot reach Ganache at {GANACHE_URL} - start it with: ganache")

abi = json.loads(Path(__file__).with_name("HotelBooking.json").read_text())["abi"]
c = w3.eth.contract(address=Web3.to_checksum_address(sys.argv[1]), abi=abi)
booking_id = int(sys.argv[2])
guest, deposit, check_in, status = c.functions.getBooking(booking_id).call()


def eth(wei):
    return f"{w3.from_wei(wei, 'ether')} ETH"


print(f"Booking {booking_id}: guest {guest}, deposit {eth(deposit)}, status {STATUS[status]}")
before = w3.eth.get_balance(guest)
print(f"Guest balance before cancel: {eth(before)}\n")

tx = c.functions.cancelBooking(booking_id).transact({"from": guest})   # sent by the booking's own guest
receipt = w3.eth.wait_for_transaction_receipt(tx)
event = c.events.BookingCancelled().process_receipt(receipt)[0]["args"]

print("cancelBooking() transaction mined" if receipt.status == 1 else "cancelBooking() FAILED")
print(f"  tx hash               : {Web3.to_hex(receipt.transactionHash)}")
print(f"  block                 : {receipt.blockNumber}")
print(f"  BookingCancelled event: booking id = {event['id']}, refund = {eth(event['refund'])}")
print(f"\nGuest balance after cancel : {eth(w3.eth.get_balance(guest))}")
print(f"Booking status now         : {STATUS[c.functions.getBooking(booking_id).call()[3]]}")
print(f"Contract balance now       : {eth(c.functions.contractBalance().call())}")
