// Internal State Definition for state machine
`define		ST_INIT				4'b0000
`define		ST_START			4'b0001
`define		ST_CALCULATE		4'b0010
`define		ST_END				4'b0011




module dig_ctrl (

	// Input from PAD

	// Output to PAD

	// Input from Scan

	// Output to Scan

	// Input from full-custom circuit

	// Output to full-custom circuit

);

	// Registers

	// Wires

	// Assign structure
											

	// Sample Un-synched inputs -----------------------
	reg			SMP_START;
	reg	[3:0]	SMP_BIAS_SET;
	reg	[3:0]	SMP_COMP_OUT;

	always @ (posedge clk or negedge RSTN)
	begin
		if(!RSTN) begin
			SMP_START		<= 1'b0;
			SMP_BIAS_SET	<= 3'b0;
			SMP_COMP_OUT	<= 3'b0;
		end
		else begin
			SMP_START		<= START;
			SMP_BIAS_SET	<= BIAS_SET;
			SMP_COMP_OUT	<= COMP_OUT;
		end
	end
	//-------------------------------------------------




	always @ (posedge clk or negedge RSTN)
	begin
		// Make your state machine

	end

endmodule
