import re
from register_table import RegisterTable


class ParsedLine:
    def __init__(self, line_num=0, raw_line=""):
        self.line_num = line_num
        self.raw_line = raw_line
        self.label = None
        self.mnemonic = None
        self.operands = []
        self.line_type = "empty"   # empty, label_only, instruction, directive
        self.error = None

    def __repr__(self):
        parts = [f"L{self.line_num}[{self.line_type}]"]
        if self.label:
            parts.append(f"lbl='{self.label}'")
        if self.mnemonic:
            parts.append(f"mn='{self.mnemonic}'")
        if self.operands:
            parts.append(f"ops={self.operands}")
        if self.error:
            parts.append(f"ERR:{self.error}")
        return " ".join(parts)


class ParsedOperand:
    def __init__(self, raw=""):
        self.raw = raw
        self.op_type = None   # register, immediate, symbol, memory
        self.reg_num = None
        self.value = None
        self.symbol = None
        self.offset = None
        self.base_reg = None

    def __repr__(self):
        if self.op_type == "register":  return f"Reg(x{self.reg_num})"
        if self.op_type == "immediate": return f"Imm({self.value})"
        if self.op_type == "symbol":    return f"Sym('{self.symbol}')"
        if self.op_type == "memory":    return f"Mem({self.offset}(x{self.base_reg}))"
        return f"?({self.raw})"


class Parser:
    DIRECTIVES = {".text", ".data", ".word", ".byte", ".half",
                  ".org", ".end", ".align", ".space", ".string",
                  ".globl", ".global", ".section", ".equ"}

    def __init__(self):
        self._regtab = RegisterTable()
        self._memory_pattern = re.compile(
            r'^(-?(?:0[xX][0-9a-fA-F]+|0[bB][01]+|\d+))\((\w+)\)$'
        )

    def parse_line(self, line, line_num=0):
        result = ParsedLine(line_num=line_num, raw_line=line)

        cleaned = self._strip_comment(line).strip()
        if not cleaned:
            return result

        label, rest = self._extract_label(cleaned)
        if label is not None:
            if not self._is_valid_label(label):
                result.error = f"Geçersiz etiket: '{label}'"
                return result
            result.label = label

        rest = rest.strip()
        if not rest:
            result.line_type = "label_only"
            return result

        tokens = rest.split(None, 1)
        mnemonic = tokens[0]
        operand_str = tokens[1].strip() if len(tokens) > 1 else ""

        result.mnemonic = mnemonic.upper() if not mnemonic.startswith(".") else mnemonic.lower()
        result.line_type = "directive" if mnemonic.startswith(".") else "instruction"

        if operand_str:
            result.operands = [p.strip() for p in operand_str.split(',') if p.strip()]

        return result

    def parse_operand(self, operand_str):
        op = ParsedOperand(raw=operand_str)
        token = operand_str.strip()
        if not token:
            return op

        # 1. Bellek adresleme: offset(register)
        mem_match = self._memory_pattern.match(token)
        if mem_match:
            base_num = self._regtab.get_number(mem_match.group(2))
            if base_num is not None:
                op.op_type = "memory"
                op.offset = self._parse_number(mem_match.group(1))
                op.base_reg = base_num
                return op

        # 2. Register
        reg_num = self._regtab.get_number(token)
        if reg_num is not None:
            op.op_type = "register"
            op.reg_num = reg_num
            return op

        # 3. Immediate
        num = self._parse_number(token)
        if num is not None:
            op.op_type = "immediate"
            op.value = num
            return op

        # 4. Sembol
        if self._is_valid_label(token):
            op.op_type = "symbol"
            op.symbol = token
            return op

        return op

    def parse_all_operands(self, operand_list):
        return [self.parse_operand(op) for op in operand_list]

    def parse_file(self, lines):
        return [self.parse_line(line, i) for i, line in enumerate(lines, 1)]

    def _strip_comment(self, line):
        for i, ch in enumerate(line):
            if ch in ('#', ';'):
                return line[:i]
        return line

    def _extract_label(self, line):
        pos = line.find(':')
        if pos == -1:
            return None, line
        label = line[:pos].strip()
        if label and ' ' not in label:
            return label, line[pos + 1:]
        return None, line

    def _is_valid_label(self, name):
        if not name or name.lower() in self.DIRECTIVES:
            return False
        if not (name[0].isalpha() or name[0] == '_'):
            return False
        return all(c.isalnum() or c == '_' for c in name)

    def _parse_number(self, token):
        try:
            return int(token.strip(), 0)
        except (ValueError, TypeError):
            return None
