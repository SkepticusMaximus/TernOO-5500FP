import ctypes
import os
import sys

# Load the shared library
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "bin/libternoo.so"))
if not os.path.exists(lib_path):
    print(f"Error: {lib_path} not found. Please run 'make' first.")
    sys.exit(1)

lib = ctypes.CDLL(lib_path)

# Define function signatures
lib.ternoo_init.argtypes = []
lib.ternoo_init.restype = None

lib.ternoo_reset.argtypes = []
lib.ternoo_reset.restype = None

lib.ternoo_run.argtypes = []
lib.ternoo_run.restype = None

lib.ternoo_read_reg.argtypes = [ctypes.c_int]
lib.ternoo_read_reg.restype = ctypes.c_uint64

lib.ternoo_write_reg.argtypes = [ctypes.c_int, ctypes.c_uint64]
lib.ternoo_write_reg.restype = None

lib.ternoo_mem_write.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
lib.ternoo_mem_write.restype = None

lib.ternoo_mem_read.argtypes = [ctypes.c_uint64]
lib.ternoo_mem_read.restype = ctypes.c_uint64

class TernOONativeEngine:
    """Python bridge to the high-speed NASM 5500FP execution engine."""
    
    def __init__(self):
        lib.ternoo_init()
        self.reset()
        
    def reset(self):
        lib.ternoo_reset()
        
    def read_reg(self, reg_idx):
        return lib.ternoo_read_reg(reg_idx)
        
    def write_reg(self, reg_idx, value):
        lib.ternoo_write_reg(reg_idx, value)
        
    def write_mem(self, addr, value):
        lib.ternoo_mem_write(addr, value)
        
    def read_mem(self, addr):
        return lib.ternoo_mem_read(addr)
        
    def load_program(self, word_list, start_addr=0):
        for i, word in enumerate(word_list):
            self.write_mem(start_addr + i, word)
            
    def run(self):
        lib.ternoo_run()

if __name__ == "__main__":
    print("Initializing NASM Engine via Python Bridge...")
    engine = TernOONativeEngine()
    
    print("Testing Register Access...")
    engine.write_reg(42, 12345)
    val = engine.read_reg(42)
    print(f"R42 = {val}")
    
    print("Bridge is fully operational.")
