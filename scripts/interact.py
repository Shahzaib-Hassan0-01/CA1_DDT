"""
interact.py - deploys HotelBooking to Ganache and tests every function with web3.py.

Run Ganache first (keep its window open), then from the repo folder:
    python scripts/interact.py
"""
import json
import time
from pathlib import Path

from web3 import Web3

GANACHE_URL = "http://127.0.0.1:8545"
ARTIFACT = Path(__file__).with_name("HotelBooking.json")   # ABI + bytecode
CHECK_IN_DATE = 1893456000                                  # 1 Jan 2030 (Unix timestamp)
STATUS = ["Booked", "Confirmed", "CheckedIn", "Cancelled"]

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise SystemExit(f"Cannot reach Ganache at {GANACHE_URL} - start it with: ganache")

artifact = json.loads(ARTIFACT.read_text())
hotel, guest, guest2 = w3.eth.accounts[0], w3.eth.accounts[1], w3.eth.accounts[2]
price = w3.to_wei(1, "ether")
passed = 0
total = 0


def eth(address):
    return f"{w3.from_wei(w3.eth.get_balance(address), 'ether'):.4f} ETH"


def send(fn, sender, value=0):
    """Send a transaction and wait for it to be mined."""
    tx = fn.transact({"from": sender, "value": value})
    return w3.eth.wait_for_transaction_receipt(tx)


def check(name, condition):
    global passed, total
    total += 1
    passed += bool(condition)
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}")


def expect_revert(name, fn, sender, reason, value=0):
    """The call must be rejected by the contract with the given reason."""
    global passed, total
    total += 1
    try:
        fn.call({"from": sender, "value": value})
        print(f"  [FAIL] {name} - was NOT rejected")
    except Exception as e:  # Ganache returns the revert reason inside the error message
        ok = reason in str(e)
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} -> reverted: \"{reason}\"")


print(f"Connected to Ganache (chain ID {w3.eth.chain_id}), block {w3.eth.block_number}")
print(f"Hotel  (receiver): {hotel}  {eth(hotel)}")
print(f"Guest  (sender)  : {guest}  {eth(guest)}")
print(f"Guest2 (sender)  : {guest2}  {eth(guest2)}\n")

# 1. Deploy - the hotel is the deployer
print("1. Deploy HotelBooking (room price 1 ETH)")
Factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
receipt = send(Factory.constructor(price), hotel)
c = w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])
print(f"  Contract address: {c.address}")
check("hotel set to deployer", c.functions.hotel().call() == hotel)

# 2. Book
print("\n2. Guest books a room and pays the deposit")
expect_revert("wrong deposit amount", c.functions.bookRoom(CHECK_IN_DATE), guest, "Exact deposit required", price // 2)
expect_revert("hotel tries to book", c.functions.bookRoom(CHECK_IN_DATE), hotel, "Hotel cannot book", price)
receipt = send(c.functions.bookRoom(CHECK_IN_DATE), guest, price)
event = c.events.RoomBooked().process_receipt(receipt)[0]["args"]
print(f"  RoomBooked event: id={event['id']} deposit={w3.from_wei(event['deposit'], 'ether')} ETH  gas used={receipt.gasUsed}")
check("deposit locked in contract (1 ETH)", c.functions.contractBalance().call() == price)

# 3. Confirm
print("\n3. Hotel confirms the booking")
expect_revert("guest calls confirmBooking", c.functions.confirmBooking(0), guest, "Only hotel")
expect_revert("check-in before confirmation", c.functions.checkIn(0), guest, "Booking not confirmed")
send(c.functions.confirmBooking(0), hotel)
check("status is Confirmed", STATUS[c.functions.getBooking(0).call()[3]] == "Confirmed")

# 4. Check in
print("\n4. Guest checks in - deposit released to hotel")
expect_revert("another user checks in", c.functions.checkIn(0), guest2, "Only guest")
hotel_before = w3.eth.get_balance(hotel)
send(c.functions.checkIn(0), guest)
check("hotel received 1 ETH", w3.eth.get_balance(hotel) - hotel_before == price)
check("contract balance back to 0", c.functions.contractBalance().call() == 0)

# 5. Cancel and refund
print("\n5. Second guest books, then cancels - automatic refund")
send(c.functions.bookRoom(CHECK_IN_DATE), guest2, price)
before = w3.eth.get_balance(guest2)
receipt = send(c.functions.cancelBooking(1), guest2)
gas_cost = receipt.gasUsed * receipt.effectiveGasPrice
check("guest2 refunded 1 ETH", w3.eth.get_balance(guest2) - before + gas_cost == price)
expect_revert("cancel the same booking twice", c.functions.cancelBooking(1), guest2, "Cannot cancel")

print(f"\nFinal balances: hotel {eth(hotel)} | guest {eth(guest)} | guest2 {eth(guest2)}")
print(f"RESULT: {passed}/{total} tests passed")
