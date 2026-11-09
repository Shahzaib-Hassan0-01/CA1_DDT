// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title  HotelBooking
/// @notice Escrow smart contract between a guest (sender) and a hotel (receiver).
///         The contract is the middle layer: it holds the guest's deposit and
///         releases it to the hotel at check-in, or refunds it on cancellation.
contract HotelBooking {

    // ---------- Data model ----------
    enum Status { Booked, Confirmed, CheckedIn, Cancelled }

    struct Booking {
        address guest;        // sender
        uint256 deposit;      // amount held in escrow (wei)
        uint256 checkInDate;  // Unix timestamp
        Status  status;
    }

    address public immutable hotel;              // receiver (the deployer)
    uint256 public immutable roomPrice;          // required deposit in wei
    uint256 public constant CANCEL_WINDOW = 1 days;
    uint256 public nextBookingId;
    mapping(uint256 => Booking) public bookings;

    // ---------- Events (on-chain audit trail) ----------
    event RoomBooked(uint256 indexed id, address indexed guest, uint256 deposit, uint256 checkInDate);
    event BookingConfirmed(uint256 indexed id);
    event CheckedIn(uint256 indexed id, uint256 amountPaid);
    event BookingCancelled(uint256 indexed id, uint256 refund);

    // ---------- Access control ----------
    modifier onlyHotel() {
        require(msg.sender == hotel, "Only hotel");
        _;
    }

    modifier onlyGuest(uint256 _id) {
        require(msg.sender == bookings[_id].guest, "Only guest");
        _;
    }

    constructor(uint256 _roomPrice) {
        require(_roomPrice > 0, "Price must be > 0");
        hotel = msg.sender;
        roomPrice = _roomPrice;
    }

    // ---------- Transactions ----------

    /// @notice Guest books a room and sends the exact deposit, which is locked in the contract.
    function bookRoom(uint256 _checkInDate) external payable returns (uint256 id) {
        require(msg.sender != hotel, "Hotel cannot book");
        require(msg.value == roomPrice, "Exact deposit required");
        require(_checkInDate > block.timestamp, "Check-in must be in future");

        id = nextBookingId++;
        bookings[id] = Booking(msg.sender, msg.value, _checkInDate, Status.Booked);
        emit RoomBooked(id, msg.sender, msg.value, _checkInDate);
    }

    /// @notice Hotel accepts a pending booking.
    function confirmBooking(uint256 _id) external onlyHotel {
        require(bookings[_id].status == Status.Booked, "Booking not pending");
        bookings[_id].status = Status.Confirmed;
        emit BookingConfirmed(_id);
    }

    /// @notice Guest confirms arrival; the deposit is released to the hotel.
    function checkIn(uint256 _id) external onlyGuest(_id) {
        Booking storage b = bookings[_id];
        require(b.status == Status.Confirmed, "Booking not confirmed");

        // Checks-Effects-Interactions: update state before sending ETH
        b.status = Status.CheckedIn;
        uint256 amount = b.deposit;
        b.deposit = 0;

        (bool ok, ) = payable(hotel).call{value: amount}("");
        require(ok, "Payment failed");
        emit CheckedIn(_id, amount);
    }

    /// @notice Guest cancels at least 1 day before check-in and is refunded automatically.
    function cancelBooking(uint256 _id) external onlyGuest(_id) {
        Booking storage b = bookings[_id];
        require(b.status == Status.Booked || b.status == Status.Confirmed, "Cannot cancel");
        require(block.timestamp + CANCEL_WINDOW <= b.checkInDate, "Too late to cancel");

        b.status = Status.Cancelled;
        uint256 amount = b.deposit;
        b.deposit = 0;

        (bool ok, ) = payable(b.guest).call{value: amount}("");
        require(ok, "Refund failed");
        emit BookingCancelled(_id, amount);
    }

    // ---------- Views (free, no gas) ----------

    function getBooking(uint256 _id) external view returns (Booking memory) {
        return bookings[_id];
    }

    function contractBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
