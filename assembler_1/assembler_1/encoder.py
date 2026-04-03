from opcode_table import OpcodeTable


class Encoder:
    def __init__(self):
        self._optab = OpcodeTable()


    def encode_r_type(self, opcode, rd, funct3, rs1, rs2, funct7):
        return ((funct7 & 0x7F) << 25 | (rs2 & 0x1F) << 20 |
                (rs1 & 0x1F) << 15 | (funct3 & 0x07) << 12 |
                (rd & 0x1F) << 7 | (opcode & 0x7F))

    def encode_i_type(self, opcode, rd, funct3, rs1, imm):
        return ((imm & 0xFFF) << 20 | (rs1 & 0x1F) << 15 |
                (funct3 & 0x07) << 12 | (rd & 0x1F) << 7 | (opcode & 0x7F))

    def encode_s_type(self, opcode, funct3, rs1, rs2, imm):
        imm_hi = (imm >> 5) & 0x7F
        imm_lo = imm & 0x1F
        return ((imm_hi & 0x7F) << 25 | (rs2 & 0x1F) << 20 |
                (rs1 & 0x1F) << 15 | (funct3 & 0x07) << 12 |
                (imm_lo & 0x1F) << 7 | (opcode & 0x7F))

    def encode_b_type(self, opcode, funct3, rs1, rs2, imm):
        b12   = (imm >> 12) & 0x1
        b11   = (imm >> 11) & 0x1
        b10_5 = (imm >> 5)  & 0x3F
        b4_1  = (imm >> 1)  & 0xF
        return ((b12 & 0x1) << 31 | (b10_5 & 0x3F) << 25 |
                (rs2 & 0x1F) << 20 | (rs1 & 0x1F) << 15 |
                (funct3 & 0x07) << 12 | (b4_1 & 0xF) << 8 |
                (b11 & 0x1) << 7 | (opcode & 0x7F))

    def encode_u_type(self, opcode, rd, imm):
        return ((imm & 0xFFFFF) << 12 | (rd & 0x1F) << 7 | (opcode & 0x7F))

    def encode_j_type(self, opcode, rd, imm):
        b20    = (imm >> 20) & 0x1
        b19_12 = (imm >> 12) & 0xFF
        b11    = (imm >> 11) & 0x1
        b10_1  = (imm >> 1)  & 0x3FF
        return ((b20 & 0x1) << 31 | (b10_1 & 0x3FF) << 21 |
                (b11 & 0x1) << 20 | (b19_12 & 0xFF) << 12 |
                (rd & 0x1F) << 7 | (opcode & 0x7F))

    # ── Yüksek seviye encoding ──

    def encode_instruction(self, mnemonic, rd=0, rs1=0, rs2=0, imm=0):
        entry = self._optab.lookup(mnemonic)
        if entry is None:
            return None

        opcode = entry.opcode
        funct3 = entry.funct3 if entry.funct3 is not None else 0
        funct7 = entry.funct7 if entry.funct7 is not None else 0

        if entry.fmt_type == "R":
            return self.encode_r_type(opcode, rd, funct3, rs1, rs2, funct7)

        elif entry.fmt_type == "I":
            # SLLI, SRLI: funct7 immediate'ın üst 7 bitine gömülür
            if mnemonic.upper() in ("SLLI", "SRLI"):
                combined_imm = (funct7 << 5) | (imm & 0x1F)
                return self.encode_i_type(opcode, rd, funct3, rs1, combined_imm)
            if mnemonic.upper() == "ECALL":
                return self.encode_i_type(opcode, 0, 0, 0, 0x000)
            return self.encode_i_type(opcode, rd, funct3, rs1, imm)

        elif entry.fmt_type == "S":
            return self.encode_s_type(opcode, funct3, rs1, rs2, imm)
        elif entry.fmt_type == "B":
            return self.encode_b_type(opcode, funct3, rs1, rs2, imm)
        elif entry.fmt_type == "U":
            return self.encode_u_type(opcode, rd, imm)
        elif entry.fmt_type == "J":
            return self.encode_j_type(opcode, rd, imm)
        return None


    @staticmethod
    def to_hex(code):
        return f"0x{code & 0xFFFFFFFF:08X}" if code is not None else "????????"

    @staticmethod
    def to_binary(code):
        if code is None: return "?" * 32
        b = f"{code & 0xFFFFFFFF:032b}"
        return " ".join(b[i:i+4] for i in range(0, 32, 4))

    @staticmethod
    def to_bytes_le(code):
        if code is None: return [0, 0, 0, 0]
        c = code & 0xFFFFFFFF
        return [(c >> i) & 0xFF for i in (0, 8, 16, 24)]
