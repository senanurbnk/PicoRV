"""
iss.py — Minimal RV32I Komut-Set Simulatoru (Instruction Set Simulator)
========================================================================
Amac: FPGA/Gowin olmadan, kendi linker'imizin urettigi GERCEK makine kodunu
calistirmak. Ozellikle loader.s'i (Faz 3) host paketleriyle besleyip dogru
calistigini kanitlamak icin. Ayrica T1/T2/T3 uygulamalarini da kosturabilir.

Desteklenen: PicoRV32 RV32I cekirdegi + bizim assembler'in urettigi alt kume
(LUI, AUIPC, JAL, JALR, BEQ/BNE/BLT/BGE/BLTU/BGEU, LB/LBU/LW, SB/SH/SW,
ADDI/SLTI/XORI/ORI/ANDI/SLLI/SRLI/SRAI, ADD/SUB/SLL/SLT/SLTU/XOR/SRL/SRA/OR/AND,
ECALL=halt). Little-endian.

Bellek haritasi (soc_top.v ile ayni):
    0x0000_0000 - 0x0000_3FFF  BRAM (16 KB)
    0x2000_0000 +0/+4          UART (DATA / STATUS)  -> UartModel
    0x1000_0000                 GPIO (LED)            -> son yazilan deger

NOT: Bu donanimin birebir kopyasi degil; mimari-seviye davranis modelidir.
Donanim ayrica Gowin sentezi + board ile dogrulanacak. Ama loader'in komut
akisini, CRC'sini, bellek yazimini ve jump'ini sentez OLMADAN kanitlar.
"""

BRAM_SIZE = 0x4000           # 16 KB
UART_BASE = 0x20000000
GPIO_BASE = 0x10000000


def _sext(val, bits):
    m = 1 << (bits - 1)
    return (val ^ m) - m


class UartModel:
    """uart.v MMIO davranisi: STATUS bit0=rx_valid, bit1=tx_busy(=0).
    rx_queue'dan okur; tx'i listeye yazar."""
    def __init__(self, rx_bytes=b""):
        self.rx = list(rx_bytes)
        self.tx = bytearray()

    def read(self, off):
        if off == 0x00:                      # DATA
            return self.rx.pop(0) if self.rx else 0
        if off == 0x04:                      # STATUS
            rx_valid = 1 if self.rx else 0
            tx_busy  = 0                     # anlik TX
            return (tx_busy << 1) | rx_valid
        return 0

    def write(self, off, val):
        if off == 0x00:                      # DATA -> TX
            self.tx.append(val & 0xFF)


class ISS:
    def __init__(self, uart=None, max_steps=5_000_000):
        self.mem = bytearray(BRAM_SIZE)
        self.reg = [0] * 32
        self.pc = 0
        self.uart = uart or UartModel()
        self.gpio = 0            # GPIO+0: LED cikis degeri (soft 1=ON)
        self.button = 0          # GPIO+4: buton girisi (1=basili)
        self.gpio_writes = []    # LED'e yazilan deger gecmisi (test/blink dogrulamasi)
        self.max_steps = max_steps
        self.halted = False
        self.halt_reason = None

    # --- bellek erisimi ---
    def _load(self, addr, size, signed):
        addr &= 0xFFFFFFFF
        if (addr & 0xF0000000) == UART_BASE:
            v = self.uart.read(addr & 0xF)
        elif (addr & 0xF0000000) == GPIO_BASE:
            off = addr & 0xF
            if off == 0x4:
                v = 1 if self.button else 0     # GPIO+4: buton
            else:
                v = self.gpio                   # GPIO+0: son yazilan LED degeri
        elif addr < BRAM_SIZE:
            v = 0
            for i in range(size):
                v |= self.mem[addr + i] << (8 * i)
        else:
            v = 0
        if signed:
            v = _sext(v, size * 8)
        return v & 0xFFFFFFFF if not signed else v

    def _store(self, addr, size, val):
        addr &= 0xFFFFFFFF
        val &= 0xFFFFFFFF
        if (addr & 0xF0000000) == UART_BASE:
            self.uart.write(addr & 0xF, val)
        elif (addr & 0xF0000000) == GPIO_BASE:
            if (addr & 0xF) == 0:               # GPIO+0: LED yaz
                self.gpio = val & 0x3F
                self.gpio_writes.append(self.gpio)
        elif addr < BRAM_SIZE:
            for i in range(size):
                self.mem[addr + i] = (val >> (8 * i)) & 0xFF

    def load_image(self, image, base=0):
        self.mem[base:base + len(image)] = image

    # --- calistir ---
    def run(self, entry=0, stop_on_pc=None):
        self.pc = entry
        steps = 0
        while not self.halted:
            if steps >= self.max_steps:
                self.halt_reason = "max_steps"
                break
            if stop_on_pc is not None and self.pc == stop_on_pc and steps > 0:
                self.halt_reason = "stop_on_pc"
                break
            self._step()
            steps += 1
            self.reg[0] = 0
        self.steps = steps
        return self.halt_reason

    def _step(self):
        pc = self.pc
        if pc + 4 > BRAM_SIZE or pc < 0:
            self.halted = True; self.halt_reason = f"pc_out_of_range:0x{pc:X}"; return
        inst = (self.mem[pc] | (self.mem[pc+1] << 8) |
                (self.mem[pc+2] << 16) | (self.mem[pc+3] << 24))
        op = inst & 0x7F
        rd = (inst >> 7) & 0x1F
        f3 = (inst >> 12) & 0x7
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F
        f7 = (inst >> 25) & 0x7F
        R = self.reg
        next_pc = (pc + 4) & 0xFFFFFFFF

        def u2s(x): return _sext(x & 0xFFFFFFFF, 32)

        if op == 0x37:        # LUI
            R[rd] = inst & 0xFFFFF000
        elif op == 0x17:      # AUIPC
            R[rd] = (pc + (inst & 0xFFFFF000)) & 0xFFFFFFFF
        elif op == 0x6F:      # JAL
            imm = _sext(((inst >> 31) & 1) << 20 | ((inst >> 12) & 0xFF) << 12 |
                        ((inst >> 20) & 1) << 11 | ((inst >> 21) & 0x3FF) << 1, 21)
            R[rd] = next_pc
            next_pc = (pc + imm) & 0xFFFFFFFF
        elif op == 0x67:      # JALR
            imm = _sext((inst >> 20) & 0xFFF, 12)
            t = next_pc
            next_pc = (R[rs1] + imm) & 0xFFFFFFFE
            R[rd] = t
        elif op == 0x63:      # branch
            imm = _sext(((inst >> 31) & 1) << 12 | ((inst >> 7) & 1) << 11 |
                        ((inst >> 25) & 0x3F) << 5 | ((inst >> 8) & 0xF) << 1, 13)
            a, b = R[rs1], R[rs2]
            take = False
            if   f3 == 0: take = (a == b)                       # BEQ
            elif f3 == 1: take = (a != b)                       # BNE
            elif f3 == 4: take = (u2s(a) <  u2s(b))             # BLT
            elif f3 == 5: take = (u2s(a) >= u2s(b))             # BGE
            elif f3 == 6: take = (a <  b)                       # BLTU
            elif f3 == 7: take = (a >= b)                       # BGEU
            if take:
                next_pc = (pc + imm) & 0xFFFFFFFF
        elif op == 0x03:      # load
            imm = _sext((inst >> 20) & 0xFFF, 12)
            addr = (R[rs1] + imm) & 0xFFFFFFFF
            if   f3 == 0: R[rd] = self._load(addr, 1, True)  & 0xFFFFFFFF  # LB
            elif f3 == 1: R[rd] = self._load(addr, 2, True)  & 0xFFFFFFFF  # LH
            elif f3 == 2: R[rd] = self._load(addr, 4, False)              # LW
            elif f3 == 4: R[rd] = self._load(addr, 1, False)              # LBU
            elif f3 == 5: R[rd] = self._load(addr, 2, False)              # LHU
        elif op == 0x23:      # store
            imm = _sext(((inst >> 25) & 0x7F) << 5 | ((inst >> 7) & 0x1F), 12)
            addr = (R[rs1] + imm) & 0xFFFFFFFF
            if   f3 == 0: self._store(addr, 1, R[rs2])  # SB
            elif f3 == 1: self._store(addr, 2, R[rs2])  # SH
            elif f3 == 2: self._store(addr, 4, R[rs2])  # SW
        elif op == 0x13:      # op-imm
            imm = _sext((inst >> 20) & 0xFFF, 12)
            a = R[rs1]
            if   f3 == 0: R[rd] = (a + imm) & 0xFFFFFFFF                 # ADDI
            elif f3 == 2: R[rd] = 1 if u2s(a) < imm else 0              # SLTI
            elif f3 == 3: R[rd] = 1 if a < (imm & 0xFFFFFFFF) else 0    # SLTIU
            elif f3 == 4: R[rd] = (a ^ (imm & 0xFFFFFFFF)) & 0xFFFFFFFF # XORI
            elif f3 == 6: R[rd] = (a | (imm & 0xFFFFFFFF)) & 0xFFFFFFFF # ORI
            elif f3 == 7: R[rd] = (a & (imm & 0xFFFFFFFF)) & 0xFFFFFFFF # ANDI
            elif f3 == 1: R[rd] = (a << (rs2)) & 0xFFFFFFFF             # SLLI (shamt=rs2 field)
            elif f3 == 5:
                shamt = rs2
                if f7 & 0x20: R[rd] = (u2s(a) >> shamt) & 0xFFFFFFFF    # SRAI
                else:         R[rd] = (a >> shamt) & 0xFFFFFFFF         # SRLI
        elif op == 0x33:      # op
            a, b = R[rs1], R[rs2]
            if   f3 == 0: R[rd] = ((a - b) if (f7 & 0x20) else (a + b)) & 0xFFFFFFFF  # ADD/SUB
            elif f3 == 1: R[rd] = (a << (b & 0x1F)) & 0xFFFFFFFF        # SLL
            elif f3 == 2: R[rd] = 1 if u2s(a) < u2s(b) else 0          # SLT
            elif f3 == 3: R[rd] = 1 if a < b else 0                    # SLTU
            elif f3 == 4: R[rd] = (a ^ b) & 0xFFFFFFFF                 # XOR
            elif f3 == 5: R[rd] = ((u2s(a) >> (b & 0x1F)) if (f7 & 0x20) else (a >> (b & 0x1F))) & 0xFFFFFFFF  # SRA/SRL
            elif f3 == 6: R[rd] = (a | b) & 0xFFFFFFFF                 # OR
            elif f3 == 7: R[rd] = (a & b) & 0xFFFFFFFF                 # AND
        elif op == 0x73:      # ECALL/EBREAK -> halt
            self.halted = True; self.halt_reason = "ecall"
        else:
            self.halted = True; self.halt_reason = f"illegal:0x{inst:08X}@0x{pc:X}"; return

        R[0] = 0
        self.pc = next_pc
