import importlib
TernOO = importlib.import_module("5500fp_ternoo_v02")

# Instantiate the machine and assembler
emu = TernOO.CPU5500FP()
a = TernOO.Asm(emu)

# Load a simple program that takes input
prog = [
    a.IN(1),        # Wait for input into R1
    a.LDI(2, 5),    # Load 5 into R2
    a.ADD(3, 1, 2), # R3 = R1 + 5
    a.OUT(3),       # Print R3
    a.HLT()
]

emu.load_program(prog)
print("Machine running... (Type a number and press Enter)")
emu.run()
emu.dump_regs()
