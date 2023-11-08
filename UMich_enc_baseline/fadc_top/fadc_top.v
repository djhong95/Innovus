

//----------------------------------------------------------------------------
//
// *File Name: fadc_top.v
//
// *Module Description: APR TOP MODULE - ICAS ORIENTATION
//
//
//----------------------------------------------------------------------------
// Developer: H.J.Lee
// CreateDate: 18-01-10
// LastChangedBy: H.J.Lee
// LastChangedDate: 18-01-11
//----------------------------------------------------------------------------

module fadc_top(
				);

	// Pad wires - Scan Chain
	wire		PAD_SCAN_PHI;
	wire		PAD_SCAN_PHI_BAR;
	wire		PAD_SCAN_DATA_IN
	wire		PAD_SCAN_LOAD_CHIP;
	wire		PAD_SCAN_LOAD_CHAIN; 
	wire		PAD_SCAN_DATA_OUT;
	// Scan chain pad internal nodes
	wire		PAD_di_SCAN_PHI;
	wire		PAD_di_SCAN_PHI_BAR; 
	wire		PAD_di_SCAN_DATA_IN; 
	wire		PAD_di_SCAN_LOAD_CHIP;
	wire		PAD_di_SCAN_LOAD_CHAIN;
	wire		PAD_do_SCAN_DATA_OUT;

	// Scan --> Digital 
	wire [15:0] A
	wire [15:0] B
	wire 		CIN

	// Digital --> Scan
	wire [7:0]  SUM
	wire 		COUT

	// FADC --> Encoder
	wire [7:0]  FADC_M_OUT

 	wire 		esd_detect;	
	
	// Pad Instantiation ========================================================================================================================
	// 	Power Pads ------------------------------------------------------------------------------------------------------------------------------
	PAD_50x60SML_VSS_TSMC180		PAD_VSS_LEFT	      		(.DETECT(esd_detect));
	PAD_50x60SML_DVDD_TSMC180		PAD_DVDD_LEFT	      		(.DETECT(esd_detect));
	PAD_50x60SML_VSS_TSMC180		PAD_VSS_BOTTOM	      		(.DETECT(esd_detect));
	PAD_50x60SML_DVDD_TSMC180		PAD_DVDD_BOTTOM	      		(.DETECT(esd_detect));
	
	//	SCAN Pads  ------------------------------------------------------------------------------------------------------------------------------
	PAD_50x60SML_DIN_TSMC180		PAD_DIN_SCAN_DATA_IN		(.DETECT(esd_detect), .PAD(PAD_SCAN_DATA_IN)	   , .Y(PAD_di_SCAN_DATA_IN) );
	PAD_50x60SML_DOUT_TSMC180		PAD_DOUT_SCAN_DATA_OUT		(.DETECT(esd_detect), .PAD(PAD_SCAN_DATA_OUT)	   , .A(PAD_do_SCAN_DATA_OUT));
	PAD_50x60SML_DIN_TSMC180		PAD_DIN_SCAN_LOAD_CHIP		(.DETECT(esd_detect), .PAD(PAD_SCAN_LOAD_CHIP)	   , .Y(PAD_di_SCAN_LOAD_CHIP));
	PAD_50x60SML_DIN_TSMC180		PAD_DIN_SCAN_LOAD_CHAIN		(.DETECT(esd_detect), .PAD(PAD_SCAN_LOAD_CHAIN)	   , .Y(PAD_di_SCAN_LOAD_CHAIN));
	PAD_50x60SML_DIN_TSMC180		PAD_DIN_SCAN_PHI			(.DETECT(esd_detect), .PAD(PAD_SCAN_PHI)		   , .Y(PAD_di_SCAN_PHI));
	PAD_50x60SML_DIN_TSMC180		PAD_DIN_SCAN_PHI_BAR		(.DETECT(esd_detect), .PAD(PAD_SCAN_PHI_BAR)	   , .Y(PAD_di_SCAN_PHI_BAR));

	// 	Analog INPUT (Override voltage)  --------------------------------------------------------------------------------------------------------
	PAD_50x60SML_AIO_TSMC180			PAD_AIO_OVR_VREF  		(.DETECT(esd_detect), .AIO(PAD_a_OVR_VREF));

	// 	Detection pad ---------------------------------------------------------------------------------------------------------------------------
	DETECTION_TSMC180				DETECTION_0					(.DETECT(esd_detect));
	DETECTION_TSMC180				DETECTION_1					(.DETECT(esd_detect));



	//	SCANCHAIN==========================================================================
	ex_scan		XEX_SCAN	(
		.scan_reset			(PAD_di_SCAN_RESET),
		.scan_phi			(PAD_di_SCAN_PHI),
    	.scan_phi_bar		(PAD_di_SCAN_PHI_BAR),
    	.scan_data_in		(PAD_di_SCAN_DATA_IN),
    	.scan_load_chip		(PAD_di_SCAN_LOAD_CHIP),
   	 	.scan_load_chain	(PAD_di_SCAN_LOAD_CHAIN),
    	.scan_data_out		(PAD_do_SCAN_DATA_OUT),
		.REF_SEL			(REF_SEL[5:0]),
		.S_OVR_VREF			(S_OVR_VREF)
	);


	// DIGITAL_CONTROL ====================================================================	
	fadc_ctrl	XFADC_CTRL (
	);



	// FADC ===============================================================================
	mainckt		XMAINCKT	(
	);
endmodule

