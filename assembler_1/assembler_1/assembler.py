from opcode_table import OpcodeTable, PSEUDO_INSTRUCTIONS
from symbol_table import SymbolTable
from register_table import RegisterTable
from parser import Parser
from encoder import Encoder


class AssemblerError:
    def __init__(self, line_num, message, line_text=""):
        self.line_num = line_num
        self.message = message
        self.line_text = line_text

    def __repr__(self):
        return f"  Satır {self.line_num}: {self.message}"


class IntermediateEntry:
    def __init__(self):
        self.address = 0
        self.parsed = None
        self.length = 0
        self.section = ".text"
        self.error = None


class Assembler:
    def __init__(self):
        self._optab = OpcodeTable()
        self._symtab = SymbolTable()
        self._regtab = RegisterTable()
        self._parser = Parser()
        self._encoder = Encoder()
        self._intermediate = []
        self._object_codes = []
        self._errors = []
        self._program_name = ""
        self._start_address = 0
        self._program_length = 0

    def assemble(self, source_lines, program_name="PROG", start_address=0):
        self._program_name = program_name
        self._start_address = start_address
        self._intermediate = []
        self._object_codes = []
        self._errors = []
        self._symtab.clear()

        self._pass1(source_lines)

        for sym in self._symtab.get_undefined_symbols():
            self._errors.append(AssemblerError(sym.line_num, f"Tanımsız sembol: '{sym.name}'"))

        self._pass2()
        return len(self._errors) == 0

 
    # PASS 1
    def _pass1(self, source_lines):
        locctr = self._start_address
        current_section = ".text"
        parsed_lines = self._parser.parse_file(source_lines)

        for pl in parsed_lines:
            entry = IntermediateEntry()
            entry.address = locctr
            entry.parsed = pl
            entry.section = current_section

            if pl.error:
                entry.error = pl.error
                self._errors.append(AssemblerError(pl.line_num, pl.error, pl.raw_line))
                self._intermediate.append(entry)
                continue

            if pl.line_type == "empty":
                self._intermediate.append(entry)
                continue

            if pl.label:
                if not self._symtab.add(pl.label, locctr, current_section, pl.line_num):
                    err = f"Çift tanımlı sembol: '{pl.label}'"
                    entry.error = err
                    self._errors.append(AssemblerError(pl.line_num, err))

            if pl.line_type == "label_only":
                self._intermediate.append(entry)
                continue

            if pl.line_type == "directive":
                length = self._directive_length(pl)
                if pl.mnemonic in (".text", ".data"):
                    current_section = pl.mnemonic
                    entry.section = current_section
                entry.length = length
                locctr += length
                self._intermediate.append(entry)
                continue

            if pl.line_type == "instruction":
                if pl.mnemonic in PSEUDO_INSTRUCTIONS or self._optab.contains(pl.mnemonic):
                    entry.length = 4
                    locctr += 4
                else:
                    err = f"Bilinmeyen komut: '{pl.mnemonic}'"
                    entry.error = err
                    self._errors.append(AssemblerError(pl.line_num, err))
                self._intermediate.append(entry)
                continue

            self._intermediate.append(entry)

        self._program_length = locctr - self._start_address

    def _directive_length(self, pl):
        m = pl.mnemonic
        ops = pl.operands
        if m in (".text", ".data", ".globl", ".global", ".section", ".end"):
            return 0
        if m == ".word":  return 4 * max(len(ops), 1)
        if m == ".half":  return 2 * max(len(ops), 1)
        if m == ".byte":  return 1 * max(len(ops), 1)
        if m == ".space" and ops:
            try: return int(ops[0], 0)
            except: return 0
        if m == ".string" and ops:
            return len(ops[0].strip('"').strip("'")) + 1
        if m == ".equ" and len(ops) >= 2:
            try: self._symtab.add(ops[0], int(ops[1], 0), ".abs", pl.line_num)
            except: pass
            return 0
        return 0

    # PASS 2
    def _pass2(self):
        for entry in self._intermediate:
            pl = entry.parsed
            if pl is None or pl.line_type in ("empty", "label_only") or entry.error:
                continue

            if pl.line_type == "directive":
                self._encode_directive(entry)
                continue

            if pl.line_type == "instruction":
                if pl.mnemonic in PSEUDO_INSTRUCTIONS:
                    code = self._expand_pseudo(pl, entry.address)
                else:
                    code = self._encode_instruction(pl, entry.address)

                if code is not None:
                    self._object_codes.append((entry.address, code))
                elif not entry.error:
                    self._errors.append(AssemblerError(
                        pl.line_num, f"Kodlama hatası: '{pl.raw_line.strip()}'"))

    def _encode_instruction(self, pl, current_addr):
        mnem = pl.mnemonic
        ops = self._parser.parse_all_operands(pl.operands)
        entry = self._optab.lookup(mnem)
        if entry is None:
            return None

        fmt = entry.fmt_type
        try:
            if fmt == "R":
                rd, rs1, rs2 = self._reg(ops,0,pl), self._reg(ops,1,pl), self._reg(ops,2,pl)
                if None in (rd, rs1, rs2): return None
                return self._encoder.encode_instruction(mnem, rd=rd, rs1=rs1, rs2=rs2)

            if fmt == "I":
                return self._encode_i(mnem, entry, ops, pl, current_addr)

            if fmt == "S":
                rs2 = self._reg(ops, 0, pl)
                mem = self._mem(ops, 1, pl)
                if rs2 is None or mem is None: return None
                return self._encoder.encode_instruction(mnem, rs1=mem[0], rs2=rs2, imm=mem[1])

            if fmt == "B":
                rs1, rs2 = self._reg(ops,0,pl), self._reg(ops,1,pl)
                imm = self._branch_target(ops, 2, current_addr, pl)
                if None in (rs1, rs2, imm): return None
                return self._encoder.encode_instruction(mnem, rs1=rs1, rs2=rs2, imm=imm)

            if fmt == "U":
                rd  = self._reg(ops, 0, pl)
                imm = self._imm(ops, 1, pl)
                if None in (rd, imm): return None
                return self._encoder.encode_instruction(mnem, rd=rd, imm=imm)

            if fmt == "J":
                rd  = self._reg(ops, 0, pl)
                imm = self._branch_target(ops, 1, current_addr, pl)
                if None in (rd, imm): return None
                return self._encoder.encode_instruction(mnem, rd=rd, imm=imm)

        except Exception as e:
            self._errors.append(AssemblerError(pl.line_num, f"İç hata: {e}"))
        return None

    def _encode_i(self, mnem, optab_entry, ops, pl, current_addr):
        upper = mnem.upper()
        if upper == "ECALL":
            return self._encoder.encode_instruction(mnem)

        if optab_entry.opcode == 0b0000011:
            rd  = self._reg(ops, 0, pl)
            mem = self._mem(ops, 1, pl)
            if rd is None or mem is None: return None
            return self._encoder.encode_instruction(mnem, rd=rd, rs1=mem[0], imm=mem[1])

        if upper == "JALR":
            rd = self._reg(ops, 0, pl)
            if rd is None: return None
            if len(ops) >= 2 and ops[1].op_type == "memory":
                return self._encoder.encode_instruction(mnem, rd=rd, rs1=ops[1].base_reg, imm=ops[1].offset)
            if len(ops) >= 3:
                rs1 = self._reg(ops, 1, pl)
                imm = self._imm(ops, 2, pl)
                if None in (rs1, imm): return None
                return self._encoder.encode_instruction(mnem, rd=rd, rs1=rs1, imm=imm)
            return None

        rd  = self._reg(ops, 0, pl)
        rs1 = self._reg(ops, 1, pl)
        imm = self._imm(ops, 2, pl)
        if None in (rd, rs1, imm): return None
        return self._encoder.encode_instruction(mnem, rd=rd, rs1=rs1, imm=imm)

    def _expand_pseudo(self, pl, current_addr):
        ops = self._parser.parse_all_operands(pl.operands)
        m = pl.mnemonic

        if m == "NOP":
            return self._encoder.encode_instruction("ADDI", rd=0, rs1=0, imm=0)
        if m == "MV":
            rd, rs = self._reg(ops,0,pl), self._reg(ops,1,pl)
            if None in (rd, rs): return None
            return self._encoder.encode_instruction("ADDI", rd=rd, rs1=rs, imm=0)
        if m == "LI":
            rd, imm = self._reg(ops,0,pl), self._imm(ops,1,pl)
            if None in (rd, imm): return None
            return self._encoder.encode_instruction("ADDI", rd=rd, rs1=0, imm=imm)
        if m == "NEG":
            rd, rs = self._reg(ops,0,pl), self._reg(ops,1,pl)
            if None in (rd, rs): return None
            return self._encoder.encode_instruction("SUB", rd=rd, rs1=0, rs2=rs)
        if m == "J":
            imm = self._branch_target(ops, 0, current_addr, pl)
            if imm is None: return None
            return self._encoder.encode_instruction("JAL", rd=0, imm=imm)
        if m == "JR":
            rs = self._reg(ops, 0, pl)
            if rs is None: return None
            return self._encoder.encode_instruction("JALR", rd=0, rs1=rs, imm=0)
        if m == "RET":
            return self._encoder.encode_instruction("JALR", rd=0, rs1=1, imm=0)
        if m == "CALL":
            imm = self._branch_target(ops, 0, current_addr, pl)
            if imm is None: return None
            return self._encoder.encode_instruction("JAL", rd=1, imm=imm)
        if m == "BEQZ":
            rs  = self._reg(ops, 0, pl)
            imm = self._branch_target(ops, 1, current_addr, pl)
            if None in (rs, imm): return None
            return self._encoder.encode_instruction("BEQ", rs1=rs, rs2=0, imm=imm)
        if m == "BNEZ":
            rs  = self._reg(ops, 0, pl)
            imm = self._branch_target(ops, 1, current_addr, pl)
            if None in (rs, imm): return None
            return self._encoder.encode_instruction("BNE", rs1=rs, rs2=0, imm=imm)
        return None

    def _encode_directive(self, entry):
        pl = entry.parsed
        m, ops = pl.mnemonic, pl.operands
        if m == ".word":
            for i, op in enumerate(ops):
                try: self._object_codes.append((entry.address + i*4, int(op,0) & 0xFFFFFFFF))
                except: pass
        elif m == ".byte":
            for i, op in enumerate(ops):
                try: self._object_codes.append((entry.address + i, int(op,0) & 0xFF))
                except: pass

    def _reg(self, ops, idx, pl):
        if idx >= len(ops):
            self._errors.append(AssemblerError(pl.line_num, f"Eksik register (pozisyon {idx+1})"))
            return None
        if ops[idx].op_type != "register":
            self._errors.append(AssemblerError(pl.line_num, f"Register bekleniyor: '{ops[idx].raw}'"))
            return None
        return ops[idx].reg_num

    def _imm(self, ops, idx, pl):
        if idx >= len(ops):
            self._errors.append(AssemblerError(pl.line_num, f"Eksik immediate (pozisyon {idx+1})"))
            return None
        if ops[idx].op_type == "immediate":
            return ops[idx].value
        if ops[idx].op_type == "symbol":
            addr = self._symtab.get_address(ops[idx].symbol)
            if addr is not None: return addr
            self._errors.append(AssemblerError(pl.line_num, f"Tanımsız sembol: '{ops[idx].symbol}'"))
        else:
            self._errors.append(AssemblerError(pl.line_num, f"Immediate bekleniyor: '{ops[idx].raw}'"))
        return None

    def _mem(self, ops, idx, pl):
        if idx >= len(ops):
            self._errors.append(AssemblerError(pl.line_num, "Eksik offset(base)"))
            return None
        if ops[idx].op_type == "memory":
            return (ops[idx].base_reg, ops[idx].offset)
        self._errors.append(AssemblerError(pl.line_num, f"offset(reg) bekleniyor: '{ops[idx].raw}'"))
        return None

    def _branch_target(self, ops, idx, current_addr, pl):
        if idx >= len(ops):
            self._errors.append(AssemblerError(pl.line_num, "Eksik dallanma hedefi"))
            return None
        op = ops[idx]
        if op.op_type == "symbol":
            addr = self._symtab.get_address(op.symbol)
            if addr is not None: return addr - current_addr
            self._errors.append(AssemblerError(pl.line_num, f"Tanımsız hedef: '{op.symbol}'"))
            return None
        if op.op_type == "immediate":
            return op.value
        self._errors.append(AssemblerError(pl.line_num, f"Hedef bekleniyor: '{op.raw}'"))
        return None

    # ÇIKTI
    def print_listing(self):
        print(f"{'ASSEMBLY LISTING':^80}")
        print(f"{'LOC':>10}  {'ObjCode':>10}  Kaynak")
        print(f"\n")
        ci = 0
        for entry in self._intermediate:
            pl = entry.parsed
            if pl.line_type == "empty":
                print(f"{'':>10}  {'':>10}  {pl.raw_line.rstrip()}")
                continue
            obj = ""
            if ci < len(self._object_codes):
                a, c = self._object_codes[ci]
                if a == entry.address and entry.length > 0:
                    obj = f"{c & 0xFFFFFFFF:08X}"
                    ci += 1
            loc = f"0x{entry.address:08X}" if entry.length > 0 or pl.label else ""
            err = " ***" if entry.error else ""
            print(f"{loc:>10}  {obj:>10}  {pl.raw_line.rstrip()}{err}")
        print(f"  Program: {self._program_length} byte (0x{self._program_length:X})")

    def print_symbol_table(self):
        self._symtab.print_table()

    def print_object_program(self):
        print(f"{'OBJECT PROGRAM (Header-Text-End)':^70}")
        print(f"{'='*70}")
        print(f"H {self._program_name:<6} {self._start_address:06X} {self._program_length:06X}")
        i = 0
        while i < len(self._object_codes):
            start = self._object_codes[i][0]
            batch = []
            for j in range(i, min(i+8, len(self._object_codes))):
                batch.append(self._object_codes[j][1])
            hex_str = "".join(f"{c & 0xFFFFFFFF:08X}" for c in batch)
            print(f"T {start:06X} {len(batch)*4:02X} {hex_str}")
            i += len(batch)
        ep = self._start_address
        for e in self._intermediate:
            if e.parsed.line_type == "instruction" and e.length > 0:
                ep = e.address
                break
        print(f"E {ep:06X}")
        print(f"{'='*70}")

    def print_errors(self):
        if not self._errors:
            print("\n  Hata yok.")
            return
        print(f"\n  HATALAR ({len(self._errors)} adet):")
        for e in self._errors:
            print(f"  {e}")

    def get_binary(self):
        if not self._object_codes: return bytearray()
        max_addr = max(a for a, _ in self._object_codes)
        mem = bytearray(max_addr + 4 - self._start_address)
        for addr, code in self._object_codes:
            off = addr - self._start_address
            for i, b in enumerate(self._encoder.to_bytes_le(code)):
                if off + i < len(mem):
                    mem[off + i] = b
        return mem

    def write_binary(self, filename):
        data = self.get_binary()
        with open(filename, 'wb') as f:
            f.write(data)
        print(f"\n  Binary: {filename} ({len(data)} byte)")



def assemble_file(asm_path, program_name=None, start_address=0):
    import os
    asm_path = str(asm_path)

    if not os.path.isfile(asm_path):
        raise FileNotFoundError(f"Kaynak dosya bulunamadı: '{asm_path}'")

    with open(asm_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if program_name is None:
        program_name = os.path.splitext(os.path.basename(asm_path))[0][:6].upper()

    asm = Assembler()
    success = asm.assemble(lines, program_name=program_name, start_address=start_address)
    return asm, success


def write_report(asm, success, txt_path):
    import io, sys

    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    try:
        print(f"  PicoRV32 (RV32I) ASSEMBLER RAPORU")
        print(f"  Program : {asm._program_name}")
        print(f"  Durum   : {'BAŞARILI' if success else 'HATA VAR'}")

        asm.print_listing()
        asm.print_symbol_table()
        asm.print_object_program()
        asm.print_errors()

        if success:
            binary = asm.get_binary()
            print(f"  HEX DUMP ({len(binary)} byte)")
            print(f"{'='*80}")
            for i in range(0, len(binary), 16):
                chunk = binary[i:i+16]
                hex_part  = " ".join(f"{b:02X}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                print(f"  {i:08X}  {hex_part:<47}  |{ascii_part}|")
            print(f"{'='*80}")
    finally:
        sys.stdout = old_stdout

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(buffer.getvalue())


def assemble_and_save(asm_path, out_dir=None, program_name=None, start_address=0,
                      write_bin=True, write_txt=True, verbose=True):
    import os

    asm_path = str(asm_path)
    base     = os.path.splitext(os.path.basename(asm_path))[0]
    src_dir  = os.path.dirname(os.path.abspath(asm_path))
    out_dir  = str(out_dir) if out_dir else src_dir

    os.makedirs(out_dir, exist_ok=True)

    bin_path = os.path.join(out_dir, base + ".bin") if write_bin else None
    txt_path = os.path.join(out_dir, base + ".txt") if write_txt else None

    asm, success = assemble_file(asm_path, program_name=program_name,
                                  start_address=start_address)

    if verbose:
        asm.print_listing()
        asm.print_symbol_table()
        asm.print_object_program()
        asm.print_errors()

    if write_bin and success:
        asm.write_binary(bin_path)
        if verbose:
            print(f"  [BIN] → {bin_path}")

    if write_txt:
        write_report(asm, success, txt_path)
        if verbose:
            print(f"  [TXT] → {txt_path}")

    return success, bin_path, txt_path