#include <stdint.h>

// Forward declarations to NASM symbols
extern void cpu_init(void);
extern void cpu_reset(void);
extern void cpu_run(void);
extern uint64_t cpu_read_reg(int reg);
extern void cpu_write_reg(int reg, uint64_t val);
extern void cpu_mem_write(uint64_t addr, uint64_t val);
extern uint64_t cpu_mem_read(uint64_t addr);

// Exported C-API
void ternoo_init(void) { cpu_init(); }
void ternoo_reset(void) { cpu_reset(); }
void ternoo_run(void) { cpu_run(); }
uint64_t ternoo_read_reg(int reg) { return cpu_read_reg(reg); }
void ternoo_write_reg(int reg, uint64_t val) { cpu_write_reg(reg, val); }
void ternoo_mem_write(uint64_t addr, uint64_t val) { cpu_mem_write(addr, val); }
uint64_t ternoo_mem_read(uint64_t addr) { return cpu_mem_read(addr); }
