module scan_dbg (
	input	wire		phi,
	input	wire		phib,
	input	wire		scan_i0o1,
	input	wire		load,
	input	wire		scan_in,
	output	wire		scan_out,
	
	input	wire	[15:0]	STREG_IN,
	output	wire	[15:0]	STREG_OUT,

	input	wire		SDA_INT,
	input	wire		SCL_INT,

	input	wire		BATON_RESETn_IN,
	output	wire		BATON_RESETn_OUT,

	input	wire		SLEEP_I2C_IN,
	output	wire		SLEEP_I2C_OUT,
	output	wire		SLEEP_I2C_B_OUT,

	input	wire		ISOLATE_I2C_IN,
	output	wire		ISOLATE_I2C_OUT,

	input	wire		RESET_I2C_IN,
	output	wire		RESET_I2C_OUT,

	input	wire		SLEEP_CPU_IN,
	output	wire		SLEEP_CPU_OUT,
	output	wire		SLEEP_CPU_B_OUT,

	input	wire		ISOLATE_CPU_IN,
	output	wire		ISOLATE_CPU_OUT,

	output	wire		I2C_OR_CPU_ISOLATE_OUT,

	input	wire		PORESETn_CPU_IN,
	output	wire		PORESETn_CPU_OUT,

	input	wire		CLEAR_STREG0_IN,
	input	wire		I2C_SLEEP_REQ_IN,

	input	wire		SCL_IN,
	output	wire		SCL_OUT,
	input	wire		SDA_IN,
	output	wire		SDA_OUT,

	output	wire		CLK_OVERRIDE_B,
	output	wire		CLK_X10_OVERRIDE_B,
	output	wire		CLK_OBSERVE_EN

	);

	wire			STREG_OVERRIDE;
	wire	[15:0]		STREG_SCAN;

	wire			BATON_RESETn_OVERRIDE;
	wire			BATON_RESETn_DBG;

	wire			I2C_CONTROL_OVERRIDE;
	wire			SLEEP_I2C_DBG;
	wire			ISOLATE_I2C_DBG;
	wire			RESET_I2C_DBG;

	wire			CPU_CONTROL_OVERRIDE;
	wire			SLEEP_CPU_DBG;
	wire			ISOLATE_CPU_DBG;
	wire			PORESETn_CPU_DBG;

	wire			I2C_OVERRIDE;
	wire			SCL_DBG;
	wire			SDA_DBG;

	assign		STREG_OUT 		= (STREG_OVERRIDE)?		STREG_SCAN		: STREG_IN;
	assign		BATON_RESETn_OUT	= (BATON_RESETn_OVERRIDE)?	BATON_RESETn_DBG	: BATON_RESETn_IN;
	assign		SLEEP_I2C_OUT		= (I2C_CONTROL_OVERRIDE)?	SLEEP_I2C_DBG		: SLEEP_I2C_IN;
	assign		SLEEP_I2C_B_OUT		= ~SLEEP_I2C_OUT;
	assign		ISOLATE_I2C_OUT		= (I2C_CONTROL_OVERRIDE)?	ISOLATE_I2C_DBG		: ISOLATE_I2C_IN;
	assign		RESET_I2C_OUT		= (I2C_CONTROL_OVERRIDE)?	RESET_I2C_DBG		: RESET_I2C_IN;
	assign		SLEEP_CPU_OUT		= (CPU_CONTROL_OVERRIDE)?	SLEEP_CPU_DBG		: SLEEP_CPU_IN;
	assign		SLEEP_CPU_B_OUT		= ~SLEEP_CPU_OUT;
	assign		ISOLATE_CPU_OUT		= (CPU_CONTROL_OVERRIDE)?	ISOLATE_CPU_DBG		: ISOLATE_CPU_IN;
	assign		I2C_OR_CPU_ISOLATE_OUT	= ISOLATE_CPU_OUT | ISOLATE_I2C_OUT;
	assign		PORESETn_CPU_OUT	= (CPU_CONTROL_OVERRIDE)?	PORESETn_CPU_DBG	: PORESETn_CPU_IN;
	assign		SCL_OUT			= (I2C_OVERRIDE)?		SCL_DBG			: SCL_IN;
	assign		SDA_OUT			= (I2C_OVERRIDE)?		SDA_DBG			: SDA_IN;


scan_chain	scan_chain_0 (
	.STREG			(STREG_IN[15:0]),
	.SDA_INT		(SDA_INT),
	.SCL_INT		(SCL_INT),
	.BATON_RESETn		(BATON_RESETn_IN),
	.SLEEP_I2C		(SLEEP_I2C_IN),
	.ISOLATE_I2C		(ISOLATE_I2C_IN),
	.RESET_I2C		(RESET_I2C_IN),
	.SLEEP_CPU		(SLEEP_CPU_IN),
	.ISOLATE_CPU		(ISOLATE_CPU_IN),
	.PORESETn_CPU		(PORESETn_CPU_IN),
	.CLEAR_STREG0		(CLEAR_STREG0_IN),
	.I2C_SLEEP_REQ		(I2C_SLEEP_REQ_IN),

	.CLK_OVERRIDE_B		(CLK_OVERRIDE_B),
	.CLK_X10_OVERRIDE_B	(CLK_X10_OVERRIDE_B),
	.CLK_OBSERVE_EN		(CLK_OBSERVE_EN),
	.STREG_OVERRIDE		(STREG_OVERRIDE),
	.STREG_DBG		(STREG_SCAN[15:0]),
	.BATON_RESETn_OVERRIDE	(BATON_RESETn_OVERRIDE),
	.BATON_RESETn_DBG	(BATON_RESETn_DBG),
	.I2C_CONTROL_OVERRIDE	(I2C_CONTROL_OVERRIDE),
	.SLEEP_I2C_DBG		(SLEEP_I2C_DBG),
	.ISOLATE_I2C_DBG	(ISOLATE_I2C_DBG),
	.RESET_I2C_DBG		(RESET_I2C_DBG),
	.CPU_CONTROL_OVERRIDE	(CPU_CONTROL_OVERRIDE),
	.SLEEP_CPU_DBG		(SLEEP_CPU_DBG),
	.ISOLATE_CPU_DBG	(ISOLATE_CPU_DBG),
	.PORESETn_CPU_DBG	(PORESETn_CPU_DBG),
	.I2C_OVERRIDE		(I2C_OVERRIDE),
	.SCL_DBG		(SCL_DBG),
	.SDA_DBG		(SDA_DBG),

	.phi		(phi),
	.phib		(phib),
	.scan_i0o1	(scan_i0o1),
	.load		(load),
	.scan_in	(scan_in),
	.scan_out	(scan_out),
	.phi_out	(),
	.phib_out	(),
	.scan_i0o1_out	(),
	.load_out	()
	);


endmodule
