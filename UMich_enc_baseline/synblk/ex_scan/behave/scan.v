



// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// !!    THIS IS A TEMPORARY FILE GENERATED BY DEPERILFY      !!
// !!             DO NOT MODIFY DIRECTLY!                     !!
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!



////////////////////////////////////////////////////////////////////////////////

module scan (

              // Inputs & outputs to the chip
              read_data_1,
              read_data_2,
              read_data_3,
              read_data_array,
              memory_load_mode,
              addr,
              input_data,
              output_data,
              w1_r0,
              write_data_1,
              write_data_2,
              write_data_3,
              write_data_array,
              scan_reset,
             
              // To the pads
              scan_phi,
              scan_phi_bar,
              scan_data_in,
              scan_data_out,
              scan_load_chip,
              scan_load_chain
             
              );

   
   // /////////////////////////////////////////////////////////////////////
   // Ports

   // Scans
   input   scan_phi;
   input   scan_phi_bar;
   input   scan_data_in;
   output  scan_data_out;
   input   scan_load_chain;
   input   scan_load_chip;

   
   input      [1-1:0]  read_data_1;
   input      [2-1:0]  read_data_2;
   input      [3-1:0]  read_data_3;
   input      [16-1:0]  read_data_array;
   output reg [1-1:0]  memory_load_mode;
   output reg [9-1:0]  addr;
   output reg [32-1:0]  input_data;
   input      [32-1:0]  output_data;
   output reg [1-1:0]  w1_r0;
   output reg [1-1:0]  write_data_1;
   output reg [2-1:0]  write_data_2;
   output reg [3-1:0]  write_data_3;
   output reg [16-1:0]  write_data_array;
   output reg [1-1:0]  scan_reset;

   
   // /////////////////////////////////////////////////////////////////////
   // Implementation

   // The scan chain is comprised of two sets of latches: scan_master and scan_slave.
   
   reg [100-1:0] scan_master;
   reg [100-1:0] scan_slave;

   reg  [100-1:0] scan_load;
   wire [100-1:0] scan_next;

   always @ (*) begin
      scan_load[0:0] = read_data_1;
      scan_load[2:1] = read_data_2;
      scan_load[5:3] = read_data_3;
      scan_load[7:6] = scan_slave[7:6];
      case (scan_slave[7:6])
         2'd0: scan_load[11:8] = read_data_array[0*4 +: 4];
         2'd1: scan_load[11:8] = read_data_array[1*4 +: 4];
         2'd2: scan_load[11:8] = read_data_array[2*4 +: 4];
         2'd3: scan_load[11:8] = read_data_array[3*4 +: 4];
      endcase
      scan_load[12:12] = memory_load_mode;
      scan_load[21:13] = addr;
      scan_load[53:22] = input_data;
      scan_load[85:54] = output_data;
      scan_load[86:86] = w1_r0;
      scan_load[87:87] = write_data_1;
      scan_load[89:88] = write_data_2;
      scan_load[92:90] = write_data_3;
      scan_load[94:93] = scan_slave[94:93];
      case (scan_slave[94:93])
         2'd0: scan_load[98:95] = write_data_array[0*4 +: 4];
         2'd1: scan_load[98:95] = write_data_array[1*4 +: 4];
         2'd2: scan_load[98:95] = write_data_array[2*4 +: 4];
         2'd3: scan_load[98:95] = write_data_array[3*4 +: 4];
      endcase
      scan_load[99:99] = scan_reset;
   end

   assign scan_next = scan_load_chain ? scan_load : {scan_data_in, scan_slave[100-1:1]};

   //synopsys one_hot "scan_phi, scan_phi_bar"
   always @ (*) begin
       if (scan_phi)
          scan_master = scan_next;
       if (scan_phi_bar)
          scan_slave  = scan_master;
   end

   always @ (*) if (scan_load_chip) begin
      memory_load_mode = scan_slave[99] ? 1'd0 : scan_slave[12:12];
      addr = scan_slave[99] ? 9'd0 : scan_slave[21:13];
      input_data = scan_slave[99] ? 32'd0 : scan_slave[53:22];
      w1_r0 = scan_slave[99] ? 1'd0 : scan_slave[86:86];
      write_data_1 = scan_slave[99] ? 1'd0 : scan_slave[87:87];
      write_data_2 = scan_slave[99] ? 2'd3 : scan_slave[89:88];
      write_data_3 = scan_slave[99] ? 3'd0 : scan_slave[92:90];
      if (scan_slave[99]) write_data_array = 16'd43605; else
      case (scan_slave[94:93])
         2'd0: write_data_array[0*4 +: 4] = scan_slave[98:95];
         2'd1: write_data_array[1*4 +: 4] = scan_slave[98:95];
         2'd2: write_data_array[2*4 +: 4] = scan_slave[98:95];
         2'd3: write_data_array[3*4 +: 4] = scan_slave[98:95];
      endcase
      scan_reset = scan_slave[99];
   end

   assign scan_data_out = scan_slave[0];

   
   // /////////////////////////////////////////////////////////////////////
   
endmodule
