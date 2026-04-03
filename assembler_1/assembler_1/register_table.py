"""
PicoRV32 (RV32I) Assembler - Register Tablosu
==============================================
32 adet genel amaçlı register: x0 (daima 0) ... x31
Hem xN formatını hem ABI isimlerini destekler.
"""


class RegisterTable:
    _ABI_MAP = {
        0: "zero", 1: "ra",  2: "sp",  3: "gp",  4: "tp",
        5: "t0",   6: "t1",  7: "t2",  8: "s0",  9: "s1",
        10: "a0", 11: "a1", 12: "a2", 13: "a3", 14: "a4",
        15: "a5", 16: "a6", 17: "a7", 18: "s2", 19: "s3",
        20: "s4", 21: "s5", 22: "s6", 23: "s7", 24: "s8",
        25: "s9", 26: "s10", 27: "s11", 28: "t3", 29: "t4",
        30: "t5", 31: "t6",
    }

    def __init__(self):
        self._name_to_num = {}
        for num in range(32):
            self._name_to_num[f"x{num}"] = num
            if num in self._ABI_MAP:
                self._name_to_num[self._ABI_MAP[num]] = num
        self._name_to_num["fp"] = 8  # fp = s0 = x8

    def get_number(self, name):
        return self._name_to_num.get(name.lower(), None)

    def is_valid_register(self, name):
        return name.lower() in self._name_to_num

    def get_abi_name(self, number):
        return self._ABI_MAP.get(number, None)

    def print_table(self):
        print(f"\n{'='*50}")
        print(f"{'REGISTER TABLE':^50}")
        print(f"{'='*50}")
        for num in range(32):
            abi = self._ABI_MAP.get(num, "?")
            print(f"  x{num:<3}  {abi:<5}  ({num:05b})")
        print(f"{'='*50}\n")
