// Mili BNN-TMR — PCIe Gen4 TLP / DLLP type definitions

package pcie_pkg;

  parameter int PCIE_LANES      = 4;
  parameter int PCIE_GEN        = 4;
  parameter int PCIE_WIDTH      = 32;   // DWORD-aligned TLP stream
  parameter int TLP_HDR_DW      = 3;    // 3 DW header (32-bit addressing)
  parameter int MAX_PAYLOAD_DW  = 1;

  typedef enum logic [2:0] {
    FMT_3DW_NO_DATA = 3'b000,
    FMT_4DW_NO_DATA = 3'b001,
    FMT_3DW_DATA    = 3'b010,
    FMT_4DW_DATA    = 3'b011
  } tlp_fmt_e;

  typedef enum logic [4:0] {
    TLP_MEM_READ  = 5'b00000,
    TLP_MEM_WRITE = 5'b00000,
    TLP_CPL       = 5'b01010,
    TLP_CPLD      = 5'b01010
  } tlp_type_e;

  typedef struct packed {
    logic [2:0]  fmt;
    logic [4:0]  tlp_type;
    logic        reserved0;
    logic [2:0]  tc;
    logic        attr;
    logic        th;
    logic [1:0]  td_ep;
    logic [1:0]  attr2;
    logic [1:0]  at;
    logic [9:0]  length;
    logic [31:0] addr_lo;
    logic [31:0] data;
  } mem_tlp_t;

  function automatic logic is_mem_write(input mem_tlp_t t);
    return (t.fmt == FMT_3DW_DATA) && (t.tlp_type == TLP_MEM_WRITE);
  endfunction

  function automatic logic is_mem_read(input mem_tlp_t t);
    return (t.fmt == FMT_3DW_NO_DATA) && (t.tlp_type == TLP_MEM_READ);
  endfunction

  function automatic mem_tlp_t pack_mem_write(input logic [31:0] addr, input logic [31:0] data);
    mem_tlp_t t;
    t.fmt       = FMT_3DW_DATA;
    t.tlp_type  = TLP_MEM_WRITE;
    t.length    = 10'd1;
    t.addr_lo   = addr;
    t.data      = data;
    return t;
  endfunction

  function automatic mem_tlp_t pack_mem_read(input logic [31:0] addr);
    mem_tlp_t t;
    t.fmt       = FMT_3DW_NO_DATA;
    t.tlp_type  = TLP_MEM_READ;
    t.length    = 10'd1;
    t.addr_lo   = addr;
    t.data      = '0;
    return t;
  endfunction

  function automatic mem_tlp_t pack_cpld(input logic [31:0] data);
    mem_tlp_t t;
    t.fmt       = FMT_3DW_DATA;
    t.tlp_type  = TLP_CPLD;
    t.length    = 10'd1;
    t.data      = data;
    return t;
  endfunction

endpackage
