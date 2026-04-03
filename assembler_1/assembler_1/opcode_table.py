class OpcodeEntry:

    def __init__(self, mnemonic, fmt_type, opcode, funct3=None, funct7=None, description=""):
        self.mnemonic = mnemonic.upper()
        self.fmt_type = fmt_type.upper()
        self.opcode = opcode
        self.funct3 = funct3
        self.funct7 = funct7
        self.length = 4
        self.description = description

    def __repr__(self):
        f3 = f"f3={self.funct3:03b}" if self.funct3 is not None else "f3=---"
        f7 = f"f7={self.funct7:07b}" if self.funct7 is not None else "f7=---"
        return f"[{self.fmt_type}] {self.mnemonic:<6} opc={self.opcode:07b} {f3} {f7}"


class OpcodeTable:

    def __init__(self):
        self._table = {}
        self._build_table()

    def _build_table(self):

        R = 0b0110011
        self._add(OpcodeEntry("ADD",  "R", R, funct3=0b000, funct7=0b0000000, description="rd = rs1 + rs2"))
        self._add(OpcodeEntry("SUB",  "R", R, funct3=0b000, funct7=0b0100000, description="rd = rs1 - rs2"))
        self._add(OpcodeEntry("AND",  "R", R, funct3=0b111, funct7=0b0000000, description="rd = rs1 & rs2"))
        self._add(OpcodeEntry("OR",   "R", R, funct3=0b110, funct7=0b0000000, description="rd = rs1 | rs2"))
        self._add(OpcodeEntry("SLT",  "R", R, funct3=0b010, funct7=0b0000000, description="rd = (rs1 < rs2) ? 1 : 0"))

        IA = 0b0010011
        self._add(OpcodeEntry("ADDI", "I", IA, funct3=0b000, description="rd = rs1 + imm"))
        self._add(OpcodeEntry("ANDI", "I", IA, funct3=0b111, description="rd = rs1 & imm"))
        self._add(OpcodeEntry("SLLI", "I", IA, funct3=0b001, funct7=0b0000000, description="rd = rs1 << shamt"))
        self._add(OpcodeEntry("SRLI", "I", IA, funct3=0b101, funct7=0b0000000, description="rd = rs1 >> shamt (logical)"))

        IL = 0b0000011
        self._add(OpcodeEntry("LW",   "I", IL, funct3=0b010, description="rd = mem[rs1+imm][31:0]"))
        self._add(OpcodeEntry("LB",   "I", IL, funct3=0b000, description="rd = sign_ext(mem[rs1+imm][7:0])"))

        self._add(OpcodeEntry("JALR", "I", 0b1100111, funct3=0b000, description="rd = PC+4; PC = (rs1+imm) & ~1"))

        self._add(OpcodeEntry("ECALL", "I", 0b1110011, funct3=0b000, description="Sistem çağrısı"))

        S = 0b0100011
        self._add(OpcodeEntry("SW",   "S", S, funct3=0b010, description="mem[rs1+imm][31:0] = rs2"))
        self._add(OpcodeEntry("SB",   "S", S, funct3=0b000, description="mem[rs1+imm][7:0] = rs2[7:0]"))

        B = 0b1100011
        self._add(OpcodeEntry("BEQ",  "B", B, funct3=0b000, description="if(rs1 == rs2) PC += imm"))
        self._add(OpcodeEntry("BNE",  "B", B, funct3=0b001, description="if(rs1 != rs2) PC += imm"))
        self._add(OpcodeEntry("BLT",  "B", B, funct3=0b100, description="if(rs1 < rs2) PC += imm"))

        self._add(OpcodeEntry("LUI",  "U", 0b0110111, description="rd = imm << 12"))

        self._add(OpcodeEntry("JAL",  "J", 0b1101111, description="rd = PC+4; PC += imm"))

    def _add(self, entry):
        self._table[entry.mnemonic] = entry

    def lookup(self, mnemonic):
        return self._table.get(mnemonic.upper(), None)

    def contains(self, mnemonic):
        return mnemonic.upper() in self._table

    def get_all_mnemonics(self):
        return sorted(self._table.keys())

    def get_by_format(self, fmt_type):
        return [e for e in self._table.values() if e.fmt_type == fmt_type.upper()]

    def size(self):
        return len(self._table)

    def print_table(self):
        print(f"\n{'='*80}")
        print(f"{'OPCODE TABLE (OPTAB) — 20 Komutluk Alt Küme':^80}")
        print(f"{'='*80}")
        print(f"{'Mnemonic':<8} {'Fmt':<4} {'Opcode':>9} {'funct3':>8} {'funct7':>11}  {'Açıklama'}")
        print(f"{'-'*80}")
        for fmt in ["R", "I", "S", "B", "U", "J"]:
            entries = sorted(self.get_by_format(fmt), key=lambda x: x.mnemonic)
            if entries:
                print(f"  ── {fmt}-type ({len(entries)} komut) ──")
                for e in entries:
                    f3 = f"0b{e.funct3:03b}" if e.funct3 is not None else "   ---"
                    f7 = f"0b{e.funct7:07b}" if e.funct7 is not None else "       ---"
                    print(f"  {e.mnemonic:<8} {e.fmt_type:<4} 0b{e.opcode:07b} {f3:>8} {f7:>11}  {e.description}")
        print(f"{'='*80}")
        print(f"  Toplam: {self.size()} komut | 6 format | 8 farklı opcode")
        print(f"{'='*80}\n")


PSEUDO_INSTRUCTIONS = {
    "NOP":  {"base": "ADDI", "description": "ADDI x0, x0, 0"},
    "MV":   {"base": "ADDI", "description": "ADDI rd, rs, 0"},
    "LI":   {"base": "ADDI", "description": "ADDI rd, x0, imm"},
    "NEG":  {"base": "SUB",  "description": "SUB rd, x0, rs"},
    "J":    {"base": "JAL",  "description": "JAL x0, offset"},
    "JR":   {"base": "JALR", "description": "JALR x0, rs, 0"},
    "RET":  {"base": "JALR", "description": "JALR x0, x1, 0"},
    "CALL": {"base": "JAL",  "description": "JAL x1, offset"},
    "BEQZ": {"base": "BEQ",  "description": "BEQ rs, x0, offset"},
    "BNEZ": {"base": "BNE",  "description": "BNE rs, x0, offset"},
}


if __name__ == "__main__":
    optab = OpcodeTable()
    optab.print_table()
    print("Desteklenen pseudo-komutlar:")
    for name, info in sorted(PSEUDO_INSTRUCTIONS.items()):
        print(f"  {name:<6} → {info['description']}")
