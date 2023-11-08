
# CONVERTER VIN, VOUT
globalNetConnect VOUT			-type pgpin -pin {VDD}				-inst {PAD_BW_VOUT}		    -module {} -verbose
globalNetConnect VOUT			-type pgpin -pin {VOUT}				-inst {XHVT_3}			    -module {} -verbose
globalNetConnect VIN			-type pgpin -pin {VDD}				-inst {PAD_BW_VIN}		    -module {} -verbose
globalNetConnect VIN			-type pgpin -pin {VIN}				-inst {XHVT_3}			    -module {} -verbose

# VDD_COMP_DIFF, VDD_CLK, VDD_TEST
globalNetConnect VDD_COMP_DFF	-type pgpin -pin {VDD}	            -inst {PAD_BW_VDD_COMP_DFF} -module {} -verbose
globalNetConnect VDD_COMP_DFF	-type pgpin -pin {VDD_COMP_DFF}	    -inst {XHVT_3}				-module {} -verbose
globalNetConnect VDD_CLK		-type pgpin -pin {VDD}              -inst {PAD_BW_VDD_CLK}		-module {} -verbose
globalNetConnect VDD_CLK		-type pgpin -pin {VDD_CLK}          -inst {XHVT_3}				-module {} -verbose

globalNetConnect VDD_CTRL		-type pgpin -pin {VDD}              -inst {PAD_BW_VDD_CTRL}		-module {} -verbose
globalNetConnect VDD_TEST		-type pgpin -pin {VDD}              -inst {XHRV_SCAN_RV3}		-module {} -verbose
globalNetConnect VDD_CTRL		-type pgpin -pin {VDD}              -inst {XHRV_CTRL}			-module {} -verbose
globalNetConnect VDD_CTRL		-type pgpin -pin {VDD_CTRL}         -inst {XHVT_3}				-module {} -verbose

#Global VSS
globalNetConnect VSS			-type pgpin -pin {VSS} 				-inst {*} 		 	   		-module {} -verbose

#PAD DVSS, DVDD --> VSS, VDD_TEST
globalNetConnect VSS 			-type pgpin -pin {DVSS}				-inst {PAD_*} 				-module {} -verbose
globalNetConnect VSS 			-type pgpin -pin {DVSS}	     		-inst {PADOSC_*} 	    	-module {} -verbose
globalNetConnect VDD_TEST 		-type pgpin -pin {DVDD}		    	-inst {PAD_*} 		    	-module {} -verbose

#DIN, DOUT DIOVDD --> VDD_TEST(DVDD)
globalNetConnect VDD_TEST		-type pgpin	-pin {DIO_VDD}			-inst {PAD_DIN_*}			-module {} -verbose
globalNetConnect VDD_TEST		-type pgpin	-pin {DIO_VDD}			-inst {PAD_DOUT_*}			-module {} -verbose
globalNetConnect VDD_TEST		-type pgpin	-pin {DIO_VDD}			-inst {PAD_DOUT_*}			-module {} -verbose

#Detection DVSS, DVDD --> VSS, VDD_TEST
globalNetConnect VSS 			-type pgpin -pin {DVSS}				-inst {DETECTION_0} 		-module {} -verbose
globalNetConnect VDD_TEST 		-type pgpin -pin {DVDD}				-inst {DETECTION_0} 		-module {} -verbose



# OSC_BLK
globalNetConnect VDD_OSC 		-type pgpin -pin {VDD}				-inst {PADOSC_BW_VDD_OSC}   -module {} -verbose
globalNetConnect VDD_OSC 		-type pgpin -pin {VDD}				-inst {XOSC}		 		-module {} -verbose
globalNetConnect VDD_TEST_OSC	-type pgpin -pin {VDD_TEST}			-inst {XOSC}		 		-module {} -verbose


#DIN, DOUT DIOVDD --> VDD_TEST(DVDD)
globalNetConnect VDD_TEST_OSC   -type pgpin -pin {DIO_VDD}	        -inst {PADOSC_DIN_*}   		-module {} -verbose
globalNetConnect VDD_TEST_OSC   -type pgpin -pin {DIO_VDD}          -inst {PADOSC_DOUT_*} 		-module {} -verbose


globalNetConnect VDD_TEST_OSC  	-type pgpin -pin {DVDD}          	-inst {PADOSC_*}  		-module {} -verbose



