# PAD Connections ===================================================================================


# VDD_TEST_OSC
addstripe -nets {VDD_TEST_OSC} -layer METAL4 -direction vertical -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 178 1787 193 1870.2]  
sroute -nets {VDD_TEST_OSC} 	-connect blockPin -block PADOSC_DVDD_OSC					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_TEST_OSC} 	-connect blockPin -block XOSC							 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
 
addstripe -nets {VSS} -layer METAL3 -direction horizontal -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 139.42 2145.355 268.54 2160.355]  

# VDD_OSC
addstripe -nets {VDD_OSC} -layer METAL1 -direction vertical -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 792.56 1675.515 807.56 1701.055]  

sroute -nets {VDD_OSC} 	-connect blockPin -block PADOSC_BW_VDD_OSC					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_OSC}		 	-connect blockPin -block XOSC							 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth




addstripe -nets {VSS} -layer METAL4 -direction horizontal -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 141.2 121.2 941.475 136.2]  
addstripe -nets {VSS} -layer METAL4 -direction vertical -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 141.2 121.61 156.42 2200]  
addstripe -nets {VDD_TEST} -layer METAL2 -direction vertical -width 5 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 491.56 1006 496.56 1190]    
addstripe -nets {VDD_TEST} -layer METAL4 -direction vertical -width 10 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 170 948.5 180 1192]  
addstripe -nets {VDD_TEST} -layer METAL1 -direction horizontal -width 7 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 170 1188 496.56 1192] 

sroute -nets {VSS VDD_TEST}  	-connect blockPin -block PAD_DVDD_LEFT					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}  	-connect blockPin -block XHRV_SCAN_RV3					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS}			    -connect blockPin -block XOSC							 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth


### VDD_TEST, VSS -  PAD 
#---main stripe
addstripe -nets {VDD_TEST} -layer METAL4 -direction horizontal -width 35 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 86.46 66.46 941.475 101.46]  
addstripe -nets {VDD_TEST} -layer METAL4 -direction vertical -width 35 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 86.46 66.46 121.46 1426.425]  
addstripe -nets {VDD_TEST_OSC} -layer METAL4 -direction vertical -width 35 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 86.46 1450 121.46 2000]  

addstripe -nets {VSS} -layer METAL4 -direction horizontal -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 141.2 121.2 941.475 136.2]  
addstripe -nets {VSS} -layer METAL4 -direction vertical -width 15 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 141.2 121.61 156.42 2000]  


# VDD_COMP_DFF POWER STRIPE
addstripe -nets {VDD_COMP_DFF} -layer METAL3 -direction vertical -width 5 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 862.73 1303.22 866.73 1333.22 ]  
sroute -nets {VDD_COMP_DFF}      -connect blockPin -block PAD_BW_VDD_COMP_DFF			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_COMP_DFF}      -connect blockPin -block XHVT_3						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth

addstripe -nets {VIN} -layer METAL3 -direction vertical -width 5 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 862.73 1219.155 866.73 1249.155]  
sroute -nets {VIN}               -connect blockPin -block PAD_BW_VIN					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VIN}               -connect blockPin -block XHVT_3						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth

addstripe -nets {VOUT} -layer METAL3 -direction vertical -width 4 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 860 1013 864 1043]  
sroute -nets {VOUT}               -connect blockPin -block PAD_BW_VOUT					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VOUT}               -connect blockPin -block XHVT_3						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth

addstripe -nets {VDD_CLK} -layer METAL3 -direction vertical -width 5 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 860 875 864 905]  
sroute -nets {VDD_CLK}            -connect blockPin -block PAD_BW_VDD_CLK				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_CLK}            -connect blockPin -block XHVT_3						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
 
addstripe -nets {VDD_CTRL} -layer METAL3 -direction vertical -width 5 -spacing 1 \
		-number_of_sets 1 -start_from bottom -area [list 860 730 864 760]  
sroute -nets {VDD_CTRL}            -connect blockPin -block PAD_BW_VDD_CTRL				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_CTRL}            -connect blockPin -block XHRV_CTRL					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_CTRL}            -connect blockPin -block XHVT_3						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth






sroute -nets {VDD_TEST}            -connect blockPin -block XHVT_3						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
 ### BLOCKS
sroute -nets {VSS}  	        -connect blockPin -block XHVT_3							 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VDD_CTRL}	        -connect blockPin -block XHVT_3							 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_CTRL}  	-connect blockPin -block XHRV_CTRL						 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}  	-connect blockPin -block XHRV_SCAN_RV3					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
#sroute -nets {VSS}  			-connect blockPin -block XOSC							 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
## Detection## Detection
sroute -nets {VSS VDD_TEST}  	-connect blockPin -block DETECTION_0					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}  	-connect blockPin -block DETECTION_1					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
## PAD Routing
sroute -nets {VSS VDD_TEST}     -connect blockPin -block PAD_VSS_LEFT					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}  	-connect blockPin -block PAD_DVDD_LEFT					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}     -connect blockPin -block PAD_VSS_BOTTOM					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}  	-connect blockPin -block PAD_DVDD_BOTTOM				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
### VDD_CTRL, VDD_CLK, VDD_COMP_DFF

#
### SCAN
sroute -nets {VSS VDD_TEST}	    -connect blockPin -block PAD_DIN_SCAN_DATA_IN			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}	    -connect blockPin -block PAD_DOUT_SCAN_DATA_OUT			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}	    -connect blockPin -block PAD_DIN_SCAN_LOAD_CHIP			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}	    -connect blockPin -block PAD_DIN_SCAN_LOAD_CHAIN		 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}	    -connect blockPin -block PAD_DIN_SCAN_PHI				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}	    -connect blockPin -block PAD_DIN_SCAN_PHI_BAR			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
#Din
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_TRIG					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_RENEW					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_CTRL_RESETN			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_R_VREF				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_R_VREF_GEN1			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_R_VREF_GEN2			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_R_VREF_GEN_DONE		 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DIN_EXT_CLK				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
#
sroute -nets {VSS VDD_TEST_OSC}	 -connect blockPin -block PADOSC_AIO_VCONT_BUF_OUT1		 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST_OSC}	 -connect blockPin -block PADOSC_AIO_VCONT_BUF_OUT0		 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST_OSC}	 -connect blockPin -block PADOSC_AIO_BIAS_AMP			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST_OSC}	 -connect blockPin -block PADOSC_AIO_OVR_VCONT			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_AIO_OVR_VREF				 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_AIO_BIAS_DELAY			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_AIO_NBODY					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_AIO_PBODY					 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
##DOUT
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DOUT_CLK_FREQ_DEC          -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST}		 -connect blockPin -block PAD_DOUT_CLK_FREQ_INC          -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
##createRouteBlk -box 0 0 95 1207  -layer {METAL1 METAL2 METAL4}	

sroute -nets {VSS VDD_TEST_OSC}  -connect blockPin -block PADOSC_DVDD_OSC 	  			 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST_OSC}  -connect blockPin -block PADOSC_DOUT_CLK_OUT         	 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST_OSC}  -connect blockPin -block PADOSC_DIN_S_OVR_VCONT      	 -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth
sroute -nets {VSS VDD_TEST_OSC}  -connect blockPin -block PADOSC_DIN_OSC_RESETN          -blockPin all -blockPinTarget nearestRingStripe -blockPinRouteWithPinWidth


