import struct
from pprint import pprint


def read_u8(f):
    return int.from_bytes(f.read(1), 'little')


def read_u16(f):
    return int.from_bytes(f.read(2), 'little')


def read_u32(f):
    return int.from_bytes(f.read(4), 'little')


def read_s8(f):
    return int.from_bytes(f.read(1), 'little', signed=True)


def read_s16(f):
    return int.from_bytes(f.read(2), 'little', signed=True)


def read_s32(f):
    return int.from_bytes(f.read(4), 'little', signed=True)


def read_float(f):
    return struct.unpack("<f", f.read(4))[0]


def extract_data(filename):
    """
    player_starting_locations format
        first_element   +0xC (element length 52: 0x34)
            40 CE AF 10 3F 9D A1 77 40 18 7A 3A BF 49 0F DB 00 00 00 00 00 0D
            C0 D7 1E 30 41 27 8C D7 3A A3 06 1A BF 66 39 99 00 01 00 00 00 01
            big endian
            +0  float   x
            +4  float   y
            +8  float   z
            +12 float   facing (radians)
            +13 int8    bsp index? (-1 = NONE)
            +14 int8    team_index (0 or 1)
            +15 int8    type 3
            +16 int8    type 2
            +17 int8    type 1
            +18 int8    type 0

        types:
            0x0     none
            0x1     ctf
            0x2     slayer
            0x3     oddball
            0x4     king
            0x5     race
            0x6     terminator
            0x7     stub
            0x8     ignored1
            0x9     ignored2
            0xA     ignored3
            0xB     ignored4
            0xC     all games
            0xD     all games except ctf
            0xE     all games except ctf and race
    """

    STARTING_OFFSET = 0xC

    locations = dict(
        x=(0x0, read_float),
        y=(0x4, read_float),
        z=(0x8, read_float),
        facing=(0xC, read_float),
        bsp_index=(0xD, read_u8),
        team_index=(0xE, read_u8),
        type_3=(0xE, read_u8),
        type_2=(0xF, read_u8),
        type_1=(0x10, read_u8),
        type_0=(0x11, read_u8),
    )

    with open(filename, 'rb') as f:

        results = {}
        # f.seek(STARTING_OFFSET)
        for name, (offset, func) in locations.items():
            f.seek(STARTING_OFFSET + offset)
            value = func(f)
            results[name] = value
        pprint(results)


if __name__ == '__main__':

    extract_data(r"L:\ce\tags\levels\test\chillout\chillout.scenario")
