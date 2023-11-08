
# Multi-Core
setMultiCpuUsage -acquireLicense 4

# Allow manual footprint declarations in conf file
set dbgGPSAutoCellFunction 0

# VARIABLES
set TOP_LEVEL fabc_top 

# LOAD DESIGN LEF FILE
set init_lef_file {	/icas/kits/tsmc180/sc/tcb018gbwp7t_270a/Back_End/lef/tcb018gbwp7t_270a/lef/tcb018gbwp7t_6lm_utm40k.lef \
					/icas/projects/00_orientation/2018/lef/ESD_PAD_TSMC180.lef }


set init_verilog ${TOP_LEVEL}.v
set init_top_cell fadc_top

# POWER, GROUND NET DEFINE
set init_gnd_net VSS

# INITIATE DESIGN
init_design



#######################################   FLOORPLAN   ###########################################
# define appropriate size #
###########################

set CHIP_width      10000
set CHIP_height     10000
set left_offset     0
set right_offset    0
set top_offset      0
set bottom_offset   0

floorPlan -s $CHIP_width $CHIP_height $left_offset $right_offset $bottom_offset $top_offset
redraw
fit

#Cell  
placeInstance   XFadc_front      	        185  171.640   R0    -fixed

#PAD LOCATION

#LEFT
#placeInstance orientation R0 R90 R180 R270 MX MX90 MY MY90
placeInstance    PADOSC_AIO_VCONT_BUF_OUT1  20    1925      R90     -fixed
placeInstance    DETECTION_0			    102.3 77.47     R0      -fixed        
#BOTTOM
#?
#RIGHT
#?
#TOP
#?

redraw
fit           
           
#######################################   POWER ROUTING   ###########################################

# GLOBALNETCONNECT (POWER PIN CONNECTION DEFINE)
clearGlobalNets

#Globalnet all VDD, VSS power net setting
source ./${TOP_LEVEL}_globalnet.tcl

applyGlobalNets

#Place power stripes for SROUTE
source ./${TOP_LEVEL}_powerstripe.tcl


######################################## ADD METAL FILLER ###########################################
#

#####################################  AUTO SIGNAL ROUTING ##########################################

#Route set up

setNanoRouteMode -routeWithViaInPin true
setNanoRouteMode -routeWithViaOnlyForStandardCellPin false
setNanoRouteMode -routeWithTimingDriven true
setNanoRouteMode -routeWithSiDriven true
setNanoRouteMode -drouteAutoStop false
setNanoRouteMode -drouteUseMinSpacingForBlockage false
setNanoRouteMode -routeMergeSpecialWire true
setNanoRouteMode -drouteHonorStubRuleForBlockPin true
setNanoRouteMode -drouteUseMinSpacingForBlockage false
setNanoRouteMode -drouteUseMultiCutViaEffort high
setNanoRouteMode -routeTopRoutingLayer 4
setNanoRouteMode -routeBottomRoutingLayer 1
setNanoRouteMode -drouteElapsedtimeLimit 1 

#setNanoRouteMode -routeInsertAntennaDiode true
#setNanoRouteMode -routeAntennaCellName "ANTENNA"
placeDesign
globalDetailRoute
#optDesign -postRoute
#timeDesign -postRoute

saveDesign "${TOP_LEVEL}.floorplan.enc"
redraw
fit

verifyGeometry

# Save Design
#saveDesign "${TOP_LEVEL}.filled.routed.enc"
#deleteObstruction -all

# Output DEF, LEF and GDSII
set dbgLefDefOutVersion 5.5
defout ${TOP_LEVEL}.def  -placement -routing 
lefout ${TOP_LEVEL}.lef
saveNetlist -excludeLeafCell ${TOP_LEVEL}.apr.v
saveNetlist -excludeLeafCell -includePowerGround ${TOP_LEVEL}.apr.pg.v
streamOut ${TOP_LEVEL}.gds \
   -mapFile "/icas/kits/tsmc180/map/tsmc18.map" \
     -libName $TOP_LEVEL \
    -structureName $TOP_LEVEL \
    -stripes 1 \
    -units 2000 \
    -mode ALL

# Generate SDF
setExtractRCMode -detail -relative_c_th 0.01 -total_c_th 0.01 -noReduce -rcdb tap.db -specialNet
extractRC -outfile ${TOP_LEVEL}.cap
#rcOut -spf ${TOP_LEVEL}.spf
#rcOut -spef ${TOP_LEVEL}.spef
#rcOut -sdc ${TOP_LEVEL}.sdc
setUseDefaultDelayLimit 10000
delayCal -sdf ${TOP_LEVEL}.apr.sdf

# Run Geometry and Connection checks
verifyGeometry -reportAllCells -viaOverlap -report ${TOP_LEVEL}.geom.rpt
fixVia -minCut

# Meant for power vias that are just too small
verifyConnectivity -type all -noAntenna -report ${TOP_LEVEL}.conn.rpt


#cp ${TOP_LEVEL}.gds ..


puts "**************************************"
puts "*                                    *"
puts "* Encounter script finished          *"
puts "*                                    *"
puts "**************************************"






