// Define some values
`define SCAN_DELAY 			#2


module tbench();
   
	// Input from PAD

	// Output to PAD

	// Input from Scan

	// Output to Scan
	
	// Input from full-custom circuit
	
	// Output to full-custom circuit

   //-----------------------------------------
   //  DUT
   //-----------------------------------------


	minipuf_ctrl dut (
		// Connect siganls SOURCE_CODE <---> TEST BENCH
	);

   
//-----------------------------------------
//  Testbench
//-----------------------------------------

always begin
	#500	clk = ~clk;
end

initial begin

	$dumpvars(0, tbench);
            
	$display("===== Initializing Inputs =====");
	// Give initial values
	
	#200
	//Change values to test


	$finish;
end

endmodule 				  
