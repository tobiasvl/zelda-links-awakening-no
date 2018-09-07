from collections import namedtuple

# Describe the location of a Map pointers table
MapDescriptor = namedtuple('MapDescriptor', ['name', 'address', 'length', 'data_base_address', 'rooms'])
# Describe the location of an area containing Rooms
RoomsDescriptor = namedtuple('RoomsDescriptor', ['name', 'address', 'length'])

# Represent a room on a Map
RoomPointer = namedtuple('RoomPointer', ['index', 'address'])
# Represent a Room and its data
class Room:
    def __init__(self, address, length, data):
        self.label = None
        self.address = address
        self.length = length
        self.data = data

class MapParser:
    """Parse a map and its rooms from a MapDescriptor

    Rooms can be divided in several memory areas - this is why a MapDescriptor
    may contain more than one RoomDescriptor.

    Furthermore, some Rooms may be unused in the map.
    """
    def __init__(self, rom_path, map_descriptor):
        self.map_descriptor = map_descriptor
        self.name = self.map_descriptor.name

        with open(rom_path, 'rb') as rom_file:
            rom = rom_file.read()
            self.room_pointers = self._parse_pointers_table(rom, map_descriptor)
            self.rooms_parsers = self._parse_rooms(rom, map_descriptor.rooms)

    def room_for_pointer(self, room_pointer):
        """Given a pointer in the map pointers table, return the associated room."""
        room_address = room_pointer.address
        for rooms_parser in self.rooms_parsers:
            for room in rooms_parser.rooms:
                if room.address == room_address:
                    return room
        raise Exception("Cannot find a room for room pointer '0x{:X}'".format(room_address))

    def room_address(self, room_index, partial_pointer):
        """Return the actual address of the room data from the partial pointer"""

        # Retrieve the base address of data for this room
        data_base_address = self.map_descriptor.data_base_address
        # (data_base_address is allowed to be a lambda expression)
        if callable(data_base_address):
            data_base_address = data_base_address(room_index)

        # Compute the room data address
        return data_base_address + partial_pointer - 0x4000

    def _parse_pointers_table(self, rom, map_descriptor):
        """Return an array of words in the pointers table"""
        # Figure out where the bytes for this pointer are located
        pointers_table_address = map_descriptor.address
        rooms_count = map_descriptor.length // 2
        room_pointers = []

        for room_index in range(0, rooms_count):
            pointer_address = pointers_table_address + (room_index * 2)

            # Grab the two bytes making up the partial pointer
            lower_byte = rom[pointer_address]
            higher_byte = rom[pointer_address + 1]

            # Combine the two bytes into a single pointer (0x byte1 byte2)
            partial_pointer = (higher_byte << 8) + lower_byte

            # Compute the actual address of the room data
            room_address = self.room_address(room_index, partial_pointer)

            # Store the data into the parsed pointers table
            room_pointer = RoomPointer(index = room_index, address = room_address)
            room_pointers.append(room_pointer)

        return room_pointers

    def _parse_rooms(self, rom, rooms_descriptors):
        """Return an array of room parsers for the given room descriptors"""
        rooms_parsers = []
        for rooms_descriptor in rooms_descriptors:
            rooms_parsers.append(RoomsParser(rom, rooms_descriptor))
        return rooms_parsers


class RoomsParser:
    """Parse an area containing rooms description and blocks"""
    def __init__(self, rom, rooms_descriptor):
        self.name = rooms_descriptor.name
        self.rooms = self._parse(rom, rooms_descriptor)

    def _parse(self, rom, descriptor):
        """Walk the rooms table, and parse data for each room"""
        rooms = []
        address = descriptor.address
        end_address = descriptor.address + descriptor.length

        while address < end_address:
            room = self._parseRoom(rom, address)
            rooms.append(room)

            address += room.length

        return rooms

    def _parseRoom(self, rom, address):
        """Parse a room data, until we reach the end marker"""
        END_BYTE = 0xFE

        data = []
        i = 0
        roomEnd = False

        while not roomEnd:
            byte = rom[address + i]
            data.append(byte)

            i += 1
            roomEnd = (byte == END_BYTE)

        return Room(address, i, data)
