#Global VSS
globalNetConnect VSS			-type pgpin -pin {VSS} 				-inst {*} 		 	   		-module {} -verbose

#PAD DVSS, DVDD --> VSS, VDD_TEST
globalNetConnect VSS 			-type pgpin -pin {DVSS}				-inst {PAD_*} 				-module {} -verbose
globalNetConnect VDD_TEST 		-type pgpin -pin {DVDD}		    	-inst {PAD_*} 		    	-module {} -verbose

#DIN, DOUT DIOVDD --> VDD_TEST(DVDD)
globalNetConnect VDD_TEST		-type pgpin	-pin {DIO_VDD}			-inst {PAD_DIN_*}			-module {} -verbose
globalNetConnect VDD_TEST		-type pgpin	-pin {DIO_VDD}			-inst {PAD_DOUT_*}			-module {} -verbose
globalNetConnect VDD_TEST		-type pgpin	-pin {DIO_VDD}			-inst {PAD_DOUT_*}			-module {} -verbose

